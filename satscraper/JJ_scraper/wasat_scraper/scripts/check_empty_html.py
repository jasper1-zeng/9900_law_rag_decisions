#!/usr/bin/env python3
"""
check_empty_html.py - HTML File Quality Checker for WASAT Cases

This module analyzes HTML case files to identify quality issues such as:
- Empty files (less than 100 bytes)
- Abnormally small files (statistical outliers)
- Abnormally large files (statistical outliers)
- Files with missing expected HTML elements
- Files with corrupt or invalid HTML structure

These checks help ensure the integrity of downloaded case data before
further processing stages like parsing and analysis.

Usage:
  python check_empty_html.py [--sample N] [--fix]

Author: Capstone Team 10A, Zhengxin Zeng
Date: 2025-04-06
"""

# Standard library imports
import os
import sys
import logging
import argparse
import statistics
import random
from collections import defaultdict

# Third-party library imports
from bs4 import BeautifulSoup

#------------------------------------------------------------------------------
# CONFIGURATION CONSTANTS
#------------------------------------------------------------------------------

# Define base paths directly
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)  # Go up one level from scripts/ to wasat_scraper/
DATA_DIR = os.path.join(BASE_DIR, "data")
HTML_DIR = os.path.join(DATA_DIR, "html")
BY_YEAR_DIR = os.path.join(HTML_DIR, "by_year")
LOG_DIR = os.path.join(BASE_DIR, "logs")

# Create essential directories if they don't exist
os.makedirs(LOG_DIR, exist_ok=True)

# Analysis settings
EMPTY_THRESHOLD = 100    # Files smaller than this (in bytes) are considered empty
MIN_ARTICLE_TEXT = 100   # Minimum expected character count in article content
MIN_PARAGRAPHS = 5       # Minimum expected paragraph elements in a valid case
STD_DEV_MULTIPLIER = 2   # How many standard deviations for outlier detection

#------------------------------------------------------------------------------
# LOGGING SETUP
#------------------------------------------------------------------------------

class HTMLChecker:
    """
    Main class for checking HTML file quality and integrity
    """
    
    @staticmethod
    def setup_logging():
        """
        Configure logging to file and console
        
        Sets up two log handlers:
        1. A file handler for all logs
        2. A console handler for real-time feedback
        
        Returns:
            logger: Configured logging object
        """
        log_file = os.path.join(LOG_DIR, "check_html_logs.txt")
        
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

    #------------------------------------------------------------------------------
    # FILE DISCOVERY AND ANALYSIS
    #------------------------------------------------------------------------------
    
    @staticmethod
    def get_all_html_files():
        """
        Get all HTML files in the year directories
        
        Traverses the year directory structure to find all HTML case files.
        
        Returns:
            list: List of dictionaries with information about each HTML file
                 Each dict contains 'year', 'case_number', and 'path' keys
        """
        html_files = []
        
        # Check if the year directory exists
        if not os.path.exists(BY_YEAR_DIR):
            logging.error(f"Year directory not found: {BY_YEAR_DIR}")
            return html_files
        
        # Traverse all year directories
        for year in os.listdir(BY_YEAR_DIR):
            year_dir = os.path.join(BY_YEAR_DIR, year)
            
            if not os.path.isdir(year_dir):
                continue
            
            # Get all HTML files in this year
            for file_name in os.listdir(year_dir):
                if file_name.endswith('.html'):
                    file_path = os.path.join(year_dir, file_name)
                    html_files.append({
                        'year': year,
                        'case_number': os.path.splitext(file_name)[0],
                        'path': file_path
                    })
        
        return html_files
    
    @staticmethod
    def check_file_sizes(html_files):
        """
        Check file sizes and identify outliers using statistical analysis
        
        Calculates size statistics for all files and identifies:
        1. Empty files (below EMPTY_THRESHOLD)
        2. Abnormally small files (below mean - STD_DEV_MULTIPLIER * std_dev)
        3. Abnormally large files (above mean + STD_DEV_MULTIPLIER * std_dev)
        
        Args:
            html_files (list): List of file information dictionaries
            
        Returns:
            tuple: Three lists containing empty, small, and large file info
        """
        if not html_files:
            logging.warning("No HTML files found to check")
            return [], [], []
        
        # Calculate file sizes
        file_sizes = []
        for file_info in html_files:
            file_path = file_info['path']
            file_size = os.path.getsize(file_path)
            file_info['size'] = file_size
            file_sizes.append(file_size)
        
        # Calculate statistics
        avg_size = statistics.mean(file_sizes)
        median_size = statistics.median(file_sizes)
        
        try:
            stddev = statistics.stdev(file_sizes)
        except statistics.StatisticsError:
            # Not enough data for standard deviation
            stddev = avg_size / 2
        
        # Define thresholds for abnormal sizes
        empty_threshold = EMPTY_THRESHOLD  # Bytes
        small_threshold = max(empty_threshold, avg_size - (STD_DEV_MULTIPLIER * stddev))
        large_threshold = avg_size + (STD_DEV_MULTIPLIER * stddev)
        
        # Identify empty, small, and large files
        empty_files = []
        small_files = []
        large_files = []
        
        for file_info in html_files:
            size = file_info['size']
            
            if size <= empty_threshold:
                empty_files.append(file_info)
            elif size < small_threshold:
                small_files.append(file_info)
            elif size > large_threshold:
                large_files.append(file_info)
        
        # Log detailed statistics for diagnostics
        logging.info(f"File size statistics:")
        logging.info(f"  Total files: {len(html_files)}")
        logging.info(f"  Average size: {avg_size:.2f} bytes")
        logging.info(f"  Median size: {median_size:.2f} bytes")
        logging.info(f"  Standard deviation: {stddev:.2f} bytes")
        logging.info(f"  Empty threshold: {empty_threshold} bytes")
        logging.info(f"  Small threshold: {small_threshold:.2f} bytes")
        logging.info(f"  Large threshold: {large_threshold:.2f} bytes")
        
        return empty_files, small_files, large_files
    
    @staticmethod
    def check_html_content(html_files, sample_size=10):
        """
        Check HTML content for structural abnormalities and missing elements
        
        Parses HTML files to check for:
        1. Missing article elements
        2. Suspiciously short article text
        3. Missing expected HTML elements (paragraphs, headings, etc.)
        
        Args:
            html_files (list): List of file information dictionaries
            sample_size (int): Number of files to analyze in detail
            
        Returns:
            list: Files with content issues
        """
        if not html_files:
            return []
        
        # Dictionary to hold files with issues
        problematic_files = []
        
        # List of elements we expect to find in valid case documents
        expected_elements = ['p', 'h1', 'h2', 'h3', 'ol', 'ul']
        
        # Examine each file in the sample
        for file_info in html_files[:sample_size]:
            try:
                with open(file_info['path'], 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Check if file has the expected article tag
                soup = BeautifulSoup(content, 'html.parser')
                article = soup.find('article', class_='the-document')
                
                if not article:
                    file_info['issue'] = "Missing article.the-document tag"
                    problematic_files.append(file_info)
                    continue
                
                # Check if article has expected content
                article_text = article.get_text(strip=True)
                
                if len(article_text) < MIN_ARTICLE_TEXT:
                    file_info['issue'] = f"Very short article text ({len(article_text)} chars)"
                    problematic_files.append(file_info)
                    continue
                    
                # Count expected element types
                found_elements = {elem: len(article.find_all(elem)) for elem in expected_elements}
                
                # If there are too few paragraphs, that's suspicious
                if found_elements['p'] < MIN_PARAGRAPHS:
                    file_info['issue'] = f"Few paragraph elements ({found_elements['p']})"
                    problematic_files.append(file_info)
                    
            except Exception as e:
                file_info['issue'] = f"Error parsing file: {str(e)}"
                problematic_files.append(file_info)
        
        return problematic_files
    
    #------------------------------------------------------------------------------
    # REPORTING AND ANALYSIS
    #------------------------------------------------------------------------------
    
    @staticmethod
    def group_files_by_year(files):
        """
        Group files by year for easier analysis and reporting
        
        Args:
            files (list): List of file information dictionaries
            
        Returns:
            dict: Files grouped by year
        """
        by_year = defaultdict(list)
        
        for file_info in files:
            by_year[file_info['year']].append(file_info)
        
        return by_year
    
    @staticmethod
    def write_problem_files_list(problematic_files):
        """
        Write list of problematic files to a text file for further processing
        
        Creates a CSV-format file with year,case_number pairs for re-downloading.
        
        Args:
            problematic_files (list): List of problematic file identifiers
            
        Returns:
            str: Path to the created file
        """
        problem_file = os.path.join(LOG_DIR, "problematic_html_files.txt")
        with open(problem_file, 'w', encoding='utf-8') as f:
            for year, case_number in sorted(problematic_files):
                f.write(f"{year},{case_number}\n")
        
        return problem_file
    
    #------------------------------------------------------------------------------
    # MAIN WORKFLOW
    #------------------------------------------------------------------------------
    
    def run_checks(self, sample_size=10, fix=False):
        """
        Run all quality checks on HTML files
        
        Orchestrates the quality checking process:
        1. Get list of all HTML files
        2. Check file sizes and identify outliers
        3. Analyze HTML content of a sample of files
        4. Group and report results
        5. Optionally fix issues (not implemented yet)
        
        Args:
            sample_size (int): Number of files to analyze in detail
            fix (bool): Whether to attempt to fix issues
            
        Returns:
            tuple: Lists of problematic files and problematic file IDs
        """
        logging.info("Starting HTML file check")
        
        # Get all HTML files
        html_files = self.get_all_html_files()
        logging.info(f"Found {len(html_files)} HTML files to check")
        
        # Check file sizes
        empty_files, small_files, large_files = self.check_file_sizes(html_files)
        
        # Log results
        logging.info(f"Found {len(empty_files)} empty files (<= {EMPTY_THRESHOLD} bytes)")
        logging.info(f"Found {len(small_files)} abnormally small files")
        logging.info(f"Found {len(large_files)} abnormally large files")
        
        # Check HTML content for a sample of files
        sample_files = []
        
        # Prioritize checking the empty and small files
        sample_files.extend(empty_files)
        sample_files.extend(small_files[:sample_size - len(sample_files)] if sample_size > len(sample_files) else [])
        
        # Add some random files to reach the sample size
        normal_files = [f for f in html_files if f not in empty_files and f not in small_files and f not in large_files]
        if normal_files and sample_size > len(sample_files):
            sample_files.extend(random.sample(normal_files, min(sample_size - len(sample_files), len(normal_files))))
        
        logging.info(f"Checking HTML content for {len(sample_files)} sample files")
        problematic_content = self.check_html_content(sample_files)
        
        # Log results
        if problematic_content:
            logging.info(f"Found {len(problematic_content)} files with HTML content issues:")
            for file_info in problematic_content:
                logging.info(f"  Year {file_info['year']}, Case {file_info['case_number']}: {file_info.get('issue', 'Unknown issue')}")
        else:
            logging.info("No HTML content issues found in the sample files")
        
        # Group empty files by year for easier analysis
        if empty_files:
            by_year = self.group_files_by_year(empty_files)
            logging.info("Empty files by year:")
            for year, files in sorted(by_year.items()):
                logging.info(f"  Year {year}: {len(files)} files")
                for file_info in files:
                    logging.info(f"    Case {file_info['case_number']}: {file_info['size']} bytes")
        
        # Combine all problematic files
        all_problematic = empty_files + small_files + problematic_content
        all_problematic_ids = {(f['year'], f['case_number']) for f in all_problematic}
        
        if all_problematic:
            logging.info(f"Found a total of {len(all_problematic_ids)} potentially problematic files")
            
            # Write problematic files to a text file for easier processing
            problem_file = self.write_problem_files_list(all_problematic_ids)
            
            logging.info(f"List of problematic files written to {problem_file}")
            
            # Provide guidance for next steps
            logging.info("To re-download these files, run html_downloader.py and provide a list of specific case numbers")
            
            # Attempt to fix if requested
            if fix:
                logging.info("Fix option enabled, would attempt to re-download problematic files")
                # This would invoke the HTML downloader to re-fetch these files
                # Not implemented yet, as we'd need to integrate with the downloader
                logging.warning("Auto-fix functionality not implemented yet")
        else:
            logging.info("No problematic files found")
        
        return all_problematic, all_problematic_ids

def main():
    """
    Main function for the HTML quality checker
    
    Command-line entry point that orchestrates the HTML quality checking process:
    1. Parse arguments
    2. Set up environment
    3. Run quality checks
    4. Report results
    """
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Check HTML files for abnormalities")
    parser.add_argument('--sample', type=int, default=10, 
                        help='Number of files to check content for (default: 10)')
    parser.add_argument('--fix', action='store_true',
                        help='Attempt to re-download problematic files')
    args = parser.parse_args()
    
    # Create checker instance
    checker = HTMLChecker()
    
    # Set up logging
    checker.setup_logging()
    
    # Run checks
    checker.run_checks(sample_size=args.sample, fix=args.fix)

if __name__ == "__main__":
    main()