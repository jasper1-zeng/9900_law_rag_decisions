import os

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
