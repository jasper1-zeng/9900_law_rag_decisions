#!/usr/bin/env python3
"""
reformat_json_for_neo4j.py - Reformats parsed WASAT case JSON files for Neo4j import.

This script processes JSON files in the data/parsed/json directory and its subdirectories,
extracts specific fields needed for Neo4j, and saves the reformatted JSON files.

Usage:
    python reformat_json_for_neo4j.py [--input INPUT_DIR] [--output OUTPUT_DIR]

Schema structure:    
- citation_number
- case_url
- legislations_structured: [{"law_title":, "law_link": "section"[{"section_title":, "section_link":}]}]
- referred_cases_structured: [{"citation_number":, "case_url":}]
"""

import os
import sys
import json
import argparse
import logging
import re
from pathlib import Path
from typing import Dict, List, Any

# Get the script directory and project base directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)  # Go up one level from scripts/ to wasat_scraper/

# Default paths
DATA_DIR = os.path.join(BASE_DIR, "data")
INPUT_DIR = os.path.join(DATA_DIR, "parsed", "json")
OUTPUT_DIR = os.path.join(DATA_DIR, "processed", "reformatted_neo4j")
LOG_DIR = os.path.join(BASE_DIR, "logs")
LOG_FILE = os.path.join(LOG_DIR, "reformat_logs.txt")

# Configure logging
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class WasatCaseReformatter:
    """Reformats WASAT case files for Neo4j import."""
    
    def __init__(self, input_dir: str = INPUT_DIR, output_dir: str = OUTPUT_DIR):
        """Initialize the reformatter with input and output directories."""
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
        
        logger.info(f"Input directory: {self.input_dir}")
        logger.info(f"Output directory: {self.output_dir}")
        
        # CSV file path for looking up case URLs
        self.csv_file_path = os.path.join(DATA_DIR, "raw", "wasat_cases_with_title_and_links.csv")
        self.case_urls = self._load_case_urls()
    
    def _load_case_urls(self) -> Dict[str, str]:
        """Load case URLs from CSV file."""
        case_urls = {}
        try:
            with open(self.csv_file_path, 'r', encoding='utf-8') as f:
                # Skip header
                next(f)
                for line in f:
                    parts = line.strip().split(',')
                    if len(parts) >= 5:
                        case_num = parts[0]
                        citation = parts[1]
                        url = parts[4]
                        key = f"{citation}_{case_num}"
                        case_urls[key] = url
            logger.info(f"Loaded {len(case_urls)} case URLs from CSV file")
        except Exception as e:
            logger.error(f"Error loading case URLs: {str(e)}")
        return case_urls
    
    def process_all_files(self):
        """Process all JSON files in the input directory and its subdirectories."""
        file_count = 0
        error_count = 0
        
        # Get all JSON files in input directory and its subdirectories
        json_files = []
        
        # Check if input directory exists
        if not self.input_dir.exists():
            logger.error(f"Input directory does not exist: {self.input_dir}")
            return
        
        # Look for year directories first
        year_dirs = [d for d in self.input_dir.iterdir() if d.is_dir() and d.name.isdigit()]
        
        if year_dirs:
            # Process year by year
            for year_dir in sorted(year_dirs):
                year_files = list(year_dir.glob('*.json'))
                logger.info(f"Found {len(year_files)} files in year directory {year_dir.name}")
                json_files.extend(year_files)
        else:
            # If no year directories, look for JSON files directly
            json_files = list(self.input_dir.glob('**/*.json'))
        
        logger.info(f"Found {len(json_files)} JSON files to process")
        
        for json_file in json_files:
            try:
                self.process_file(json_file)
                file_count += 1
                if file_count % 10 == 0:
                    logger.info(f"Processed {file_count} files")
            except Exception as e:
                logger.error(f"Error processing {json_file}: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                error_count += 1
        
        logger.info(f"Processing complete. Processed {file_count} files with {error_count} errors.")
    
    def process_file(self, file_path: Path):
        """Process a single JSON file."""
        # Load the JSON file
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON in file: {file_path}")
                raise
        
        # Extract case info
        case_number = data.get('case_number', '')
        year = data.get('year', '')
        
        # Reformat the data
        reformatted_data = self.reformat_data(data)
        
        # Save the reformatted data
        self.save_reformatted_data(reformatted_data, case_number, year)
    
    def reformat_data(self, data: Dict) -> Dict:
        """Reformat the data according to the specified requirements."""
        metadata = data.get('metadata', {})
        
        # Get citation number
        citation_number = ''
        if 'extracted_citation' in metadata and 'full' in metadata['extracted_citation']:
            citation_number = metadata['extracted_citation']['full']
        
        # Get case URL
        case_url = ''
        key = f"{metadata.get('extracted_citation', {}).get('full', '')}_{data.get('case_number', '')}"
        if key in self.case_urls:
            case_url = self.case_urls[key]
        
        # Legislation links
        legislations_structured = self._structure_legislation_links(metadata.get('LEGISLATION_LINKS', []))

        # Referred cases
        referred_cases_structured = self._structure_referred_cases(metadata.get('cases_referred_with_links', []))
        
        # Create reformatted data dictionary with only the required fields
        reformatted_data = {
            "citation_number": citation_number,
            "case_url": case_url,
            "legislations_structured": legislations_structured,
            "referred_cases_structured": referred_cases_structured,
        }
        
        return reformatted_data
    
    def _structure_legislation_links(self, legislation_links: List[Dict]) -> List[Dict]:
        """
        Structure legislation links in the format:
        [
            {
                "law_title": "Law Title",
                "law_link": "law_link",
                "sections": [
                    {
                        "section_title": "Section Title",
                        "section_link": "section_link"
                    },
                    ...
                ]
            },
            ...
        ]
        """
        if not legislation_links or not isinstance(legislation_links, list):
            return []
            
        # Group by law
        laws = {}
        
        for item in legislation_links:
            href = item.get('href', '')
            text = item.get('text', '')
            
            if not href or not text:
                continue
                
            # Check if it's a section (has .html in href)
            is_section = '.html' in href
            
            if is_section:
                # Extract the law code from the section link
                parts = href.split('/')
                if len(parts) > 1:
                    law_code = parts[-2]  # Get the law code
                    
                    # Create the law entry if it doesn't exist
                    if law_code not in laws:
                        # Find the matching law entry
                        law_entry = None
                        for link in legislation_links:
                            if law_code in link.get('href', '') and '.html' not in link.get('href', ''):
                                law_entry = link
                                break
                        
                        if law_entry:
                            laws[law_code] = {
                                "law_title": law_entry.get('text', ''),
                                "law_link": law_entry.get('href', ''),
                                "sections": []
                            }
                        else:
                            # If no matching law found, create a placeholder
                            laws[law_code] = {
                                "law_title": law_code,
                                "law_link": href.rsplit('/', 1)[0] + '/',
                                "sections": []
                            }
                    
                    # Add the section to the law
                    laws[law_code]['sections'].append({
                        "section_title": text,
                        "section_link": "https://www.austlii.edu.au" + href
                    })
            else:
                # It's a law
                law_code = href.rstrip('/').split('/')[-1]
                
                if law_code not in laws:
                    laws[law_code] = {
                        "law_title": text,
                        "law_link": "https://www.austlii.edu.au" + href,
                        "sections": []
                    }
        
        # Convert dictionary to list
        return list(laws.values())
    
    def _structure_referred_cases(self, cases_referred: List[Dict]) -> List[Dict]:
        """
        Structure referred cases in the format:
        [
            {
                "citation_number": "Case Citation",
                "case_url": "case_link"
            },
            ...
        ]
        """
        if not cases_referred or not isinstance(cases_referred, list):
            return []
            
        structured_cases = []
        
        for case in cases_referred:
            links = case.get('links', [])
            if not links:
                continue
                
            # Process each link in the case
            for link in links:
                case_citation = link.get('text', '')
                case_link = link.get('href', '')
                
                if case_citation and case_link:
                    structured_cases.append({
                        "citation_number": case_citation,
                        "case_url": "https://www.austlii.edu.au" + case_link
                    })
        
        return structured_cases
    
    def save_reformatted_data(self, data: Dict, case_number: str, year: str):
        """Save reformatted data to a JSON file."""
        # Create year directory if it doesn't exist
        year_dir = self.output_dir / year
        os.makedirs(year_dir, exist_ok=True)
        
        # Output file path
        output_file = year_dir / f"{case_number}.json"
        
        # Save the reformatted data
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved reformatted data to {output_file}")

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description='Reformat WASAT case JSON files for Neo4j import.')
    parser.add_argument('--input', default=INPUT_DIR, help='Input directory containing JSON files')
    parser.add_argument('--output', default=OUTPUT_DIR, help='Output directory for reformatted JSON files')
    args = parser.parse_args()
    
    # Create reformatter
    reformatter = WasatCaseReformatter(input_dir=args.input, output_dir=args.output)
    
    # Process all files
    reformatter.process_all_files()

if __name__ == '__main__':
    main() 