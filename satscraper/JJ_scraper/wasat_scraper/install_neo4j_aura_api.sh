#!/bin/bash
# install_neo4j_aura_api.sh - Script to install the neo4j_aura_api server package

echo "Installing neo4j_aura_api server package..."
cd neo4j_aura_api
pip install -e .
echo "Installation complete!"
echo
echo "You can now use the following command:"
echo "  neo4j-aura-api - Run the Neo4j Aura API server"
echo
echo "Example usage:"
echo "  neo4j-aura-api --uri NEO4J_AURA_URI --user NEO4J_USER --password NEO4J_PASSWORD --port 5000"
echo
echo "For more information, see neo4j_aura_api/README.md" 