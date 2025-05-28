# Neo4j Aura API Server

This provides a REST API server for accessing the Neo4j Aura database containing WASAT case data.

## Features

- REST API for accessing case data and relationships
- Web interface for visualizing case networks
- Swagger UI documentation for the API

## Installation and Usage

```bash
# Install dependencies
pip install -r requirements.txt

# Run the API server
python app.py --uri neo4j+s://3d34e9d7.databases.neo4j.io --user neo4j --password wXydxCfCnWMZINiNbm0jhAzzWwbW5yjQkvjGdGd7DWw --port 5000
```

## Web Visualizer

The web visualizer is available at:
http://localhost:5000/visualizer

## API Access

Access the API at http://localhost:5000/api/

## API Documentation

Once the API server is running, you can access the Swagger UI documentation at:
http://localhost:5000/api/

## API Endpoints

### Case Endpoints

- `GET /api/cases/search?q=<query>&limit=<limit>` - Search for cases matching a query string
- `GET /api/cases/<citation_number>` - Get details about a specific case and its citations
- `GET /api/cases/<citation_number>/graph` - Get visualization data for a specific case
- `GET /api/cases/<citation_number>/cited_by` - Get cases that cite this case

### Law Endpoints

- `GET /api/laws/search?q=<query>&limit=<limit>` - Search for laws matching a query string
- `GET /api/laws/<law_id>` - Get details about a specific law and cases that cite it
- `GET /api/laws/<law_id>/graph` - Get visualization data for a specific law
- `GET /api/laws/<law_id>/cited_by` - Get cases that cite this law

### Section Endpoints

- `GET /api/sections/<law_id>/<section_id>` - Get details about a specific law section
- `GET /api/sections/<law_id>/<section_id>/graph` - Get visualization data for a specific law section
- `GET /api/sections/<law_id>/<section_id>/cited_by` - Get cases that cite this section

### Network Endpoint

- `POST /api/network` - Get a network of cases and their relationships for visualization 