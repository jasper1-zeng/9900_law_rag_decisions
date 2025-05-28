#!/usr/bin/env python3
"""
html_downloader.py - HTML Content Downloader for WASAT Cases

This module downloads HTML content for court cases from the Western Australia
State Administrative Tribunal (WASAT) website. It uses case metadata from a CSV
file to identify URLs, downloads the content, and saves it in an organized 
directory structure by year and case number.

Features:
- Concurrent downloads with configurable parallelism
- Robust error handling and retry logic
- Content validation and extraction
- Detailed logging and progress tracking
- Disk space verification
- Support for downloading only new cases

Usage:
  python html_downloader.py --limit N --workers N --new-only

Author: Capstone Team 10A, Zhengxin Zeng
Date: 2025-04-06
"""

# Standard library imports
import os
import sys
import csv
import time
import logging
import traceback
import argparse
import shutil
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# Third-party library imports
import requests
from bs4 import BeautifulSoup

#------------------------------------------------------------------------------
# CONFIGURATION CONSTANTS
#------------------------------------------------------------------------------

# Define base paths directly
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)  # Go up one level from scripts/ to wasat_scraper/
DATA_DIR = os.path.join(BASE_DIR, "data")
RAW_DIR = os.path.join(DATA_DIR, "raw")
HTML_DIR = os.path.join(DATA_DIR, "html")
BY_YEAR_DIR = os.path.join(HTML_DIR, "by_year")
PARSED_DIR = os.path.join(DATA_DIR, "parsed")
LOG_DIR = os.path.join(BASE_DIR, "logs")
CASES_CSV = os.path.join(RAW_DIR, "wasat_cases_with_title_and_links.csv")

# Create essential directories if they don't exist
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(BY_YEAR_DIR, exist_ok=True)

# HTTP request settings
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/91.0.4472.124 Safari/537.36"
}
MAX_RETRIES = 3           # Maximum number of retry attempts for failed requests
RETRY_DELAY = 2           # Base delay in seconds before retry (exponential backoff)
REQUEST_TIMEOUT = 30      # Seconds to wait before timing out a request
MAX_WORKERS = 5           # Number of concurrent downloads
PAUSE_BETWEEN_REQUESTS = 1  # Seconds to wait between requests (rate limiting)

#------------------------------------------------------------------------------
# INFRASTRUCTURE CLASS
#------------------------------------------------------------------------------

class WasatInfrastructure:
    """
    Handles basic infrastructure needs for HTML downloading
    """
    
    @staticmethod
    def setup_logging():
        """
        Configure logging to file and console with detailed error tracking
        
        Sets up multiple log handlers:
        1. Standard log file for general information
        2. Error log file for detailed error tracking
        3. Debug log file for verbose diagnostics
        4. Failed cases log for tracking problem cases
        5. Console handler for real-time feedback
        
        Returns:
            logger: Configured logging object
        """
        log_file = os.path.join(LOG_DIR, "download_logs.txt")
        error_log_file = os.path.join(LOG_DIR, "error_logs.txt")
        debug_log_file = os.path.join(LOG_DIR, "debug_logs.txt")
        failed_cases_log_file = os.path.join(LOG_DIR, "failed_cases.txt")
        
        # Configure root logger
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)  # Capture all levels
        
        # Clear existing handlers if any
        if logger.handlers:
            logger.handlers = []
        
        # Create formatters
        standard_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        detailed_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')
        
        # File handlers
        handlers = [
            # Standard log file
            logging.FileHandler(log_file, encoding='utf-8'),
            # Error log file
            logging.FileHandler(error_log_file, encoding='utf-8'),
            # Debug log file
            logging.FileHandler(debug_log_file, encoding='utf-8'),
            # Failed cases log file
            logging.FileHandler(failed_cases_log_file, encoding='utf-8')
        ]
        
        # Configure log levels and formatters
        handlers[0].setLevel(logging.INFO)
        handlers[0].setFormatter(standard_formatter)
        
        handlers[1].setLevel(logging.ERROR)
        handlers[1].setFormatter(detailed_formatter)
        
        handlers[2].setLevel(logging.DEBUG)
        handlers[2].setFormatter(detailed_formatter)
        
        handlers[3].setLevel(logging.WARNING)
        handlers[3].setFormatter(standard_formatter)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(standard_formatter)
        
        # Add handlers to logger
        for handler in handlers + [console_handler]:
            logger.addHandler(handler)
        
        return logger
    
    @staticmethod
    def create_basic_directories():
        """
        Create the minimum required directories for downloading
        
        Ensures all necessary directory structures exist before downloading begins.
        Creates parent directories if they don't exist.
        """
        directories = [
            DATA_DIR,           # Main data directory
            RAW_DIR,            # Raw data (CSVs, etc.)
            HTML_DIR,           # HTML content 
            BY_YEAR_DIR,        # Organized HTML by year
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)

#------------------------------------------------------------------------------
# DATA MANAGER CLASS
#------------------------------------------------------------------------------

class WasatDataManager:
    """
    Handles loading and managing case data for downloading
    """
    
    def __init__(self, csv_path=CASES_CSV):
        """
        Initialize with the path to the cases CSV file
        
        Args:
            csv_path (str): Path to the CSV file containing case metadata
        """
        self.csv_path = csv_path
        self.cases = []
    
    def read_case_data(self):
        """
        Read cases from CSV file
        
        Loads case metadata from the CSV file specified by csv_path.
        
        Returns:
            list: List of dictionaries, each containing metadata for a single case.
                 Empty list if file not found or error occurs.
        """
        if not os.path.exists(self.csv_path):
            logging.error(f"Case data file not found: {self.csv_path}")
            return []
        
        cases = []
        try:
            with open(self.csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    cases.append(row)
            
            logging.info(f"Read {len(cases)} cases from CSV file")
            self.cases = cases
            return cases
        except Exception as e:
            logging.error(f"Error reading case data: {e}")
            logging.error(traceback.format_exc())
            return []
    
    def filter_new_cases(self):
        """
        Filter the list of cases to include only those that haven't been downloaded yet
        
        Returns:
            list: List of cases that don't have corresponding HTML files
        """
        if not self.cases:
            self.read_case_data()
        
        new_cases = []
        for case in self.cases:
            case_number = case.get('case_number')
            year = self._extract_year_from_case(case)
            
            # Check if file already exists
            year_dir = os.path.join(BY_YEAR_DIR, year)
            file_path = os.path.join(year_dir, f"{case_number}.html")
            
            if not os.path.exists(file_path):
                new_cases.append(case)
        
        logging.info(f"Found {len(new_cases)} new cases that need downloading")
        return new_cases
    
    def _extract_year_from_case(self, case):
        """
        Extract the year from a case record
        
        Args:
            case (dict): Case metadata dictionary
            
        Returns:
            str: Year as a string, or current year if not found
        """
        # Try to extract year from citation or decision_date
        year = None
        citation = case.get('citation', '')
        if citation:
            # Extract year from citation format like "[2023] WASAT 123"
            citation_match = citation.strip('[]').split('] ')[0]
            if citation_match.isdigit():
                year = citation_match
        
        if not year and case.get('decision_date'):
            # Extract year from ISO date format (YYYY-MM-DD)
            year = case.get('decision_date').split('-')[0]
        
        if not year:
            # Use current year as fallback
            year = str(datetime.now().year)
            
        return year

#------------------------------------------------------------------------------
# HTML FETCHER CLASS
#------------------------------------------------------------------------------

class WasatHTMLFetcher:
    """
    Handles fetching HTML content from URLs with robust error handling
    """
    
    def __init__(self, headers=HEADERS, timeout=REQUEST_TIMEOUT, retries=MAX_RETRIES, retry_delay=RETRY_DELAY):
        """
        Initialize fetcher with HTTP settings
        
        Args:
            headers (dict): HTTP headers for requests
            timeout (int): Request timeout in seconds
            retries (int): Maximum number of retry attempts
            retry_delay (int): Base delay between retries in seconds
        """
        self.headers = headers
        self.timeout = timeout
        self.max_retries = retries
        self.retry_delay = retry_delay
    
    def fetch_html(self, url):
        """
        Fetch HTML content with retry logic and enhanced error handling
        
        Requests the URL and handles various error conditions including:
        - HTTP errors (404, 500, etc.)
        - Network timeouts
        - Encoding issues
        - Connection problems
        
        Args:
            url (str): The URL to fetch
            
        Returns:
            str or None: HTML content if successful, None otherwise
        """
        for attempt in range(self.max_retries):
            try:
                # Make the HTTP request
                response = requests.get(url, headers=self.headers, timeout=self.timeout)
                
                # Check for specific HTTP errors
                if response.status_code == 404:
                    logging.error(f"URL not found (404): {url}")
                    logging.warning(f"Failed Case URL: {url}")
                    return None
                
                # Raise exception for other HTTP errors
                response.raise_for_status()
                
                # Detect and log encoding
                detected_encoding = response.encoding or 'utf-8'
                logging.debug(f"Detected encoding for {url}: {detected_encoding}")
                
                # Attempt to decode with robust error handling
                try:
                    # Try to get text with detected encoding, fallback to utf-8 with replacement
                    text = response.content.decode(detected_encoding, errors='replace')
                except Exception as e:
                    logging.warning(f"Encoding error for {url}: {e}. Falling back to utf-8 with replacement.")
                    text = response.content.decode('utf-8', errors='replace')
                
                logging.debug(f"Content length for {url}: {len(text)} characters")
                return text
            
            except requests.RequestException as e:
                logging.error(f"Request attempt {attempt + 1} failed for {url}: {e}")
                
                # Additional diagnostic information on failure
                try:
                    # Try a HEAD request to check if server is responding
                    head_response = requests.head(url, headers=self.headers, timeout=self.timeout)
                    logging.error(f"HEAD request status for {url}: {head_response.status_code}")
                except Exception as head_error:
                    logging.error(f"Error checking HEAD for {url}: {head_error}")
                
                # Implement exponential backoff
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    time.sleep(wait_time)
                else:
                    # All attempts failed
                    logging.error(f"All fetch attempts failed for {url}")
                    logging.warning(f"Failed Case URL: {url}")
                    return None

#------------------------------------------------------------------------------
# CONTENT EXTRACTOR CLASS
#------------------------------------------------------------------------------

class WasatContentExtractor:
    """
    Handles extracting and processing HTML content
    """
    
    def extract_article_content(self, html_content):
        """
        Extract article content from HTML
        
        Parses the full HTML page and extracts just the article/document content
        for cleaner storage and processing.
        
        Args:
            html_content (str): Full HTML content from the webpage
            
        Returns:
            str or None: Extracted article content if found, None otherwise
        """
        try:
            # Parse HTML content
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find the main article element
            article = soup.select_one('article.the-document')
            
            if article:
                # Convert to string with robust encoding
                article_str = str(article)
                logging.debug(f"Article content length: {len(article_str)}")
                logging.debug(f"Article content snippet: {article_str[:500]}")
                
                return article_str
            else:
                # Log detailed information about the HTML
                logging.error("No article found. HTML content length: %d", len(html_content))
                logging.debug(f"HTML content snippet: {html_content[:1000]}")
                return None
        except Exception as e:
            logging.error(f"Error extracting article content: {e}")
            logging.error(traceback.format_exc())
            return None

#------------------------------------------------------------------------------
# FILE MANAGER CLASS
#------------------------------------------------------------------------------

class WasatFileManager:
    """
    Handles file operations for saving HTML content
    """
    
    def save_html(self, content, case_number, year):
        """
        Save HTML content with enhanced unicode and error handling
        
        Performs extensive validation before saving:
        - Validates content is not empty
        - Ensures proper encoding
        - Checks write permissions
        - Verifies available disk space
        - Creates necessary directories
        
        Args:
            content (str): HTML content to save
            case_number (str): Unique identifier for the case
            year (str): Year of the case decision for directory organization
            
        Returns:
            bool: True if save was successful, False otherwise
        """
        # Validate content
        if not content:
            logging.error(f"No content to save for case {case_number}")
            logging.warning(f"Failed Save Case: {case_number}")
            return False
        
        # Ensure content is a string with proper encoding
        try:
            # Replace unsupported characters and ensure valid UTF-8
            content_str = str(content).encode('utf-8', errors='replace').decode('utf-8')
        except Exception as e:
            logging.error(f"Failed to process content for case {case_number}: {e}")
            logging.warning(f"Failed Save Case: {case_number}")
            return False
        
        # Create year directory if it doesn't exist
        year_dir = os.path.join(BY_YEAR_DIR, year)
        try:
            os.makedirs(year_dir, exist_ok=True)
        except Exception as e:
            logging.error(f"Failed to create directory {year_dir}: {e}")
            logging.warning(f"Failed Save Case: {case_number}")
            return False
        
        # Prepare file path
        year_path = os.path.join(year_dir, f"{case_number}.html")
        
        # Attempt to save file with detailed error handling
        try:
            # Check directory permissions
            if not os.access(year_dir, os.W_OK):
                logging.error(f"No write permission for directory {year_dir}")
                logging.warning(f"Failed Save Case: {case_number}")
                return False
            
            # Check file size
            if len(content_str) == 0:
                logging.error(f"Attempting to save empty content for case {case_number}")
                logging.warning(f"Failed Save Case: {case_number}")
                return False
            
            # Check available disk space
            total, used, free = shutil.disk_usage(year_dir)
            content_size = len(content_str.encode('utf-8', errors='replace'))
            
            if content_size > free:
                logging.error(f"Insufficient disk space to save case {case_number}. Content size: {content_size}, Free space: {free}")
                logging.warning(f"Failed Save Case: {case_number}")
                return False
            
            # Save file with robust encoding
            with open(year_path, 'w', encoding='utf-8', errors='replace') as f:
                f.write(content_str)
            
            # Verify file was written
            if not os.path.exists(year_path):
                logging.error(f"File was not created for case {case_number}")
                logging.warning(f"Failed Save Case: {case_number}")
                return False
            
            logging.info(f"Successfully saved case {case_number} to {year_path}")
            return True
        
        except Exception as e:
            logging.error(f"Unexpected error saving case {case_number}: {e}")
            logging.error(traceback.format_exc())
            logging.warning(f"Failed Save Case: {case_number}")
            return False

#------------------------------------------------------------------------------
# CASE PROCESSOR CLASS
#------------------------------------------------------------------------------

class WasatCaseProcessor:
    """
    Orchestrates the process of downloading and saving case HTML content
    """
    
    def __init__(self):
        """Initialize with component classes"""
        self.fetcher = WasatHTMLFetcher()
        self.extractor = WasatContentExtractor()
        self.file_manager = WasatFileManager()
        self.data_manager = WasatDataManager()
    
    def process_case(self, case):
        """
        Process a single case (fetch and save)
        
        Complete workflow for a single case:
        1. Extract case metadata
        2. Determine target year/directory
        3. Check if already downloaded
        4. Fetch HTML content
        5. Extract article content
        6. Save to appropriate location
        
        Args:
            case (dict): Dictionary containing case metadata
            
        Returns:
            bool: True if processing was successful, False otherwise
        """
        case_number = case.get('case_number')
        url = case.get('url')
        
        # Validate URL
        if not url:
            logging.error(f"No URL found for case {case_number}")
            logging.warning(f"Failed Case: {case_number}")
            return False
        
        # Extensive logging for diagnostics
        logging.info(f"Processing case {case_number} from URL: {url}")
        
        # Extract year from case
        year = self.data_manager._extract_year_from_case(case)
        
        # Check if file already exists
        year_dir = os.path.join(BY_YEAR_DIR, year)
        file_path = os.path.join(year_dir, f"{case_number}.html")
        
        if os.path.exists(file_path):
            logging.info(f"Case {case_number} already downloaded, skipping")
            return True
        
        # Fetch the HTML
        html_content = self.fetcher.fetch_html(url)
        if not html_content:
            logging.error(f"Failed to fetch HTML for case {case_number} (URL: {url})")
            logging.warning(f"Failed Case: {case_number}")
            return False
        
        # Extract article content
        article_content = self.extractor.extract_article_content(html_content)
        if not article_content:
            logging.error(f"Failed to extract article content for case {case_number}")
            logging.warning(f"Failed Case: {case_number}")
            return False
        
        # Save the HTML
        if self.file_manager.save_html(article_content, case_number, year):
            logging.info(f"Successfully saved case {case_number} (year {year})")
            return True
        else:
            logging.error(f"Failed to save case {case_number}")
            logging.warning(f"Failed Case: {case_number}")
            return False
    
    def download_all_cases(self, cases, max_workers=MAX_WORKERS):
        """
        Download all cases with a thread pool
        
        Uses concurrent execution to download multiple cases simultaneously.
        Tracks progress and reports statistics.
        
        Args:
            cases (list): List of case dictionaries to process
            max_workers (int): Maximum number of concurrent downloads
            
        Returns:
            tuple: (successful, failed) counts of case processing results
        """
        total_cases = len(cases)
        successful = 0
        failed = 0
        
        logging.info(f"Starting download of {total_cases} cases with {max_workers} workers")
        
        if max_workers > 1:
            # Use ThreadPoolExecutor for concurrent downloads
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all tasks
                future_to_case = {executor.submit(self.process_case, case): case for case in cases}
                
                # Process results as they complete
                for future in as_completed(future_to_case):
                    case = future_to_case[future]
                    try:
                        if future.result():
                            successful += 1
                        else:
                            failed += 1
                    except Exception as e:
                        logging.error(f"Error processing case {case.get('case_number')}: {e}")
                        failed += 1
                    
                    # Log progress
                    completed = successful + failed
                    if completed % 10 == 0 or completed == total_cases:
                        logging.info(f"Progress: {completed}/{total_cases} cases processed ({successful} successful, {failed} failed)")
        else:
            # Sequential processing
            for i, case in enumerate(cases):
                if self.process_case(case):
                    successful += 1
                else:
                    failed += 1
                
                # Log progress
                completed = i + 1
                if completed % 10 == 0 or completed == total_cases:
                    logging.info(f"Progress: {completed}/{total_cases} cases processed ({successful} successful, {failed} failed)")
                
                # Be nice to the server
                time.sleep(PAUSE_BETWEEN_REQUESTS)
        
        logging.info(f"Download complete: {successful} successful, {failed} failed")
        return successful, failed

#------------------------------------------------------------------------------
# MAIN EXECUTION
#------------------------------------------------------------------------------

def run_html_downloader(limit=None, workers=MAX_WORKERS, new_only=False):
    """
    Run the HTML downloader
    
    Args:
        limit (int): Optional limit on number of cases to process
        workers (int): Number of concurrent workers
        new_only (bool): If True, only download cases that don't exist yet
        
    Returns:
        tuple: (successful, failed) counts
    """
    # Create essential directories
    WasatInfrastructure.create_basic_directories()
    
    # Set up logging
    WasatInfrastructure.setup_logging()
    
    mode_str = "new cases only" if new_only else "all cases"
    logging.info(f"Starting WASAT HTML downloader ({mode_str})")
    
    # Create processor
    processor = WasatCaseProcessor()
    
    # Read case data
    data_manager = WasatDataManager()
    cases = data_manager.read_case_data()
    
    if not cases:
        logging.error("No cases to download. Run wasat_case_manager.py first.")
        return 0, 0
    
    # Filter for new cases if requested
    if new_only:
        cases = data_manager.filter_new_cases()
        if not cases:
            logging.info("No new cases to download. All existing cases are already downloaded.")
            return 0, 0
    
    # Apply limit if specified
    if limit and limit > 0:
        cases = cases[:limit]
        logging.info(f"Limited to downloading {limit} cases for testing")
    
    # Download cases
    successful, failed = processor.download_all_cases(cases, max_workers=workers)
    
    # Final summary
    logging.info("HTML download completed")
    logging.info(f"Total cases processed: {len(cases)}")
    logging.info(f"Successfully downloaded: {successful}")
    logging.info(f"Failed to download: {failed}")
    
    # Additional logging for failed cases
    if failed > 0:
        logging.warning("Check 'logs/failed_cases.txt' for details of failed downloads")
    
    return successful, failed

def main():
    """
    Main function for the HTML downloader
    
    Command-line entry point that orchestrates the HTML download process:
    1. Parse arguments
    2. Set up environment
    3. Read case data
    4. Download HTML content
    5. Report results
    """
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Download HTML content for WASAT cases")
    parser.add_argument('--limit', type=int, help='Limit the number of cases to download (for testing)')
    parser.add_argument('--workers', type=int, default=MAX_WORKERS, 
                        help=f'Number of concurrent downloads (default: {MAX_WORKERS})')
    parser.add_argument('--new-only', action='store_true',
                        help='Only download cases that have not been downloaded yet')
    args = parser.parse_args()
    
    # Run the downloader with the specified options
    run_html_downloader(
        limit=args.limit,
        workers=args.workers if args.workers > 0 else MAX_WORKERS,
        new_only=args.new_only
    )

if __name__ == "__main__":
    main()