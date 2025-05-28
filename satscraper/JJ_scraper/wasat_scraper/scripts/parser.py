#!/usr/bin/env python3
"""
Enhanced parser.py - Parses HTML content from WASAT case files to structured JSON
Focuses on correctly parsing metadata and decision structure with improved handling
of complex document structures and multiple sections.
"""

import os
import sys
import json
import logging
import argparse
import re
from bs4 import BeautifulSoup, Tag, NavigableString
from datetime import datetime
from pathlib import Path

# Define base paths directly
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)  # Go up one level from scripts/ to wasat_scraper/
DATA_DIR = os.path.join(BASE_DIR, "data")
HTML_DIR = os.path.join(DATA_DIR, "html")
BY_YEAR_DIR = os.path.join(HTML_DIR, "by_year")
PARSED_DIR = os.path.join(DATA_DIR, "parsed")
JSON_DIR = os.path.join(PARSED_DIR, "json")
LOG_DIR = os.path.join(BASE_DIR, "logs")

# Create essential directories if they don't exist
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(JSON_DIR, exist_ok=True)

def setup_logging(debug=False):
    """Configure logging to file and console"""
    log_file = os.path.join(LOG_DIR, "parser_logs.txt")
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    
    # Clear existing handlers if any
    if logger.handlers:
        logger.handlers = []
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG if debug else logging.INFO)
    file_handler.setFormatter(formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if debug else logging.INFO)
    console_handler.setFormatter(formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def clean_text(text):
    """Clean up text by removing extra whitespace and newlines"""
    if not text:
        return ""
    # Replace multiple whitespace with a single space
    text = re.sub(r'\s+', ' ', text)
    # Remove leading/trailing whitespace
    text = text.strip()
    return text

def is_element_after(elem1, elem2):
    """Check if elem1 appears after elem2 in the document"""
    # Get all elements
    all_elements = list(elem1.parent.parent.find_all())
    
    # Find positions
    try:
        pos1 = all_elements.index(elem1)
        pos2 = all_elements.index(elem2)
        return pos1 > pos2
    except ValueError:
        # If one of the elements is not found, return False
        return False

def find_decision_header(soup):
    """Find the 'REASONS FOR DECISION' header that marks the end of metadata"""
    # Look for <p align="center"> tags with "REASONS FOR DECISION" text
    for p in soup.find_all('p', align='center'):
        if re.search(r'REASONS FOR DECISION', p.get_text(), re.IGNORECASE):
            return p
    
    # If not found with align="center", try other methods
    for b_tag in soup.find_all('b'):
        if re.search(r'REASONS FOR DECISION', b_tag.get_text(), re.IGNORECASE):
            return b_tag.parent
    
    # As a last resort, try any occurrence of the phrase
    for elem in soup.find_all(string=re.compile(r'REASONS FOR DECISION', re.IGNORECASE)):
        if isinstance(elem, str) and elem.strip():
            return elem.parent
    
    return None

def find_decision_headers(soup):
    """Find all decision headers in the document"""
    decision_headers = []
    
    # Look for <p align="center"> tags with "REASONS FOR DECISION" text
    center_paragraphs = soup.find_all('p', align='center')
    
    for p in center_paragraphs:
        text = clean_text(p.get_text())
        if re.search(r'REASONS FOR DECISION', text, re.IGNORECASE):
            decision_headers.append((p, text))
        else:
            # Check if there's a <b> tag inside with "REASONS FOR DECISION" text
            b_tag = p.find('b')
            if b_tag and re.search(r'REASONS FOR DECISION', b_tag.get_text(), re.IGNORECASE):
                decision_headers.append((p, clean_text(b_tag.get_text())))
    
    # If no decision headers found with <p align="center">, try other methods
    if not decision_headers:
        # Look for bold tags with "REASONS FOR DECISION"
        for b_tag in soup.find_all('b'):
            if re.search(r'REASONS FOR DECISION', b_tag.get_text(), re.IGNORECASE):
                parent = b_tag.parent
                decision_headers.append((parent, clean_text(b_tag.get_text())))
                break
    
    # If still no headers found, try any occurrence of the phrase
    if not decision_headers:
        for elem in soup.find_all(string=re.compile(r'REASONS FOR DECISION', re.IGNORECASE)):
            if isinstance(elem, str) and elem.strip():  # Make sure it's a non-empty string
                parent = elem.parent
                decision_headers.append((parent, clean_text(elem)))
                break
    
    return decision_headers

def find_next_metadata_section(current_p, soup, decision_header):
    """
    Find the next metadata section (with bold tag) after the current paragraph.
    Returns None if there is no next section before the decision header.
    """
    next_p = current_p
    
    while True:
        next_p = next_p.find_next_sibling('p')
        if not next_p:
            break
            
        # Stop if we've reached the decision header
        if decision_header and (next_p == decision_header or is_element_after(next_p, decision_header)):
            return None
            
        # Check if this paragraph has a bold tag (indicating new section)
        b_tag = next_p.find('b')
        if b_tag and ':' in b_tag.get_text():
            b_text = clean_text(b_tag.get_text())
            # Skip if it doesn't look like metadata
            if not (' v ' in b_text.lower() or '[' in b_text or ']' in b_text):
                return next_p
        
        # Also check for italics tag with colon as a new section marker
        i_tag = next_p.find('i')
        if i_tag and ':' in i_tag.get_text():
            return next_p
    
    return None

def extract_italics_sections(soup, metadata, decision_header):
    """
    Extract sections marked with <i>SectionName:</i> patterns
    This will capture Catchwords, Legislation, Result, Category, etc.
    """
    # Define the section names we're looking for
    section_names = ["Catchwords", "Legislation", "Result", "Category"]
    
    # Track what we've found
    found_sections = {}
    
    # Look for paragraphs with italics tag
    for p in soup.find_all('p'):
        # Skip if after decision header
        if decision_header and is_element_after(p, decision_header):
            continue
            
        # Look for italics tag with colon
        i_tag = p.find('i')
        if i_tag and ':' in i_tag.get_text():
            i_text = clean_text(i_tag.get_text())
            
            # Extract section name before the colon
            section_name = i_text.split(':', 1)[0].strip()
            
            # Check if this is one of our target sections
            if section_name in section_names:
                # Get the content from this paragraph and potentially following paragraphs
                section_content = []
                
                # Process the current paragraph
                # Remove the section name and colon
                current_text = clean_text(p.get_text().replace(i_text, '', 1))
                if current_text:
                    section_content.append(current_text)
                
                # Look for content in following paragraphs until next section
                current_p = p
                while True:
                    next_p = current_p.find_next_sibling('p')
                    if not next_p:
                        break
                        
                    # Stop if we hit another section marker
                    next_i_tag = next_p.find('i')
                    if next_i_tag and ':' in next_i_tag.get_text():
                        break
                        
                    # Stop if we hit a bold tag (new major section)
                    if next_p.find('b'):
                        break
                        
                    # Stop if we've reached the decision header
                    if decision_header and (next_p == decision_header or is_element_after(next_p, decision_header)):
                        break
                        
                    # Add content if there is any
                    next_text = clean_text(next_p.get_text())
                    if next_text:
                        section_content.append(next_text)
                    
                    current_p = next_p
                
                # Store the content
                found_sections[section_name] = {
                    "content": " ".join(section_content),
                    "structured_content": section_content
                }
                
                # Also extract links if this is the Legislation section
                if section_name == "Legislation":
                    links = []
                    for a_tag in p.find_all('a', class_="autolink_findacts"):
                        links.append({
                            "text": clean_text(a_tag.get_text()),
                            "href": a_tag.get('href', '')
                        })
                    
                    # Look for links in following paragraphs
                    current_p = p
                    while True:
                        next_p = current_p.find_next_sibling('p')
                        if not next_p:
                            break
                            
                        # Stop if we hit another section marker
                        next_i_tag = next_p.find('i')
                        if next_i_tag and ':' in next_i_tag.get_text():
                            break
                            
                        # Stop if we hit a bold tag (new major section)
                        if next_p.find('b'):
                            break
                            
                        # Extract links
                        for a_tag in next_p.find_all('a', class_="autolink_findacts"):
                            links.append({
                                "text": clean_text(a_tag.get_text()),
                                "href": a_tag.get('href', '')
                            })
                        
                        current_p = next_p
                    
                    if links:
                        found_sections[section_name]["links"] = links
    
    # Add what we found to the metadata
    for section_name, content in found_sections.items():
        metadata[section_name.upper()] = content["content"]
        metadata[f"{section_name.upper()}_STRUCTURED"] = content["structured_content"]
        
        if "links" in content:
            metadata[f"{section_name.upper()}_LINKS"] = content["links"]

def process_special_section(soup, section_key, p, metadata, decision_header):
    """
    Process special sections like BETWEEN which span multiple paragraphs.
    Enhanced to collect all content until the next metadata section.
    Also handles ACT field with links.
    """
    # Special handling for ACT field to extract link information
    if section_key == "ACT":
        # Look for links in the paragraph
        links = []
        for a_tag in p.find_all('a'):
            links.append({
                "text": clean_text(a_tag.get_text()),
                "href": a_tag.get('href', '')
            })
        
        if links:
            metadata["ACT_LINKS"] = links
    
    # Collect content from paragraphs immediately following until we hit another bold tag or section
    related_content = []
    current_content = clean_text(p.get_text().replace(f"{section_key}:", ""))
    
    # Add the first paragraph content if not empty (after removing the bold part)
    if current_content:
        related_content.append(current_content)
    
    current_p = p
    
    # Find the next metadata section
    next_section_p = find_next_metadata_section(current_p, soup, decision_header)
    
    # Iterate through all paragraphs until next section or decision header
    while True:
        next_p = current_p.find_next_sibling('p')
        if not next_p:
            break
            
        # Stop if we've reached the next section or decision header
        if (next_section_p and next_p == next_section_p) or \
           (decision_header and (next_p == decision_header or is_element_after(next_p, decision_header))):
            break
        
        current_p = next_p
        
        # Skip if it's not a paragraph or contains an img tag
        if current_p.name != 'p' or current_p.find('img'):
            continue
        
        # Check if this paragraph has an italics tag with colon
        i_tag = current_p.find('i')
        if i_tag and ':' in i_tag.get_text():
            i_text = clean_text(i_tag.get_text())
            
            # If this is a section name, store it as a separate attribute in metadata
            section_name = i_text.split(':', 1)[0].strip()
            if section_name:
                # Extract the content following the section name
                section_content = clean_text(current_p.get_text().replace(i_text, '', 1))
                
                # Store in metadata
                metadata[f"{section_key}_{section_name.upper()}"] = section_content
                
                # Also look for links
                links = []
                for a_tag in current_p.find_all('a'):
                    links.append({
                        "text": clean_text(a_tag.get_text()),
                        "href": a_tag.get('href', '')
                    })
                
                if links:
                    metadata[f"{section_key}_{section_name.upper()}_LINKS"] = links
                
                # Don't add this to related_content since we're storing it separately
                continue
        
        # In BETWEEN sections, we also want to capture party designations (Applicant, Respondent)
        party_text = clean_text(current_p.get_text())
        if section_key == "BETWEEN" and party_text.lower() in ["applicant", "respondent", "and"]:
            related_content.append(party_text)
            continue
        
        # Add content if it's not empty (excluding certain patterns)
        content_text = clean_text(current_p.get_text())
        if content_text and not content_text.startswith("<!--"):
            related_content.append(content_text)
    
    # Store the full content as a single string for the main metadata key
    if related_content:
        metadata[section_key] = " ".join(related_content)
        # Also store the structured content
        metadata[f"{section_key}_STRUCTURED"] = related_content

def extract_case_links(paragraph):
    """
    Extract links from a paragraph containing case citations
    """
    links = []
    
    # Find all 'a' tags in the paragraph
    for a_tag in paragraph.find_all('a'):
        if a_tag.get('href'):
            links.append({
                'text': clean_text(a_tag.get_text()),
                'href': a_tag.get('href'),
                'class': a_tag.get('class', [])
            })
    
    return links

def process_cases_referred(soup, metadata, decision_header):
    """
    Extract cases referred from the document, including links to the case citations.
    Enhanced to handle complex case reference patterns and multiple paragraphs.
    """
    cases_referred = []
    cases_with_links = []
    
    # First look for <p name="CasesReferred">
    cases_section = soup.find('p', attrs={'name': 'CasesReferred'})
    
    # If not found, try to find by bold text
    if not cases_section:
        for b_tag in soup.find_all('b'):
            if 'Case(s) referred to in decision(s):' in b_tag.get_text():
                cases_section = b_tag.parent
                break
    
    if cases_section:
        # Find the judgment header or reasons for decision header
        judgment_header = None
        for p in soup.find_all('p', align='center'):
            if re.search(r'REASONS FOR DECISION', p.get_text(), re.IGNORECASE) or \
               re.search(r'JUDGMENT', p.get_text(), re.IGNORECASE):
                judgment_header = p
                break
        
        # Look for the StartOfIndex marker
        start_of_index = soup.find('p', attrs={'name': 'StartOfIndex'})
        
        if start_of_index:
            # Process all paragraphs between StartOfIndex and judgment header
            current = start_of_index
            
            # Skip to the next element after StartOfIndex
            if current:
                current = current.next_sibling
                
            while current:
                if judgment_header and (current == judgment_header or is_element_after(current, judgment_header)):
                    break
                    
                if isinstance(current, Tag) and current.name == 'p':
                    # Check if this paragraph has content we want (skip empty paragraphs)
                    case_text = clean_text(current.get_text())
                    
                    # Skip if it seems to be a new major section
                    if current.find('b') and not re.search(r' v |vs\.', case_text, re.IGNORECASE):
                        # Check if it's not part of a case name (some cases have bold elements)
                        b_text = clean_text(current.find('b').get_text())
                        if len(b_text) > 15 and ':' in b_text:  # Likely a heading, not case name
                            break
                    
                    # Process paragraph if it contains case references
                    if (case_text and 
                        (re.search(r' v |vs\.', case_text, re.IGNORECASE) or 
                         re.search(r'\[\d{4}\]', case_text) or
                         re.search(r'\(\d{4}\)', case_text))):
                        
                        # Extract each case if there are multiple in the paragraph
                        # Split by line breaks if they exist
                        if '<br/>' in str(current) or '<br>' in str(current):
                            # Try to extract individual cases by <br> tags
                            parts = []
                            current_part = ""
                            
                            for elem in current.contents:
                                if hasattr(elem, 'name') and elem.name in ['br', 'p']:
                                    if current_part:
                                        parts.append(current_part.strip())
                                        current_part = ""
                                else:
                                    if hasattr(elem, 'get_text'):
                                        current_part += elem.get_text()
                                    elif isinstance(elem, str):
                                        current_part += elem
                            
                            # Add the last part if any
                            if current_part:
                                parts.append(current_part.strip())
                                
                            # Process each part as a separate case
                            for part in parts:
                                part_text = clean_text(part)
                                if part_text and (re.search(r' v |vs\.', part_text, re.IGNORECASE) or 
                                                 re.search(r'\[\d{4}\]', part_text) or
                                                 re.search(r'\(\d{4}\)', part_text)):
                                    cases_referred.append(part_text)
                        else:
                            # Add as a single case reference
                            cases_referred.append(case_text)
                        
                        # Extract links from this paragraph
                        links = extract_case_links(current)
                        if links:
                            # If we have multiple cases in one paragraph but single set of links,
                            # associate links with the whole paragraph text
                            cases_with_links.append({
                                'text': case_text,
                                'links': links
                            })
                
                current = current.next_sibling
        
        # If no StartOfIndex, try to find cases in immediately following paragraphs
        else:
            # Find paragraphs that appear to be case citations
            current = cases_section.next_sibling
            end_of_cases = False
            
            while current and not end_of_cases:
                if judgment_header and (current == judgment_header or is_element_after(current, judgment_header)):
                    break
                
                if isinstance(current, Tag) and current.name == 'p':
                    # Check if we've reached the end of the cases section
                    if current.get('align') == 'center' or (current.find('b') and len(current.find('b').get_text()) > 10):
                        # Check if it's a heading-like element
                        if re.search(r'REASONS|JUDGMENT|INTRODUCTION|BACKGROUND', 
                                     current.get_text(), re.IGNORECASE):
                            end_of_cases = True
                            break
                    
                    # Process paragraph if it contains case references
                    case_text = clean_text(current.get_text())
                    if (case_text and 
                        (re.search(r' v |vs\.', case_text, re.IGNORECASE) or 
                         re.search(r'\[\d{4}\]', case_text) or
                         re.search(r'\(\d{4}\)', case_text))):
                        
                        # Extract each case if there are multiple in the paragraph
                        if '<br/>' in str(current) or '<br>' in str(current):
                            # Try to extract individual cases by <br> tags
                            parts = []
                            current_part = ""
                            
                            for elem in current.contents:
                                if hasattr(elem, 'name') and elem.name in ['br', 'p']:
                                    if current_part:
                                        parts.append(current_part.strip())
                                        current_part = ""
                                else:
                                    if hasattr(elem, 'get_text'):
                                        current_part += elem.get_text()
                                    elif isinstance(elem, str):
                                        current_part += elem
                            
                            # Add the last part if any
                            if current_part:
                                parts.append(current_part.strip())
                                
                            # Process each part as a separate case
                            for part in parts:
                                part_text = clean_text(part)
                                if part_text and (re.search(r' v |vs\.', part_text, re.IGNORECASE) or 
                                                 re.search(r'\[\d{4}\]', part_text) or
                                                 re.search(r'\(\d{4}\)', part_text)):
                                    cases_referred.append(part_text)
                        else:
                            # Add as a single case reference
                            cases_referred.append(case_text)
                        
                        # Extract links from this paragraph
                        links = extract_case_links(current)
                        if links:
                            # If we have multiple cases in one paragraph but single set of links,
                            # associate links with the whole paragraph text
                            cases_with_links.append({
                                'text': case_text,
                                'links': links
                            })
                
                current = current.next_sibling
    
    # Clean up and deduplicate the cases list
    cleaned_cases = []
    seen_cases = set()
    
    for case in cases_referred:
        # Some basic normalization to help with deduplication
        normalized = re.sub(r'\s+', ' ', case.lower())
        if normalized not in seen_cases and len(normalized) > 5:  # Avoid very short fragments
            cleaned_cases.append(case)
            seen_cases.add(normalized)
    
    metadata['cases_referred'] = cleaned_cases
    metadata['cases_referred_with_links'] = cases_with_links

def process_representation_tables(soup, metadata, decision_header):
    """Extract representation details from tables in the document"""
    representation = {}
    
    # Find all representation section headers (format: <b>CC XXXX of XXXX</b>)
    cc_headers = []
    for p in soup.find_all('p'):
        if decision_header and is_element_after(p, decision_header):
            continue
            
        b_tag = p.find('b')
        if b_tag and re.match(r'CC\s+\d+\s+of\s+\d+', b_tag.get_text()):
            cc_headers.append(p)
    
    for cc_header in cc_headers:
        cc_name = clean_text(cc_header.get_text())
        representation[cc_name] = {}
        
        # Find Counsel and Solicitors sections that follow this CC header
        current_p = cc_header
        while True:
            next_p = current_p.find_next_sibling('p')
            if not next_p:
                break
                
            current_p = next_p
            
            # Stop if we hit another CC header or the decision header
            if (current_p.find('b') and current_p.find('b').get_text().startswith('CC')) or \
               (decision_header and is_element_after(current_p, decision_header)):
                break
            
            # Look for Counsel or Solicitors headers
            i_tag = current_p.find('i')
            if i_tag and i_tag.get_text() in ['Counsel:', 'Solicitors:']:
                section_type = clean_text(i_tag.get_text()).replace(':', '')
                representation[cc_name][section_type] = {}
                
                # Find the table after this header
                table = current_p.find_next('table')
                if table:
                    rows = table.find_all('tr')
                    for row in rows:
                        cells = row.find_all('td')
                        if len(cells) >= 3:
                            party = clean_text(cells[0].get_text())
                            value = clean_text(cells[2].get_text())
                            if party and value:
                                representation[cc_name][section_type][party] = value
    
    if representation:
        metadata['REPRESENTATION_DETAILS'] = representation

def extract_metadata(soup):
    """Extract metadata from the HTML document with enhanced structure"""
    metadata = {}
    
    # Find the decision header which marks the end of metadata section
    decision_header = find_decision_header(soup)
    if decision_header:
        logging.debug("Found decision header: %s", clean_text(decision_header.get_text()))
    else:
        logging.warning("Could not find 'REASONS FOR DECISION' header")
    
    # Extract title from h1
    h1_tag = soup.find('h1')
    if h1_tag:
        metadata['case_name'] = clean_text(h1_tag.get_text())
        
        # Extract citation from title if possible
        citation_match = re.search(r'\[(\d{4})\]\s+(\w+)\s+(\d+)', metadata['case_name'])
        if citation_match:
            metadata['extracted_citation'] = {
                'year': citation_match.group(1),
                'court': citation_match.group(2),
                'number': citation_match.group(3),
                'full': f"[{citation_match.group(1)}] {citation_match.group(2)} {citation_match.group(3)}"
            }
    
    # Extract "Last Updated" field if present
    last_updated_p = soup.find('p', string=re.compile(r'Last Updated:', re.IGNORECASE))
    if last_updated_p:
        last_updated_text = clean_text(last_updated_p.get_text())
        if "Last Updated:" in last_updated_text:
            date_part = last_updated_text.split("Last Updated:", 1)[1].strip()
            metadata['last_updated'] = date_part
    
    # Extract specific italics sections (Catchwords, Legislation, Result, Category)
    extract_italics_sections(soup, metadata, decision_header)
            
    # Track seen keys to handle duplicates
    seen_keys = {}
    
    # Process first level metadata (bold tags with colon)
    first_level_sections = {}
    bold_tag_info = []
    
    for p in soup.find_all('p'):
        # Skip if after decision header
        if decision_header and is_element_after(p, decision_header):
            continue
        
        # Skip paragraphs with align="center" (likely headers)
        if p.get('align') == 'center':
            continue
        
        # Skip paragraphs with img tags
        if p.find('img'):
            continue
        
        # Look for bold tags with colon in this paragraph
        b_tag = p.find('b')
        if b_tag and ':' in b_tag.get_text():
            b_text = clean_text(b_tag.get_text())
            
            # Skip if it doesn't look like metadata
            if ' v ' in b_text.lower() or '[' in b_text or ']' in b_text:
                continue
                
            # Extract key and value
            key, value_part = b_text.split(':', 1)
            key = key.strip().upper()
            
            # Get the full paragraph text (excluding the bold part)
            para_text = ""
            for elem in p.contents:
                if elem != b_tag:
                    if hasattr(elem, 'get_text'):
                        para_text += elem.get_text()
                    elif isinstance(elem, str):
                        para_text += elem
            
            # Handle duplicate keys
            if key in seen_keys:
                seen_keys[key] += 1
                original_key = key
                key = f"{key}_{seen_keys[key]}"
                logging.debug(f"Found duplicate key {original_key}, renamed to {key}")
            else:
                seen_keys[key] = 0
            
            # Store both the bold text value and the paragraph value
            first_level_sections[key] = {
                'bold_value': value_part.strip(),
                'para_value': clean_text(para_text),
                'position': len(first_level_sections),  # Track order
                'paragraph': p
            }
            
            # Special handling for ACT field - extract links
            if key == "ACT":
                links = []
                for a_tag in p.find_all('a'):
                    links.append({
                        "text": clean_text(a_tag.get_text()),
                        "href": a_tag.get('href', '')
                    })
                
                if links:
                    metadata["ACT_LINKS"] = links
            
            # Add to our list for easy iteration later
            bold_tag_info.append({
                'key': key,
                'tag': b_tag,
                'paragraph': p
            })
    
    # First pass: populate main metadata fields
    for key, info in first_level_sections.items():
        # Use the paragraph value if it's not empty, otherwise use the bold value
        value = info['para_value'] if info['para_value'] else info['bold_value']
        metadata[key] = value
        
        # Enhanced special handling for BETWEEN sections and similar multi-paragraph fields
        special_sections = ["BETWEEN", "FILE NO/S", "APPLICANT", "RESPONDENT", "ACT"]
        
        # Check if key is a special section or contains one of the special section names
        is_special = False
        for special_key in special_sections:
            if key == special_key or special_key in key:
                is_special = True
                break
                
        if is_special:
            process_special_section(soup, key, info['paragraph'], metadata, decision_header)
    
    # Rest of the function remains the same...
    
    # Second pass: process second-level metadata (italics tags)
    subsections = {}
    
    for bold_info in bold_tag_info:
        key = bold_info['key']
        p = bold_info['paragraph']
        
        # Initialize subsections for this key
        if key not in subsections:
            subsections[key] = []
        
        # Find the next paragraph
        current_p = p
        
        # Process italic tags that follow this bold tag
        while True:
            # Get the next paragraph
            next_sibling = current_p.find_next_sibling()
            if not next_sibling:
                break
                
            current_p = next_sibling
            
            # Skip if it's a <br> tag or if it contains a bold tag (new section)
            if current_p.name != 'p' or current_p.find('b'):
                break
            
            # Skip if it contains an img tag
            if current_p.find('img'):
                continue
            
            # Stop if we've reached the decision header
            if decision_header and (current_p == decision_header or is_element_after(current_p, decision_header)):
                break
            
            # Look for italics tags
            i_tag = current_p.find('i')
            if i_tag and ':' in i_tag.get_text():
                i_text = clean_text(i_tag.get_text())
                i_key, i_value_part = i_text.split(':', 1)
                i_key = i_key.strip()
                i_value = i_value_part.strip()
                
                # Store initial subsection
                subsection_entry = {
                    'key': i_key,
                    'value': i_value,
                    'related_content': []
                }
                
                # Get the next paragraph for the value (if it exists and isn't a new section)
                value_p = current_p.find_next_sibling('p')
                if value_p and not value_p.find('b') and not value_p.find('i'):
                    # Add the content of this paragraph
                    subsection_entry['value'] = clean_text(value_p.get_text())
                    
                    # Look for additional related paragraphs until we hit another section
                    next_p = value_p
                    while True:
                        next_p = next_p.find_next_sibling('p')
                        if not next_p:
                            break
                            
                        # Stop if we hit a section marker
                        if next_p.find('b') or next_p.find('i') or (decision_header and is_element_after(next_p, decision_header)):
                            break
                            
                        # Skip paragraphs with img tags
                        if next_p.find('img'):
                            continue
                            
                        content_text = clean_text(next_p.get_text())
                        if content_text:
                            subsection_entry['related_content'].append(content_text)
                    
                    current_p = next_p
                
                # Store the subsection
                subsections[key].append(subsection_entry)
    
    # Add subsections to metadata
    for key, items in subsections.items():
        if items:
            metadata[f"{key}_DETAILS"] = items
    
    # Special handling for REPRESENTATION sections
    process_representation_tables(soup, metadata, decision_header)
    
    # Process cases referred
    process_cases_referred(soup, metadata, decision_header)
    
    return metadata

def extract_single_decision_structure(soup, header, end_elem, header_text):
    """
    Extract the structure of a single decision section
    Captures all text under a heading until the next heading or end of document
    Enhanced to handle different heading styles and list structures
    """
    # Create root section for this decision
    current_section = {
        "title": header_text, 
        "content": ""
    }
    
    # Start from the element after the header
    current_element = header.find_next()
    
    # Collect content parts
    content_parts = []
    
    # Track list structure for proper nesting
    current_list_type = None
    list_items = []
    
    while current_element and current_element != end_elem:
        # Check if we've hit the next heading by class
        if (isinstance(current_element, Tag) and 
            current_element.name == 'p' and 
            current_element.get('class') and 
            current_element.get('class')[0].startswith('h')):
            break
            
        # Check if we've hit the next centered heading
        if (isinstance(current_element, Tag) and 
            current_element.name == 'p' and 
            current_element.get('align') == 'center' and
            (current_element.get_text().isupper() or current_element.find('b'))):
            # Only break if it looks like a major heading
            if len(clean_text(current_element.get_text())) > 5:  # Avoid breaking on short centered elements
                break
        
        # Extract text based on element type
        if isinstance(current_element, Tag):
            # Handle lists specially
            if current_element.name in ['ol', 'ul']:
                current_list_type = current_element.name
                list_items = []
                
                # Process list items
                for li in current_element.find_all('li', recursive=False):
                    item_text = clean_text(li.get_text())
                    if item_text:
                        list_items.append(item_text)
                
                # Add the formatted list
                if list_items:
                    if current_list_type == 'ol':
                        # For ordered lists, use numbers
                        for i, item in enumerate(list_items, 1):
                            content_parts.append(f"{i}. {item}")
                    else:
                        # For unordered lists, use bullets
                        for item in list_items:
                            content_parts.append(f"• {item}")
                    
                    # Reset for next list
                    current_list_type = None
                    list_items = []
            
            # Handle list items directly in the content (not inside a list container)
            elif current_element.name == 'li':
                # Get the list item's value if it exists
                item_value = current_element.get('value', '')
                item_text = clean_text(current_element.get_text())
                
                if item_text:
                    if item_value:
                        content_parts.append(f"{item_value}. {item_text}")
                    else:
                        content_parts.append(f"• {item_text}")
            
            # Handle standard paragraphs
            elif current_element.name == 'p':
                text = clean_text(current_element.get_text())
                if text and not text.startswith('<!--'):
                    content_parts.append(text)
            
            # Handle table elements
            elif current_element.name == 'table':
                # Extract table as formatted text
                table_text = []
                rows = current_element.find_all('tr')
                
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    row_text = []
                    
                    for cell in cells:
                        cell_text = clean_text(cell.get_text())
                        if cell_text:
                            row_text.append(cell_text)
                    
                    if row_text:
                        table_text.append(" | ".join(row_text))
                
                if table_text:
                    content_parts.append("\n".join(table_text))
            
            # For other elements, just get the text
            else:
                text = clean_text(current_element.get_text())
                if text and not text.startswith('<!--'):
                    content_parts.append(text)
        
        # Move to next element
        current_element = current_element.find_next()
    
    # Join content parts
    current_section['content'] = "\n\n".join(content_parts)
    
    return current_section

def extract_centered_headings(soup):
    """
    Find all centered paragraphs that appear to be headings in the document.
    This is an alternative to class-based headings.
    """
    centered_headings = []
    
    # First identify the decision/judgment header which marks the start of the decision content
    decision_start = None
    for p in soup.find_all('p', align='center'):
        if re.search(r'REASONS FOR DECISION|JUDGMENT', p.get_text(), re.IGNORECASE):
            decision_start = p
            centered_headings.append(p)
            break
    
    if not decision_start:
        return []
    
    # Look for other centered paragraphs after the decision start
    current = decision_start.next_sibling
    
    while current:
        if isinstance(current, Tag) and current.name == 'p' and current.get('align') == 'center':
            # Check if it looks like a heading (all uppercase, or has bold tag)
            text = clean_text(current.get_text())
            if (text and (text.isupper() or current.find('b'))):
                centered_headings.append(current)
        
        current = current.next_sibling
    
    return centered_headings

def extract_decision_structure(soup):
    """
    Extract the structure of all headings from the document.
    Enhanced to handle both class-based and centered headings.
    """
    decisions = []
    
    # First try to find class-based headings
    headings = soup.find_all('p', class_=lambda value: value and value.startswith('h'))
    
    # If no class-based headings, try centered headings
    if not headings:
        headings = extract_centered_headings(soup)
        
        if not headings:
            # As a last resort, look for numbered list items that might be top-level sections
            judgment_started = False
            potential_headings = []
            
            # Find the judgment header first
            for p in soup.find_all('p'):
                if re.search(r'REASONS FOR DECISION|JUDGMENT', p.get_text(), re.IGNORECASE):
                    judgment_started = True
                    potential_headings.append(p)
                    break
            
            if judgment_started:
                # Find list items with value="1" which often start main sections
                for li in soup.find_all('li', attrs={'value': '1'}):
                    if li.parent and li.parent.name == 'ol':
                        potential_headings.append(li)
            
            if potential_headings:
                headings = potential_headings
            else:
                logging.warning("Could not find any headings")
                return decisions
    
    # For each heading, extract its content
    for i, header in enumerate(headings):
        # Determine the end of this section (start of next heading or end of document)
        end_elem = None
        if i < len(headings) - 1:
            end_elem = headings[i+1]
        
        # Extract structure for this section
        decision = extract_single_decision_structure(soup, header, end_elem, clean_text(header.get_text()))
        decisions.append(decision)
    
    return decisions

def parse_html_file(file_info):
    """Parse a single HTML file and return structured data"""
    try:
        with open(file_info['path'], 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract metadata
        metadata = extract_metadata(soup)
        
        # Extract decision structure
        decisions = extract_decision_structure(soup)
        
        # Combine into a single structure
        result = {
            'case_number': file_info['case_number'],
            'year': file_info['year'],
            'metadata': metadata,
            'decisions': decisions
        }
        
        return result
    except Exception as e:
        logging.error(f"Error parsing file {file_info['path']}: {str(e)}")
        import traceback
        logging.error(traceback.format_exc())
        return None

def save_json_file(parsed_data, file_info):
    """
    Save parsed data to a JSON file.
    Enhanced to handle various file naming conventions.
    """
    if not parsed_data:
        return False
    
    # Create directory for year if it doesn't exist
    year_dir = os.path.join(JSON_DIR, file_info['year'])
    os.makedirs(year_dir, exist_ok=True)
    
    # Save file with the same case number as the HTML file
    json_path = os.path.join(year_dir, f"{file_info['case_number']}.json")
    try:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(parsed_data, f, indent=2, ensure_ascii=False)
        
        logging.info(f"Saved JSON to {os.path.relpath(json_path)}")
        return True
    except Exception as e:
        logging.error(f"Error saving JSON file {json_path}: {str(e)}")
        return False

def get_html_files(year=None, case_number=None, file_path=None):
    """
    Get HTML files to parse, optionally filtered by year and/or case number or specific file path.
    Enhanced to find ALL HTML files in all directories and subdirectories.
    """
    html_files = []
    
    # If a specific file path is provided, use that
    if file_path:
        if not os.path.exists(file_path):
            logging.error(f"File not found: {file_path}")
            return html_files
        
        # Extract case number from file name (without extension)
        file_name = os.path.basename(file_path)
        case_number = os.path.splitext(file_name)[0]
        
        # Try to determine year from path structure
        path_parts = Path(file_path).parts
        year = None
        for part in path_parts:
            if part.isdigit() and len(part) == 4:
                year = part
                break
        
        if not year:
            year = "unknown"
        
        html_files.append({
            'year': year,
            'case_number': case_number,
            'path': file_path
        })
        
        return html_files
    
    # Check if BY_YEAR_DIR exists
    if not os.path.exists(BY_YEAR_DIR):
        logging.error(f"by_year directory not found at: {BY_YEAR_DIR}")
        return html_files
    
    if year:
        # Look in specific year directory
        year_dir = os.path.join(BY_YEAR_DIR, str(year))
        if not os.path.exists(year_dir):
            logging.error(f"Year directory not found: {year_dir}")
            return html_files
        
        # Look for specific case number if provided
        if case_number:
            # Try different possible filenames
            potential_files = [
                os.path.join(year_dir, f"{case_number}.html"),  # Standard format
                os.path.join(year_dir, f"{case_number}.htm"),   # Alternative extension
            ]
            
            for file_path in potential_files:
                if os.path.exists(file_path):
                    html_files.append({
                        'year': year,
                        'case_number': case_number,
                        'path': file_path
                    })
                    break
            else:
                logging.warning(f"Case file not found for case number {case_number} in year {year}")
        else:
            # Get all HTML files in this year and its subdirectories
            files_found = find_all_html_files(year_dir, year)
            html_files.extend(files_found)
            logging.info(f"Found {len(files_found)} HTML files in year {year} and its subdirectories")
    else:
        # Traverse all directories
        total_files = 0
        all_dirs = []
        
        try:
            all_dirs = sorted(os.listdir(BY_YEAR_DIR))
            logging.info(f"Found {len(all_dirs)} directories in by_year: {', '.join(all_dirs)}")
        except Exception as e:
            logging.error(f"Error listing directories in {BY_YEAR_DIR}: {str(e)}")
            return html_files
        
        # Process each directory
        for dir_name in all_dirs:
            dir_path = os.path.join(BY_YEAR_DIR, dir_name)
            
            # Skip if not a directory
            if not os.path.isdir(dir_path):
                logging.debug(f"Skipping non-directory: {dir_name}")
                continue
            
            # Find all HTML files in this directory and subdirectories
            dir_files = find_all_html_files(dir_path, dir_name)
            html_files.extend(dir_files)
            
            # Report the count
            if dir_files:
                dir_type = "year" if dir_name.isdigit() and len(dir_name) == 4 else "directory"
                logging.info(f"Found {len(dir_files)} HTML files in {dir_type} {dir_name}")
                total_files += len(dir_files)
        
        logging.info(f"Total HTML files found across all directories: {total_files}")
    
    # Sort files by year and case number for consistent processing
    # For case numbers, try to sort numerically if they're all numbers
    def sort_key(file_info):
        case_num = file_info['case_number']
        # Try to convert to int for numerical sorting
        try:
            if case_num.isdigit():
                return (file_info['year'], int(case_num))
        except:
            pass
        # Fall back to string sorting
        return (file_info['year'], case_num)
    
    html_files.sort(key=sort_key)
    
    return html_files

def find_all_html_files(dir_path, parent_name):
    """
    Recursively find all HTML files in a directory and its subdirectories.
    """
    html_files = []
    
    try:
        # Get all files and directories in this directory
        for item in os.listdir(dir_path):
            item_path = os.path.join(dir_path, item)
            
            # If it's a directory, recurse into it
            if os.path.isdir(item_path):
                # For subdirectories, still associate with parent directory
                subdir_files = find_all_html_files(item_path, parent_name)
                html_files.extend(subdir_files)
            
            # If it's an HTML file, add it to our list
            elif item.lower().endswith(('.html', '.htm')):
                case_number = os.path.splitext(item)[0]
                html_files.append({
                    'year': parent_name,
                    'case_number': case_number,
                    'path': item_path
                })
    except Exception as e:
        logging.error(f"Error accessing directory {dir_path}: {str(e)}")
    
    return html_files

def parse_files(files, limit=None):
    """
    Parse multiple HTML files and save as JSON.
    Enhanced with better error handling and progress reporting.
    """
    total_files = len(files)
    successful = 0
    failed = 0
    
    if limit and limit > 0 and limit < len(files):
        files = files[:limit]
        logging.info(f"Limited processing to first {limit} files")
    
    # Group files by year for better reporting
    files_by_year = {}
    for file_info in files:
        year = file_info['year']
        if year not in files_by_year:
            files_by_year[year] = []
        files_by_year[year].append(file_info)
    
    logging.info(f"Processing files from {len(files_by_year)} years")
    
    # Process files year by year
    for year, year_files in sorted(files_by_year.items()):
        year_success = 0
        year_failed = 0
        
        logging.info(f"Starting to process {len(year_files)} files from year {year}")
        
        for i, file_info in enumerate(year_files):
            try:
                logging.info(f"Parsing file {i+1}/{len(year_files)} from year {year}: {file_info['path']}")
                
                parsed_data = parse_html_file(file_info)
                
                if parsed_data and save_json_file(parsed_data, file_info):
                    successful += 1
                    year_success += 1
                else:
                    failed += 1
                    year_failed += 1
                
                # Log progress for this year
                if (i+1) % 10 == 0 or i+1 == len(year_files):
                    logging.info(f"Year {year} progress: {i+1}/{len(year_files)} files processed ({year_success} successful, {year_failed} failed)")
            except Exception as e:
                logging.error(f"Unexpected error processing file {file_info['path']}: {str(e)}")
                import traceback
                logging.error(traceback.format_exc())
                failed += 1
                year_failed += 1
        
        # Log summary for this year
        logging.info(f"Completed year {year}: {year_success} successful, {year_failed} failed")
    
    # Log overall progress
    logging.info(f"Parsing complete: {successful}/{total_files} successful ({failed} failed)")
    return successful, failed

def main():
    """
    Main function - Parse HTML case files to structured JSON with improved metadata extraction
    
    Key enhancements:
    1. Better handling of BETWEEN sections to capture all content until the next section
    2. Enhanced cases_referred extraction that includes links to referenced cases
    3. Improved citation extraction from case titles
    4. Better handling of special sections like APPLICANT and RESPONDENT
    5. More robust parsing of multi-paragraph sections
    6. Proper handling of italics sections like Catchwords, Legislation, Result, and Category
    7. Improved decision structure extraction from different heading styles
    8. Comprehensive year directory processing with detailed logging
    """
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Parse HTML case files to structured JSON")
    parser.add_argument('--year', type=str, help='Process files from specific year')
    parser.add_argument('--case', type=str, help='Process specific case number')
    parser.add_argument('--limit', type=int, help='Limit the number of files to process')
    parser.add_argument('--file', type=str, help='Process a specific file (full path)')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    args = parser.parse_args()
    
    # Set up logging
    logger = setup_logging(args.debug)
    
    logging.info("Starting enhanced WASAT HTML parser")
    logging.info(f"Base directory: {BASE_DIR}")
    logging.info(f"HTML directory: {HTML_DIR}")
    logging.info(f"Output directory: {JSON_DIR}")
    
    # Verify essential directories exist
    for dir_path in [BASE_DIR, DATA_DIR, HTML_DIR, BY_YEAR_DIR, PARSED_DIR, JSON_DIR]:
        if not os.path.exists(dir_path):
            logging.warning(f"Directory does not exist: {dir_path}")
            os.makedirs(dir_path, exist_ok=True)
            logging.info(f"Created directory: {dir_path}")
    
    # Check if BY_YEAR_DIR is accessible and has content
    if not os.path.exists(BY_YEAR_DIR):
        logging.error(f"by_year directory not found: {BY_YEAR_DIR}")
        return
    
    if not os.access(BY_YEAR_DIR, os.R_OK):
        logging.error(f"No read permission for directory: {BY_YEAR_DIR}")
        return
    
    try:
        if len(os.listdir(BY_YEAR_DIR)) == 0:
            logging.warning(f"by_year directory is empty: {BY_YEAR_DIR}")
    except Exception as e:
        logging.error(f"Error accessing by_year directory: {str(e)}")
        return
    
    # Get HTML files to process
    html_files = get_html_files(args.year, args.case, args.file)
    
    if not html_files:
        logging.warning("No HTML files found to process")
        return
    
    logging.info(f"Found {len(html_files)} total HTML files to process")
    
    # Parse files
    parse_files(html_files, args.limit)

if __name__ == "__main__":
    main()