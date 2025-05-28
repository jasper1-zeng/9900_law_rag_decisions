#!/bin/bash
# This script installs langchain and related packages in a compatible combination

echo "Installing langchain packages..."

# First uninstall any existing installations to prevent conflicts
pip uninstall -y langchain langchain-core langchain-community langchain-openai langchain-text-splitters langsmith

# Install specific versions known to work together with pydantic 2.4.2
pip install langchain==0.0.335
pip install langchain-core==0.1.16
pip install langchain-community==0.0.13
pip install langchain-openai==0.0.5
pip install langchain-text-splitters==0.0.1

echo "Langchain installation complete." 