#!/usr/bin/env python3
"""
analyze_json_fields.py - Analyzes JSON fields across parsed WASAT case files.

This script scans through all parsed JSON files to identify field patterns, frequencies,
and data consistency. It generates reports about metadata fields, decision sections,
and other key data structures to help understand the dataset.

Usage:
    python analyze_json_fields.py [--output OUTPUT_DIR] [--year YEAR] [--detailed]
"""

import os
import sys
import json
import argparse
import logging
import csv
from pathlib import Path
from typing import Dict, List, Any, Set, Counter as CounterType
from collections import Counter, defaultdict
import re
from datetime import datetime

# Get the script directory and project base directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)  # Go up one level from scripts/ to wasat_scraper/

# Import project configuration if available
try:
    sys.path.append(BASE_DIR)
    import config
    CONFIG_EXISTS = True
except ImportError:
    CONFIG_EXISTS = False

# Default paths
DATA_DIR = os.path.join(BASE_DIR, "data")
INPUT_DIR = os.path.join(DATA_DIR, "parsed", "json")
OUTPUT_DIR = os.path.join(BASE_DIR, "reports", "json_analysis")
LOG_DIR = os.path.join(BASE_DIR, "logs")
LOG_FILE = os.path.join(LOG_DIR, "json_analysis_logs.txt")

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

class JsonFieldAnalyzer:
    """Analyzes JSON fields across parsed WASAT case files."""
    
    def __init__(self, input_dir: str = INPUT_DIR, output_dir: str = OUTPUT_DIR, year: str = None, detailed: bool = False):
        """Initialize the analyzer with input and output directories."""
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.year = year
        self.detailed = detailed
        
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
        
        logger.info(f"Input directory: {self.input_dir}")
        logger.info(f"Output directory: {self.output_dir}")
        
        # Statistics counters
        self.total_files = 0
        self.processed_files = 0
        self.error_files = 0
        
        # Field analysis data
        self.metadata_fields = Counter()
        self.decision_titles = Counter()
        self.top_level_fields = Counter()
        self.metadata_field_types = defaultdict(Counter)
        self.field_values = defaultdict(set)
        self.field_examples = defaultdict(dict)
        self.years_data = defaultdict(int)
        self.case_numbers = defaultdict(list)
        
        # For detailed analysis
        self.act_links = Counter()
        self.citation_patterns = Counter()
        self.metadata_nested_fields = defaultdict(Counter)
    
    def analyze_all_files(self):
        """Process all JSON files in the input directory and its subdirectories."""
        json_files = []
        
        # Check if input directory exists
        if not self.input_dir.exists():
            logger.error(f"Input directory does not exist: {self.input_dir}")
            return
        
        # Look for year directories
        year_dirs = sorted([d for d in self.input_dir.iterdir() if d.is_dir() and d.name.isdigit()])
        
        if self.year:
            year_dir = self.input_dir / self.year
            if year_dir.exists() and year_dir.is_dir():
                year_dirs = [year_dir]
            else:
                logger.error(f"Year directory {self.year} does not exist")
                return
        
        if year_dirs:
            # Process year by year
            for year_dir in year_dirs:
                year_files = list(year_dir.glob('*.json'))
                logger.info(f"Found {len(year_files)} files in year directory {year_dir.name}")
                json_files.extend(year_files)
                self.years_data[year_dir.name] = len(year_files)
        else:
            # If no year directories, look for JSON files directly
            json_files = list(self.input_dir.glob('**/*.json'))
        
        self.total_files = len(json_files)
        logger.info(f"Found {self.total_files} JSON files to analyze")
        
        for json_file in json_files:
            try:
                self.analyze_file(json_file)
                self.processed_files += 1
                if self.processed_files % 50 == 0:
                    logger.info(f"Analyzed {self.processed_files}/{self.total_files} files")
            except Exception as e:
                logger.error(f"Error analyzing {json_file}: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                self.error_files += 1
        
        logger.info(f"Analysis complete. Processed {self.processed_files} files with {self.error_files} errors.")
        self.generate_reports()
    
    def analyze_file(self, file_path: Path):
        """Analyze a single JSON file."""
        # Load the JSON file
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON in file: {file_path}")
                raise
        
        # Get year and case number
        year = data.get('year', '')
        case_number = data.get('case_number', '')
        self.case_numbers[year].append(case_number)
        
        # Analyze top-level fields
        for field in data.keys():
            self.top_level_fields[field] += 1
            
            # Store example values for top-level fields
            if self.detailed and field not in self.field_examples:
                self.field_examples[field] = {
                    'file': str(file_path),
                    'value': str(data[field])[:100] + ('...' if len(str(data[field])) > 100 else '')
                }
        
        # Analyze metadata fields
        if 'metadata' in data and isinstance(data['metadata'], dict):
            metadata = data['metadata']
            for field, value in metadata.items():
                self.metadata_fields[field] += 1
                
                # Track field types
                field_type = type(value).__name__
                self.metadata_field_types[field][field_type] += 1
                
                # Store sample values (limited to prevent memory issues)
                if len(self.field_values[field]) < 10:
                    if isinstance(value, (str, int, float, bool)) or value is None:
                        self.field_values[field].add(str(value)[:100])
                
                # Analyze nested fields in metadata
                if self.detailed and isinstance(value, dict):
                    for nested_field in value.keys():
                        self.metadata_nested_fields[field][nested_field] += 1
                
                # Special analysis for ACT_LINKS
                if field == 'ACT_LINKS' and isinstance(value, list):
                    for act_link in value:
                        if isinstance(act_link, dict) and 'text' in act_link:
                            self.act_links[act_link['text']] += 1
                
                # Analyze citation patterns
                if field == 'CITATION' and isinstance(value, str):
                    citation_pattern = self._extract_citation_pattern(value)
                    if citation_pattern:
                        self.citation_patterns[citation_pattern] += 1
        
        # Analyze decision sections
        if 'decisions' in data and isinstance(data['decisions'], list):
            decisions = data['decisions']
            for decision in decisions:
                if isinstance(decision, dict) and 'title' in decision:
                    title = decision.get('title', '').lower()
                    if title:
                        self.decision_titles[title] += 1
    
    def _extract_citation_pattern(self, citation: str) -> str:
        """Extract pattern from citation for analysis."""
        # Look for patterns like [YYYY] COURT NN
        match = re.search(r'\[\d{4}\]\s+([A-Za-z]+)\s+\d+', citation)
        if match:
            return match.group(1)
        return ''
    
    def generate_reports(self):
        """Generate analysis reports."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Summary report
        summary_path = self.output_dir / f"summary_report_{timestamp}.txt"
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write("JSON Field Analysis Summary Report\n")
            f.write("=================================\n\n")
            f.write(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Files Analyzed: {self.processed_files}\n")
            f.write(f"Files with Errors: {self.error_files}\n\n")
            
            f.write("Files by Year:\n")
            for year, count in sorted(self.years_data.items()):
                f.write(f"  {year}: {count} files\n")
            
            f.write("\nTop-Level Fields:\n")
            for field, count in self.top_level_fields.most_common():
                percentage = (count / self.processed_files) * 100
                f.write(f"  {field}: {count} ({percentage:.1f}%)\n")
            
            f.write("\nTop 20 Metadata Fields:\n")
            for field, count in self.metadata_fields.most_common(20):
                percentage = (count / self.processed_files) * 100
                f.write(f"  {field}: {count} ({percentage:.1f}%)\n")
            
            f.write("\nTop 20 Decision Section Titles:\n")
            for title, count in self.decision_titles.most_common(20):
                percentage = (count / self.processed_files) * 100
                f.write(f"  {title}: {count} ({percentage:.1f}%)\n")
        
        logger.info(f"Generated summary report: {summary_path}")
        
        # Metadata fields CSV
        metadata_path = self.output_dir / f"metadata_fields_{timestamp}.csv"
        with open(metadata_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Field', 'Count', 'Percentage', 'Types', 'Sample Values'])
            
            for field, count in self.metadata_fields.most_common():
                percentage = (count / self.processed_files) * 100
                types = ', '.join([f"{t}({c})" for t, c in self.metadata_field_types[field].most_common()])
                samples = '; '.join(list(self.field_values[field])[:5])
                writer.writerow([field, count, f"{percentage:.1f}%", types, samples])
        
        logger.info(f"Generated metadata fields report: {metadata_path}")
        
        # Decision titles CSV
        decisions_path = self.output_dir / f"decision_titles_{timestamp}.csv"
        with open(decisions_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Title', 'Count', 'Percentage'])
            
            for title, count in self.decision_titles.most_common():
                percentage = (count / self.processed_files) * 100
                writer.writerow([title, count, f"{percentage:.1f}%"])
        
        logger.info(f"Generated decision titles report: {decisions_path}")
        
        # Case numbers by year
        cases_path = self.output_dir / f"case_numbers_{timestamp}.csv"
        with open(cases_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Year', 'Total Cases', 'Missing Cases', 'Missing Numbers'])
            
            for year, case_numbers in sorted(self.case_numbers.items()):
                case_numbers = [int(cn) for cn in case_numbers if cn.isdigit()]
                if not case_numbers:
                    continue
                    
                total = len(case_numbers)
                expected_range = set(range(1, max(case_numbers) + 1))
                actual_set = set(case_numbers)
                missing = expected_range - actual_set
                missing_count = len(missing)
                missing_str = ', '.join(str(m) for m in sorted(missing)[:20])
                if len(missing) > 20:
                    missing_str += f" and {len(missing) - 20} more"
                
                writer.writerow([year, total, missing_count, missing_str])
        
        logger.info(f"Generated case numbers report: {cases_path}")
        
        # Detailed reports
        if self.detailed:
            # ACT links
            acts_path = self.output_dir / f"act_links_{timestamp}.csv"
            with open(acts_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Act Name', 'Count', 'Percentage'])
                
                for act, count in self.act_links.most_common():
                    percentage = (count / self.processed_files) * 100
                    writer.writerow([act, count, f"{percentage:.1f}%"])
            
            logger.info(f"Generated ACT links report: {acts_path}")
            
            # Citation patterns
            citation_path = self.output_dir / f"citation_patterns_{timestamp}.csv"
            with open(citation_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Citation Pattern', 'Count', 'Percentage'])
                
                for pattern, count in self.citation_patterns.most_common():
                    percentage = (count / self.processed_files) * 100
                    writer.writerow([pattern, count, f"{percentage:.1f}%"])
            
            logger.info(f"Generated citation patterns report: {citation_path}")
            
            # Field examples
            examples_path = self.output_dir / f"field_examples_{timestamp}.txt"
            with open(examples_path, 'w', encoding='utf-8') as f:
                f.write("Field Examples from JSON Files\n")
                f.write("=============================\n\n")
                
                for field, example in self.field_examples.items():
                    f.write(f"Field: {field}\n")
                    f.write(f"File: {example['file']}\n")
                    f.write(f"Example: {example['value']}\n\n")
            
            logger.info(f"Generated field examples report: {examples_path}")
            
            # Nested fields
            nested_path = self.output_dir / f"nested_fields_{timestamp}.csv"
            with open(nested_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Parent Field', 'Nested Field', 'Count'])
                
                for parent, nested_fields in self.metadata_nested_fields.items():
                    for nested_field, count in nested_fields.most_common():
                        writer.writerow([parent, nested_field, count])
            
            logger.info(f"Generated nested fields report: {nested_path}")

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description='Analyze JSON fields across parsed WASAT case files.')
    parser.add_argument('--output', default=OUTPUT_DIR, help='Output directory for analysis reports')
    parser.add_argument('--year', help='Analyze files from a specific year only')
    parser.add_argument('--detailed', action='store_true', help='Generate detailed analysis reports')
    args = parser.parse_args()
    
    # Create analyzer
    analyzer = JsonFieldAnalyzer(
        input_dir=INPUT_DIR, 
        output_dir=args.output,
        year=args.year,
        detailed=args.detailed
    )
    
    # Process all files
    analyzer.analyze_all_files()

if __name__ == '__main__':
    main() 