# FETCH

## Description
FETCH is a Python script designed to automate the process of downloading Instagram reels from direct messages (DMs). It uses Selenium WebDriver to interact with the Instagram web interface, allowing users to log in, navigate to a specific DM conversation, and download reels shared in that conversation.

## Features
- Automated Instagram login
- Navigation to a specific DM conversation
- Scrolling through messages to find reels
- Downloading multiple reels from a conversation
- Compiling downloaded reels into a single video file

## Prerequisites
Before you begin, ensure you have met the following requirements:
- Python 3.7+
- Chrome browser
- ChromeDriver (compatible with your Chrome version)

## Installation
1. Clone this repository:
   ```
   git clone https://github.com/Hash0utlaw/FETCH.git
   ```
2. Navigate to the project directory:
   ```
   cd FETCH
   ```
3. Install the required Python packages:
   ```
   pip install -r requirements.txt
   ```

## Configuration
1. Create a `.env` file in the project root directory.
2. Add the following lines to the `.env` file:
   ```
   INSTAGRAM_USERNAME=your_instagram_username
   INSTAGRAM_PASSWORD=your_instagram_password
   TARGET_USERNAME=username_to_fetch_reels_from
   ```

## Usage
Run the script using the following command:
```
python instagram_reel_scraper.py
```

The script will log in to Instagram, navigate to the specified DM conversation, download available reels, and compile them into a single video file.

## Contributing
Contributions to FETCH are welcome. Please feel free to submit a Pull Request.

## License
This project is licensed under the [MIT License](https://opensource.org/licenses/MIT).

## Disclaimer
This tool is for educational purposes only. Make sure you have the right to download and use the content as per Instagram's terms of service.