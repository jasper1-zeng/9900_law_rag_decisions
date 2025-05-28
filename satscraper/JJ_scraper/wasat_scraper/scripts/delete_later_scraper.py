#!/usr/bin/env python3
"""
scraper.py - Scrapes case metadata from WASAT website
Extracts case information and saves to CSV

This script crawls the Western Australia State Administrative Tribunal (WASAT) website,
extracts case metadata, and organizes the data into structured CSV files.

1. Modular structure with four distinct classes:
   - WasatInfrastructure: Basic setup like logging and HTTP
   - WasatMetadataCollector: Gets database stats and available years
   - WasatCaseScraper: Core scraping of case information
   - WasatRSSUpdater: RSS feed functionality
2. Independent operation modes:
   - run_full_scraper(): Complete scraping process
   - run_rss_update_only(): Just update RSS feeds, perfect for daily cron jobs
3. Command-line support:
   - python scraper.py: Run full scraping
   - python scraper.py rss: Run only RSS update

Author: Capstone Team 10A, Zhengxin Zeng
Date: 2025-04-05
"""

# Standard library imports
import os
import sys
import csv
import time
import re
import logging
from datetime import datetime

# Third-party library imports
import requests
from bs4 import BeautifulSoup

#------------------------------------------------------------------------------
# CONFIGURATION CONSTANTS
#------------------------------------------------------------------------------

# Define base paths directly (don't rely on config for initial setup)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)  # Go up one level from scripts/ to wasat_scraper/
DATA_DIR = os.path.join(BASE_DIR, "data")
RAW_DIR = os.path.join(DATA_DIR, "raw")
HTML_DIR = os.path.join(DATA_DIR, "html")
BY_YEAR_DIR = os.path.join(HTML_DIR, "by_year")
PARSED_DIR = os.path.join(DATA_DIR, "parsed")
LOG_DIR = os.path.join(BASE_DIR, "logs")
RSS_DIR = os.path.join(RAW_DIR, "rss_feeds")

# URLs and request settings
BASE_URL = "https://www.austlii.edu.au/cgi-bin/viewdb/au/cases/wa/WASAT/"
RSS_URL = "https://www.austlii.edu.au/cgi-bin/feed/au/cases/wa/WASAT/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/91.0.4472.124 Safari/537.36"
}
MAX_RETRIES = 3        # Maximum number of attempts for failed requests
RETRY_DELAY = 2        # Base delay in seconds before retry
REQUEST_TIMEOUT = 30   # Maximum time to wait for a response in seconds
PAUSE_BETWEEN_REQUESTS = 1  # Pause between requests to avoid overwhelming the server

# CSV settings
CASES_CSV = os.path.join(RAW_DIR, "wasat_cases_with_title_and_links.csv")
CSV_FIELDS = [
    'case_number',     # Unique identifier for the case
    'citation',        # Official citation format e.g. "[2023] WASAT 123"
    'title',           # Case title typically involving parties
    'decision_date',   # Date of the case decision in ISO format
    'url'              # URL to the full case document
]

#------------------------------------------------------------------------------
# INFRASTRUCTURE CLASS
#------------------------------------------------------------------------------

class WasatInfrastructure:
    """
    Handles basic infrastructure needs like logging, directories, and HTTP requests
    """
    
    @staticmethod
    def setup_logging():
        """
        Configure logging to file and console
        
        Sets up three logging handlers:
        1. A file handler for all logs (INFO and above)
        2. A file handler for errors only (ERROR and above)
        3. A console handler for all logs (INFO and above)
        
        Returns:
            logger: Configured logging object
        """
        # Create logs directory if it doesn't exist
        os.makedirs(LOG_DIR, exist_ok=True)
        
        log_file = os.path.join(LOG_DIR, "scrape_logs.txt")
        error_log_file = os.path.join(LOG_DIR, "error_logs.txt")
        
        # Configure root logger
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        
        # Clear existing handlers if any
        if logger.handlers:
            logger.handlers = []
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        
        # File handler for all logs
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        
        # File handler for errors only
        error_file_handler = logging.FileHandler(error_log_file)
        error_file_handler.setLevel(logging.ERROR)
        error_file_handler.setFormatter(formatter)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        
        # Add handlers to logger
        logger.addHandler(file_handler)
        logger.addHandler(error_file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    @staticmethod
    def create_basic_directories():
        """
        Create the minimum required directories for scraping
        
        Ensures all necessary directory structures exist before scraping starts.
        Creates multiple levels of directories for organizing scraped data.
        """
        directories = [
            DATA_DIR,           # Main data directory
            RAW_DIR,            # Raw data (CSVs, etc.)
            RSS_DIR,            # RSS feed archives
            HTML_DIR,           # HTML content
            BY_YEAR_DIR,        # Organized HTML by year
            os.path.join(PARSED_DIR, "json"),  # Parsed JSON data
            os.path.join(PARSED_DIR, "text"),  # Extracted text content
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    @staticmethod
    def fetch_page(url):
        """
        Fetch a web page with retry logic
        
        Attempts to retrieve HTML content from the provided URL with 
        exponential backoff on failures.
        
        Args:
            url (str): The URL to fetch
            
        Returns:
            str or None: HTML content if successful, None otherwise
        """
        max_retries = MAX_RETRIES
        for attempt in range(max_retries):
            try:
                response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
                response.raise_for_status()  # Raise exception for 4XX/5XX responses
                return response.text
            except requests.RequestException as e:
                logging.error(f"Error fetching {url}: {e}")
                if attempt < max_retries - 1:
                    wait_time = RETRY_DELAY * (2 ** attempt)  # Exponential backoff
                    logging.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logging.error(f"Failed to fetch {url} after {max_retries} attempts")
                    return None

#------------------------------------------------------------------------------
# METADATA COLLECTION CLASS
#------------------------------------------------------------------------------

class WasatMetadataCollector:
    """
    Collects metadata about the WASAT database and available data
    """
    
    def __init__(self):
        """Initialize the metadata collector"""
        self.infrastructure = WasatInfrastructure()
    
    def extract_db_stats(self, html):
        """
        Extract database statistics from the page
        
        Parses HTML to extract database metadata including last update date,
        most recent document, document count, and access statistics.
        
        Args:
            html (str): HTML content of the main page
            
        Returns:
            dict or None: Dictionary of extracted statistics if found, None otherwise
        """
        soup = BeautifulSoup(html, 'html.parser')

        # Find the database statistics section
        stats_section = soup.select_one('.side-statistics .db-stats')
        if not stats_section:
            logging.warning("Database statistics section not found")
            return None

        # Initialize stats dictionary
        stats = {
            'extraction_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'last_updated': None,
            'most_recent_document': None,
            'number_of_documents': None,
            'yearly_accesses': None
        }

        # Extract each statistic
        last_updated = stats_section.select_one('.last-updated strong')
        if last_updated:
            stats['last_updated'] = last_updated.text.strip()

        most_recent = stats_section.select_one('.most-recent strong')
        if most_recent:
            stats['most_recent_document'] = most_recent.text.strip()

        num_docs = stats_section.select_one('.number-docs strong')
        if num_docs:
            stats['number_of_documents'] = num_docs.text.strip().replace(',', '')

        yearly_access = stats_section.select_one('.accesses-yearly strong')
        if yearly_access:
            stats['yearly_accesses'] = yearly_access.text.strip().replace(',', '')

        return stats
    
    def extract_years(self, html):
        """
        Extract available years from the year dropdown
        
        Parses HTML to find all years for which case data is available.
        
        Args:
            html (str): HTML content of the main page
            
        Returns:
            list: List of years sorted in descending order (most recent first)
        """
        soup = BeautifulSoup(html, 'html.parser')

        # Find the year options list
        year_section = soup.select_one('.year-specific-options')
        if not year_section:
            logging.warning("Year options section not found")
            return []

        years = []
        # Look for all year links in the dropdown
        for year_link in year_section.select('li h5 a'):
            href = year_link.get('href', '')
            year_match = re.search(r'(\d{4})/?$', href)
            if year_match:
                years.append(year_match.group(1))

        return sorted(years, reverse=True)  # Most recent first
    
    def save_db_stats_to_csv(self, stats):
        """
        Save database statistics to CSV
        
        Args:
            stats (dict): Database statistics to save
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not stats:
            return False
            
        stats_csv = os.path.join(RAW_DIR, "wasat_db_stats.csv")
        with open(stats_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=stats.keys())
            writer.writeheader()
            writer.writerow(stats)
        logging.info(f"Saved database statistics to {os.path.relpath(stats_csv)}")
        return True
    
    def save_years_to_csv(self, years):
        """
        Save available years to CSV
        
        Args:
            years (list): List of years to save
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not years:
            return False
            
        years_csv = os.path.join(RAW_DIR, "wasat_available_years.csv")
        with open(years_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Year', 'URL'])
            for year in years:
                writer.writerow([year, f"{BASE_URL}{year}/"])
        logging.info(f"Saved {len(years)} available years to {os.path.relpath(years_csv)}")
        return True
    
    def collect_metadata(self):
        """
        Collect all metadata from the main page
        
        Returns:
            tuple: (stats, years) containing database stats and available years
        """
        # Fetch main page
        main_html = WasatInfrastructure.fetch_page(BASE_URL)
        if not main_html:
            logging.error("Failed to fetch main page")
            return None, []

        # Extract database stats
        stats = self.extract_db_stats(main_html)
        if stats:
            logging.info("Database Statistics:")
            for key, value in stats.items():
                logging.info(f"  {key}: {value}")
            self.save_db_stats_to_csv(stats)

        # Extract available years
        years = self.extract_years(main_html)
        if not years:
            logging.error("No years found on the main page")
            return stats, []

        logging.info(f"Found {len(years)} years: {', '.join(years)}")
        self.save_years_to_csv(years)
        
        return stats, years

#------------------------------------------------------------------------------
# CASE SCRAPER CLASS
#------------------------------------------------------------------------------

class WasatCaseScraper:
    """
    Handles the extraction of case data from WASAT website
    """
    
    def __init__(self):
        """Initialize the case scraper"""
        self.infrastructure = WasatInfrastructure()
    
    def extract_cases_by_year(self, year_url, year):
        """
        Extract case information from a specific year page
        
        Retrieves and parses all case listings for a given year, extracting
        metadata for each case including number, citation, title, and date.
        
        Args:
            year_url (str): URL for the specific year's case listing
            year (str): The year being processed
            
        Returns:
            list: List of dictionaries, each containing metadata for a single case
        """
        logging.info(f"Fetching cases for year {year} from {year_url}...")
        year_html = WasatInfrastructure.fetch_page(year_url)
        if not year_html:
            logging.error(f"Failed to fetch year page for {year}")
            return []

        soup = BeautifulSoup(year_html, 'html.parser')
        cases = []

        # Find all sections (each section is a month)
        month_sections = soup.select('div.all-section')

        for section in month_sections:
            # Extract all case links in this section
            case_links = section.select('div.card ul li')

            for li in case_links:
                link = li.select_one('a')
                if not link:
                    continue

                case_url = link.get('href', '')

                # Make sure the URL is absolute
                if case_url and not case_url.startswith('http'):
                    if case_url.startswith('/'):
                        case_url = f"https://www.austlii.edu.au{case_url}"
                    else:
                        case_url = f"https://www.austlii.edu.au/{case_url}"

                full_case_name = link.text.strip()
                
                # Extract case number using regex
                case_number_match = re.search(r'(\d+)\.html$', case_url)
                case_number = case_number_match.group(1) if case_number_match else "unknown"
                
                # Extract citation (e.g., "[2025] WASAT 2")
                citation_match = re.search(r'\[(\d{4})\]\s+WASAT\s+(\d+)', full_case_name)
                citation = citation_match.group(0) if citation_match else ""
                
                # Extract case title (everything before the citation)
                title = full_case_name
                if citation:
                    title_parts = full_case_name.split(citation)
                    title = title_parts[0].strip()
                
                # Extract case date from the name if available
                date_match = re.search(r'\((\d+\s+\w+\s+\d{4})\)$', full_case_name)
                case_date_text = date_match.group(1) if date_match else ""
                
                # Format the date to ISO format (YYYY-MM-DD)
                decision_date = ""
                if case_date_text:
                    try:
                        date_parts = case_date_text.split()
                        if len(date_parts) == 3:
                            day, month_name, year = date_parts
                            # List of full month names for date parsing
                            month_names = ["January", "February", "March", "April", "May", "June",
                                         "July", "August", "September", "October", "November", "December"]
                            try:
                                # Convert month name to number (1-12)
                                month_idx = month_names.index(month_name) + 1
                                # Format as YYYY-MM-DD with leading zeros
                                decision_date = f"{year}-{str(month_idx).zfill(2)}-{day.zfill(2)}"
                            except ValueError:
                                decision_date = ""
                    except (ValueError, IndexError):
                        decision_date = ""

                # Add case data to our collection
                cases.append({
                    'case_number': case_number,
                    'citation': citation,
                    'title': title,
                    'decision_date': decision_date,
                    'url': case_url
                })

        logging.info(f"Found {len(cases)} cases for year {year}")
        return cases
    
    def save_cases_to_csv(self, all_cases, csv_path=CASES_CSV):
        """
        Save cases to CSV file with optimized schema
        
        Writes the collected case metadata to a CSV file using the defined schema.
        
        Args:
            all_cases (list): List of case dictionaries to save
            csv_path (str): Path where the CSV file should be saved
            
        Returns:
            bool: True if saving was successful, False otherwise
        """
        if all_cases:
            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
                writer.writeheader()
                writer.writerows(all_cases)
            
            logging.info(f"Saved {len(all_cases)} cases to {os.path.relpath(csv_path)}")
            return True
        else:
            logging.warning("No cases found to save")
            return False
    
    def collect_all_cases(self, years=None):
        """
        Collect information about all cases across specified years
        
        Iterates through each year to collect case data and saves it to CSV.
        
        Args:
            years (list): List of years to scrape; if None, years are obtained from metadata
            
        Returns:
            list: Combined list of all cases across specified years
        """
        logging.info("Starting case collection...")
        all_cases = []
        
        # If no years provided, get them from metadata
        if not years:
            metadata_collector = WasatMetadataCollector()
            _, years = metadata_collector.collect_metadata()
            
        if not years:
            logging.error("No years available for scraping")
            return []

        # Make sure by_year directory exists
        os.makedirs(BY_YEAR_DIR, exist_ok=True)
        
        # For each year, extract case information
        for year in years:
            year_url = f"{BASE_URL}{year}/"
            year_cases = self.extract_cases_by_year(year_url, year)
            all_cases.extend(year_cases)

            # Create year directory in by_year structure if it doesn't exist
            year_dir = os.path.join(BY_YEAR_DIR, year)
            os.makedirs(year_dir, exist_ok=True)

            # Be nice to the server
            time.sleep(PAUSE_BETWEEN_REQUESTS)

        # Save all cases to CSV using the optimized schema
        self.save_cases_to_csv(all_cases, CASES_CSV)

        return all_cases

#------------------------------------------------------------------------------
# RSS FEED UPDATER CLASS
#------------------------------------------------------------------------------

class WasatRSSUpdater:
    """
    Handles fetching and processing of RSS feeds for updates
    """
    
    def __init__(self):
        """Initialize the RSS updater"""
        self.infrastructure = WasatInfrastructure()
        # Ensure the RSS directory exists
        os.makedirs(RSS_DIR, exist_ok=True)
    
    def fetch_rss_feeds(self):
        """
        Fetch the latest RSS feeds from AustLII
        
        Retrieves the current RSS feed containing recent case additions and updates.
        Saves both a latest version and a dated archive copy.
        
        Returns:
            bool: True if fetching and saving was successful, False otherwise
        """
        logging.info(f"Fetching RSS feed from {RSS_URL}")
        rss_content = WasatInfrastructure.fetch_page(RSS_URL)
        
        if rss_content:
            # Save the latest RSS feed
            latest_rss_path = os.path.join(RSS_DIR, "latest.xml")
            with open(latest_rss_path, 'w', encoding='utf-8') as f:
                f.write(rss_content)
            
            # Also save a dated copy for historical reference
            dated_rss_path = os.path.join(RSS_DIR, f"{datetime.now().strftime('%Y%m%d')}.xml")
            with open(dated_rss_path, 'w', encoding='utf-8') as f:
                f.write(rss_content)
            
            logging.info(f"Saved RSS feed to {os.path.relpath(latest_rss_path)} and {os.path.relpath(dated_rss_path)}")
            return True
        else:
            logging.error("Failed to fetch RSS feed")
            return False
    
    def process_rss_updates(self):
        """
        Process RSS feed to extract updates
        
        Can be extended to parse the RSS feed and identify new cases
        
        Returns:
            list: List of new cases found in the RSS feed
        """
        # This is a placeholder for future RSS processing logic
        # Could be expanded to parse the XML and extract new case information
        return []

#------------------------------------------------------------------------------
# MAIN EXECUTION
#------------------------------------------------------------------------------

def run_full_scraper():
    """Run the complete scraping process"""
    logging.info("Starting full WASAT case scraper")
    
    # Create infrastructure
    WasatInfrastructure.create_basic_directories()
    WasatInfrastructure.setup_logging()
    
    # Log basic info
    logging.info(f"Working directory: {os.getcwd()}")
    logging.info(f"Base directory: {BASE_DIR}")
    
    # Collect metadata
    metadata_collector = WasatMetadataCollector()
    stats, years = metadata_collector.collect_metadata()
    
    # Scrape cases
    case_scraper = WasatCaseScraper()
    all_cases = case_scraper.collect_all_cases(years)
    
    # Fetch RSS feeds
    rss_updater = WasatRSSUpdater()
    rss_updater.fetch_rss_feeds()
    
    # Log completion
    logging.info("Scraping complete")
    logging.info(f"Total cases collected: {len(all_cases)}")
    logging.info(f"Data saved to {os.path.abspath(CASES_CSV)}")
    
    return all_cases

def run_rss_update_only():
    """Run only the RSS feed update, suitable for daily cron jobs"""
    # Setup minimal infrastructure
    WasatInfrastructure.setup_logging()
    os.makedirs(RSS_DIR, exist_ok=True)
    
    logging.info("Starting RSS feed update only")
    
    # Fetch and process RSS feeds
    rss_updater = WasatRSSUpdater()
    success = rss_updater.fetch_rss_feeds()
    
    # Process updates (placeholder for future enhancement)
    # new_cases = rss_updater.process_rss_updates()
    
    logging.info("RSS update complete")
    return success

def main():
    """
    Main function to run the scraper
    
    Parse command-line arguments to determine which mode to run in:
    - 'full': Run the complete scraper
    - 'rss': Run only the RSS updater
    - No arguments: Run the complete scraper
    """
    # Check for command-line arguments
    if len(sys.argv) > 1 and sys.argv[1].lower() == 'rss':
        run_rss_update_only()
    else:
        run_full_scraper()

if __name__ == "__main__":
    main()