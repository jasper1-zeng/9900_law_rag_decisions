#!/usr/bin/env python3
"""
cases_graph_api.py - Streamlined API for Neo4j case graph visualization with D3.js.

This script creates a Flask-RESTx API that provides an endpoint for retrieving 
case graph data for visualization with D3.js. The API is documented with Swagger UI.

Usage:
    python cases_graph_api.py --uri NEO4J_AURA_URI --user NEO4J_USER --password NEO4J_PASSWORD [--port PORT]
"""

import os
import sys
import argparse
import logging
from typing import Dict, List, Optional

try:
    from neo4j import GraphDatabase
    from flask import Flask, request, jsonify, Response, render_template, send_from_directory
    from flask_cors import CORS
    from flask_restx import Api, Resource, fields, Namespace
except ImportError:
    print("Required packages not found. Please install them using:")
    print("pip install neo4j flask flask-cors flask-restx")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Create templates and static directories
TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
os.makedirs(TEMPLATES_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

# Create D3.js visualization template
with open(os.path.join(TEMPLATES_DIR, 'd3_case_graph.html'), 'w') as f:
    f.write('''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Case Graph Visualization</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        body, html {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            width: 100%;
            height: 100%;
            overflow: hidden;
        }
        #graph-container {
            width: 100%;
            height: 100vh;
            background-color: #f5f5f5;
        }
        .node {
            stroke: #fff;
            stroke-width: 1.5px;
            cursor: pointer;
        }
        .link {
            stroke: #999;
            stroke-opacity: 0.6;
        }
        .node text {
            font-size: 10px;
            font-family: sans-serif;
        }
        .tooltip {
            position: absolute;
            background: rgba(0,0,0,0.7);
            color: white;
            padding: 5px 10px;
            border-radius: 3px;
            font-size: 12px;
            pointer-events: none;
            opacity: 0;
        }
        .controls {
            position: absolute;
            top: 10px;
            left: 10px;
            background: white;
            padding: 10px;
            border-radius: 5px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.3);
            z-index: 10;
        }
        .legend {
            position: absolute;
            bottom: 10px;
            left: 10px;
            background: white;
            padding: 10px;
            border-radius: 5px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.3);
        }
        .legend-item {
            display: flex;
            align-items: center;
            margin-bottom: 5px;
        }
        .legend-color {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }
        button {
            background-color: #4CAF50;
            border: none;
            color: white;
            padding: 5px 10px;
            text-align: center;
            text-decoration: none;
            display: inline-block;
            font-size: 14px;
            margin: 2px;
            cursor: pointer;
            border-radius: 3px;
        }
        .details-panel {
            position: absolute;
            top: 10px;
            right: 10px;
            width: 300px;
            background: white;
            border-radius: 5px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.3);
            padding: 15px;
            max-height: 80%;
            overflow-y: auto;
            display: none;
        }
        .loading {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            font-size: 18px;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div id="graph-container">
        <div id="loading" class="loading">Loading graph data...</div>
        <div id="tooltip" class="tooltip"></div>
        <svg id="graph"></svg>
    </div>
    
    <div class="controls">
        <button id="reset-zoom">Reset View</button>
        <button id="toggle-labels">Show Labels</button>
    </div>
    
    <div class="legend">
        <div class="legend-item">
            <div class="legend-color" style="background-color: #6baed6;"></div>
            <span>Case</span>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background-color: #fd8d3c;"></div>
            <span>Law</span>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background-color: #74c476;"></div>
            <span>Law Section</span>
        </div>
    </div>
    
    <div id="details-panel" class="details-panel">
        <h3 id="details-title">Node Details</h3>
        <div id="details-content"></div>
    </div>
    
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            // Get graph data from URL parameter
            const urlParams = new URLSearchParams(window.location.search);
            const query = urlParams.get('query');
            const depth = urlParams.get('depth') || 1;
            
            if (!query) {
                document.getElementById('loading').textContent = 'No search query provided';
                return;
            }
            
            // Fetch graph data from API
            fetch(`/api/cases/graph?query=${encodeURIComponent(query)}&max_depth=${depth}`)
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        document.getElementById('loading').textContent = `Error: ${data.error}`;
                        return;
                    }
                    renderGraph(data);
                    document.getElementById('loading').style.display = 'none';
                })
                .catch(error => {
                    document.getElementById('loading').textContent = `Error loading data: ${error.message}`;
                });
                
            // Toggle labels button
            let showLabels = false;
            document.getElementById('toggle-labels').addEventListener('click', function() {
                showLabels = !showLabels;
                this.textContent = showLabels ? 'Hide Labels' : 'Show Labels';
                d3.selectAll('.node-label').style('display', showLabels ? 'block' : 'none');
            });
        });
        
        function renderGraph(graphData) {
            const svg = d3.select('#graph');
            const width = document.getElementById('graph-container').clientWidth;
            const height = document.getElementById('graph-container').clientHeight;
            
            // Clear any previous content
            svg.selectAll('*').remove();
            
            // Set SVG size
            svg.attr('width', width).attr('height', height);
            
            // Create a group for zoom behavior
            const g = svg.append('g');
            
            // Create zoom behavior
            const zoom = d3.zoom()
                .scaleExtent([0.1, 4])
                .on('zoom', (event) => {
                    g.attr('transform', event.transform);
                });
            
            svg.call(zoom);
            
            // Define arrow markers for directed links
            svg.append('defs').append('marker')
                .attr('id', 'arrowhead')
                .attr('viewBox', '-0 -5 10 10')
                .attr('refX', 20)
                .attr('refY', 0)
                .attr('orient', 'auto')
                .attr('markerWidth', 6)
                .attr('markerHeight', 6)
                .attr('xoverflow', 'visible')
                .append('path')
                .attr('d', 'M 0,-5 L 10,0 L 0,5')
                .attr('fill', '#999')
                .style('stroke', 'none');
                
            // Define color scale for node types
            const colorScale = d3.scaleOrdinal()
                .domain(['case', 'law', 'section'])
                .range(['#6baed6', '#fd8d3c', '#74c476']);
                
            // Create links
            const link = g.append('g')
                .selectAll('line')
                .data(graphData.links)
                .enter().append('line')
                .attr('class', 'link')
                .attr('stroke-width', 1)
                .attr('marker-end', 'url(#arrowhead)')
                .on('mouseenter', function(event, d) {
                    showTooltip(event, d.type);
                })
                .on('mousemove', moveTooltip)
                .on('mouseleave', hideTooltip);
                
            // Create nodes
            const node = g.append('g')
                .selectAll('circle')
                .data(graphData.nodes)
                .enter().append('circle')
                .attr('class', 'node')
                .attr('r', d => d.type === 'case' ? 10 : (d.type === 'law' ? 12 : 8))
                .attr('fill', d => colorScale(d.type))
                .on('mouseenter', function(event, d) {
                    showTooltip(event, d.label);
                })
                .on('mousemove', moveTooltip)
                .on('mouseleave', hideTooltip)
                .on('click', showNodeDetails)
                .call(d3.drag()
                    .on('start', dragstarted)
                    .on('drag', dragged)
                    .on('end', dragended));
                
            // Create labels (hidden by default)
            const labels = g.append('g')
                .selectAll('text')
                .data(graphData.nodes)
                .enter().append('text')
                .attr('class', 'node-label')
                .text(d => d.label)
                .attr('font-size', 10)
                .attr('dx', 12)
                .attr('dy', 4)
                .style('display', 'none');
                
            // Create force simulation
            const simulation = d3.forceSimulation(graphData.nodes)
                .force('link', d3.forceLink(graphData.links).id(d => d.id).distance(100))
                .force('charge', d3.forceManyBody().strength(-300))
                .force('center', d3.forceCenter(width / 2, height / 2))
                .force('collision', d3.forceCollide().radius(20))
                .on('tick', ticked);
                
            function ticked() {
                link
                    .attr('x1', d => d.source.x)
                    .attr('y1', d => d.source.y)
                    .attr('x2', d => d.target.x)
                    .attr('y2', d => d.target.y);
                    
                node
                    .attr('cx', d => d.x)
                    .attr('cy', d => d.y);
                    
                labels
                    .attr('x', d => d.x)
                    .attr('y', d => d.y);
            }
            
            function dragstarted(event, d) {
                if (!event.active) simulation.alphaTarget(0.3).restart();
                d.fx = d.x;
                d.fy = d.y;
            }
            
            function dragged(event, d) {
                d.fx = event.x;
                d.fy = event.y;
            }
            
            function dragended(event, d) {
                if (!event.active) simulation.alphaTarget(0);
                d.fx = null;
                d.fy = null;
            }
            
            // Reset zoom button
            document.getElementById('reset-zoom').addEventListener('click', function() {
                svg.transition().duration(750).call(
                    zoom.transform,
                    d3.zoomIdentity,
                    d3.zoomTransform(svg.node()).invert([width / 2, height / 2])
                );
            });
            
            // Auto-center and zoom to fit
            svg.call(zoom.transform, d3.zoomIdentity);
            
            // Tooltip functions
            function showTooltip(event, text) {
                d3.select('#tooltip')
                    .style('opacity', 0.9)
                    .html(text);
                moveTooltip(event);
            }
            
            function moveTooltip(event) {
                d3.select('#tooltip')
                    .style('left', (event.pageX + 10) + 'px')
                    .style('top', (event.pageY - 28) + 'px');
            }
            
            function hideTooltip() {
                d3.select('#tooltip').style('opacity', 0);
            }
            
            // Node details panel
            function showNodeDetails(event, d) {
                const panel = document.getElementById('details-panel');
                const title = document.getElementById('details-title');
                const content = document.getElementById('details-content');
                
                // Format node details based on type
                title.textContent = d.label;
                
                let detailsHtml = '';
                if (d.type === 'case') {
                    detailsHtml = `
                        <p><strong>Type:</strong> Case</p>
                        <p><strong>Citation:</strong> ${d.properties.citation_number}</p>
                        <p><a href="${d.properties.url}" target="_blank">View Case</a></p>
                    `;
                } else if (d.type === 'law') {
                    detailsHtml = `
                        <p><strong>Type:</strong> Law</p>
                        <p><strong>Law ID:</strong> ${d.properties.law_id}</p>
                        <p><a href="${d.properties.url}" target="_blank">View Law</a></p>
                    `;
                } else if (d.type === 'section') {
                    detailsHtml = `
                        <p><strong>Type:</strong> Law Section</p>
                        <p><strong>Law ID:</strong> ${d.properties.law_id}</p>
                        <p><strong>Section ID:</strong> ${d.properties.section_id}</p>
                        <p><a href="${d.properties.url}" target="_blank">View Section</a></p>
                    `;
                }
                
                content.innerHTML = detailsHtml;
                panel.style.display = 'block';
                
                // Add event listener to close panel when clicking outside
                document.getElementById('graph-container').onclick = function(e) {
                    if (e.target.id === 'graph-container' || e.target.tagName === 'svg') {
                        panel.style.display = 'none';
                    }
                };
            }
        }
    </script>
</body>
</html>
''')

# Initialize API with Swagger documentation
api = Api(
    app,
    version='1.0',
    title='Case Graph Visualization API',
    description='API for visualizing case graphs using D3.js',
    doc='/api/docs'
)

# Create namespace for cases
ns_cases = Namespace('cases', description='Case graph operations')
api.add_namespace(ns_cases, path='/api/cases')

# Define models for Swagger UI
case_model = api.model('Case', {
    'citation_number': fields.String(required=True, description='Case citation number'),
    'url': fields.String(description='Link to the case document')
})

node_model = api.model('Node', {
    'id': fields.String(required=True, description='Node ID'),
    'type': fields.String(required=True, description='Node type (case, law, section)'),
    'label': fields.String(description='Display label for the node'),
    'properties': fields.Raw(description='Node properties')
})

link_model = api.model('Link', {
    'id': fields.String(required=True, description='Link ID'),
    'source': fields.String(required=True, description='Source node ID'),
    'target': fields.String(required=True, description='Target node ID'),
    'type': fields.String(description='Relationship type')
})

graph_model = api.model('Graph', {
    'nodes': fields.List(fields.Nested(node_model), description='Nodes in the graph'),
    'links': fields.List(fields.Nested(link_model), description='Links between nodes')
})

# Global Neo4j driver
neo4j_driver = None

class Neo4jGraphAPI:
    """API for Neo4j graph operations"""
    
    def __init__(self, uri: str, user: str, password: str):
        """Initialize the Neo4j driver"""
        self.uri = uri
        self.user = user
        self.password = password
        self.driver = None
        
        self._connect()
        
    def _connect(self):
        """Connect to Neo4j database"""
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            logger.info(f"Connected to Neo4j at {self.uri}")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {str(e)}")
            raise
            
    def close(self):
        """Close the Neo4j connection"""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j connection closed")
            
    def run_query(self, query: str, params: Optional[Dict] = None) -> List[Dict]:
        """Run a Cypher query and return the results"""
        if not params:
            params = {}
            
        try:
            with self.driver.session() as session:
                result = session.run(query, params)
                records = []
                for record in result:
                    records.append(dict(record))
                return records
        except Exception as e:
            logger.error(f"Error running query: {str(e)}")
            return [{"error": str(e)}]
            
    def search_cases(self, query: str, max_depth: int = 1) -> Dict:
        """Search for cases and return a graph of related entities"""
        # Validate max_depth parameter
        max_depth = min(max(1, max_depth), 3)  # Between 1 and 3
        
        # Create a pattern for partial matching
        pattern = f"(?i).*{query}.*"  # Case insensitive
        
        # Dynamically build the query based on max_depth to avoid parameter in path pattern
        if max_depth == 1:
            path_pattern = "[:REFERS_TO|CITES]"
        elif max_depth == 2:
            path_pattern = "[:REFERS_TO|CITES*1..2]"
        else:  # max_depth == 3
            path_pattern = "[:REFERS_TO|CITES*1..3]"
        
        # Try to find cases matching the query pattern
        cypher = f"""
        // Find cases matching the query pattern
        MATCH (c:Case)
        WHERE c.citation_number =~ $pattern
        
        // Find related entities directly using path pattern
        MATCH path = (c)-{path_pattern}->(related)
        
        // Collect all nodes
        WITH collect(DISTINCT c) + collect(DISTINCT related) as allNodes, 
             collect(DISTINCT path) as paths
        
        // Process nodes
        UNWIND allNodes AS node
        WITH collect({{
            id: id(node),
            labels: labels(node),
            properties: properties(node)
        }}) AS nodes, paths
        
        // Process relationships
        UNWIND paths AS p
        UNWIND relationships(p) AS rel
        
        RETURN nodes, collect(DISTINCT {{
            id: id(rel),
            type: type(rel),
            startNode: id(startNode(rel)),
            endNode: id(endNode(rel)),
            properties: properties(rel)
        }}) AS relationships
        """
        
        try:
            results = self.run_query(cypher, {"pattern": pattern})
            
            # If the directional query doesn't work, fall back to a minimal query
            if not results or (results and "error" in results[0]):
                # Minimal query for direct connections only
                minimal_cypher = f"""
                // Match cases matching the pattern
                MATCH (c:Case)
                WHERE c.citation_number =~ $pattern
                
                // Find directly connected nodes (1-hop only)
                OPTIONAL MATCH (c)-[r1:REFERS_TO]->(c2:Case)
                OPTIONAL MATCH (c)-[r2:CITES]->(l:Law)
                OPTIONAL MATCH (c)-[r3:CITES]->(s:LawSection)
                
                // Collect nodes
                WITH collect(DISTINCT c) + collect(DISTINCT c2) + collect(DISTINCT l) + collect(DISTINCT s) AS allNodes,
                     collect(DISTINCT r1) + collect(DISTINCT r2) + collect(DISTINCT r3) AS allRels
                
                // Format nodes
                UNWIND allNodes AS node
                WHERE node IS NOT NULL
                WITH collect({{
                    id: id(node),
                    labels: labels(node),
                    properties: properties(node)
                }}) AS nodes, allRels
                
                // Format relationships
                UNWIND allRels AS rel
                WHERE rel IS NOT NULL
                
                RETURN nodes, collect({{
                    id: id(rel),
                    type: type(rel),
                    startNode: id(startNode(rel)),
                    endNode: id(endNode(rel)),
                    properties: properties(rel)
                }}) AS relationships
                """
                
                results = self.run_query(minimal_cypher, {"pattern": pattern})
            
            if not results:
                return {"error": "No results found"}
                
            if "error" in results[0]:
                return {"error": results[0]["error"]}
                
            return self._format_graph_response(results[0])
            
        except Exception as e:
            logger.error(f"Error in search_cases: {str(e)}")
            return {"error": f"An error occurred: {str(e)}"}
            
    def _format_graph_response(self, raw_data: Dict) -> Dict:
        """Format the graph data for D3.js visualization"""
        nodes = []
        links = []
        
        # Process nodes
        for node in raw_data.get("nodes", []):
            # Get node type from labels
            node_type = "unknown"
            if "Case" in node["labels"]:
                node_type = "case"
            elif "Law" in node["labels"]:
                node_type = "law"
            elif "LawSection" in node["labels"]:
                node_type = "section"
                
            # Create label based on node type
            label = ""
            if node_type == "case":
                label = node["properties"].get("citation_number", "")
            elif node_type == "law":
                label = node["properties"].get("law_id", "")
            elif node_type == "section":
                section_id = node["properties"].get("section_id", "")
                law_id = node["properties"].get("law_id", "")
                label = f"{law_id} § {section_id}"
                
            # Add node to list
            nodes.append({
                "id": str(node["id"]),
                "type": node_type,
                "label": label,
                "properties": node["properties"]
            })
            
        # Process relationships
        for rel in raw_data.get("relationships", []):
            links.append({
                "id": str(rel["id"]),
                "source": str(rel["startNode"]),
                "target": str(rel["endNode"]),
                "type": rel["type"].lower()
            })
            
        return {
            "nodes": nodes,
            "links": links
        }

# API routes
@app.route('/')
def index():
    """Redirect to API docs"""
    return '''
    <html>
        <head>
            <title>Case Graph API</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                }
                .button {
                    display: inline-block;
                    background-color: #4CAF50;
                    color: white;
                    padding: 10px 15px;
                    text-decoration: none;
                    border-radius: 5px;
                    margin-right: 10px;
                }
            </style>
        </head>
        <body>
            <h1>Case Graph Visualization API</h1>
            <p>Use this API to search for cases and visualize their relationships.</p>
            <p>
                <a href="/api/docs" class="button">API Documentation</a>
                <a href="/visualizer" class="button">Graph Visualizer</a>
            </p>
        </body>
    </html>
    '''

@app.route('/visualizer')
def visualizer():
    """Render the graph visualization page"""
    return render_template('d3_case_graph.html')

@app.route('/static/<path:path>')
def send_static(path):
    """Serve static files"""
    return send_from_directory(STATIC_DIR, path)

@ns_cases.route('/graph')
class CaseGraph(Resource):
    @api.doc(
        description='Get a graph of cases and related entities matching a search query',
        params={
            'query': 'Search query (partial citation match)',
            'max_depth': 'Maximum relationship depth (1-3, default: 1)'
        },
        responses={
            200: 'Success',
            400: 'Bad Request',
            500: 'Server Error'
        }
    )
    @api.response(200, 'Success', graph_model)
    def get(self):
        """Get a graph of cases and related entities matching a search query"""
        query = request.args.get('query', '')
        max_depth = int(request.args.get('max_depth', 1))
        
        if not query:
            return {"error": "Query parameter is required"}, 400
            
        result = neo4j_driver.search_cases(query, max_depth)
        
        if "error" in result:
            return {"error": result["error"]}, 500
            
        return result

@ns_cases.route('/search')
class CaseSearch(Resource):
    @api.doc(
        description='Search for cases by partial citation match',
        params={
            'q': 'Search query (partial citation match)',
            'format': 'Response format (json or redirect, default: json)'
        },
        responses={
            200: 'Success',
            302: 'Redirect to visualizer',
            400: 'Bad Request'
        }
    )
    def get(self):
        """Search for cases and optionally redirect to the visualizer"""
        query = request.args.get('q', '')
        response_format = request.args.get('format', 'json')
        
        if not query:
            return {"error": "Query parameter 'q' is required"}, 400
            
        if response_format == 'redirect':
            # Redirect to visualizer with query parameter
            return Response(
                status=302,
                headers={"Location": f"/visualizer?query={query}"}
            )
        else:
            # Return a simplified search result
            pattern = f"(?i).*{query}.*"
            cypher = """
            MATCH (c:Case)
            WHERE c.citation_number =~ $pattern
            RETURN c.citation_number as citation_number, c.url as url
            LIMIT 10
            """
            
            results = neo4j_driver.run_query(cypher, {"pattern": pattern})
            
            if not results or "error" in results[0]:
                return {"results": []}
                
            return {"results": results}

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Case Graph Visualization API')
    parser.add_argument('--uri', required=True, help='Neo4j connection URI')
    parser.add_argument('--user', required=True, help='Neo4j username')
    parser.add_argument('--password', required=True, help='Neo4j password')
    parser.add_argument('--port', type=int, default=5006, help='Port to run the API server on')
    parser.add_argument('--host', default='0.0.0.0', help='Host to run the API server on')
    args = parser.parse_args()
    
    global neo4j_driver
    
    try:
        # Initialize Neo4j driver
        neo4j_driver = Neo4jGraphAPI(
            uri=args.uri,
            user=args.user,
            password=args.password
        )
        
        # Run Flask app
        app.run(host=args.host, port=args.port)
        
    except Exception as e:
        logger.error(f"Error starting API: {str(e)}")
        sys.exit(1)
    finally:
        if neo4j_driver:
            neo4j_driver.close()

if __name__ == '__main__':
    main() 