#!/usr/bin/env python3
"""
reformat_json.py - Reformats parsed WASAT case JSON files according to specified requirements.

This script processes all JSON files in the data/parsed/json directory and its subdirectories,
extracts specific fields according to the defined requirements, and saves the reformatted JSON files.

Usage:
    python reformat_json.py [--input INPUT_DIR] [--output OUTPUT_DIR]


Schema structure:    

-- id: I don't know the meaning of it
case_url
case_title
citation_number
case_year
case_act
++ case_act_links: the structure is ["link1", "link2"]
-- case_topic: I do not have the mapping relationship
++ jurisdiction: text
member
heard_date
delivery_date
file_no
case_between
catchwords
legislations
++ legislations_structured: the format is [{"law_title":, "law_link": "section"[{"section_title":, "section_link":}]}]
result
category
-- representation: Can't extract in my scraper, so use its original
-- referred_cases
++ referred_cases_structured: [{"case_name":, "case_citation":, "case_link:"}]
++ metadata_pure_text: all metadata in pure text format
++ reasons_pure_text:
++ reasons_order: Title is "orders" or "order" (case insensitive)
++ reasons_introduction: Title is "introduction" or "introduction and background" or "introduction and overview" or "introduction and outcome" (case insensitive)
++ reasons_summary: Title is "summary of tribunal's decision" or "summary of the tribunal's decision" or "summary" or "summary of tribunal’s decision" (case insensitive)
++ reasons_conclusion: Title is "conclusion" or "conclusions" or "conclusion and orders" or "conclusion and order" or "conclusions and orders" (case insensitive)
++ reasons_other: all other sections that are not in the reasons_order, reasons_introduction, reasons_summary, reasons_conclusion
"""

import os
import sys
import json
import argparse
import logging
import re
from pathlib import Path
from typing import Dict, List, Any, Optional

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
OUTPUT_DIR = os.path.join(DATA_DIR, "processed", "reformatted")
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
    """Reformats WASAT case files according to specified requirements."""
    
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
        decisions = data.get('decisions', [])
        
        # Extract case title from metadata.CITATION, removing text after " ["
        case_title = metadata.get('CITATION', '')
        if case_title:
            match = re.search(r'(.*?)\s+\[', case_title)
            if match:
                case_title = match.group(1)
        
        # Get citation number
        citation_number = ''
        if 'extracted_citation' in metadata and 'full' in metadata['extracted_citation']:
            citation_number = metadata['extracted_citation']['full']
        
        # Get case URL
        case_url = ''
        key = f"{metadata.get('extracted_citation', {}).get('full', '')}_{data.get('case_number', '')}"
        if key in self.case_urls:
            case_url = self.case_urls[key]
        
        # Get case year
        case_year = data.get('year', '')
        
        # Get case act
        case_act = ''
        if 'ACT_LINKS' in metadata and len(metadata['ACT_LINKS']) > 0:
            case_act = metadata['ACT_LINKS'][0].get('text', '')
        
        # Get case act links
        case_act_links = []
        if 'ACT_LINKS' in metadata:
            for act_link in metadata['ACT_LINKS']:
                if 'href' in act_link:
                    case_act_links.append("https://www.austlii.edu.au" + act_link['href'])
        
        # Get jurisdiction
        jurisdiction = metadata.get('JURISDICTION', '')
        
        # Get member
        member = metadata.get('MEMBER', '')
        
        # Get heard_date
        heard_date = metadata.get('HEARD', '')
        
        # Get delivery_date
        delivery_date = metadata.get('DELIVERED', '')
        
        # Get file_no (remove "FILE NO/S : " if present)
        file_no = metadata.get('FILE NO/S', '')
        if file_no.startswith('FILE NO/S : '):
            file_no = file_no[12:]
        
        # Get case_between (remove "BETWEEN : " if present)
        case_between = metadata.get('BETWEEN', '')
        if case_between.startswith('BETWEEN : '):
            case_between = case_between[10:]
        
        # Get catchwords
        catchwords = metadata.get('CATCHWORDS', '')
        
        # Get legislations
        legislations = metadata.get('LEGISLATION', '')
        
        # legislations [{"law_title":, "law_link": "section"[{"section_title":, "section_link":}]}]
        legislations_structured = self._structure_legislation_links(metadata.get('LEGISLATION_LINKS', []))

        # Get result
        result = metadata.get('RESULT', '')
        
        # Get category
        category = metadata.get('CATEGORY', '')

        # referred_cases_structured: [{"case_citation":, "case_link":}]
        referred_cases_structured = self._structure_referred_cases(metadata.get('cases_referred_with_links', []))

        # Convert metadata to text
        metadata_pure_text = self._convert_metadata_to_text(metadata)
        
        # Convert decisions to text
        reasons_pure_text = self._convert_decisions_to_text(decisions)
        
        # Extract specific sections
        reasons_order = self._extract_section(decisions, ['orders', 'order'])
        reasons_introduction = self._extract_section(decisions, ['introduction', 'introduction and background', 
                                                           'introduction and overview', 'introduction and outcome'])
        reasons_summary = self._extract_section(decisions, ['summary of tribunal\'s decision', 
                                                      'summary of the tribunal\'s decision', 
                                                      'summary', 'summary of tribunal\'s decision'])
        reasons_conclusion = self._extract_section(decisions, ['conclusion', 'conclusions', 
                                                        'conclusion and orders', 'conclusion and order', 
                                                        'conclusions and orders'])
        
        # the other sections that are not in the reasons_order, reasons_introduction, reasons_summary, reasons_conclusion
        reasons_other = self._extract_other_sections(decisions, ['orders', 'order', 'introduction', 'introduction and background', 
                                                        'introduction and overview', 'introduction and outcome',
                                                        'summary of tribunal\'s decision', 'summary of the tribunal\'s decision', 
                                                        'summary', 'summary of tribunal\'s decision',
                                                        'conclusion', 'conclusions', 'conclusion and orders', 
                                                        'conclusion and order', 'conclusions and orders'])
        
        
        # Create reformatted data dictionary
        reformatted_data = {
            "case_url": case_url,
            "case_title": case_title,
            "citation_number": citation_number,
            "case_year": case_year,
            "case_act": case_act,
            "case_act_links": case_act_links,
            "jurisdiction": jurisdiction,
            "member": member,
            "heard_date": heard_date,
            "delivery_date": delivery_date,
            "file_no": file_no,
            "case_between": case_between,
            "catchwords": catchwords,
            "legislations": legislations,
            "legislations_structured": legislations_structured,
            "result": result,
            "category": category,
            "referred_cases_structured": referred_cases_structured,
            "metadata_pure_text": metadata_pure_text,
            "reasons_pure_text": reasons_pure_text,
            "reasons_order": reasons_order,
            "reasons_introduction": reasons_introduction,
            "reasons_summary": reasons_summary,
            "reasons_conclusion": reasons_conclusion,
            "reasons_other": reasons_other
        }
        
        return reformatted_data
    
    def _convert_metadata_to_text(self, metadata: Dict) -> str:
        """Convert metadata to text format."""
        text_parts = []
        
        for key, value in metadata.items():
            # Skip complex nested structures
            if isinstance(value, dict) or (isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict)):
                continue
                
            if value:
                if isinstance(value, list):
                    value = "\n".join(value)
                text_parts.append(f"{key}: {value}")
        
        return "\n\n".join(text_parts)
    
    def _convert_decisions_to_text(self, decisions: List[Dict]) -> str:
        """Convert decisions to text format."""
        text_parts = []
        
        for decision in decisions:
            title = decision.get('title', '')
            content = decision.get('content', '')
            
            if title and content:
                text_parts.append(f"# {title}\n\n{content}")
            elif content:
                text_parts.append(content)
        
        return "\n\n".join(text_parts)
    
    def _extract_section(self, decisions: List[Dict], titles: List[str]) -> str:
        """Extract a specific section from decisions based on title."""
        for decision in decisions:
            title = decision.get('title', '').lower()
            if title in titles:
                return decision.get('content', '')
        return ''
    
    def _extract_other_sections(self, decisions: List[Dict], excluded_titles: List[str]) -> Dict[str, str]:
        """Extract all sections that are not in the excluded_titles list."""
        other_sections = {}
        
        for decision in decisions:
            title = decision.get('title', '')
            if title and title.lower() not in excluded_titles:
                other_sections[title] = decision.get('content', '')
                
        return other_sections
    
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
                # Example: "/cgi-bin/viewdoc/au/legis/wa/consol_act/pada2005236/s138.html"
                parts = href.split('/')
                if len(parts) > 1:
                    law_code = parts[-2]  # Get the law code (pada2005236)
                    
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
                "case_citation": "Case Citation",
                "case_link": "case_link"
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
                        "case_citation": case_citation,
                        "case_link": "https://www.austlii.edu.au" + case_link
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
    parser = argparse.ArgumentParser(description='Reformat WASAT case JSON files.')
    parser.add_argument('--input', default=INPUT_DIR, help='Input directory containing JSON files')
    parser.add_argument('--output', default=OUTPUT_DIR, help='Output directory for reformatted JSON files')
    args = parser.parse_args()
    
    # Create reformatter
    reformatter = WasatCaseReformatter(input_dir=args.input, output_dir=args.output)
    
    # Process all files
    reformatter.process_all_files()

if __name__ == '__main__':
    main() 