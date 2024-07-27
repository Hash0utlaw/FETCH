import os
import asyncio
import logging
from dotenv import load_dotenv
from playwright.async_api import async_playwright
from moviepy.editor import VideoFileClip, concatenate_videoclips

# Constants
MAX_REELS = 10
SCROLL_ATTEMPTS = 5
WAIT_TIME = 20000  # 20 seconds in milliseconds
POPUP_WAIT_TIME = 5000  # 5 seconds in milliseconds
REEL_WAIT_TIME = 30000  # 30 seconds in milliseconds
MAX_SCROLL_ATTEMPTS = 10  # Limit the number of scrolling attempts

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def login_to_instagram(page, username, password):
    await page.goto("https://www.instagram.com/")
    logging.info("Loaded Instagram login page")
    
    await page.fill('input[name="username"]', username)
    await page.fill('input[name="password"]', password)
    
    await page.click('button[type="submit"]')
    
    await page.wait_for_load_state("networkidle")
    logging.info("Logged in successfully")

    await handle_popup(page, "text=Not Now", "login info prompt")

async def navigate_to_dms(page):
    try:
        # Wait for the DM button to be visible
        dm_button = await page.wait_for_selector('a[href="/direct/inbox/"]', state='visible', timeout=WAIT_TIME)
        
        # Try to click the button directly
        try:
            await dm_button.click(timeout=5000)
        except:
            # If direct click fails, try JavaScript click
            await page.evaluate('(element) => element.click()', dm_button)
        
        # Wait for navigation to complete
        await page.wait_for_load_state("networkidle")
        logging.info("Navigated to DM inbox")

        await handle_popup(page, "text=Not Now", "notification prompt")
    except Exception as e:
        logging.error(f"Error navigating to DMs: {str(e)}")
        # If navigation fails, try going to the DM URL directly
        await page.goto('https://www.instagram.com/direct/inbox/')
        await page.wait_for_load_state("networkidle")
        logging.info("Navigated to DM inbox using direct URL")

async def handle_popup(page, selector, popup_name):
    try:
        await page.click(selector, timeout=POPUP_WAIT_TIME)
        logging.info(f"Clicked 'Not Now' on {popup_name}")
    except:
        logging.info(f"No {popup_name} found or it disappeared quickly")

async def find_user_dm(page, target_username):
    logging.info(f"Searching for DM with user: {target_username}")
    
    for _ in range(SCROLL_ATTEMPTS):
        try:
            user_element = await page.wait_for_selector(f"text={target_username}", timeout=5000)
            await user_element.click()
            logging.info(f"Found and clicked on DM with {target_username}")
            return True
        except:
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)
    
    logging.warning(f"Could not find DM with user: {target_username}")
    return False

async def scroll_messages(page):
    logging.info("Attempting to scroll up in the message area")
    message_area = await page.wait_for_selector("div[role='grid']")
    
    for i in range(MAX_SCROLL_ATTEMPTS):
        # Get current scroll position
        current_scroll = await message_area.evaluate('element => element.scrollTop')
        
        # Scroll up
        await message_area.evaluate('element => element.scrollTo(0, element.scrollTop - element.clientHeight)')
        await asyncio.sleep(2)
        
        # Check new scroll position
        new_scroll = await message_area.evaluate('element => element.scrollTop')
        
        if new_scroll >= current_scroll:
            logging.info(f"Reached the top of the message thread after {i+1} attempts")
            break
        
        logging.info(f"Completed scroll {i+1}/{MAX_SCROLL_ATTEMPTS}")

async def wait_for_reel_viewer(page, timeout=REEL_WAIT_TIME):
    try:
        await page.wait_for_selector('video', timeout=timeout)
        return True
    except:
        return False

async def close_reel_viewer(page):
    try:
        await page.click("button[aria-label='Close']")
        logging.info("Closed the reel viewer")
    except:
        logging.info("Couldn't find close button, attempting to click outside")
        await page.mouse.click(0, 0)

async def download_video(page, video_url, reel_count):
    filename = f"reel_{reel_count}.mp4"
    async with page.context.new_page() as new_page:
        await new_page.goto(video_url)
        await new_page.wait_for_load_state("networkidle")
        await new_page.video.save_as(filename)
    if os.path.exists(filename) and os.path.getsize(filename) > 0:
        logging.info(f"Downloaded reel {reel_count}")
        return filename
    else:
        logging.error(f"Failed to download video for reel {reel_count}")
        return None

async def compile_videos(video_paths, output_path):
    if not video_paths:
        logging.warning("No videos to compile")
        return
    
    clips = [VideoFileClip(path) for path in video_paths]
    final_clip = concatenate_videoclips(clips)
    final_clip.write_videofile(output_path)
    logging.info(f"Compilation created successfully: {output_path}")

async def cleanup(video_paths):
    for path in video_paths:
        try:
            os.remove(path)
            logging.info(f"Removed temporary file: {path}")
        except Exception as e:
            logging.error(f"Failed to remove file {path}: {str(e)}")

async def download_reels(page, target_username, max_reels=MAX_REELS):
    video_paths = []
    reel_count = 0
    scroll_count = 0
    
    logging.info(f"Starting to look for reels in the DM with {target_username}")
    
    if not await find_user_dm(page, target_username):
        return video_paths
    
    await asyncio.sleep(10)
    
    reel_selectors = [
        "div[role='button']:has(div.xsgs5s9)",
        "div[role='button']:has(video)",
        "div._ab8w:has(div._aacl)",
        "div[data-visualcompletion='media-message']"  # Added this selector
    ]
    
    while reel_count < max_reels and scroll_count < MAX_SCROLL_ATTEMPTS:
        await scroll_messages(page)
        scroll_count += 1
        
        for selector in reel_selectors:
            potential_reels = await page.query_selector_all(selector)
            if potential_reels:
                logging.info(f"Found {len(potential_reels)} potential reel elements using selector: {selector}")
                for element in potential_reels:
                    try:
                        # Log the HTML content of the potential reel element
                        element_html = await page.evaluate('(element) => element.outerHTML', element)
                        logging.info(f"Potential reel element HTML: {element_html}")
                        
                        logging.info(f"Attempting to interact with potential reel {reel_count + 1}")
                        await element.scroll_into_view_if_needed()
                        await element.click()
                        if await wait_for_reel_viewer(page):
                            video_element = await page.query_selector('video')
                            if video_element:
                                video_url = await video_element.get_attribute('src')
                                logging.info(f"Found video URL: {video_url}")
                                
                                filename = await download_video(page, video_url, reel_count)
                                if filename:
                                    video_paths.append(filename)
                                    reel_count += 1
                                    if reel_count >= max_reels:
                                        return video_paths
                            else:
                                logging.warning("No video element found in reel viewer")
                        else:
                            logging.warning("Reel viewer did not load within the expected time")
                        
                        await close_reel_viewer(page)
                        
                        await asyncio.sleep(3)
                    except Exception as e:
                        logging.error(f"Error processing potential reel: {str(e)}")
                        continue
            else:
                logging.info(f"No potential reel elements found with selector: {selector}")
        
        if not potential_reels:
            logging.warning(f"No potential reel elements found after scroll attempt {scroll_count}")
    
    if reel_count == 0:
        logging.warning("No reels found or downloaded.")
    
    return video_paths

async def main():
    load_dotenv()
    username = os.getenv("INSTAGRAM_USERNAME")
    password = os.getenv("INSTAGRAM_PASSWORD")
    target_username = os.getenv("TARGET_USERNAME")
    
    if not username or not password or not target_username:
        logging.error("Instagram credentials or target username not found in environment variables")
        return
    
    async with async_playwright() as p:
        for browser_type in [p.chromium, p.firefox, p.webkit]:
            try:
                browser = await browser_type.launch(headless=False)
                logging.info(f"Successfully launched {browser_type.name}")
                break
            except Exception as e:
                logging.warning(f"Failed to launch {browser_type.name}: {str(e)}")
        else:
            logging.error("Failed to launch any browser. Please ensure at least one browser is installed.")
            return

        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            await login_to_instagram(page, username, password)
            await navigate_to_dms(page)
            video_paths = await download_reels(page, target_username)
            
            if video_paths:
                await compile_videos(video_paths, "compilation.mp4")
                await cleanup(video_paths)
            else:
                logging.info("No new reels to compile.")
        
        except Exception as e:
            logging.error(f"An error occurred in main execution: {str(e)}")
            await page.screenshot(path='error_screenshot.png')
            logging.info("Screenshot saved as error_screenshot.png")
        
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())