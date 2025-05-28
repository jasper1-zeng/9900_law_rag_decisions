#!/usr/bin/env python3
"""
import_to_neo4j_aura.py - Imports reformatted WASAT case JSON data directly to Neo4j Aura.

This script reads the reformatted JSON files from the processed directory and creates
a Neo4j Aura graph database with nodes for Cases, Laws, and Law Sections, and relationships
between them.

Usage:
    python import_to_neo4j_aura.py [--input INPUT_DIR] [--uri NEO4J_AURA_URI] [--user NEO4J_USER] [--password NEO4J_PASSWORD] [--clean]
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Set
import re
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
LOG_FILE = os.path.join(LOG_DIR, "import_to_neo4j_aura_logs.txt")

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

class Neo4jAuraImporter:
    """Imports data directly into Neo4j Aura database."""
    
    def __init__(self, input_dir: str = INPUT_DIR, uri: str = None, 
                 user: str = None, password: str = None,
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
        
        # Connect to Neo4j Aura
        self._connect()
        
    def _connect(self):
        """Connect to Neo4j Aura database."""
        if not self.uri or not self.user or not self.password:
            raise ValueError("Neo4j Aura URI, username, and password are required")
            
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            logger.info(f"Connected to Neo4j Aura at {self.uri}")
            
            # Test connection
            with self.driver.session() as session:
                result = session.run("MATCH (n) RETURN count(n) as count")
                count = result.single()["count"]
                logger.info(f"Database contains {count} nodes")
                
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j Aura: {str(e)}")
            raise
    
    def close(self):
        """Close the Neo4j connection."""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j Aura connection closed")
    
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
            "CREATE CONSTRAINT case_id IF NOT EXISTS FOR (c:Case) REQUIRE c.citation_number IS UNIQUE",
            "CREATE CONSTRAINT law_id IF NOT EXISTS FOR (l:Law) REQUIRE l.law_id IS UNIQUE",
            "CREATE CONSTRAINT section_id IF NOT EXISTS FOR (s:LawSection) REQUIRE s.unique_id IS UNIQUE"
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
        
        # Import each file in batches for better performance
        batch_size = 100
        current_batch = []
        
        for json_file in json_files:
            try:
                # Process the file and get data to import
                data = self.process_file(json_file)
                if data:
                    current_batch.append(data)
                
                # If batch is full or this is the last file, import the batch
                if len(current_batch) >= batch_size or json_file == json_files[-1]:
                    self.import_batch(current_batch)
                    imported += len(current_batch)
                    logger.info(f"Imported {imported}/{total_files} files")
                    current_batch = []
                    
            except Exception as e:
                logger.error(f"Error importing {json_file}: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
        
        logger.info(f"Import complete. Imported {imported}/{total_files} files.")
        
        # Log stats
        logger.info(f"Created {len(self.cases_processed)} unique Case nodes")
        logger.info(f"Created {len(self.laws_processed)} unique Law nodes")
        logger.info(f"Created {len(self.sections_processed)} unique LawSection nodes")
    
    def process_file(self, file_path: Path) -> Dict:
        """Process a single JSON file and extract data for Neo4j import."""
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
        
        # Skip if still no citation
        if not case_citation:
            logger.warning(f"Skipping file with no citation: {file_path}")
            return None
        
        return {
            'case_citation': case_citation,
            'case_url': data.get('case_url', ''),
            'legislations': data.get('legislations_structured', []),
            'referred_cases': data.get('referred_cases_structured', [])
        }
    
    def import_batch(self, batch: List[Dict]):
        """Import a batch of processed files to Neo4j."""
        # Group data by type for batch processing
        case_nodes = []
        law_nodes = []
        section_nodes = []
        case_law_rels = []
        case_section_rels = []
        case_case_rels = []
        law_section_rels = []
        
        # Process each file data
        for data in batch:
            case_citation = data['case_citation']
            case_url = data['case_url']
            
            # Add case node
            if case_citation not in self.cases_processed:
                case_nodes.append({
                    'citation_number': case_citation,
                    'url': case_url
                })
                self.cases_processed.add(case_citation)
            
            # Process legislations
            for legislation in data['legislations']:
                law_title = legislation.get('law_title', '')
                law_link = legislation.get('law_link', '')
                
                # Skip if no law_title
                if not law_title:
                    continue
                
                # Add law node
                if law_title not in self.laws_processed:
                    law_nodes.append({
                        'law_id': law_title,
                        'text': law_title,
                        'url': law_link
                    })
                    self.laws_processed.add(law_title)
                
                # Add case-law relationship
                case_law_rels.append({
                    'from': case_citation,
                    'to': law_title
                })
                
                # Process sections
                for section in legislation.get('sections', []):
                    section_title = section.get('section_title', '')
                    section_link = section.get('section_link', '')
                    
                    # Generate section_id
                    section_id = self._extract_section_id_from_title(section_title)
                    
                    # Skip if no section_id
                    if not section_id:
                        continue
                    
                    # Create unique section ID
                    unique_section_id = f"{law_title}:{section_id}"
                    
                    # Add section node
                    if unique_section_id not in self.sections_processed:
                        section_nodes.append({
                            'law_id': law_title,
                            'section_id': section_id,
                            'unique_id': unique_section_id,
                            'text': section_title,
                            'url': section_link
                        })
                        self.sections_processed.add(unique_section_id)
                    
                    # Add case-section relationship
                    case_section_rels.append({
                        'from': case_citation,
                        'to': unique_section_id
                    })
                    
                    # Add law-section relationship
                    law_section_rels.append({
                        'from': law_title,
                        'to': unique_section_id
                    })
            
            # Process referred cases
            for ref_case in data['referred_cases']:
                ref_citation = ref_case.get('citation_number', '')
                ref_url = ref_case.get('case_url', '')
                
                # Skip if no citation
                if not ref_citation:
                    continue
                
                # Add referred case node
                if ref_citation not in self.cases_processed:
                    case_nodes.append({
                        'citation_number': ref_citation,
                        'url': ref_url
                    })
                    self.cases_processed.add(ref_citation)
                
                # Add case-case relationship
                case_case_rels.append({
                    'from': case_citation,
                    'to': ref_citation
                })
        
        # Batch create nodes
        self.batch_create_case_nodes(case_nodes)
        self.batch_create_law_nodes(law_nodes)
        self.batch_create_section_nodes(section_nodes)
        
        # Batch create relationships
        self.batch_create_case_law_rels(case_law_rels)
        self.batch_create_case_section_rels(case_section_rels)
        self.batch_create_case_case_rels(case_case_rels)
        self.batch_create_law_section_rels(law_section_rels)
    
    def batch_create_case_nodes(self, nodes: List[Dict]):
        """Create Case nodes in batch."""
        if not nodes:
            return
            
        cypher = """
        UNWIND $nodes as node
        MERGE (c:Case {citation_number: node.citation_number})
        ON CREATE SET c.url = node.url
        """
        
        with self.driver.session() as session:
            session.run(cypher, nodes=nodes)
    
    def batch_create_law_nodes(self, nodes: List[Dict]):
        """Create Law nodes in batch."""
        if not nodes:
            return
            
        cypher = """
        UNWIND $nodes as node
        MERGE (l:Law {law_id: node.law_id})
        ON CREATE SET l.text = node.text, l.url = node.url
        """
        
        with self.driver.session() as session:
            session.run(cypher, nodes=nodes)
    
    def batch_create_section_nodes(self, nodes: List[Dict]):
        """Create LawSection nodes in batch."""
        if not nodes:
            return
            
        cypher = """
        UNWIND $nodes as node
        MERGE (s:LawSection {unique_id: node.unique_id})
        ON CREATE SET 
            s.law_id = node.law_id,
            s.section_id = node.section_id,
            s.text = node.text,
            s.url = node.url
        """
        
        with self.driver.session() as session:
            session.run(cypher, nodes=nodes)
    
    def batch_create_case_law_rels(self, rels: List[Dict]):
        """Create Case-Law relationships in batch."""
        if not rels:
            return
            
        cypher = """
        UNWIND $rels as rel
        MATCH (c:Case {citation_number: rel.from})
        MATCH (l:Law {law_id: rel.to})
        MERGE (c)-[r:CITES]->(l)
        """
        
        with self.driver.session() as session:
            session.run(cypher, rels=rels)
    
    def batch_create_case_section_rels(self, rels: List[Dict]):
        """Create Case-Section relationships in batch."""
        if not rels:
            return
            
        cypher = """
        UNWIND $rels as rel
        MATCH (c:Case {citation_number: rel.from})
        MATCH (s:LawSection {unique_id: rel.to})
        MERGE (c)-[r:CITES]->(s)
        """
        
        with self.driver.session() as session:
            session.run(cypher, rels=rels)
    
    def batch_create_case_case_rels(self, rels: List[Dict]):
        """Create Case-Case relationships in batch."""
        if not rels:
            return
            
        cypher = """
        UNWIND $rels as rel
        MATCH (c1:Case {citation_number: rel.from})
        MATCH (c2:Case {citation_number: rel.to})
        MERGE (c1)-[r:REFERS_TO]->(c2)
        """
        
        with self.driver.session() as session:
            session.run(cypher, rels=rels)
    
    def batch_create_law_section_rels(self, rels: List[Dict]):
        """Create Law-Section relationships in batch."""
        if not rels:
            return
            
        cypher = """
        UNWIND $rels as rel
        MATCH (l:Law {law_id: rel.from})
        MATCH (s:LawSection {unique_id: rel.to})
        MERGE (l)-[r:HAS_SECTION]->(s)
        """
        
        with self.driver.session() as session:
            session.run(cypher, rels=rels)
    
    def _extract_section_id_from_title(self, section_title: str) -> str:
        """Extract a section_id from a section_title like 's 29(1)'."""
        if not section_title:
            return ""
            
        try:
            # Extract section id from patterns like "s 29(1)", "section 29" etc.
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

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description='Import reformatted WASAT case JSON data into Neo4j Aura.')
    parser.add_argument('--input', default=INPUT_DIR, help='Input directory containing reformatted JSON files')
    parser.add_argument('--uri', required=True, help='Neo4j Aura connection URI (required)')
    parser.add_argument('--user', required=True, help='Neo4j Aura username (required)')
    parser.add_argument('--password', required=True, help='Neo4j Aura password (required)')
    parser.add_argument('--clean', action='store_true', help='Clean the database before importing')
    args = parser.parse_args()
    
    importer = Neo4jAuraImporter(
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