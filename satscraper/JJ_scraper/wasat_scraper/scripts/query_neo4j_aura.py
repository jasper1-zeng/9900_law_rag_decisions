#!/usr/bin/env python3
"""
query_neo4j_aura.py - Query Neo4j Aura database directly from Python.

This script connects to your Neo4j Aura database and allows you to:
1. Run Cypher queries and view the results
2. Get database statistics
3. Run some sample predefined queries

Usage:
    python query_neo4j_aura.py --uri NEO4J_AURA_URI --user NEO4J_USER --password NEO4J_PASSWORD [--query "CYPHER QUERY"]
"""

import os
import sys
import json
import argparse
import logging
import pandas as pd
from typing import Dict, List, Optional
from tabulate import tabulate

try:
    from neo4j import GraphDatabase
except ImportError:
    print("neo4j package not found. Please install it using:")
    print("pip install neo4j")
    sys.exit(1)

try:
    import tabulate
except ImportError:
    print("tabulate package not found. Please install it using:")
    print("pip install tabulate")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class Neo4jAuraQuerier:
    """Queries a Neo4j Aura database."""
    
    def __init__(self, uri: str, user: str, password: str):
        """Initialize the querier with connection details."""
        self.uri = uri
        self.user = user
        self.password = password
        self.driver = None
        
        # Connect to Neo4j Aura
        self._connect()
        
    def _connect(self):
        """Connect to Neo4j Aura database."""
        if not self.uri or not self.user or not self.password:
            raise ValueError("Neo4j Aura URI, username, and password are required")
            
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            logger.info(f"Connected to Neo4j Aura at {self.uri}")
                
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j Aura: {str(e)}")
            raise
    
    def close(self):
        """Close the Neo4j connection."""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j Aura connection closed")
    
    def get_database_stats(self) -> Dict:
        """Get basic statistics about the database."""
        stats = {}
        
        # Query node counts by label
        node_counts_query = "CALL db.labels() YIELD label CALL apoc.cypher.run('MATCH (n:`' + $label + '`) RETURN count(n) as count', {label: label}) YIELD value RETURN label, value.count AS count"
        
        try:
            with self.driver.session() as session:
                # If APOC is not available, use a simpler query
                try:
                    result = session.run(node_counts_query)
                    node_counts = {record["label"]: record["count"] for record in result}
                except Exception:
                    # Fallback to manual label counts
                    node_counts = {}
                    labels_result = session.run("CALL db.labels()")
                    labels = [record["label"] for record in labels_result]
                    
                    for label in labels:
                        count_result = session.run(f"MATCH (n:`{label}`) RETURN count(n) as count")
                        node_counts[label] = count_result.single()["count"]
                
                stats["node_counts"] = node_counts
                
                # Get relationship counts by type
                rel_counts = {}
                
                try:
                    rel_types_result = session.run("CALL db.relationshipTypes()")
                    rel_types = [record["relationshipType"] for record in rel_types_result]
                    
                    for rel_type in rel_types:
                        count_result = session.run(f"MATCH ()-[r:`{rel_type}`]->() RETURN count(r) as count")
                        rel_counts[rel_type] = count_result.single()["count"]
                    
                    stats["relationship_counts"] = rel_counts
                except Exception as e:
                    stats["relationship_counts_error"] = str(e)
                
                # Get total node and relationship counts
                try:
                    count_result = session.run("MATCH (n) RETURN count(n) as nodes")
                    stats["total_nodes"] = count_result.single()["nodes"]
                    
                    count_result = session.run("MATCH ()-[r]->() RETURN count(r) as rels")
                    stats["total_relationships"] = count_result.single()["rels"]
                except Exception as e:
                    stats["count_error"] = str(e)
                
                return stats
                
        except Exception as e:
            logger.error(f"Error getting database stats: {str(e)}")
            return {"error": str(e)}
    
    def run_query(self, query: str, params: Optional[Dict] = None) -> List[Dict]:
        """Run a Cypher query and return the results as a list of dictionaries."""
        if not params:
            params = {}
            
        try:
            with self.driver.session() as session:
                result = session.run(query, params)
                
                # Convert the result to a list of dictionaries
                records = []
                for record in result:
                    records.append(dict(record))
                
                return records
                
        except Exception as e:
            logger.error(f"Error running query: {str(e)}")
            logger.error(f"Query: {query}")
            logger.error(f"Parameters: {params}")
            return [{"error": str(e)}]
    
    def print_query_results(self, query: str, params: Optional[Dict] = None):
        """Run a query and print the results in a formatted table."""
        records = self.run_query(query, params)
        
        if not records:
            print("No results found.")
            return
            
        if "error" in records[0]:
            print(f"Error: {records[0]['error']}")
            return
            
        # Convert to a pandas DataFrame for nicer display
        try:
            df = pd.DataFrame(records)
            print(tabulate(df, headers=df.columns, tablefmt="grid"))
            print(f"Total records: {len(records)}")
        except Exception:
            # Fallback to simple print if pandas/tabulate fails
            for i, record in enumerate(records):
                print(f"Record {i+1}:")
                for key, value in record.items():
                    print(f"  {key}: {value}")
                print("")
            print(f"Total records: {len(records)}")
    
    def run_sample_queries(self):
        """Run some sample queries to demonstrate how to query the database."""
        sample_queries = [
            {
                "name": "Top 10 Cases",
                "query": "MATCH (c:Case) RETURN c.citation_number, c.url LIMIT 10"
            },
            {
                "name": "Top 10 Laws",
                "query": "MATCH (l:Law) RETURN l.law_id, l.text, l.url LIMIT 10"
            },
            {
                "name": "Top 10 Law Sections",
                "query": "MATCH (s:LawSection) RETURN s.law_id, s.section_id, s.text, s.url LIMIT 10"
            },
            {
                "name": "Most Referenced Cases",
                "query": """
                MATCH (c:Case)<-[r:REFERS_TO]-()
                RETURN c.citation_number, count(r) as reference_count
                ORDER BY reference_count DESC
                LIMIT 10
                """
            },
            {
                "name": "Most Cited Laws",
                "query": """
                MATCH (l:Law)<-[r:CITES]-()
                RETURN l.law_id, count(r) as citation_count
                ORDER BY citation_count DESC
                LIMIT 10
                """
            },
            {
                "name": "Most Cited Law Sections",
                "query": """
                MATCH (s:LawSection)<-[r:CITES]-()
                RETURN s.law_id, s.section_id, s.text, count(r) as citation_count
                ORDER BY citation_count DESC
                LIMIT 10
                """
            },
            {
                "name": "Laws with Most Sections",
                "query": """
                MATCH (l:Law)-[r:HAS_SECTION]->(s:LawSection)
                RETURN l.law_id, count(r) as section_count
                ORDER BY section_count DESC
                LIMIT 10
                """
            }
        ]
        
        for query_info in sample_queries:
            print(f"\n=== {query_info['name']} ===")
            self.print_query_results(query_info["query"])
    
    def interactive_mode(self):
        """Enter an interactive mode where users can input Cypher queries."""
        print("\n=== Interactive Cypher Query Mode ===")
        print("Enter Cypher queries to execute (enter 'exit' or 'quit' to exit)")
        
        while True:
            try:
                query = input("\nCypher> ")
                
                if query.lower() in ("exit", "quit"):
                    break
                    
                if query.strip():
                    self.print_query_results(query)
                    
            except KeyboardInterrupt:
                print("\nExiting interactive mode...")
                break
            except Exception as e:
                print(f"Error: {str(e)}")

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description='Query Neo4j Aura database.')
    parser.add_argument('--uri', required=True, help='Neo4j Aura connection URI (required)')
    parser.add_argument('--user', required=True, help='Neo4j Aura username (required)')
    parser.add_argument('--password', required=True, help='Neo4j Aura password (required)')
    parser.add_argument('--query', help='Cypher query to run')
    parser.add_argument('--stats', action='store_true', help='Get database statistics')
    parser.add_argument('--samples', action='store_true', help='Run sample queries')
    parser.add_argument('--interactive', action='store_true', help='Enter interactive query mode')
    args = parser.parse_args()
    
    querier = Neo4jAuraQuerier(
        uri=args.uri,
        user=args.user,
        password=args.password
    )
    
    try:
        if args.stats:
            print("\n=== Database Statistics ===")
            stats = querier.get_database_stats()
            
            print(f"Total nodes: {stats.get('total_nodes', 'N/A')}")
            print(f"Total relationships: {stats.get('total_relationships', 'N/A')}")
            
            print("\nNode counts by label:")
            for label, count in stats.get('node_counts', {}).items():
                print(f"  {label}: {count}")
            
            print("\nRelationship counts by type:")
            for rel_type, count in stats.get('relationship_counts', {}).items():
                print(f"  {rel_type}: {count}")
        
        if args.query:
            print(f"\n=== Query Results ===")
            querier.print_query_results(args.query)
        
        if args.samples:
            querier.run_sample_queries()
            
        if args.interactive:
            querier.interactive_mode()
            
        # If no options specified, show statistics and sample queries
        if not (args.stats or args.query or args.samples or args.interactive):
            print("\n=== Database Statistics ===")
            stats = querier.get_database_stats()
            
            print(f"Total nodes: {stats.get('total_nodes', 'N/A')}")
            print(f"Total relationships: {stats.get('total_relationships', 'N/A')}")
            
            print("\nNode counts by label:")
            for label, count in stats.get('node_counts', {}).items():
                print(f"  {label}: {count}")
            
            print("\nRelationship counts by type:")
            for rel_type, count in stats.get('relationship_counts', {}).items():
                print(f"  {rel_type}: {count}")
                
            querier.run_sample_queries()
        
    finally:
        querier.close()

if __name__ == '__main__':
    main() 