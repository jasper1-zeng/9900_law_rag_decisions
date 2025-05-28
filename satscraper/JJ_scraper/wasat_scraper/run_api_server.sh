#!/bin/bash
# run_api_server.sh - Script to run the Neo4j Aura API server

echo "Starting Neo4j Aura API Server..."
cd neo4j_aura_api
python app.py --uri neo4j+s://3d34e9d7.databases.neo4j.io --user neo4j --password wXydxCfCnWMZINiNbm0jhAzzWwbW5yjQkvjGdGd7DWw --port 5000 