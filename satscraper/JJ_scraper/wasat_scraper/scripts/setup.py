#!/usr/bin/env python3
"""
setup.py - Initial setup for WASAT scraper project
Creates necessary directories and configuration files
"""

import os
import sys
import logging
import argparse
import json
from datetime import datetime

# Base configuration
BASE_DIR = "wasat_scraper"
DATA_DIR = os.path.join(BASE_DIR, "data")
RAW_DIR = os.path.join(DATA_DIR, "raw")
HTML_DIR = os.path.join(DATA_DIR, "html")
BY_YEAR_DIR = os.path.join(HTML_DIR, "by_year")
PARSED_DIR = os.path.join(DATA_DIR, "parsed")
LOG_DIR = os.path.join(BASE_DIR, "logs")
DB_DIR = os.path.join(BASE_DIR, "db")
SCRIPTS_DIR = os.path.join(BASE_DIR, "scripts")

def setup_logging():
    """Configure logging to file and console"""
    os.makedirs(LOG_DIR, exist_ok=True)
    
    log_file = os.path.join(LOG_DIR, "setup_logs.txt")
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Clear existing handlers if any
    if logger.handlers:
        logger.handlers = []
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def create_directory_structure():
    """Create all necessary directories for the project"""
    directories = [
        BASE_DIR,
        DATA_DIR,
        RAW_DIR,
        os.path.join(RAW_DIR, "rss_feeds"),
        HTML_DIR,
        BY_YEAR_DIR,
        PARSED_DIR,
        os.path.join(PARSED_DIR, "json"),
        os.path.join(PARSED_DIR, "text"),
        SCRIPTS_DIR,
        LOG_DIR,
        DB_DIR
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logging.info(f"Created directory: {directory}")
    
    logging.info("Directory structure created successfully")

def create_config_file():
    """Create the config.py file with project settings"""
    config_path = os.path.join(BASE_DIR, "config.py")
    
    if os.path.exists(config_path):
        logging.info(f"Config file already exists at {config_path}")
        return
    
    config_content = """import os

# Base configuration
BASE_DIR = "wasat_scraper"
DATA_DIR = os.path.join(BASE_DIR, "data")
RAW_DIR = os.path.join(DATA_DIR, "raw")
HTML_DIR = os.path.join(DATA_DIR, "html")
BY_YEAR_DIR = os.path.join(HTML_DIR, "by_year")
PARSED_DIR = os.path.join(DATA_DIR, "parsed")
LOG_DIR = os.path.join(BASE_DIR, "logs")
DB_DIR = os.path.join(BASE_DIR, "db")

# File paths
DB_PATH = os.path.join(DB_DIR, "cases.db")
CASES_CSV = os.path.join(RAW_DIR, "wasat_cases.csv")
RSS_DIR = os.path.join(RAW_DIR, "rss_feeds")
LATEST_RSS = os.path.join(RSS_DIR, "latest.xml")

# URLs
BASE_URL = "https://www.austlii.edu.au/cgi-bin/viewdb/au/cases/wa/WASAT/"
RSS_URL = "https://www.austlii.edu.au/cgi-bin/feed/au/cases/wa/WASAT/"

# HTTP request settings
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/91.0.4472.124 Safari/537.36"
}
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds
REQUEST_TIMEOUT = 30  # seconds

# Scraper settings
PAUSE_BETWEEN_REQUESTS = 1  # seconds

# CSV Schema
CSV_FIELDS = [
    'case_number',
    'citation',
    'title',
    'decision_date',
    'url'
]
"""

    with open(config_path, 'w') as f:
        f.write(config_content)
    
    logging.info(f"Created config file at {config_path}")

def create_readme():
    """Create a README.md file with project documentation"""
    readme_path = os.path.join(BASE_DIR, "README.md")
    
    if os.path.exists(readme_path):
        logging.info(f"README already exists at {readme_path}")
        return
    
    readme_content = """# WASAT Case Scraper

A tool for scraping, downloading, and parsing cases from the Western Australia State Administrative Tribunal.

## Directory Structure

```
wasat_scraper/
├── data/
│   ├── raw/
│   │   ├── wasat_cases.csv
│   │   └── rss_feeds/         # Store RSS feed data
│   │       └── latest.xml     # Most recent RSS feed
│   ├── html/
│   │   └── by_year/           # Organized by year
│   │       ├── 2001/
│   │       │   ├── 12345.html # Named by case number only
│   │       │   └── ...
│   │       └── ...
│   └── parsed/                # For your parsed data output
│       ├── json/              # Structured data
│       └── text/              # Extracted text content
├── scripts/
│   ├── wasat_case_manager.py            # Case metadata manager
│   ├── html_downloader.py    # Downloads HTML content
│   ├── parser.py             # Parses HTML into structured data
│   └── rss_monitor.py        # Monitors RSS for updates
├── logs/
│   ├── scrape_logs.txt
│   ├── download_logs.txt
│   └── error_logs.txt
├── db/
│   └── cases.db              # SQLite database to track what's been scraped
├── config.py                 # Configuration settings
├── requirements.txt
└── README.md
```

## Usage

1. Initial Setup:
   ```
   python setup.py
   ```

2. Collect case metadata:
   ```
   python scripts/wasat_case_manager.py
   ```

3. Download HTML content:
   ```
   python scripts/html_downloader.py
   ```

4. Parse HTML content:
   ```
   python scripts/parser.py
   ```

5. Monitor for updates:
   ```
   python scripts/rss_monitor.py
   ```

## Requirements

- Python 3.7+
- BeautifulSoup4
- Requests
- [other dependencies]

## License

[Your license information]
"""
    
    with open(readme_path, 'w') as f:
        f.write(readme_content)
    
    logging.info(f"Created README file at {readme_path}")

def create_requirements():
    """Create requirements.txt file"""
    req_path = os.path.join(BASE_DIR, "requirements.txt")
    
    if os.path.exists(req_path):
        logging.info(f"Requirements file already exists at {req_path}")
        return
    
    requirements = [
        "requests>=2.28.0",
        "beautifulsoup4>=4.11.0",
        "pandas>=1.4.0",
        "lxml>=4.8.0"
    ]
    
    with open(req_path, 'w') as f:
        f.write("\n".join(requirements))
    
    logging.info(f"Created requirements file at {req_path}")

def main():
    """Main setup function"""
    parser = argparse.ArgumentParser(description="Setup for WASAT scraper project")
    parser.add_argument('--force', action='store_true', help='Force recreation of files even if they exist')
    args = parser.parse_args()
    
    # Setup logging
    logger = setup_logging()
    logging.info("Starting WASAT scraper setup")
    
    # Create directory structure
    create_directory_structure()
    
    # Create configuration files
    create_config_file()
    create_readme()
    create_requirements()
    
    logging.info("Setup complete")
    logging.info(f"Project initialized at {os.path.abspath(BASE_DIR)}")
    logging.info("Run 'pip install -r wasat_scraper/requirements.txt' to install dependencies")
    logging.info("Then run 'python wasat_scraper/scripts/wasat_case_manager.py' to start collecting case data")

if __name__ == "__main__":
    main()