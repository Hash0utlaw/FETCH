import os
import time
import logging
import requests
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.common.action_chains import ActionChains
from moviepy.editor import VideoFileClip, concatenate_videoclips

# Constants
MAX_REELS = 10
SCROLL_ATTEMPTS = 5
WAIT_TIME = 20
POPUP_WAIT_TIME = 10
REEL_WAIT_TIME = 30

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def login_to_instagram(driver, username, password):
    driver.get("https://www.instagram.com/")
    logging.info("Loaded Instagram login page")
    
    username_input = WebDriverWait(driver, WAIT_TIME).until(EC.presence_of_element_located((By.NAME, "username")))
    password_input = WebDriverWait(driver, WAIT_TIME).until(EC.presence_of_element_located((By.NAME, "password")))
    
    username_input.send_keys(username)
    password_input.send_keys(password)
    
    login_button = WebDriverWait(driver, WAIT_TIME).until(EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']")))
    login_button.click()
    
    WebDriverWait(driver, 30).until(EC.url_contains("instagram.com/accounts/onetap/"))
    logging.info("Logged in successfully")

    handle_popup(driver, "//button[contains(text(), 'Not Now')]", "login info prompt")

def navigate_to_dms(driver):
    try:
        dm_button = WebDriverWait(driver, WAIT_TIME).until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, '/direct/inbox/')]"))
        )
        dm_button.click()
        WebDriverWait(driver, WAIT_TIME).until(EC.url_contains("/direct/inbox/"))
        logging.info("Navigated to DM inbox")

        handle_popup(driver, "//button[contains(text(), 'Not Now')]", "notification prompt")
    except Exception as e:
        logging.error(f"Error navigating to DMs: {str(e)}")

def handle_popup(driver, xpath, popup_name):
    try:
        button = WebDriverWait(driver, POPUP_WAIT_TIME).until(EC.element_to_be_clickable((By.XPATH, xpath)))
        button.click()
        logging.info(f"Clicked 'Not Now' on {popup_name}")
    except TimeoutException:
        logging.info(f"No {popup_name} found or it disappeared quickly")

def click_with_retry(driver, element, max_attempts=3):
    for attempt in range(max_attempts):
        try:
            driver.execute_script("arguments[0].click();", element)
            return True
        except StaleElementReferenceException:
            if attempt == max_attempts - 1:
                raise
            time.sleep(1)
    return False

def wait_for_reel_viewer(driver, timeout=10):
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.TAG_NAME, "video"))
        )
        return True
    except TimeoutException:
        return False

def find_user_dm(driver, target_username):
    logging.info(f"Searching for DM with user: {target_username}")
    
    for _ in range(SCROLL_ATTEMPTS):
        try:
            user_element = driver.find_element(By.XPATH, f"//span[contains(text(), '{target_username}')]")
            user_element.click()
            logging.info(f"Found and clicked on DM with {target_username}")
            return True
        except NoSuchElementException:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
    
    logging.warning(f"Could not find DM with user: {target_username}")
    return False
def download_reels(driver, target_username, max_reels=MAX_REELS):
    video_paths = []
    reel_count = 0
    
    logging.info(f"Starting to look for reels in the DM with {target_username}")
    
    if not find_user_dm(driver, target_username):
        return video_paths
    
    time.sleep(10)
    
    scroll_messages(driver)
    
    reel_xpaths = [
        "//div[contains(@role, 'button') and .//div[contains(@class, 'xsgs5s9')]]",
        "//div[contains(@role, 'button') and .//video]",
        "//div[contains(@class, '_ab8w') and .//div[contains(@class, '_aacl')]]"
    ]
    
    while reel_count < max_reels:
        potential_reels = []
        for xpath in reel_xpaths:
            potential_reels = driver.find_elements(By.XPATH, xpath)
            if potential_reels:
                logging.info(f"Found {len(potential_reels)} potential reel elements using xpath: {xpath}")
                break
        
        if not potential_reels:
            logging.warning("No potential reel elements found")
            break
        
        element = potential_reels[0]  # Always interact with the first element
        
        try:
            logging.info(f"Attempting to interact with potential reel {reel_count + 1}")
            if click_with_retry(driver, element):
                if wait_for_reel_viewer(driver):
                    video_elements = driver.find_elements(By.TAG_NAME, "video")
                    if video_elements:
                        video_url = video_elements[0].get_attribute('src')
                        logging.info(f"Found video URL: {video_url}")
                        
                        filename = download_video(video_url, reel_count)
                        if filename:
                            video_paths.append(filename)
                            reel_count += 1
                    else:
                        logging.warning("No video element found in reel viewer")
                else:
                    logging.warning("Reel viewer did not load within the expected time")
            else:
                logging.warning(f"Failed to click reel {reel_count + 1} after multiple attempts")
            
            close_reel_viewer(driver)
            
            time.sleep(3)
        
        except Exception as e:
            logging.error(f"Error processing potential reel: {str(e)}")
            continue
        
        # Log additional information
        logging.info(f"Current URL: {driver.current_url}")
        logging.info(f"Page title: {driver.title}")
        logging.info(f"Number of video elements: {len(driver.find_elements(By.TAG_NAME, 'video'))}")
    
    if reel_count == 0:
        logging.warning("No reels found or downloaded.")
    
    return video_paths

def scroll_messages(driver):
    logging.info("Attempting to scroll the message area")
    last_height = driver.execute_script("return document.body.scrollHeight")
    for i in range(SCROLL_ATTEMPTS):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
        logging.info(f"Completed scroll {i+1}/{SCROLL_ATTEMPTS}")

def download_video(video_url, reel_count):
    response = requests.get(video_url, stream=True)
    if response.status_code == 200:
        filename = f"reel_{reel_count}.mp4"
        with open(filename, 'wb') as file:
            for chunk in response.iter_content(chunk_size=1024*1024):
                if chunk:
                    file.write(chunk)
        logging.info(f"Downloaded reel {reel_count}")
        return filename
    else:
        logging.error(f"Failed to download video. Status code: {response.status_code}")
        return None

def close_reel_viewer(driver):
    close_buttons = driver.find_elements(By.XPATH, "//button[@aria-label='Close']")
    if close_buttons:
        driver.execute_script("arguments[0].click();", close_buttons[0])
        logging.info("Closed the reel viewer")
    else:
        logging.info("Couldn't find close button, attempting to click outside")
        action = ActionChains(driver)
        action.move_by_offset(0, 0).click().perform()

def log_error_state(driver):
    logging.error("Current URL: %s", driver.current_url)
    logging.error("Page source (first 1000 characters):")
    logging.error(driver.page_source[:1000])

def compile_videos(video_paths, output_path):
    if not video_paths:
        logging.warning("No videos to compile")
        return
    
    clips = [VideoFileClip(path) for path in video_paths]
    final_clip = concatenate_videoclips(clips)
    final_clip.write_videofile(output_path)
    logging.info(f"Compilation created successfully: {output_path}")

def cleanup(video_paths):
    for path in video_paths:
        try:
            os.remove(path)
            logging.info(f"Removed temporary file: {path}")
        except Exception as e:
            logging.error(f"Failed to remove file {path}: {str(e)}")

def main():
    load_dotenv()
    username = os.getenv("INSTAGRAM_USERNAME")
    password = os.getenv("INSTAGRAM_PASSWORD")
    target_username = os.getenv("TARGET_USERNAME")
    
    if not username or not password or not target_username:
        logging.error("Instagram credentials or target username not found in environment variables")
        return
    
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    driver = webdriver.Chrome(options=options)
    
    try:
        login_to_instagram(driver, username, password)
        navigate_to_dms(driver)
        video_paths = download_reels(driver, target_username)
        
        if video_paths:
            compile_videos(video_paths, "compilation.mp4")
            cleanup(video_paths)
        else:
            logging.info("No new reels to compile.")
    
    except Exception as e:
        logging.error(f"An error occurred in main execution: {str(e)}")
        driver.save_screenshot("error_screenshot.png")
        logging.info("Screenshot saved as error_screenshot.png")
    
    finally:
        driver.quit()

if __name__ == "__main__":
    main()