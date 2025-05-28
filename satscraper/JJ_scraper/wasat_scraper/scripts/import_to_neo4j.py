#!/usr/bin/env python3
"""
import_to_neo4j.py - Imports reformatted WASAT case JSON data into Neo4j.

This script reads the reformatted JSON files from the processed directory and creates
a Neo4j graph database with nodes for Cases, Laws, and Law Sections, and relationships
between them.

Usage:
    python import_to_neo4j.py [--input INPUT_DIR] [--uri NEO4J_URI] [--user NEO4J_USER] [--password NEO4J_PASSWORD] [--clean]
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Set
import glob

try:
    from neo4j import GraphDatabase
except ImportError:
    print("neo4j package not found. Please install it using:")
    print("pip install neo4j")
    sys.exit(1)

# Get the script directory and project base directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)

# Default paths
DATA_DIR = os.path.join(BASE_DIR, "data")
INPUT_DIR = os.path.join(DATA_DIR, "processed", "reformatted_neo4j")
LOG_DIR = os.path.join(BASE_DIR, "logs")
LOG_FILE = os.path.join(LOG_DIR, "import_to_neo4j_logs.txt")

# Default Neo4j connection
DEFAULT_NEO4J_URI = "bolt://localhost:7687"
DEFAULT_NEO4J_USER = "neo4j"
DEFAULT_NEO4J_PASSWORD = "88888888"

# Configure logging
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class Neo4jImporter:
    """Imports data into Neo4j database."""
    
    def __init__(self, input_dir: str = INPUT_DIR, uri: str = DEFAULT_NEO4J_URI, 
                 user: str = DEFAULT_NEO4J_USER, password: str = DEFAULT_NEO4J_PASSWORD,
                 clean_db: bool = False):
        """Initialize the importer with connection details."""
        self.input_dir = Path(input_dir)
        self.uri = uri
        self.user = user
        self.password = password
        self.clean_db = clean_db
        self.driver = None
        
        # Track entities to avoid duplicates
        self.cases_processed = set()
        self.laws_processed = set()
        self.sections_processed = set()
        
        # Connect to Neo4j
        self._connect()
        
    def _connect(self):
        """Connect to Neo4j database."""
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            logger.info(f"Connected to Neo4j at {self.uri}")
            
            # Test connection
            with self.driver.session() as session:
                result = session.run("MATCH (n) RETURN count(n) as count")
                count = result.single()["count"]
                logger.info(f"Database contains {count} nodes")
                
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {str(e)}")
            raise
    
    def close(self):
        """Close the Neo4j connection."""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j connection closed")
    
    def clean_database(self):
        """Clean the database by removing all nodes and relationships."""
        logger.info("Cleaning database...")
        
        try:
            with self.driver.session() as session:
                # First delete all relationships
                result = session.run("MATCH ()-[r]-() DELETE r")
                
                # Then delete all nodes
                result = session.run("MATCH (n) DELETE n")
                
                logger.info("Database cleaned successfully")
        except Exception as e:
            logger.error(f"Error cleaning database: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
    
    def setup_constraints(self):
        """Set up constraints for nodes to ensure uniqueness."""
        constraints = [
            "CREATE CONSTRAINT case_citation IF NOT EXISTS FOR (c:Case) REQUIRE c.citation_number IS UNIQUE",
            "CREATE CONSTRAINT law_title IF NOT EXISTS FOR (l:Law) REQUIRE l.law_id IS UNIQUE",
            "CREATE CONSTRAINT section_id IF NOT EXISTS FOR (s:LawSection) REQUIRE (s.law_id, s.section_id) IS UNIQUE"
        ]
        
        with self.driver.session() as session:
            for constraint in constraints:
                try:
                    session.run(constraint)
                except Exception as e:
                    logger.error(f"Error creating constraint: {str(e)}")
    
    def import_all_files(self):
        """Import all JSON files from the input directory."""
        # Clean database if requested
        if self.clean_db:
            self.clean_database()
        
        # Setup constraints first
        self.setup_constraints()
        
        # Get all JSON files
        json_files = []
        
        # Find year directories
        year_dirs = [d for d in self.input_dir.iterdir() if d.is_dir() and d.name.isdigit()]
        
        if year_dirs:
            for year_dir in sorted(year_dirs):
                json_files.extend(list(year_dir.glob('*.json')))
        else:
            json_files = list(self.input_dir.glob('**/*.json'))
        
        total_files = len(json_files)
        logger.info(f"Found {total_files} JSON files to import")
        
        # Track progress
        imported = 0
        
        # Import each file
        for json_file in json_files:
            try:
                self.import_file(json_file)
                imported += 1
                if imported % 10 == 0:
                    logger.info(f"Imported {imported}/{total_files} files")
            except Exception as e:
                logger.error(f"Error importing {json_file}: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
        
        logger.info(f"Import complete. Imported {imported}/{total_files} files.")
        
        # Log stats
        logger.info(f"Created {len(self.cases_processed)} unique Case nodes")
        logger.info(f"Created {len(self.laws_processed)} unique Law nodes")
        logger.info(f"Created {len(self.sections_processed)} unique LawSection nodes")
    
    def import_file(self, file_path: Path):
        """Import a single JSON file into Neo4j."""
        # Load the JSON file
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Get case info
        case_citation = data.get('citation_number', '')
        
        # If empty, try to use filename as last resort
        if not case_citation:
            case_number = file_path.stem
            year = file_path.parent.name
            case_citation = f"[{year}] WASAT {case_number}"
            logger.warning(f"Using generated citation for {file_path}: {case_citation}")
            
        case_url = data.get('case_url', '')
        
        # Skip if still no citation
        if not case_citation:
            logger.warning(f"Skipping file with no citation: {file_path}")
            return
        
        # Create the case node if it doesn't exist
        self.create_case_node(case_citation, case_url)
        
        # Process legislations structured
        self.process_legislations_structured(case_citation, data.get('legislations_structured', []))
        
        # Process referred cases structured
        self.process_referred_cases_structured(case_citation, data.get('referred_cases_structured', []))
    
    def create_case_node(self, citation: str, url: str):
        """Create a Case node if it doesn't exist yet."""
        if citation in self.cases_processed:
            return
        
        cypher = """
        MERGE (c:Case {citation_number: $citation})
        ON CREATE SET c.url = $url
        RETURN c
        """
        
        with self.driver.session() as session:
            session.run(cypher, citation=citation, url=url)
        
        self.cases_processed.add(citation)
    
    def process_legislations_structured(self, case_citation: str, legislations: List[Dict]):
        """Process structured legislation items and create relations to the case."""
        for legislation in legislations:
            law_title = legislation.get('law_title', '')
            law_link = legislation.get('law_link', '')
            sections = legislation.get('sections', [])
            
            # Use the law_title as the law_id
            law_id = law_title
            
            # Skip if no law_id
            if not law_id:
                logger.warning(f"Skipping legislation with no law_title")
                continue
            
            # Create Law node
            self.create_law_node(law_id, law_title, law_link)
            
            # Create CITES relationship from Case to Law
            self.create_cites_relationship(case_citation, 'Law', law_id, law_title)
            
            # Process each section
            for section in sections:
                section_title = section.get('section_title', '')
                section_link = section.get('section_link', '')
                
                # Generate a section_id from the section_title
                section_id = self._extract_section_id_from_title(section_title)
                
                # Skip if no section_id
                if not section_id:
                    logger.warning(f"Skipping section with no extractable section_id: {section_title}")
                    continue
                
                # Create LawSection node
                self.create_law_section_node(law_id, section_id, section_title, section_link)
                
                # Create CITES relationship from Case to LawSection
                self.create_cites_relationship(case_citation, 'LawSection', f"{law_id}:{section_id}", section_title)
                
                # Create HAS_SECTION relationship from Law to LawSection
                self.create_has_section_relationship(law_id, section_id)
    
    def _extract_section_id_from_title(self, section_title: str) -> str:
        """Extract a section_id from a section_title like 's 29(1)'."""
        if not section_title:
            return ""
            
        try:
            # Extract section id from patterns like "s 29(1)", "section 29" etc.
            import re
            match = re.search(r'(?:s|section)\s*([^(\s]+)(?:\(([^)]+)\))?', section_title.lower())
            if match:
                section_num = match.group(1)
                subsection = match.group(2)
                if subsection:
                    return f"{section_num}_{subsection}"
                return section_num
                
            # Fallback to using the whole title if no pattern matches
            return section_title.replace(' ', '_').lower()
            
        except Exception as e:
            logger.error(f"Error extracting section_id from {section_title}: {str(e)}")
            
        return ""
    
    def create_law_node(self, law_id: str, text: str, href: str):
        """Create a Law node if it doesn't exist yet."""
        if law_id in self.laws_processed:
            return
        
        cypher = """
        MERGE (l:Law {law_id: $law_id})
        ON CREATE SET l.text = $text, l.url = $href
        RETURN l
        """
        
        with self.driver.session() as session:
            session.run(cypher, law_id=law_id, text=text, href=href)
        
        self.laws_processed.add(law_id)
    
    def create_law_section_node(self, law_id: str, section_id: str, text: str, href: str):
        """Create a LawSection node if it doesn't exist yet."""
        section_key = f"{law_id}:{section_id}"
        if section_key in self.sections_processed:
            return
        
        cypher = """
        MERGE (s:LawSection {law_id: $law_id, section_id: $section_id})
        ON CREATE SET s.text = $text, s.url = $href
        RETURN s
        """
        
        with self.driver.session() as session:
            session.run(cypher, law_id=law_id, section_id=section_id, text=text, href=href)
        
        self.sections_processed.add(section_key)
    
    def create_cites_relationship(self, case_citation: str, target_type: str, target_id: str, text: str):
        """Create a CITES relationship from a Case to a Law or LawSection."""
        cypher = ""
        params = {"case_citation": case_citation, "text": text}
        
        if target_type == 'Law':
            cypher = """
            MATCH (c:Case {citation_number: $case_citation})
            MATCH (l:Law {law_id: $target_id})
            MERGE (c)-[r:CITES]->(l)
            RETURN r
            """
            params["target_id"] = target_id
            
        elif target_type == 'LawSection':
            law_id, section_id = target_id.split(':')
            cypher = """
            MATCH (c:Case {citation_number: $case_citation})
            MATCH (s:LawSection {law_id: $law_id, section_id: $section_id})
            MERGE (c)-[r:CITES]->(s)
            RETURN r
            """
            params["law_id"] = law_id
            params["section_id"] = section_id
        
        with self.driver.session() as session:
            session.run(cypher, **params)
    
    def create_has_section_relationship(self, law_id: str, section_id: str):
        """Create a HAS_SECTION relationship from a Law to a LawSection."""
        cypher = """
        MATCH (l:Law {law_id: $law_id})
        MATCH (s:LawSection {law_id: $law_id, section_id: $section_id})
        MERGE (l)-[r:HAS_SECTION]->(s)
        RETURN r
        """
        
        with self.driver.session() as session:
            session.run(cypher, law_id=law_id, section_id=section_id)
    
    def process_referred_cases_structured(self, case_citation: str, referred_cases: List[Dict]):
        """Process structured referred cases and create REFERS_TO relationships."""
        for ref_case in referred_cases:
            ref_citation = ref_case.get('citation_number', '')
            ref_url = ref_case.get('case_url', '')
            
            # Skip if no citation
            if not ref_citation:
                continue
            
            # Create the referred case node if it doesn't exist
            self.create_case_node(ref_citation, ref_url)
            
            # Create REFERS_TO relationship
            self.create_refers_to_relationship(case_citation, ref_citation)
    
    def create_refers_to_relationship(self, from_citation: str, to_citation: str):
        """Create a REFERS_TO relationship between two cases."""
        cypher = """
        MATCH (c1:Case {citation_number: $from_citation})
        MATCH (c2:Case {citation_number: $to_citation})
        MERGE (c1)-[r:REFERS_TO]->(c2)
        RETURN r
        """
        
        with self.driver.session() as session:
            session.run(cypher, from_citation=from_citation, to_citation=to_citation)

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description='Import reformatted WASAT case JSON data into Neo4j.')
    parser.add_argument('--input', default=INPUT_DIR, help='Input directory containing reformatted JSON files')
    parser.add_argument('--uri', default=DEFAULT_NEO4J_URI, help='Neo4j connection URI')
    parser.add_argument('--user', default=DEFAULT_NEO4J_USER, help='Neo4j username')
    parser.add_argument('--password', default=DEFAULT_NEO4J_PASSWORD, help='Neo4j password')
    parser.add_argument('--clean', action='store_true', help='Clean the database before importing')
    args = parser.parse_args()
    
    importer = Neo4jImporter(
        input_dir=args.input,
        uri=args.uri,
        user=args.user,
        password=args.password,
        clean_db=args.clean
    )
    
    try:
        importer.import_all_files()
    finally:
        importer.close()

if __name__ == '__main__':
    main()
