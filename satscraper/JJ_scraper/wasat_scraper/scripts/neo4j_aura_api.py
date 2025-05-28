#!/usr/bin/env python3
"""
neo4j_aura_api.py - REST API for Neo4j Aura database queries.

This script creates a Flask-based REST API that allows users to query the Neo4j Aura
database for cases, laws, and their relationships. The API is designed to be used by
front-end applications for displaying graph visualizations.

Usage:
    python neo4j_aura_api.py --uri NEO4J_AURA_URI --user NEO4J_USER --password NEO4J_PASSWORD [--port PORT]
"""

import os
import sys
import json
import argparse
import logging
from typing import Dict, List, Optional, Any, Union
import re

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

# Create a templates directory
TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
os.makedirs(TEMPLATES_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

# Create the visualization template
with open(os.path.join(TEMPLATES_DIR, 'graph_visualization.html'), 'w') as f:
    f.write('''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Legal Case Visualization</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f5f5f5;
        }
        .container {
            display: flex;
            flex-direction: column;
            height: 100vh;
            overflow: hidden;
        }
        .header {
            padding: 10px 20px;
            background-color: #333;
            color: white;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .title {
            font-size: 1.2em;
            font-weight: bold;
        }
        .controls {
            display: flex;
            gap: 10px;
            align-items: center;
        }
        .visualization {
            flex-grow: 1;
            overflow: hidden;
            position: relative;
        }
        svg {
            width: 100%;
            height: 100%;
            background-color: #f5f5f5;
        }
        .details-panel {
            position: absolute;
            top: 10px;
            right: 10px;
            width: 300px;
            background: white;
            border-radius: 5px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            padding: 15px;
            overflow-y: auto;
            max-height: 80%;
            display: none;
            z-index: 100;
        }
        .node-info h3 {
            margin-top: 0;
            border-bottom: 1px solid #eee;
            padding-bottom: 8px;
        }
        .node-info p {
            margin: 5px 0;
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
            z-index: 100;
        }
        .node {
            stroke: #fff;
            stroke-width: 1.5px;
            cursor: pointer;
        }
        .link {
            stroke-opacity: 0.6;
        }
        .node text {
            font-size: 10px;
            font-family: sans-serif;
            pointer-events: none;
        }
        .loading {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            font-size: 18px;
            font-weight: bold;
        }
        .button {
            padding: 5px 10px;
            border: none;
            border-radius: 3px;
            background-color: #4CAF50;
            color: white;
            cursor: pointer;
            font-size: 14px;
        }
        .button:hover {
            background-color: #45a049;
        }
        .search-container {
            background: white;
            padding: 10px 15px;
            border-bottom: 1px solid #ddd;
        }
        .search-form {
            display: flex;
            gap: 5px;
        }
        .search-input {
            flex-grow: 1;
            padding: 8px;
            border: 1px solid #ccc;
            border-radius: 3px;
        }
        .debug-info {
            position: absolute;
            bottom: 10px;
            left: 10px;
            background: rgba(255,255,255,0.8);
            padding: 5px;
            border-radius: 3px;
            font-size: 12px;
            display: none;
        }
        .search-select {
            padding: 8px;
            border: 1px solid #ccc;
            border-radius: 3px;
            margin-right: 5px;
        }
        .search-results {
            background: white;
            border: 1px solid #ddd;
            border-top: none;
            max-height: 200px;
            overflow-y: auto;
            display: none;
        }
        .search-result-item {
            padding: 8px 12px;
            border-bottom: 1px solid #eee;
            cursor: pointer;
        }
        .search-result-item:hover {
            background-color: #f5f5f5;
        }
        .search-result-item.selected {
            background-color: #e8f0fe;
        }
        .legend {
            position: absolute;
            bottom: 20px;
            right: 20px;
            background: rgba(255, 255, 255, 0.9);
            padding: 10px;
            border-radius: 5px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            font-size: 12px;
        }
        .legend h4 {
            margin: 0 0 5px 0;
            padding-bottom: 5px;
            border-bottom: 1px solid #eee;
        }
        .legend-item {
            display: flex;
            align-items: center;
            margin: 5px 0;
        }
        .legend-color {
            display: inline-block;
            width: 14px;
            height: 14px;
            border-radius: 50%;
            margin-right: 8px;
        }
        .legend-section {
            margin-top: 10px;
        }
        .legend-section h5 {
            margin-bottom: 5px;
        }
        .legend-line {
            display: inline-block;
            width: 10px;
            height: 2px;
            margin-right: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="title">WASAT Legal Case Graph</div>
            <div class="controls">
                <button id="resetZoom" class="button">Reset View</button>
                <button id="toggleLabels" class="button">Toggle Labels</button>
                <button id="toggleDebug" class="button">Debug Info</button>
            </div>
        </div>
        
        <div class="search-container">
            <form id="searchForm" class="search-form">
                <select id="searchType" class="search-select">
                    <option value="case">Search Cases</option>
                    <option value="law">Search Laws</option>
                    <option value="section">Search Sections</option>
                </select>
                <input type="text" id="searchQuery" class="search-input" placeholder="Enter search term...">
                <button type="submit" class="button">Search</button>
                <button type="button" id="addNode" class="button" style="display:none;">Add to Graph</button>
            </form>
            <div id="searchResults" class="search-results"></div>
        </div>
        
        <div class="visualization">
            <div id="loading" class="loading">Loading graph data...</div>
            <div id="tooltip" class="tooltip"></div>
            <svg id="graph"></svg>
            <div id="detailsPanel" class="details-panel">
                <div id="nodeInfo" class="node-info"></div>
                <button id="expandNode" class="button expand-button">Expand Node</button>
            </div>
            <div id="legend" class="legend">
                <h4>Legend</h4>
                <div class="legend-section">
                    <h5>Nodes</h5>
                    <div class="legend-item"><span class="legend-color" style="background-color: #6baed6;"></span> Case</div>
                    <div class="legend-item"><span class="legend-color" style="background-color: #fd8d3c;"></span> Law</div>
                    <div class="legend-item"><span class="legend-color" style="background-color: #74c476;"></span> Law Section</div>
                </div>
                <div class="legend-section">
                    <h5>Relationships</h5>
                    <div class="legend-item"><span class="legend-line" style="background-color: #636363;"></span> Refers To</div>
                    <div class="legend-item"><span class="legend-line" style="background-color: #9e9ac8;"></span> Cites</div>
                    <div class="legend-item"><span class="legend-line" style="background-color: #a1d99b;"></span> Has Section</div>
                </div>
            </div>
            <div id="debugInfo" class="debug-info"></div>
        </div>
    </div>

    <script>
        // Initialize from server variables
        let apiBaseUrl = '{{ api_base_url }}';
        let initialDataUrl = '{{ data_url }}';
        
        let showLabels = false;
        let showDebug = false;
        let graphData = {nodes: [], links: []};
        let simulation;
        let currentDataUrl = '';
        let selectedNode = null;
        
        // Add event listeners after DOM is loaded
        document.addEventListener('DOMContentLoaded', function() {
            // Initialize with URL parameter from server or from URL
            if (initialDataUrl) {
                currentDataUrl = initialDataUrl;
                fetchGraphData(initialDataUrl);
            } else {
                const urlParams = new URLSearchParams(window.location.search);
                const dataUrl = urlParams.get('dataUrl');
                
                if (dataUrl) {
                    currentDataUrl = dataUrl;
                    fetchGraphData(dataUrl);
                } else {
                    document.getElementById('loading').textContent = 'No data URL provided. Use the search to find data.';
                }
            }
            
            // Helper function to properly encode citation numbers that may contain square brackets
            function encodeCitationNumber(citation) {
                if (!citation) return '';
                
                // Log the citation being encoded
                console.log(`Encoding citation: ${citation}`);
                
                // First encode everything
                let encoded = encodeURIComponent(citation);
                
                // Then replace square brackets with their original characters for Neo4j compatibility
                encoded = encoded.replace(/%5B/g, '[').replace(/%5D/g, ']');
                
                console.log(`Encoded result: ${encoded}`);
                return encoded;
            }
            
            // Handle search form submission
            document.getElementById('searchForm').addEventListener('submit', function(e) {
                e.preventDefault();
                const searchType = document.getElementById('searchType').value;
                const query = document.getElementById('searchQuery').value.trim();
                
                if (!query) return;
                
                // Choose appropriate endpoint based on search type
                let searchEndpoint;
                if (searchType === 'case') {
                    searchEndpoint = `${apiBaseUrl}/api/cases/search?q=${encodeURIComponent(query)}`;
                } else if (searchType === 'law') {
                    searchEndpoint = `${apiBaseUrl}/api/laws/search?q=${encodeURIComponent(query)}`;
                } else {
                    // For now, law sections are harder to search directly
                    alert('Law section search not yet implemented.');
                    return;
                }
                
                // Show loading
                document.getElementById('loading').style.display = 'block';
                
                // Perform search
                fetch(searchEndpoint)
                    .then(response => response.json())
                    .then(data => {
                        if (data.error) {
                            alert(`Error: ${data.error}`);
                            document.getElementById('loading').style.display = 'none';
                            return;
                        }
                        
                        if (data.length === 0) {
                            const searchQuery = document.getElementById('searchQuery').value.trim();
                            const searchType = document.getElementById('searchType').value;
                            alert(`No results found for ${searchType}: "${searchQuery}"`);
                            document.getElementById('loading').style.display = 'none';
                            document.getElementById('searchResults').style.display = 'none';
                            document.getElementById('addNode').style.display = 'none';
                            return;
                        }
                        
                        // Display search results
                        displaySearchResults(data, searchType);
                        document.getElementById('loading').style.display = 'none';
                    })
                    .catch(error => {
                        console.error('Error searching:', error);
                        alert('Error performing search.');
                        document.getElementById('loading').style.display = 'none';
                    });
            });
            
            let selectedSearchResult = null;
            
            function displaySearchResults(results, type) {
                const resultsContainer = document.getElementById('searchResults');
                resultsContainer.innerHTML = '';
                resultsContainer.style.display = 'block';
                
                results.forEach(result => {
                    const item = document.createElement('div');
                    item.className = 'search-result-item';
                    
                    if (type === 'case') {
                        item.textContent = result.citation_number;
                    } else if (type === 'law') {
                        item.textContent = result.law_id + (result.text ? ` - ${result.text}` : '');
                    }
                    
                    item.addEventListener('click', function() {
                        // Clear previous selection
                        document.querySelectorAll('.search-result-item.selected').forEach(el => {
                            el.classList.remove('selected');
                        });
                        
                        // Highlight this item
                        item.classList.add('selected');
                        
                        // Store selected result
                        selectedSearchResult = {
                            type: type,
                            data: result
                        };
                        
                        // Show add button
                        document.getElementById('addNode').style.display = 'inline-block';
                    });
                    
                    resultsContainer.appendChild(item);
                });
            }
            
            // Handle add node button
            document.getElementById('addNode').addEventListener('click', function() {
                if (!selectedSearchResult) return;
                
                const type = selectedSearchResult.type;
                const data = selectedSearchResult.data;
                
                // Show loading
                document.getElementById('loading').style.display = 'block';
                document.getElementById('loading').textContent = `Adding ${type}: ${type === 'case' ? data.citation_number : data.law_id}...`;
                
                // First try fetching the graph visualization data
                let detailsUrl;
                if (type === 'case') {
                    detailsUrl = `${apiBaseUrl}/api/cases/${encodeCitationNumber(data.citation_number)}/graph?max_depth=1`;
                } else if (type === 'law') {
                    detailsUrl = `${apiBaseUrl}/api/laws/${encodeCitationNumber(data.law_id)}/graph`;
                } else {
                    return; // Unhandled type
                }
                
                fetch(detailsUrl)
                    .then(response => {
                        if (!response.ok) {
                            // If graph data isn't available, create a basic node from search result
                            if (response.status === 404) {
                                console.log('Graph data not available, creating basic node from search result');
                                
                                // Create a basic node with the information we have
                                const basicNode = createBasicNodeFromSearchResult(selectedSearchResult);
                                
                                // Add the node to the graph
                                if (basicNode) {
                                    addNodesToGraph({
                                        nodes: [basicNode],
                                        links: []
                                    });
                                    
                                    // Hide search results and add button
                                    document.getElementById('searchResults').style.display = 'none';
                                    document.getElementById('addNode').style.display = 'none';
                                    selectedSearchResult = null;
                                    
                                    document.getElementById('loading').style.display = 'none';
                                    
                                    // Show success notification for the fallback method
                                    const fallbackNodeType = type.charAt(0).toUpperCase() + type.slice(1);
                                    showNotification(`Added ${fallbackNodeType}: ${basicNode.label} (without relationship data)`);
                                    
                                    // After adding a basic node, check for paths to other existing case nodes
                                    if (type === 'case' && graphData.nodes.filter(n => n.type === 'case' && n.id !== basicNode.id).length > 0) {
                                        findPathsBetweenCases(basicNode);
                                    }
                                    
                                    return;
                                }
                            }
                            throw new Error(`HTTP error ${response.status}: The requested resource was not found`);
                        }
                        return response.json();
                    })
                    .then(detailData => {
                        if (!detailData) return; // Already handled in the catch block or previous then
                        
                        if (detailData.error) {
                            console.error('Error getting node details:', detailData.error);
                            document.getElementById('loading').textContent = 'Error: ' + detailData.error;
                            return;
                        }
                        
                        // Find the main node being added
                        const mainNode = detailData.nodes.find(n => n.type === type);
                        
                        if (mainNode) {
                            // Filter to include only relationships that involve the main node
                            const filteredData = {
                                nodes: [],
                                links: detailData.links.filter(link => {
                                    const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
                                    const targetId = typeof link.target === 'object' ? link.target.id : link.target;
                                    return sourceId === mainNode.id || targetId === mainNode.id;
                                })
                            };
                            
                            // Collect node IDs needed for these relationships
                            const relevantNodeIds = new Set([mainNode.id]);
                            filteredData.links.forEach(link => {
                                const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
                                const targetId = typeof link.target === 'object' ? link.target.id : link.target;
                                relevantNodeIds.add(sourceId);
                                relevantNodeIds.add(targetId);
                            });
                            
                            // Add only relevant nodes
                            filteredData.nodes = detailData.nodes.filter(node => relevantNodeIds.has(node.id));
                            
                            // Add any new nodes and links to the existing graph
                            const newNodesAdded = addNodesToGraph(filteredData);
                        } else {
                            // If we can't find the main node, fall back to adding everything
                            const newNodesAdded = addNodesToGraph(detailData);
                        }
                        
                        // Store the main node ID for later path finding
                        const mainNodeId = mainNode ? mainNode.id : null;
                        
                        // Hide search results and add button
                        document.getElementById('searchResults').style.display = 'none';
                        document.getElementById('addNode').style.display = 'none';
                        selectedSearchResult = null;
                        
                        document.getElementById('loading').style.display = 'none';
                        
                        // Show success notification for the normal flow
                        const successNodeType = type.charAt(0).toUpperCase() + type.slice(1);
                        const successLabel = type === 'case' ? data.citation_number : data.law_id;
                        showNotification(`Added ${successNodeType}: ${successLabel} with relationship data`);
                        
                        // If we just added a case, try to find paths to other cases
                        if (type === 'case' && mainNode) {
                            findPathsBetweenCases(mainNode);
                        }
                    })
                    .catch(error => {
                        console.error('Error adding node:', error);
                        document.getElementById('loading').textContent = 'Error adding node: ' + 
                            (error.message || 'The resource might not exist in the database.');
                        setTimeout(() => {
                            document.getElementById('loading').style.display = 'none';
                        }, 3000);
                    });
            });
            
            // Function to find and add paths between a new case and existing cases
            function findPathsBetweenCases(newCaseNode) {
                // Find all other case nodes in the graph
                const otherCaseNodes = graphData.nodes.filter(n => 
                    n.type === 'case' && n.id !== newCaseNode.id
                );
                
                if (otherCaseNodes.length === 0) {
                    return; // No other cases to connect to
                }
                
                // Show loading message
                document.getElementById('loading').style.display = 'block';
                document.getElementById('loading').textContent = 'Finding paths between cases...';
                
                // Build a list of cases to check paths for
                const caseCitations = otherCaseNodes.map(node => node.properties.citation_number);
                
                // Create a URL to fetch the network of cases
                const networkUrl = `${apiBaseUrl}/api/network`;
                
                // Create post data with all cases including the new one
                const postData = {
                    citation_numbers: [newCaseNode.properties.citation_number, ...caseCitations],
                    max_depth: 2 // Using depth 2 to find connections through intermediate nodes
                };
                
                // Fetch the network data
                fetch(networkUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(postData)
                })
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP error ${response.status}`);
                    }
                    return response.json();
                })
                .then(networkData => {
                    if (networkData.error) {
                        console.error('Error finding paths:', networkData.error);
                        showNotification('Error finding paths between cases');
                        document.getElementById('loading').style.display = 'none';
                        return;
                    }
                    
                    // Filter network data to only include relationships involving the new case node
                    const filteredNetworkData = {
                        nodes: networkData.nodes,
                        links: networkData.links.filter(link => {
                            // Get source and target node IDs
                            const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
                            const targetId = typeof link.target === 'object' ? link.target.id : link.target;
                            
                            // Find the actual nodes
                            const sourceNode = networkData.nodes.find(n => n.id === sourceId);
                            const targetNode = networkData.nodes.find(n => n.id === targetId);
                            
                            // Only include links where either source or target is the new case node
                            if (!sourceNode || !targetNode) return false;
                            
                            return (sourceNode.properties.citation_number === newCaseNode.properties.citation_number ||
                                   targetNode.properties.citation_number === newCaseNode.properties.citation_number);
                        })
                    };
                    
                    // Now only include nodes that are part of these relationships
                    const relevantNodeIds = new Set();
                    filteredNetworkData.links.forEach(link => {
                        const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
                        const targetId = typeof link.target === 'object' ? link.target.id : link.target;
                        relevantNodeIds.add(sourceId);
                        relevantNodeIds.add(targetId);
                    });
                    
                    // Add the new case node
                    relevantNodeIds.add(newCaseNode.id);
                    
                    // Filter nodes to only include those relevant to relationships
                    filteredNetworkData.nodes = networkData.nodes.filter(node => relevantNodeIds.has(node.id));
                    
                    // Add the filtered nodes and links to the graph
                    const newNodesAdded = addNodesToGraph(filteredNetworkData);
                    
                    // Update the display
                    document.getElementById('loading').style.display = 'none';
                    
                    if (newNodesAdded > 0) {
                        // Get a snapshot of existing nodes before the update
                        const existingNodeIds = new Set(graphData.nodes.map(n => n.id));
                        const existingLinkIds = new Set(graphData.links.map(l => {
                            const source = typeof l.source === 'object' ? l.source.id : l.source;
                            const target = typeof l.target === 'object' ? l.target.id : l.target;
                            return `${source}-${target}-${l.type}`;
                        }));
                        
                        // Count new cases (exclude the newly added case itself)
                        const newCaseNodes = filteredNetworkData.nodes.filter(node => 
                            !existingNodeIds.has(node.id) && 
                            node.type === 'case' && 
                            node.id !== newCaseNode.id
                        );
                        
                        // Count new links
                        const newLinks = filteredNetworkData.links.filter(link => {
                            const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
                            const targetId = typeof link.target === 'object' ? link.target.id : link.target;
                            return !existingLinkIds.has(`${sourceId}-${targetId}-${link.type}`);
                        });
                        
                        if (newCaseNodes.length > 0 && newLinks.length > 0) {
                            showNotification(`Found connections between ${newCaseNode.properties.citation_number} and ${newCaseNodes.length} other cases (${newLinks.length} links)`);
                        } else if (newLinks.length > 0) {
                            showNotification(`Found ${newLinks.length} connections between ${newCaseNode.properties.citation_number} and existing cases`);
                        } else {
                            showNotification(`No new connections found for ${newCaseNode.properties.citation_number}`);
                        }
                    } else {
                        showNotification(`No new connections found for ${newCaseNode.properties.citation_number}`);
                    }
                })
                .catch(error => {
                    console.error('Error finding paths between cases:', error);
                    document.getElementById('loading').style.display = 'none';
                });
            }
            
            // Function to create a basic node from search result when graph data isn't available
            function createBasicNodeFromSearchResult(searchResult) {
                const type = searchResult.type;
                const data = searchResult.data;
                
                // Generate a random ID for the node
                const randomId = 'temp_' + Math.random().toString(36).substr(2, 9);
                
                if (type === 'case') {
                    return {
                        id: randomId,
                        type: 'case',
                        label: data.citation_number,
                        properties: {
                            citation_number: data.citation_number,
                            url: data.url || ''
                        }
                    };
                } else if (type === 'law') {
                    return {
                        id: randomId,
                        type: 'law',
                        label: data.law_id,
                        properties: {
                            law_id: data.law_id,
                            text: data.text || '',
                            url: data.url || ''
                        }
                    };
                }
                
                return null;
            }
            
            function addNodesToGraph(data) {
                if (!data.nodes || data.nodes.length === 0) {
                    console.log('No nodes to add');
                    return 0; // Return 0 to indicate no nodes added
                }
                
                // Add any new nodes and links to the existing graph
                const newNodes = [];
                const newLinks = [];
                const existingNodeIds = new Set(graphData.nodes.map(n => n.id));
                const existingLinkIds = new Set(graphData.links.map(l => {
                    const source = typeof l.source === 'object' ? l.source.id : l.source;
                    const target = typeof l.target === 'object' ? l.target.id : l.target;
                    return `${source}-${target}-${l.type}`;
                }));
                
                // Add new nodes
                data.nodes.forEach(newNode => {
                    if (!existingNodeIds.has(newNode.id)) {
                        newNodes.push(newNode);
                    }
                });
                
                // Add new links
                if (data.links) {
                    data.links.forEach(newLink => {
                        const sourceId = typeof newLink.source === 'object' ? newLink.source.id : newLink.source;
                        const targetId = typeof newLink.target === 'object' ? newLink.target.id : newLink.target;
                        const linkId = `${sourceId}-${targetId}-${newLink.type}`;
                        
                        if (!existingLinkIds.has(linkId)) {
                            newLinks.push(newLink);
                        }
                    });
                }
                
                // If we have new data, update the graph
                if (newNodes.length > 0 || newLinks.length > 0) {
                    // Add to current graph data
                    graphData.nodes = graphData.nodes.concat(newNodes);
                    graphData.links = graphData.links.concat(newLinks);
                    
                    // Update debug info
                    updateDebugInfo();
                    
                    // Re-render the graph
                    renderGraph(graphData);
                    
                    // Return the count of new entities added
                    return newNodes.length + newLinks.length;
                } else {
                    console.log('No new nodes or links found');
                    return 0;
                }
            }
            
            // Reset zoom button
            document.getElementById('resetZoom').addEventListener('click', function() {
                if (simulation) {
                    resetZoom();
                }
            });
            
            // Toggle labels button
            document.getElementById('toggleLabels').addEventListener('click', function() {
                showLabels = !showLabels;
                updateLabels();
            });
            
            // Toggle debug info
            document.getElementById('toggleDebug').addEventListener('click', function() {
                showDebug = !showDebug;
                const debugPanel = document.getElementById('debugInfo');
                if (showDebug) {
                    debugPanel.style.display = 'block';
                    updateDebugInfo();
                } else {
                    debugPanel.style.display = 'none';
                }
            });
            
            // Expand node button
            document.getElementById('expandNode').addEventListener('click', function() {
                if (selectedNode) {
                    expandNode(selectedNode);
                }
            });
        });
        
        function updateDebugInfo() {
            if (!showDebug) return;
            
            const debugPanel = document.getElementById('debugInfo');
            debugPanel.innerHTML = `
                <p>Nodes: ${graphData.nodes.length}</p>
                <p>Links: ${graphData.links.length}</p>
                <p>Current URL: ${currentDataUrl}</p>
            `;
        }
        
        function fetchGraphData(url) {
            document.getElementById('loading').style.display = 'block';
            
            // Basic URL - always use depth of 1 for initial load
            let fullUrl = url.includes('?') ? `${url}&max_depth=1` : `${url}?max_depth=1`;
            
            fetch(fullUrl)
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP error ${response.status}: The requested resource was not found`);
                    }
                    return response.json();
                })
                .then(data => {
                    if (data.error) {
                        console.error('Error in fetched data:', data.error);
                        document.getElementById('loading').textContent = 'Error: ' + data.error;
                        return;
                    }
                    
                    // Store the graph data
                    graphData = data;
                    
                    // Update debug info
                    updateDebugInfo();
                    
                    // Render the graph
                    renderGraph(graphData);
                    document.getElementById('loading').style.display = 'none';
                })
                .catch(error => {
                    console.error('Error fetching graph data:', error);
                    document.getElementById('loading').textContent = 'Error loading graph data: ' + 
                        (error.message || 'Resource not found. The case, law, or section might not exist in the database.');
                });
        }
        
        function expandNode(node) {
            // Create a URL to fetch relationships based on node type
            let nodeUrl;
            let fallbackUrl;
            
            // Add detailed logging about the node being expanded
            console.log('Expanding node:', {
                id: node.id,
                type: node.type,
                label: node.label,
                properties: node.properties
            });
            
            // Special case handling to ensure we get both case references and law citations
            if (node.type === 'case') {
                // For cases, we'll use a multi-step approach to ensure we get all relationships
                expandCaseNode(node);
                return;
            } else if (node.type === 'law') {
                nodeUrl = `${apiBaseUrl}/api/laws/${encodeCitationNumber(node.properties.law_id)}/graph`;
                fallbackUrl = `${apiBaseUrl}/api/laws/${encodeCitationNumber(node.properties.law_id)}/cited_by`;
            } else if (node.type === 'section') {
                // Check if the section has the required unique_id property
                if (!node.properties.unique_id && node.properties.law_id && node.properties.section_id) {
                    // Compute the unique_id from law_id and section_id
                    node.properties.unique_id = `${node.properties.law_id}:${node.properties.section_id}`;
                    console.log(`Added missing unique_id to section: ${node.properties.unique_id}`);
                }
                
                nodeUrl = `${apiBaseUrl}/api/sections/${encodeCitationNumber(node.properties.law_id)}/${encodeCitationNumber(node.properties.section_id)}/graph`;
                fallbackUrl = `${apiBaseUrl}/api/sections/${encodeCitationNumber(node.properties.law_id)}/${encodeCitationNumber(node.properties.section_id)}/cited_by`;
            } else {
                console.error('Cannot expand node of unknown type:', node.type);
                return;
            }
            
            // Debug logging
            console.log(`Expanding ${node.type} node: ${node.label}`);
            console.log(`Requesting URL: ${nodeUrl}`);
            console.log(`Fallback URL: ${fallbackUrl}`);
            
            // Show loading
            document.getElementById('loading').style.display = 'block';
            document.getElementById('loading').textContent = `Expanding ${node.type}: ${node.label}...`;
            
            // Function to try the fallback URL if the main one fails
            function tryFallbackUrl() {
                console.log(`Trying fallback URL: ${fallbackUrl}`);
                document.getElementById('loading').textContent = `Trying alternative approach...`;
                
                // Check if URL is constructed properly
                if (!fallbackUrl || fallbackUrl.includes('undefined')) {
                    console.error('Invalid fallback URL:', fallbackUrl);
                    document.getElementById('loading').textContent = 'Error: Invalid URL';
                    showNotification('Error: Could not construct a valid URL with the data available');
                    setTimeout(() => {
                        document.getElementById('loading').style.display = 'none';
                    }, 3000);
                    return;
                }
                
                // Make request with detailed error handling
                fetch(fallbackUrl)
                    .then(response => {
                        console.log(`Fallback response status: ${response.status}`);
                        if (!response.ok) {
                            throw new Error(`HTTP error ${response.status} on fallback: The requested resource was not found`);
                        }
                        return response.json();
                    })
                .then(data => {
                        console.log(`Received fallback data:`, data);
                        
                    if (data.error) {
                            console.error('Error with fallback:', data.error);
                            document.getElementById('loading').textContent = 'Error with fallback: ' + data.error;
                            showNotification(`Error with fallback: ${data.error}`);
                            return;
                        }
                        
                        // Process the data as normal
                        processGraphData(data);
                    })
                    .catch(error => {
                        console.error('Error with fallback:', error);
                        document.getElementById('loading').textContent = 'Could not find relationships: ' + 
                            (error.message || 'No data available');
                        showNotification(`Could not expand node: ${error.message || 'No data available'}`);
                        setTimeout(() => {
                            document.getElementById('loading').style.display = 'none';
                        }, 3000);
                    });
            }
            
            // Special function to handle case expansion
            function expandCaseNode(caseNode) {
                const citation = caseNode.properties.citation_number;
                console.log(`Expanding case node with citation: ${citation}`);
                
                // Show loading message
                document.getElementById('loading').style.display = 'block';
                document.getElementById('loading').textContent = `Expanding case: ${citation}...`;
                
                // We'll use the network endpoint for cases with a depth of 1 to ensure we get all related nodes
                const networkUrl = `${apiBaseUrl}/api/network`;
                const postData = {
                    citation_numbers: [citation],
                    max_depth: 1  // Keep it simple to ensure it works
                };
                
                console.log(`Posting to ${networkUrl} with data:`, postData);
                
                // Use the POST endpoint for case networks
                fetch(networkUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(postData)
                })
                .then(response => {
                    console.log(`Network endpoint response status: ${response.status}`);
                    if (!response.ok) {
                        throw new Error(`HTTP error ${response.status}: The requested resource was not found`);
                    }
                    return response.json();
                })
                .then(data => {
                    console.log(`Received network data:`, data);
                    
                    if (data.error) {
                        console.error('Error fetching case network:', data.error);
                        document.getElementById('loading').textContent = 'Error: ' + data.error;
                        
                        // Try the fallback approach with the graph endpoint
                        console.log('Trying fallback with graph endpoint...');
                        const graphUrl = `${apiBaseUrl}/api/cases/${encodeCitationNumber(citation)}/graph?max_depth=1`;
                        
                        fetch(graphUrl)
                            .then(response => response.json())
                            .then(graphData => {
                                if (graphData.error) {
                                    throw new Error(graphData.error);
                                }
                                processGraphData(graphData);
                            })
                            .catch(error => {
                                console.error('Error with graph endpoint:', error);
                                document.getElementById('loading').textContent = 'Error: Could not expand case';
                                showNotification(`Error: Could not expand case ${citation}`);
                                setTimeout(() => {
                                    document.getElementById('loading').style.display = 'none';
                                }, 3000);
                            });
                        return;
                    }
                    
                    // Process the network data
                    processGraphData(data);
                })
                .catch(error => {
                    console.error('Error expanding case node:', error);
                    document.getElementById('loading').textContent = 'Error expanding case: ' + 
                        (error.message || 'Unable to retrieve related data.');
                    showNotification(`Error expanding case: ${error.message || 'Unable to retrieve related data'}`);
                    
                    // Try cited_by endpoint as last resort
                    const citedByUrl = `${apiBaseUrl}/api/cases/${encodeCitationNumber(citation)}/cited_by`;
                    console.log(`Trying cited_by endpoint: ${citedByUrl}`);
                    
                    setTimeout(() => {
                        fetch(citedByUrl)
                            .then(response => response.json())
                            .then(citedByData => {
                                if (citedByData.error && !citedByData.nodes) {
                                    throw new Error(citedByData.error);
                                }
                                processGraphData(citedByData);
                            })
                            .catch(finalError => {
                                console.error('All case expansion attempts failed:', finalError);
                                document.getElementById('loading').textContent = 'Could not expand case';
                                setTimeout(() => {
                                    document.getElementById('loading').style.display = 'none';
                                }, 3000);
                            });
                    }, 1000);
                });
            }
            
            // Function to process the graph data once received
            function processGraphData(data) {
                // Validate the data format
                if (!data) {
                    console.error('Received null or undefined data');
                    document.getElementById('loading').textContent = 'Error: Invalid data received';
                    setTimeout(() => {
                        document.getElementById('loading').style.display = 'none';
                    }, 2000);
                    return;
                }
                
                // Check data structure
                console.log('Checking data structure:', {
                    hasNodes: !!data.nodes,
                    nodesLength: data.nodes ? data.nodes.length : 0,
                    hasLinks: !!data.links,
                    linksLength: data.links ? data.links.length : 0
                });
                
                // Check if we have any data
                if (!data.nodes || data.nodes.length === 0) {
                    console.log('No additional relationships found');
                    document.getElementById('loading').textContent = 'No additional relationships found for this node.';
                    showNotification(`No additional relationships found for ${node.type}: ${node.label}`);
                    setTimeout(() => {
                        document.getElementById('loading').style.display = 'none';
                    }, 2000);
                        return;
                    }
                    
                    // Add any new nodes and links to the existing graph
                    const newNodes = [];
                    const newLinks = [];
                    const existingNodeIds = new Set(graphData.nodes.map(n => n.id));
                const existingLinkIds = new Set(graphData.links.map(l => {
                    const source = typeof l.source === 'object' ? l.source.id : l.source;
                    const target = typeof l.target === 'object' ? l.target.id : l.target;
                    return `${source}-${target}-${l.type}`;
                }));
                
                // Examine first few nodes for debugging
                console.log('Sample of nodes to add:', data.nodes.slice(0, 3));
                    
                    // Add new nodes
                    data.nodes.forEach(newNode => {
                        if (!existingNodeIds.has(newNode.id)) {
                            newNodes.push(newNode);
                        }
                    });
                
                // Examine first few links for debugging
                if (data.links && data.links.length > 0) {
                    console.log('Sample of links to add:', data.links.slice(0, 3));
                }
                    
                    // Add new links
                if (data.links) {
                    data.links.forEach(newLink => {
                        // Handle potential null source/target
                        if (!newLink.source || !newLink.target) {
                            console.error('Invalid link found:', newLink);
                            return;
                        }
                        
                        const sourceId = typeof newLink.source === 'object' ? newLink.source.id : newLink.source;
                        const targetId = typeof newLink.target === 'object' ? newLink.target.id : newLink.target;
                        
                        // Skip links with invalid source/target
                        if (!sourceId || !targetId) {
                            console.error('Link has null sourceId or targetId:', {sourceId, targetId, link: newLink});
                            return;
                        }
                        
                        const linkId = `${sourceId}-${targetId}-${newLink.type}`;
                        
                        if (!existingLinkIds.has(linkId)) {
                            newLinks.push(newLink);
                        }
                    });
                }
                
                console.log(`Found ${newNodes.length} new nodes and ${newLinks.length} new links`);
                    
                    // If we have new data, update the graph
                    if (newNodes.length > 0 || newLinks.length > 0) {
                    // Count the number of each type of node added
                    const newCases = newNodes.filter(n => n.type === 'case').length;
                    const newLaws = newNodes.filter(n => n.type === 'law').length;
                    const newSections = newNodes.filter(n => n.type === 'section').length;
                    
                    console.log(`Adding: ${newCases} cases, ${newLaws} laws, ${newSections} sections`);
                    
                        // Add to current graph data
                        graphData.nodes = graphData.nodes.concat(newNodes);
                        graphData.links = graphData.links.concat(newLinks);
                        
                        // Update debug info
                        updateDebugInfo();
                        
                        // Re-render the graph
                        renderGraph(graphData);
                    
                    // Generate detailed success message
                    let addedDetails = [];
                    if (newCases > 0) addedDetails.push(`${newCases} cases`);
                    if (newLaws > 0) addedDetails.push(`${newLaws} laws`);
                    if (newSections > 0) addedDetails.push(`${newSections} sections`);
                    
                    const linkText = newLinks.length === 1 ? '1 connection' : `${newLinks.length} connections`;
                    
                    // Show success notification with detailed breakdown
                    if (addedDetails.length > 0) {
                        showNotification(`Expanded ${node.type}: ${node.label} (Added ${addedDetails.join(', ')} and ${linkText})`);
                    } else {
                        showNotification(`Expanded ${node.type}: ${node.label} (Added ${linkText})`);
                    }
                } else {
                    showNotification(`No new relationships found for ${node.type}: ${node.label}`);
                    }
                    
                    document.getElementById('loading').style.display = 'none';
            }
            
            // Fetch the node's relationships with error tracking
            // First check if the URL is valid
            if (!nodeUrl || nodeUrl.includes('undefined')) {
                console.error('Invalid URL:', nodeUrl);
                document.getElementById('loading').textContent = 'Error: Invalid URL';
                showNotification('Error: Could not construct a valid URL with the data available');
                setTimeout(() => {
                    document.getElementById('loading').style.display = 'none';
                }, 3000);
                return;
            }
            
            // Make the request
            fetch(nodeUrl)
                .then(response => {
                    console.log(`Response status: ${response.status}`);
                    console.log(`Response headers:`, Array.from(response.headers).reduce((obj, [key, val]) => {
                        obj[key] = val;
                        return obj;
                    }, {}));
                    
                    if (!response.ok) {
                        if (response.status === 404) {
                            // Try the fallback URL if the main one returns 404
                            tryFallbackUrl();
                            return;
                        }
                        throw new Error(`HTTP error ${response.status}: The requested resource was not found`);
                    }
                    return response.json().catch(err => {
                        console.error('Error parsing JSON:', err);
                        throw new Error('Failed to parse response as JSON');
                    });
                })
                .then(data => {
                    if (!data) return; // If tryFallbackUrl was called, don't proceed
                    
                    console.log(`Received data:`, data);
                    
                    if (data.error) {
                        // If there's an error, try the fallback
                        console.error('Error expanding node:', data.error);
                        document.getElementById('loading').textContent = 'Error expanding node: ' + data.error;
                        tryFallbackUrl();
                        return;
                    }
                    
                    // Process the data
                    processGraphData(data);
                })
                .catch(error => {
                    console.error('Error expanding node:', error);
                    document.getElementById('loading').textContent = 'Error expanding node: ' + 
                        (error.message || 'Unable to retrieve related data.');
                    showNotification(`Error expanding node: ${error.message || 'Unable to retrieve related data'}`);
                    
                    // Try the fallback if it's not a connection error
                    if (!error.message.includes('Failed to fetch')) {
                        setTimeout(() => tryFallbackUrl(), 1000);
                    } else {
                        setTimeout(() => {
                    document.getElementById('loading').style.display = 'none';
                        }, 3000);
                    }
                });
        }
        
        function removeNode(nodeId) {
            // Find the node to remove
            const nodeIndex = graphData.nodes.findIndex(n => n.id === nodeId);
            
            if (nodeIndex === -1) {
                console.error('Node not found:', nodeId);
                return;
            }
            
            // Store node type for notification
            const nodeType = graphData.nodes[nodeIndex].type;
            const nodeLabel = graphData.nodes[nodeIndex].label;
            
            // Remove the node
            graphData.nodes.splice(nodeIndex, 1);
            
            // Remove all links connected to this node
            graphData.links = graphData.links.filter(link => {
                const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
                const targetId = typeof link.target === 'object' ? link.target.id : link.target;
                return sourceId !== nodeId && targetId !== nodeId;
            });
            
            // Find and remove orphaned nodes (nodes with no connections)
            const connectedNodeIds = new Set();
            
            // Collect all node IDs that are part of links
            graphData.links.forEach(link => {
                const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
                const targetId = typeof link.target === 'object' ? link.target.id : link.target;
                connectedNodeIds.add(sourceId);
                connectedNodeIds.add(targetId);
            });
            
            // Remove orphaned nodes
            const initialNodeCount = graphData.nodes.length;
            graphData.nodes = graphData.nodes.filter(node => connectedNodeIds.has(node.id));
            const orphanedNodesRemoved = initialNodeCount - graphData.nodes.length;
            
            // Update debug info
            updateDebugInfo();
            
            // Re-render the graph
            renderGraph(graphData);
            
            // Show notification about removal
            if (orphanedNodesRemoved > 0) {
                showNotification(`Removed ${nodeType}: ${nodeLabel} and ${orphanedNodesRemoved} orphaned nodes`);
            } else {
                showNotification(`Removed ${nodeType}: ${nodeLabel}`);
            }
        }
        
        function hideNodeDetails() {
            document.getElementById('detailsPanel').style.display = 'none';
        }
        
        function renderGraph(data) {
            const svg = d3.select('#graph');
            svg.selectAll('*').remove();
            
            const width = svg.node().getBoundingClientRect().width;
            const height = svg.node().getBoundingClientRect().height;
            
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
            
            // Create links - ensure source and target are properly formatted for D3
            const links = data.links.map(link => {
                return {
                    id: link.id,
                    source: link.source,
                    target: link.target,
                    type: link.type,
                    properties: link.properties
                };
            });
            
            // Define link colors based on relationship type
            const linkColor = d => {
                switch(d.type.toLowerCase()) {
                    case 'refers_to': return '#636363';  // Grey for case references
                    case 'cites': return '#9e9ac8';      // Purple for citations
                    case 'has_section': return '#a1d99b'; // Light green for law sections
                    default: return '#999';              // Default grey
                }
            };
            
            const link = g.append('g')
                .selectAll('line')
                .data(links)
                .enter().append('line')
                .attr('class', 'link')
                .attr('stroke', linkColor)
                .attr('stroke-width', 1)
                .attr('marker-end', 'url(#arrowhead)')
                .on('mouseenter', function(event, d) {
                    showTooltip(event, `${d.type}`);
                })
                .on('mousemove', function(event) {
                    moveTooltip(event);
                })
                .on('mouseleave', function() {
                    hideTooltip();
                });
            
            // Create nodes with different colors based on type
            const nodeColor = d => {
                switch(d.type) {
                    case 'case': return '#6baed6';  // Blue for cases
                    case 'law': return '#fd8d3c';   // Orange for laws
                    case 'section': return '#74c476'; // Green for law sections
                    default: return '#969696';      // Grey for unknown
                }
            };
            
            const node = g.append('g')
                .selectAll('circle')
                .data(data.nodes)
                .enter().append('circle')
                .attr('class', 'node')
                .attr('r', d => d.type === 'case' ? 10 : 8)  // Cases slightly larger
                .attr('fill', nodeColor)
                .attr('stroke-width', 1.5)
                .on('mouseenter', function(event, d) {
                    showTooltip(event, d.label);
                })
                .on('mousemove', function(event) {
                    moveTooltip(event);
                })
                .on('mouseleave', function() {
                    hideTooltip();
                })
                .on('click', function(event, d) {
                    selectedNode = d;
                    showNodeDetails(d);
                    // Highlight connected nodes and links
                    highlightConnections(d.id);
                })
                .call(d3.drag()
                    .on('start', dragstarted)
                    .on('drag', dragged)
                    .on('end', dragended));
            
            // Create labels
            const labels = g.append('g')
                .selectAll('text')
                .data(data.nodes)
                .enter().append('text')
                .text(d => d.label)
                .attr('font-size', 10)
                .attr('dx', 12)
                .attr('dy', 4)
                .style('display', showLabels ? 'block' : 'none');
            
            // Define force simulation
            simulation = d3.forceSimulation(data.nodes)
                .force('link', d3.forceLink(links).id(d => d.id).distance(100))
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
            
            // Auto-center and zoom to fit
            resetZoom();
            
            // Set up updateLabels function
            window.updateLabels = function() {
                labels.style('display', showLabels ? 'block' : 'none');
            };
            
            // Set up highlightConnections function
            window.highlightConnections = function(nodeId) {
                // Reset all nodes and links
                node.attr('opacity', 0.3);
                link.attr('opacity', 0.3);
                
                // Find connected links and nodes
                const connectedLinks = links.filter(l => 
                    (l.source.id === nodeId) || (l.target.id === nodeId)
                );
                
                // Get IDs of connected nodes
                const connectedNodeIds = new Set();
                connectedNodeIds.add(nodeId); // Add the selected node
                
                connectedLinks.forEach(l => {
                    connectedNodeIds.add(l.source.id);
                    connectedNodeIds.add(l.target.id);
                });
                
                // Highlight connected nodes and links
                node.filter(d => connectedNodeIds.has(d.id)).attr('opacity', 1);
                link.filter(d => connectedNodeIds.has(d.source.id) && connectedNodeIds.has(d.target.id))
                    .attr('opacity', 1);
            };
            
            // Add event listener to reset highlighting when clicking elsewhere
            svg.on('click', function(event) {
                if (event.target === svg.node()) {
                    node.attr('opacity', 1);
                    link.attr('opacity', 1);
                    hideNodeDetails();
                    selectedNode = null;
                }
            });
        }
        
        function resetZoom() {
            const svg = d3.select('#graph');
            const width = svg.node().getBoundingClientRect().width;
            const height = svg.node().getBoundingClientRect().height;
            
            svg.transition().duration(750).call(
                d3.zoom().transform,
                d3.zoomIdentity
                    .translate(width / 2, height / 2)
                    .scale(0.8)
            );
        }
        
        function showTooltip(event, text) {
            const tooltip = d3.select('#tooltip')
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
        
        function showNodeDetails(node) {
            const panel = document.getElementById('detailsPanel');
            const info = document.getElementById('nodeInfo');
            const expandBtn = document.getElementById('expandNode');
            
            // Display appropriate details based on node type
            let detailsHtml = `<h3>${node.label}</h3>`;
            
            if (node.type === 'case') {
            detailsHtml += `
                    <p><strong>Type:</strong> Legal Case</p>
                    <p><strong>Citation:</strong> ${node.properties.citation_number || 'N/A'}</p>
                `;
                
                if (node.properties.url) {
                    detailsHtml += `<p><a href="${node.properties.url}" target="_blank">View Case Document</a></p>`;
                }
                
                // Update expand button text/action based on type
                expandBtn.textContent = 'Expand Case (Find Cited Laws & Cases)';
                expandBtn.style.display = 'block';
                
            } else if (node.type === 'law') {
                detailsHtml += `
                    <p><strong>Type:</strong> Law</p>
                    <p><strong>Law ID:</strong> ${node.properties.law_id || 'N/A'}</p>
                    <p><strong>Text:</strong> ${node.properties.text || 'N/A'}</p>
                `;
                
                if (node.properties.url) {
                    detailsHtml += `<p><a href="${node.properties.url}" target="_blank">View Law Document</a></p>`;
                }
                
                expandBtn.textContent = 'Expand Law (Find Sections & Citing Cases)';
                expandBtn.style.display = 'block';
                
            } else if (node.type === 'section') {
                // Check if the section has the required unique_id property
                if (!node.properties.unique_id && node.properties.law_id && node.properties.section_id) {
                    // Compute the unique_id from law_id and section_id
                    node.properties.unique_id = `${node.properties.law_id}:${node.properties.section_id}`;
                    console.log(`Added missing unique_id to section: ${node.properties.unique_id}`);
                }
                
                detailsHtml += `
                    <p><strong>Type:</strong> Law Section</p>
                    <p><strong>Law ID:</strong> ${node.properties.law_id || 'N/A'}</p>
                    <p><strong>Section ID:</strong> ${node.properties.section_id || 'N/A'}</p>
                    <p><strong>Text:</strong> ${node.properties.text || 'N/A'}</p>
                `;
                
                if (node.properties.url) {
                    detailsHtml += `<p><a href="${node.properties.url}" target="_blank">View Section Document</a></p>`;
                }
                
                expandBtn.textContent = 'Expand Section (Find Citing Cases)';
                expandBtn.style.display = 'block';
                
            } else {
                detailsHtml += `<p><strong>Type:</strong> ${node.type}</p>`;
                expandBtn.style.display = 'none';
            }
            
            // Add remove option
            detailsHtml += `<p><button id="removeNode" class="button" style="background-color: #d9534f;">Remove Node</button></p>`;
            
            info.innerHTML = detailsHtml;
            panel.style.display = 'block';
            
            // Add event listener for remove button
            document.getElementById('removeNode').addEventListener('click', function() {
                removeNode(node.id);
                hideNodeDetails();
            });
        }

        // Function to show a temporary notification to the user
        function showNotification(message, duration = 3000) {
            // Create notification element if it doesn't exist
            let notification = document.getElementById('notification');
            if (!notification) {
                notification = document.createElement('div');
                notification.id = 'notification';
                notification.style.position = 'fixed';
                notification.style.top = '10px';
                notification.style.left = '50%';
                notification.style.transform = 'translateX(-50%)';
                notification.style.background = 'rgba(50, 50, 50, 0.9)';
                notification.style.color = 'white';
                notification.style.padding = '10px 20px';
                notification.style.borderRadius = '5px';
                notification.style.zIndex = '1000';
                notification.style.boxShadow = '0 2px 10px rgba(0,0,0,0.2)';
                document.body.appendChild(notification);
            }
            
            // Set the message and show the notification
            notification.textContent = message;
            notification.style.display = 'block';
            
            // Hide the notification after the specified duration
            setTimeout(() => {
                notification.style.display = 'none';
            }, duration);
        }
    </script>
</body>
</html>
''')

# Create a basic index page with links to API docs
with open(os.path.join(TEMPLATES_DIR, 'index.html'), 'w') as f:
    f.write('''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WASAT Legal Database API</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.6;
        }
        h1 {
            color: #333;
            border-bottom: 1px solid #ddd;
            padding-bottom: 10px;
        }
        .card {
            background: #f9f9f9;
            border-radius: 5px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        .btn {
            display: inline-block;
            background: #4CAF50;
            color: white;
            padding: 10px 15px;
            text-decoration: none;
            border-radius: 3px;
            margin-right: 10px;
        }
        code {
            background: #eee;
            padding: 2px 5px;
            border-radius: 3px;
        }
        .endpoints {
            margin-top: 20px;
        }
        .endpoint {
            margin-bottom: 10px;
        }
        .method {
            background: #34495e;
            color: white;
            padding: 3px 6px;
            border-radius: 3px;
            font-size: 12px;
            margin-right: 5px;
        }
    </style>
</head>
<body>
    <h1>WASAT Legal Database API</h1>
    
    <div class="card">
        <h2>Welcome to the API</h2>
        <p>This API provides access to WASAT legal cases and their relationships.</p>
        <p>
            <a href="/api/docs" class="btn">API Documentation</a>
            <a href="/visualizer" class="btn">Case Graph Visualizer</a>
        </p>
    </div>
    
    <div class="card">
        <h2>Key Features</h2>
        <ul>
            <li>Search for cases by citation number</li>
            <li>Get detailed information about specific cases</li>
            <li>Visualize relationships between cases</li>
            <li>Network analysis of case citation patterns</li>
        </ul>
    </div>
    
    <div class="card">
        <h2>Quick Examples</h2>
        <div class="endpoints">
            <div class="endpoint">
                <span class="method">GET</span>
                <code>/api/cases/search?q=your_search_term</code> - Search for cases
            </div>
            <div class="endpoint">
                <span class="method">GET</span>
                <code>/api/cases/[2022] WASAT 1</code> - Get case details
            </div>
            <div class="endpoint">
                <span class="method">GET</span>
                <code>/api/cases/[2022] WASAT 1/graph</code> - Get case visualization data
            </div>
            <div class="endpoint">
                <span class="method">POST</span>
                <code>/api/network</code> - Get network of multiple cases
            </div>
        </div>
    </div>
</body>
</html>
''')

# Create CSS file for visualizer
with open(os.path.join(STATIC_DIR, 'visualizer.css'), 'w') as f:
    f.write('''
body {
    font-family: Arial, sans-serif;
    margin: 0;
    padding: 0;
}
.container {
    display: flex;
    height: 100vh;
}
.sidebar {
    width: 300px;
    background: #f5f5f5;
    padding: 20px;
    overflow-y: auto;
}
.visualization {
    flex-grow: 1;
    position: relative;
}
.iframe-container {
    width: 100%;
    height: 100%;
}
iframe {
    width: 100%;
    height: 100%;
    border: none;
}
''')

# Initialize Flask-RESTx
authorizations = {
    'apikey': {
        'type': 'apiKey',
        'in': 'header',
        'name': 'X-API-KEY'
    }
}

api = Api(
    app,
    version='1.0',
    title='WASAT Legal Database API',
    description='API for querying relationships between legal cases, laws, and law sections',
    doc='/api/docs',
    authorizations=authorizations
)

# Create namespaces for organizing endpoints
ns_cases = Namespace('cases', description='Case operations')
ns_laws = Namespace('laws', description='Law operations')
ns_sections = Namespace('sections', description='Law section operations')
ns_network = Namespace('network', description='Network visualization operations')

api.add_namespace(ns_cases, path='/api/cases')
api.add_namespace(ns_laws, path='/api/laws')
api.add_namespace(ns_sections, path='/api/sections')
api.add_namespace(ns_network, path='/api/network')

# Global Neo4j driver
neo4j_driver = None

# Define models for API documentation
case_model = api.model('Case', {
    'citation_number': fields.String(required=True, description='Case citation number'),
    'url': fields.String(description='Link to the case document')
})

law_model = api.model('Law', {
    'law_id': fields.String(required=True, description='Law ID/title'),
    'text': fields.String(description='Law title'),
    'url': fields.String(description='Link to the law document')
})

section_model = api.model('LawSection', {
    'law_id': fields.String(required=True, description='Parent law ID'),
    'section_id': fields.String(required=True, description='Section ID'),
    'text': fields.String(description='Section title/text'),
    'url': fields.String(description='Link to the section document')
})

case_detail_model = api.model('CaseDetail', {
    'citation_number': fields.String(required=True, description='Case citation number'),
    'url': fields.String(description='Link to the case document'),
    'laws': fields.List(fields.Nested(law_model), description='Laws cited by this case'),
    'sections': fields.List(fields.Nested(section_model), description='Law sections cited by this case'),
    'referred_cases': fields.List(fields.Nested(case_model), description='Cases referred to by this case')
})

law_detail_model = api.model('LawDetail', {
    'law_id': fields.String(required=True, description='Law ID/title'),
    'text': fields.String(description='Law title'),
    'url': fields.String(description='Link to the law document'),
    'citing_cases': fields.List(fields.Nested(case_model), description='Cases that cite this law'),
    'sections': fields.List(fields.Nested(section_model), description='Sections in this law')
})

section_detail_model = api.model('SectionDetail', {
    'law_id': fields.String(required=True, description='Parent law ID'),
    'section_id': fields.String(required=True, description='Section ID'),
    'text': fields.String(description='Section title/text'),
    'url': fields.String(description='Link to the section document'),
    'citing_cases': fields.List(fields.Nested(case_model), description='Cases that cite this section'),
    'parent_law': fields.Nested(law_model, description='Parent law of this section')
})

node_model = api.model('NetworkNode', {
    'id': fields.String(required=True, description='Node ID'),
    'type': fields.String(required=True, description='Node type (case, law, section)'),
    'label': fields.String(description='Display label for the node'),
    'properties': fields.Raw(description='Node properties from the database')
})

link_model = api.model('NetworkLink', {
    'id': fields.String(required=True, description='Link ID'),
    'source': fields.String(required=True, description='Source node ID'),
    'target': fields.String(required=True, description='Target node ID'),
    'type': fields.String(description='Relationship type'),
    'properties': fields.Raw(description='Link properties from the database')
})

network_model = api.model('Network', {
    'nodes': fields.List(fields.Nested(node_model), description='Nodes in the network'),
    'links': fields.List(fields.Nested(link_model), description='Links between nodes')
})

network_request_model = api.model('NetworkRequest', {
    'citation_numbers': fields.List(fields.String, required=True, description='List of case citation numbers'),
    'max_depth': fields.Integer(default=1, description='Maximum depth for finding related nodes (1-3)')
})


class Neo4jAuraAPI:
    """Queries Neo4j Aura database and provides data for the API."""
    
    def __init__(self, uri: str, user: str, password: str):
        """Initialize the API with Neo4j connection details."""
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
    
    def run_query(self, query: str, params: Optional[Dict] = None) -> List[Dict]:
        """Run a Cypher query and return the results as a list of dictionaries."""
        if not params:
            params = {}
            
        try:
            # Add some defensive logging for citation numbers with square brackets
            if 'citation_number' in params and isinstance(params['citation_number'], str) and '[' in params['citation_number']:
                logger.info(f"Processing citation with brackets: {params['citation_number']}")
                
            with self.driver.session() as session:
                result = session.run(query, params)
                
                # Convert the result to a list of dictionaries
                records = []
                for record in result:
                    records.append(dict(record))
                
                # If no records found for a citation query, provide a clearer error
                if not records and 'citation_number' in params:
                    return [{"error": f"No data found for citation: {params['citation_number']}"}]
                
                return records
                
        except Exception as e:
            logger.error(f"Error running query: {str(e)}")
            logger.error(f"Query: {query}")
            logger.error(f"Parameters: {params}")
            return [{"error": str(e)}]
    
    def get_case_info(self, citation_number: str) -> Dict:
        """Get basic information about a case."""
        query = """
        MATCH (c:Case {citation_number: $citation_number})
        RETURN c.citation_number as citation_number, c.url as url
        """
        
        results = self.run_query(query, {"citation_number": citation_number})
        
        if not results or "error" in results[0]:
            return {"error": "Case not found or error occurred"}
        
        return results[0]
    
    def get_case_network(self, citation_numbers: List[str], max_depth: int = 1) -> Dict:
        """
        Get a network of cases and their relationships to a specified depth.
        Returns nodes and relationships in a format suitable for visualization.
        """
        # Log input parameters for debugging
        logger.info(f"get_case_network called with citation_numbers={citation_numbers}, max_depth={max_depth}")
        
        # Create Cypher parameter for the list of cases
        params = {"citation_numbers": citation_numbers, "max_depth": max_depth}
        
        # Query to get the network of cases and their relationships
        query = """
        // Start with the input cases
        MATCH (c:Case)
        WHERE c.citation_number IN $citation_numbers
        
        // Find referenced cases up to max_depth
        CALL apoc.path.expand(c, "REFERS_TO|CITES", "", 1, $max_depth) YIELD path
        
        // Collect all nodes and relationships in the paths
        WITH collect(path) AS paths
        
        // Extract all nodes
        UNWIND paths AS path
        UNWIND nodes(path) AS node
        
        // Collect nodes with their labels and properties
        WITH collect(DISTINCT {
            id: id(node),
            labels: labels(node),
            properties: properties(node)
        }) AS nodes, paths
        
        // Extract all relationships
        UNWIND paths AS path
        UNWIND relationships(path) AS rel
        
        // Collect relationships with their type and properties
        WITH nodes, collect(DISTINCT {
            id: id(rel),
            type: type(rel),
            startNode: id(startNode(rel)),
            endNode: id(endNode(rel)),
            properties: properties(rel)
        }) AS relationships
        
        RETURN nodes, relationships
        """
        
        # Try to run with APOC first (if available in Neo4j Aura)
        try:
            logger.info("Attempting query with APOC")
            results = self.run_query(query, params)
            
            if results and not "error" in results[0]:
                logger.info(f"APOC query successful, found {len(results[0].get('nodes', []))} nodes and {len(results[0].get('relationships', []))} relationships")
                return self._format_network_response(results[0])
                
        except Exception as e:
            logger.warning(f"Error with APOC query: {str(e)}, falling back to simpler query")
        
        # Fallback query without APOC
        fallback_query = """
        // Start with input cases
        MATCH (start:Case)
        WHERE start.citation_number IN $citation_numbers
        
        // Custom path expansion for relationships - include both REFERS_TO and CITES
        MATCH path = (start)-[:REFERS_TO|CITES*1..$max_depth]->(related)
        
        // Collect all nodes
        WITH collect(DISTINCT start) + collect(DISTINCT related) as allNodes, 
             collect(DISTINCT path) as paths
        
        // Process nodes
        UNWIND allNodes AS node
        WITH collect({
            id: id(node),
            labels: labels(node),
            properties: properties(node)
        }) AS nodes, paths
        
        // Process relationships
        UNWIND paths AS p
        UNWIND relationships(p) AS rel
        
        RETURN nodes, collect(DISTINCT {
            id: id(rel),
            type: type(rel),
            startNode: id(startNode(rel)),
            endNode: id(endNode(rel)),
            properties: properties(rel)
        }) AS relationships
        """
        
        logger.info("Attempting fallback query without APOC")
        results = self.run_query(fallback_query, params)
        
        if not results or "error" in results[0]:
            logger.warning(f"Fallback query failed: {results[0].get('error') if results else 'No results'}")
            
            # If both queries fail, try a minimal version that just gets direct connections
            logger.info("Attempting minimal query with direct connections only")
            minimal_query = """
            // Match the input cases
            MATCH (c:Case)
            WHERE c.citation_number IN $citation_numbers
            
            // Find directly connected nodes (1-hop only) - be explicit about all relationship types
            OPTIONAL MATCH (c)-[r1:REFERS_TO]->(c2:Case)
            OPTIONAL MATCH (c)-[r2:CITES]->(c3:Case)  // Also check CITES relationships between cases
            OPTIONAL MATCH (c)-[r3:CITES]->(l:Law)
            OPTIONAL MATCH (c)-[r4:CITES]->(s:LawSection)
            
            // Collect nodes, ensuring we have no nulls
            WITH c, 
                 COLLECT(DISTINCT c2) AS citedCases1,
                 COLLECT(DISTINCT c3) AS citedCases2,
                 COLLECT(DISTINCT l) AS citedLaws,
                 COLLECT(DISTINCT s) AS citedSections,
                 COLLECT(DISTINCT r1) AS rels1,
                 COLLECT(DISTINCT r2) AS rels2,
                 COLLECT(DISTINCT r3) AS rels3,
                 COLLECT(DISTINCT r4) AS rels4
                 
            WITH COLLECT(DISTINCT c) + 
                 [x IN citedCases1 WHERE x IS NOT NULL] + 
                 [x IN citedCases2 WHERE x IS NOT NULL] + 
                 [x IN citedLaws WHERE x IS NOT NULL] + 
                 [x IN citedSections WHERE x IS NOT NULL] AS allNodes,
                 
                 [x IN rels1 WHERE x IS NOT NULL] + 
                 [x IN rels2 WHERE x IS NOT NULL] + 
                 [x IN rels3 WHERE x IS NOT NULL] + 
                 [x IN rels4 WHERE x IS NOT NULL] AS allRels
            
            // Format nodes
            UNWIND allNodes AS node
            WITH collect({
                id: id(node),
                labels: labels(node),
                properties: properties(node)
            }) AS nodes, allRels
            
            // Format relationships
            UNWIND allRels AS rel
            
            RETURN nodes, collect({
                id: id(rel),
                type: type(rel),
                startNode: id(startNode(rel)),
                endNode: id(endNode(rel)),
                properties: properties(rel)
            }) AS relationships
            """
            
            results = self.run_query(minimal_query, params)
            
            if not results or "error" in results[0]:
                logger.error(f"All queries failed for citation_numbers={citation_numbers}")
                return {"error": "Failed to retrieve network data"}
        
            logger.info(f"Minimal query successful, found {len(results[0].get('nodes', []))} nodes and {len(results[0].get('relationships', []))} relationships")
        else:
            logger.info(f"Fallback query successful, found {len(results[0].get('nodes', []))} nodes and {len(results[0].get('relationships', []))} relationships")
        
        formatted_result = self._format_network_response(results[0])
        logger.info(f"Returning network with {len(formatted_result.get('nodes', []))} nodes and {len(formatted_result.get('links', []))} links")
        return formatted_result
    
    def _format_network_response(self, raw_data: Dict) -> Dict:
        """Format the network data for API response."""
        # Process nodes
        nodes = []
        for node in raw_data.get("nodes", []):
            # Convert Neo4j internal ID to string for frontend compatibility
            node_id = str(node["id"])
            
            # Determine node type from labels
            node_type = "unknown"
            if "Case" in node["labels"]:
                node_type = "case"
            elif "Law" in node["labels"]:
                node_type = "law"
            elif "LawSection" in node["labels"]:
                node_type = "section"
                
            # Extract key properties based on node type
            label = ""
            if node_type == "case":
                label = node["properties"].get("citation_number", "")
            elif node_type == "law":
                label = node["properties"].get("law_id", "")
            elif node_type == "section":
                section_id = node["properties"].get("section_id", "")
                law_id = node["properties"].get("law_id", "")
                label = f"{law_id} § {section_id}"
                
            # Create formatted node
            formatted_node = {
                "id": node_id,
                "type": node_type,
                "label": label,
                "properties": node["properties"]
            }
            nodes.append(formatted_node)
            
        # Process relationships
        links = []
        for rel in raw_data.get("relationships", []):
            # Format relationship
            formatted_rel = {
                "id": str(rel["id"]),
                "source": str(rel["startNode"]),
                "target": str(rel["endNode"]),
                "type": rel["type"].lower(),
                "properties": rel.get("properties", {})
            }
            links.append(formatted_rel)
            
        return {
            "nodes": nodes,
            "links": links
        }
    
    def search_cases(self, query: str, limit: int = 10) -> List[Dict]:
        """Search for cases matching a query string (partial citation match)."""
        if not query:
            return []
            
        # Create a partial match pattern
        pattern = f".*{re.escape(query)}.*"
        
        cypher = """
        MATCH (c:Case)
        WHERE c.citation_number =~ $pattern
        RETURN c.citation_number as citation_number, c.url as url
        LIMIT $limit
        """
        
        results = self.run_query(cypher, {"pattern": pattern, "limit": limit})
        
        if not results:
            return []
            
        if "error" in results[0]:
            logger.error(f"Error searching cases: {results[0]['error']}")
            return []
            
        return results
    
    def search_laws(self, query: str, limit: int = 10) -> List[Dict]:
        """Search for laws matching a query string (partial title match)."""
        if not query:
            return []
            
        # Create a partial match pattern
        pattern = f".*{re.escape(query)}.*"
        
        cypher = """
        MATCH (l:Law)
        WHERE l.law_id =~ $pattern OR l.text =~ $pattern
        RETURN l.law_id as law_id, l.text as text, l.url as url
        LIMIT $limit
        """
        
        results = self.run_query(cypher, {"pattern": pattern, "limit": limit})
        
        if not results:
            return []
            
        if "error" in results[0]:
            logger.error(f"Error searching laws: {results[0]['error']}")
            return []
            
        return results
    
    def get_case_citations(self, citation_number: str) -> Dict:
        """Get all laws and sections cited by a specific case."""
        query = """
        MATCH (c:Case {citation_number: $citation_number})
        
        // Get laws cited by this case
        OPTIONAL MATCH (c)-[:CITES]->(l:Law)
        WITH c, collect({law_id: l.law_id, text: l.text, url: l.url}) AS laws
        
        // Get sections cited by this case
        OPTIONAL MATCH (c)-[:CITES]->(s:LawSection)
        WITH c, laws, collect({
            law_id: s.law_id, 
            section_id: s.section_id, 
            text: s.text, 
            url: s.url
        }) AS sections
        
        // Get cases referred by this case
        OPTIONAL MATCH (c)-[:REFERS_TO]->(c2:Case)
        
        RETURN c.citation_number AS citation_number, 
               c.url AS url,
               laws, sections,
               collect({citation_number: c2.citation_number, url: c2.url}) AS referred_cases
        """
        
        results = self.run_query(query, {"citation_number": citation_number})
        
        if not results:
            return {"error": "Case not found"}
            
        if "error" in results[0]:
            return {"error": results[0]["error"]}
            
        return results[0]
    
    def get_case_visualization(self, citation_number: str, max_depth: int = 1) -> Dict:
        """Get a visualization of a case and its relationships, including laws and sections."""
        network_data = self.get_case_network([citation_number], max_depth)
        
        if "error" in network_data:
            return network_data
        
        # Return full network data including all node types (cases, laws, sections)
        return network_data
    
    def get_law_citations(self, law_id: str) -> Dict:
        """Get all cases that cite a specific law."""
        query = """
        MATCH (l:Law {law_id: $law_id})
        
        // Get cases citing this law
        OPTIONAL MATCH (c:Case)-[:CITES]->(l)
        WITH l, collect({citation_number: c.citation_number, url: c.url}) AS citing_cases
        
        // Get sections of this law
        OPTIONAL MATCH (l)-[:HAS_SECTION]->(s:LawSection)
        
        RETURN l.law_id AS law_id, 
               l.text AS text,
               l.url AS url,
               citing_cases,
               collect({
                   section_id: s.section_id,
                   text: s.text,
                   url: s.url
               }) AS sections
        """
        
        results = self.run_query(query, {"law_id": law_id})
        
        if not results:
            return {"error": "Law not found"}
            
        if "error" in results[0]:
            return {"error": results[0]["error"]}
            
        return results[0]
    
    def get_section_citations(self, law_id: str, section_id: str) -> Dict:
        """Get all cases that cite a specific law section."""
        # Create the unique section ID
        unique_section_id = f"{law_id}:{section_id}"
        
        query = """
        MATCH (s:LawSection {unique_id: $unique_section_id})
        
        // Get cases citing this section
        OPTIONAL MATCH (c:Case)-[:CITES]->(s)
        WITH s, collect({citation_number: c.citation_number, url: c.url}) AS citing_cases
        
        // Get the parent law
        OPTIONAL MATCH (l:Law)-[:HAS_SECTION]->(s)
        
        RETURN s.law_id AS law_id,
               s.section_id AS section_id,
               s.text AS text,
               s.url AS url,
               citing_cases,
               {
                   law_id: l.law_id,
                   text: l.text,
                   url: l.url
               } AS parent_law
        """
        
        results = self.run_query(query, {"unique_section_id": unique_section_id})
        
        if not results:
            return {"error": "Section not found"}
            
        if "error" in results[0]:
            return {"error": results[0]["error"]}
            
        return results[0]

    def get_law_visualization(self, law_id: str) -> Dict:
        """Get a visualization of a law and all cases that cite it."""
        # Create a custom query for law visualization
        params = {"law_id": law_id}
        
        query = """
        // Find the law
        MATCH (l:Law {law_id: $law_id})
        
        // Find cases that cite this law
        OPTIONAL MATCH (c:Case)-[:CITES]->(l)
        
        // Find sections of this law
        OPTIONAL MATCH (l)-[:HAS_SECTION]->(s:LawSection)
        
        // Find cases that cite any section of this law
        OPTIONAL MATCH (c2:Case)-[:CITES]->(s)
        
        // Collect all nodes
        WITH l, collect(DISTINCT c) + collect(DISTINCT s) + collect(DISTINCT c2) AS allNodes,
             collect(DISTINCT {type: 'CITES', start: id(c), end: id(l)}) +
             collect(DISTINCT {type: 'HAS_SECTION', start: id(l), end: id(s)}) +
             collect(DISTINCT {type: 'CITES', start: id(c2), end: id(s)}) AS allRels
        
        // Format nodes
        UNWIND allNodes AS node
        WHERE node IS NOT NULL
        WITH collect({
            id: id(node),
            labels: labels(node),
            properties: properties(node)
        }) AS nodes, l, allRels
        
        // Format relationships
        UNWIND allRels AS rel
        WHERE rel.start IS NOT NULL AND rel.end IS NOT NULL
        
        RETURN nodes, collect({
            type: rel.type,
            startNode: rel.start,
            endNode: rel.end,
            id: rel.start + '-' + rel.type + '-' + rel.end
        }) AS relationships
        """
        
        results = self.run_query(query, params)
        
        if not results or "error" in results[0]:
            return {"error": "Failed to retrieve visualization data for law"}
        
        return self._format_network_response(results[0])
    
    def get_section_visualization(self, law_id: str, section_id: str) -> Dict:
        """Get a visualization of a law section and all cases that cite it."""
        # Create the unique section ID
        unique_section_id = f"{law_id}:{section_id}"
        params = {"unique_section_id": unique_section_id}
        
        query = """
        // Find the section
        MATCH (s:LawSection {unique_id: $unique_section_id})
        
        // Find the parent law
        OPTIONAL MATCH (l:Law)-[:HAS_SECTION]->(s)
        
        // Find cases that cite this section
        OPTIONAL MATCH (c:Case)-[:CITES]->(s)
        
        // Find other sections of the same law
        OPTIONAL MATCH (l)-[:HAS_SECTION]->(s2:LawSection)
        WHERE s <> s2
        
        // Collect all nodes
        WITH s, l, collect(DISTINCT c) + [l] + collect(DISTINCT s2) AS allNodes,
             collect(DISTINCT {type: 'CITES', start: id(c), end: id(s)}) +
             collect(DISTINCT {type: 'HAS_SECTION', start: id(l), end: id(s)}) +
             collect(DISTINCT {type: 'HAS_SECTION', start: id(l), end: id(s2)}) AS allRels
        
        // Format nodes
        UNWIND allNodes AS node
        WHERE node IS NOT NULL
        WITH collect({
            id: id(node),
            labels: labels(node),
            properties: properties(node)
        }) AS nodes, s, allRels
        
        // Format relationships
        UNWIND allRels AS rel
        WHERE rel.start IS NOT NULL AND rel.end IS NOT NULL
        
        RETURN nodes, collect({
            type: rel.type,
            startNode: rel.start,
            endNode: rel.end,
            id: rel.start + '-' + rel.type + '-' + rel.end
        }) AS relationships
        """
        
        results = self.run_query(query, params)
        
        if not results or "error" in results[0]:
            return {"error": "Failed to retrieve visualization data for section"}
        
        return self._format_network_response(results[0])

    def get_cases_citing_case(self, citation_number: str) -> Dict:
        """Get cases that cite a specific case."""
        query = """
        MATCH (citing:Case)-[r:CITES]->(c:Case {citation_number: $citation_number})
        RETURN collecting {
            nodes: collect(distinct {
                id: id(citing), 
                labels: labels(citing),
                properties: properties(citing)
            }) + [{
                id: id(c), 
                labels: labels(c),
                properties: properties(c)
            }],
            relationships: collect({
                id: id(r),
                type: type(r),
                startNode: id(citing),
                endNode: id(c),
                properties: properties(r)
            })
        } as results
        """
        
        results = self.run_query(query, {"citation_number": citation_number})
        
        if not results or not results[0].get('results'):
            return {"error": "No cases citing this case found", "nodes": [], "links": []}
            
        return self._format_network_response(results[0]['results'])

    def get_cases_citing_law(self, law_id: str) -> Dict:
        """Get cases that cite a specific law."""
        query = """
        MATCH (citing:Case)-[r:REFERS_TO]->(l:Law {law_id: $law_id})
        RETURN collecting {
            nodes: collect(distinct {
                id: id(citing), 
                labels: labels(citing),
                properties: properties(citing)
            }) + [{
                id: id(l), 
                labels: labels(l),
                properties: properties(l)
            }],
            relationships: collect({
                id: id(r),
                type: type(r),
                startNode: id(citing),
                endNode: id(l),
                properties: properties(r)
            })
        } as results
        """
        
        results = self.run_query(query, {"law_id": law_id})
        
        if not results or not results[0].get('results'):
            return {"error": "No cases citing this law found", "nodes": [], "links": []}
            
        return self._format_network_response(results[0]['results'])

    def get_cases_citing_section(self, law_id: str, section_id: str) -> Dict:
        """Get cases that cite a specific law section."""
        # Create the unique section ID
        unique_section_id = f"{law_id}:{section_id}"
        
        query = """
        MATCH (citing:Case)-[r:CITES]->(s:LawSection {unique_id: $unique_section_id})
        RETURN {
            nodes: collect(distinct {
                id: id(citing), 
                labels: labels(citing),
                properties: properties(citing)
            }) + [{
                id: id(s), 
                labels: labels(s),
                properties: properties(s)
            }],
            relationships: collect({
                id: id(r),
                type: type(r),
                startNode: id(citing),
                endNode: id(s),
                properties: properties(r)
            })
        } as results
        """
        
        results = self.run_query(query, {"unique_section_id": unique_section_id})
        
        if not results or not results[0].get('results'):
            return {"error": "No cases citing this section found", "nodes": [], "links": []}
            
        return self._format_network_response(results[0]['results'])


# API routes with Flask-RESTx decorators

@api.route('/api/health')
class HealthCheck(Resource):
    @api.doc(description="Health check endpoint")
    def get(self):
        """Health check endpoint."""
        return {
            "status": "ok",
            "message": "Neo4j Aura API is running"
        }

@ns_cases.route('/search')
class CaseSearch(Resource):
    @api.doc(description="Search for cases matching a query string", 
             params={'q': 'Search query', 'limit': 'Maximum number of results (default: 10)'})
    @api.response(200, 'Success', [case_model])
    @api.response(400, 'Bad Request')
    def get(self):
        """Search for cases matching a query string."""
        query = request.args.get('q', '')
        limit = int(request.args.get('limit', 10))
        
        if not query:
            return {"error": "Query parameter 'q' is required"}, 400
            
        results = neo4j_driver.search_cases(query, limit)
        return results

@ns_laws.route('/search')
class LawSearch(Resource):
    @api.doc(description="Search for laws matching a query string",
             params={'q': 'Search query', 'limit': 'Maximum number of results (default: 10)'})
    @api.response(200, 'Success', [law_model])
    @api.response(400, 'Bad Request')
    def get(self):
        """Search for laws matching a query string."""
        query = request.args.get('q', '')
        limit = int(request.args.get('limit', 10))
        
        if not query:
            return {"error": "Query parameter 'q' is required"}, 400
            
        results = neo4j_driver.search_laws(query, limit)
        return results

@ns_cases.route('/<path:citation_number>')
class CaseDetail(Resource):
    @api.doc(description="Get details about a specific case and its citations",
             params={'citation_number': 'Case citation number'})
    @api.response(200, 'Success', case_detail_model)
    @api.response(404, 'Case not found')
    def get(self, citation_number):
        """Get details about a specific case and its citations."""
        # URL decode the citation number
        citation_number = citation_number.replace('_', ' ')
        
        result = neo4j_driver.get_case_citations(citation_number)
        
        if "error" in result:
            return {"error": result["error"]}, 404
            
        return result

@ns_cases.route('/<path:citation_number>/graph')
class CaseGraphVisualization(Resource):
    @api.doc(description="Get visualization data for a specific case and its relationships",
             params={'citation_number': 'Case citation number',
                     'max_depth': 'Maximum relationship depth (default: 1, max: 3)'})
    @api.response(200, 'Success', network_model)
    @api.response(404, 'Case not found')
    def get(self, citation_number):
        """Get visualization data for a specific case and its relationships."""
        # URL decode the citation number
        citation_number = citation_number.replace('_', ' ')
        
        # Get the max depth parameter, default to 1
        max_depth = min(int(request.args.get('max_depth', 1)), 3)
        
        result = neo4j_driver.get_case_visualization(citation_number, max_depth)
        
        if "error" in result:
            return {"error": result["error"]}, 404
            
        return result

@ns_laws.route('/<path:law_id>')
class LawDetail(Resource):
    @api.doc(description="Get details about a specific law and cases that cite it",
             params={'law_id': 'Law ID/title'})
    @api.response(200, 'Success', law_detail_model)
    @api.response(404, 'Law not found')
    def get(self, law_id):
        """Get details about a specific law and cases that cite it."""
        # URL decode the law ID
        law_id = law_id.replace('_', ' ')
        
        result = neo4j_driver.get_law_citations(law_id)
        
        if "error" in result:
            return {"error": result["error"]}, 404
            
        return result

@ns_sections.route('/<path:law_id>/<path:section_id>')
class SectionDetail(Resource):
    @api.doc(description="Get details about a specific law section and cases that cite it",
             params={'law_id': 'Law ID/title', 'section_id': 'Section ID'})
    @api.response(200, 'Success', section_detail_model)
    @api.response(404, 'Section not found')
    def get(self, law_id, section_id):
        """Get details about a specific law section and cases that cite it."""
        # URL decode the law ID and section ID
        law_id = law_id.replace('_', ' ')
        section_id = section_id.replace('_', ' ')
        
        result = neo4j_driver.get_section_citations(law_id, section_id)
        
        if "error" in result:
            return {"error": result["error"]}, 404
            
        return result

@ns_laws.route('/<path:law_id>/graph')
class LawGraphVisualization(Resource):
    @api.doc(description="Get visualization data for a specific law and its related cases/sections",
             params={'law_id': 'Law ID/title'})
    @api.response(200, 'Success', network_model)
    @api.response(404, 'Law not found')
    def get(self, law_id):
        """Get visualization data for a specific law and its related cases/sections."""
        # URL decode the law ID
        law_id = law_id.replace('_', ' ')
        
        result = neo4j_driver.get_law_visualization(law_id)
        
        if "error" in result:
            return {"error": result["error"]}, 404
            
        return result

@ns_sections.route('/<path:law_id>/<path:section_id>/graph')
class SectionGraphVisualization(Resource):
    @api.doc(description="Get visualization data for a specific law section and its related cases",
             params={'law_id': 'Law ID/title', 'section_id': 'Section ID'})
    @api.response(200, 'Success', network_model)
    @api.response(404, 'Section not found')
    def get(self, law_id, section_id):
        """Get visualization data for a specific law section and its related cases."""
        # URL decode the law ID and section ID
        law_id = law_id.replace('_', ' ')
        section_id = section_id.replace('_', ' ')
        
        result = neo4j_driver.get_section_visualization(law_id, section_id)
        
        if "error" in result:
            return {"error": result["error"]}, 404
            
        return result

@ns_network.route('')
class NetworkVisualization(Resource):
    @api.doc(description="Get a network of cases and their relationships for visualization")
    @api.expect(network_request_model)
    @api.response(200, 'Success', network_model)
    @api.response(400, 'Bad Request')
    @api.response(500, 'Server Error')
    def post(self):
        """Get a network of cases and their relationships for visualization."""
        data = request.json
        
        if not data or not data.get('citation_numbers'):
            return {"error": "Request body must include 'citation_numbers' array"}, 400
            
        citation_numbers = data['citation_numbers']
        max_depth = int(data.get('max_depth', 1))
        
        # Limit max_depth to prevent large queries
        if max_depth > 3:
            max_depth = 3
            
        result = neo4j_driver.get_case_network(citation_numbers, max_depth)
        
        if "error" in result:
            return {"error": result["error"]}, 500
        
        # Return full network including all node types (cases, laws, sections)
        return result

@ns_cases.route('/<path:citation_number>/cited_by')
class CaseCitedBy(Resource):
    @api.doc(description="Get cases that cite this case",
             params={'citation_number': 'Case citation number'})
    @api.response(200, 'Success', network_model)
    @api.response(404, 'Case not found')
    def get(self, citation_number):
        """Get cases that cite this case."""
        # URL decode the citation number
        citation_number = citation_number.replace('_', ' ')
        
        result = neo4j_driver.get_cases_citing_case(citation_number)
        
        if "error" in result:
            return {"error": result["error"]}, 404
            
        return result

@ns_laws.route('/<path:law_id>/cited_by')
class LawCitedBy(Resource):
    @api.doc(description="Get cases that cite this law",
             params={'law_id': 'Law ID/title'})
    @api.response(200, 'Success', network_model)
    @api.response(404, 'Law not found')
    def get(self, law_id):
        """Get cases that cite this law."""
        # URL decode the law ID
        law_id = law_id.replace('_', ' ')
        
        result = neo4j_driver.get_cases_citing_law(law_id)
        
        if "error" in result:
            return {"error": result["error"]}, 404
            
        return result

@ns_sections.route('/<path:law_id>/<path:section_id>/cited_by')
class SectionCitedBy(Resource):
    @api.doc(description="Get cases that cite this section",
             params={'law_id': 'Law ID/title', 'section_id': 'Section ID'})
    @api.response(200, 'Success', network_model)
    @api.response(404, 'Section not found')
    def get(self, law_id, section_id):
        """Get cases that cite this section."""
        # URL decode the law ID and section ID
        law_id = law_id.replace('_', ' ')
        section_id = section_id.replace('_', ' ')
        
        result = neo4j_driver.get_cases_citing_section(law_id, section_id)
        
        if "error" in result:
            return {"error": result["error"]}, 404
            
        return result

# Add routes for visualization pages
@app.route('/')
def index():
    """Render the main index page."""
    return render_template('index.html')

@app.route('/visualizer')
def visualizer():
    """Render the graph visualizer page."""
    # Check if a dataUrl parameter is provided
    data_url = request.args.get('dataUrl')
    
    # Inject the base URL into the template for API calls
    base_url = request.url_root.rstrip('/')
    
    # Render the template with the base URL and data URL
    return render_template(
        'graph_visualization.html', 
        api_base_url=base_url,
        data_url=data_url
    )

@app.route('/static/<path:path>')
def send_static(path):
    """Serve static files."""
    return send_from_directory(STATIC_DIR, path)

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description='REST API for Neo4j Aura database.')
    parser.add_argument('--uri', required=True, help='Neo4j Aura connection URI (required)')
    parser.add_argument('--user', required=True, help='Neo4j Aura username (required)')
    parser.add_argument('--password', required=True, help='Neo4j Aura password (required)')
    parser.add_argument('--port', type=int, default=5003, help='Port to run the API server on')
    parser.add_argument('--host', default='0.0.0.0', help='Host to run the API server on')
    args = parser.parse_args()
    
    global neo4j_driver
    
    try:
        # Initialize the Neo4j driver
        neo4j_driver = Neo4jAuraAPI(
            uri=args.uri,
            user=args.user,
            password=args.password
        )
        
        # Run the Flask app
        app.run(host=args.host, port=args.port)
        
    except Exception as e:
        logger.error(f"Error starting API: {str(e)}")
        sys.exit(1)
    finally:
        if neo4j_driver:
            neo4j_driver.close()

if __name__ == '__main__':
    main() 