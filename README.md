[![Open in Visual Studio Code](https://classroom.github.com/assets/open-in-vscode-2e0aaae1b6195c2367325f4f02e2d04e9abb55f0b24a779b69b11b9e10269abc.svg)](https://classroom.github.com/online_ide?assignment_repo_id=18241161&assignment_repo_type=AssignmentRepo)

# SAT Decisions RAG

<div align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue.svg" />
  <img src="https://img.shields.io/badge/FastAPI-0.105.0-green.svg" />
  <img src="https://img.shields.io/badge/React-19.0.0-blue.svg" />
  <img src="https://img.shields.io/badge/LangChain-0.0.335-yellow.svg" />
  <img src="https://img.shields.io/badge/Neo4j-4.4-brightgreen.svg" />
</div>

A Retrieval Augmented Generation (RAG) system for searching, analyzing, and exploring State Administrative Tribunal (SAT) decisions using AI and semantic search.

## 📋 Table of Contents

- [Overview](#-overview)
- [System Architecture](#-system-architecture)
- [Key Features](#-key-features)
- [Getting Started](#-getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation with Docker](#installation-with-docker)
  - [Manual Installation](#manual-installation)
- [Running the Project](#-running-the-project)
  - [Docker Compose (Recommended)](#docker-compose-recommended)
  - [Running Components Separately](#running-components-separately)
  - [Default Credentials](#-default-credentials-for-testing)
- [RAG Architecture](#-rag-architecture)
  - [Retrieval Process](#retrieval-process)
  - [Multi-Step Reasoning](#multi-step-reasoning)
  - [Single-Call Alternative](#single-call-alternative)
- [Component Details](#component-details)
  - [Backend](#backend)
  - [Frontend](#frontend)
  - [Neo4j Citation Graph API](#neo4j-citation-graph-api)
  - [Data Pipeline](#data-pipeline)
- [Testing](#-testing)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)

## 🔍 Overview

The SAT Decisions RAG system is designed to help legal professionals, researchers, and students efficiently search and analyze SAT (State Administrative Tribunal) legal decisions. Traditional keyword search often misses relevant cases due to different terminology or phrasing. Our system uses modern RAG techniques with semantic embeddings to understand the meaning behind queries,return the most relevant legal documents and provide legal arguments and insights given query case description.

## 🏗️ System Architecture

```
                                  ┌─────────────────────┐
                                  │                     │
                                  │   SAT Website       │
                                  │                     │
                                  └─────────┬───────────┘
                                            │
                                            ▼
┌─────────────────┐             ┌─────────────────────┐
│                 │  Extract    │                     │
│  satscraper     ├────────────►│  Raw Case Data      │
│  (Scrapy)       │  Cases      │                     │
│                 │             └─────────┬───────────┘
└─────────────────┘                       │
                                          │ Process
                                          ▼
┌─────────────────┐             ┌─────────────────────┐       ┌─────────────────────┐
│                 │  Store      │                     │       │                     │
│  PostgreSQL     │◄────────────┤  data_processing    │───────►  Neo4j Database     │
│  (pgvector)     │  Embeddings │                     │ Graph │  (Citation Network) │
│                 │             └─────────┬───────────┘ Data  │                     │
└───────┬─────────┘                       │                   └────────┬────────────┘
        │                                 │                            │
        │                                 ▼                            │
        │                       ┌─────────────────────┐                │
        │                       │                     │                │
        │                       │     RAG System      │                │
        └──────────────────────►│ (LangChain + Models)│                │
                                │                     │                │
                                └─────────┬───────────┘                │
                                          │                            │
                                          │                            │
           ┌────────────────┐             │             ┌──────────────▼─────────┐
           │                │  API        │             │                        │
           │   Frontend     │◄────────────┘-------------┤  Neo4j API Server      │
           │   (React)      │                           │  (Citation Visualizer) │
           │                │                           │                        │
           └────────────────┘                           └────────────────────────┘
```

## 🧩 Key Features

### 1. Semantic Search
Find relevant cases even when they use different terminology thanks to vector-based similarity search.

### 2. Legal Argument Generation
Generate legal arguments and insights, utilizing a multi-step reasoning approach:
- **Analysis & Comparison**: Analyze cases and compare to similar precedents
- **Argument Identification**: Identify and evaluate potential legal arguments
- **Final Formulation**: Create well-reasoned, structured legal arguments

### 3. Citation Graph Visualization
Explore relationships between cases through interactive citation network visualization powered by Neo4j.
- **Interactive Network**: Visual exploration of case citation relationships
- **Case Hierarchy**: See which cases cite others and common precedents
- **Filtering Options**: Filter by date, court level, and relationship type

### 4. Chat Interface
Get responses to legal questions in a conversational format using general LLM with RAG support.

### 5. Document Upload
Upload case documents with automatic processing and embedding generation.

## 🚀 Getting Started

### Prerequisites

- **Docker & Docker Compose** (for containerized setup - recommended)
- For manual installation:
  - **Python 3.10+**: For backend, scraper, and data processing
  - **Node.js 18+**: For frontend development
  - **React 19.0.0**: For frontend UI components
  - **PostgreSQL with pgvector**: For database storage
  - **Neo4j**: For citation graph database
  - **API keys** for OpenAI and/or DeepSeek

### Installation with Docker

The simplest way to set up the entire project is using Docker Compose:

1. Clone/Extract the Project

   If from GitHub
   ```bash
   git clone <https://github.com/unsw-cse-comp99-3900/capstone-project-25t1-9900-t10a-chocolate-1.git>
   cd capstone-project-25t1-9900-t10a-chocolate-1
   ```
   If from zip file
   ```bash
   unzip capstone-project-25t1-9900-t10a-chocolate-1.zip
   cd capstone-project-25t1-9900-t10a-chocolate-1
   ```

2. Create a `.env` file with your API keys if `.env` file is not provided
   ```bash
   # Create .env file in project root
   echo "OPENAI_API_KEY=" > .env
   echo "DEEPSEEK_API_KEY=" >> .env
   
   # Optional: Configure Neo4j connection (defaults will work if not specified)
   # echo "NEO4J_URI=neo4j+s://your-instance-id.databases.neo4j.io" >> .env
   # echo "NEO4J_USER=neo4j" >> .env
   # echo "NEO4J_PASSWORD=your-password" >> .env
   ```

### Manual Installation

<details>
<summary>Expand for manual installation steps</summary>

#### 1. Clone the Repository

```bash
git clone <repository-url>
cd sat-decisions-rag
```

#### 2. Set Up Database

```bash
# Install PostgreSQL with pgvector extension
# This varies by platform - example for Ubuntu:
sudo apt install postgresql postgresql-contrib
sudo -u postgres psql -c "CREATE DATABASE satdata;"
sudo -u postgres psql -d satdata -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

#### 3. Backend Setup

```bash
# Navigate to backend
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install LangChain packages
chmod +x install_langchain.sh
./install_langchain.sh

# Configure environment
cp .env.example .env
# Edit .env with your database and API keys
```

#### 4. Frontend Setup

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env
# Edit .env with backend API URL
```

#### 5. Neo4j API Server Setup

```bash
# Navigate to Neo4j API server directory
cd satscraper/JJ_scraper/wasat_scraper/neo4j_aura_api

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the server
python app.py --uri neo4j+s://your-instance-id.databases.neo4j.io --user neo4j --password your-password --port 5001
```

#### 6. Scraper Setup (Optional)

```bash
# Navigate to scraper
cd satscraper

# Install dependencies
pip install -e .
```
</details>

## 🏃‍♂️ Running the Project

### Docker Compose (Recommended)

After completing the installation steps above, you can run the project:

```bash
# Ensure Docker Desktop is running first
# Start Docker Desktop and wait until it's fully running

# Start all services
docker-compose up -d

# View logs (optional)
docker-compose logs -f

# Stop services when done
docker-compose down
```

> **IMPORTANT:** After starting the services, wait until the backend API is fully initialized before using the frontend. You can verify the backend is ready by visiting http://localhost:8000 in your browser - you should see the message: `{"message":"Welcome to the SAT Legal Decisions API. Visit /docs for API documentation."}` This typically takes 20-30 seconds after containers start.

The Docker setup starts:
- PostgreSQL database with pgvector
- Backend API server
- Frontend web application
- Neo4j API server for citation visualization
- Cypress test runner (on demand)

You can access the application at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- Neo4j Citation Visualizer: http://localhost:5001/visualizer

### Running Components Separately

<details>
<summary>Expand for instructions on running components separately</summary>

#### Backend API

```bash
cd backend
source venv/bin/activate  # On Windows: venv\Scripts\activate
python run.py
```

The API will be available at `http://localhost:8000` with Swagger documentation at `http://localhost:8000/docs`.

#### Frontend Development Server

```bash
cd frontend
npm start
```

The frontend will be available at `http://localhost:3000`.

#### Neo4j API Server

```bash
cd satscraper/JJ_scraper/wasat_scraper/neo4j_aura_api
source venv/bin/activate  # On Windows: venv\Scripts\activate
python app.py --uri neo4j+s://your-instance-id.databases.neo4j.io --user neo4j --password your-password --port 5001
```

The Neo4j API and visualizer will be available at `http://localhost:5001`.

#### Running Tests

```bash
# Frontend Cypress tests
cd frontend
npx cypress open

# Backend tests
cd backend
python -m pytest
```
</details>

### 🧪 Default Credentials (For Testing)

- **Username**: `will.ren@student.unsw.edu.au`  
- **Password**: `123456`

## 📊 RAG Architecture

Our Retrieval-Augmented Generation (RAG) pipeline is the core of the application:

```
┌───────────────┐     ┌───────────────┐     ┌────────────────┐     ┌────────────────┐
│   User Input   │────▶│   Embedding   │────▶│   Retrieval    │────▶│   Reranking    │
│  (Case Query)  │     │  Generation   │     │   by Vector    │     │ (Relevance     │
└───────────────┘     └───────────────┘     │  Similarity    │     │  Improvement)   │
                                            └────────────────┘     └────────┬───────┘
                                                                            │
┌───────────────┐     ┌───────────────┐     ┌────────────────┐              │
│  Final Output  │◀────│   LLM with    │◀────│   Context      │◀─────────────┘
│  to User       │     │   Reasoning   │     │  Formatting    │
└───────────────┘     └───────────────┘     └────────────────┘
```

### Retrieval Process

1. **Embedding Generation**: The user's query is converted into a vector embedding
2. **Initial Retrieval**: The system retrieves relevant documents by measuring vector similarity
3. **Chunk Retrieval**: For longer documents, specific relevant chunks are retrieved
4. **Reranking**: A more intensive similarity calculation improves relevance ranking
5. **Threshold Filtering**: Only high-similarity documents are passed to the next stage

### Multi-Step Reasoning

For the Build Arguments feature, our system uses an advanced multi-step reasoning approach:

1. **Analyze Case & Compare**: The LLM analyzes the user's case and compares it to retrieved similar cases
2. **Identify & Evaluate Arguments**: Potential legal arguments are identified and evaluated for strength
3. **Formulate Final Arguments**: The LLM formulates the final structured arguments with supporting cases and reasoning

This chain-of-thought approach improves legal reasoning quality by:
- Building on previous analysis at each step
- Following how a lawyer might approach the problem
- Enabling deeper exploration of complex legal concepts

### Single-Call Alternative suitable for strong reasoning LLMs

For faster results, the system also offers a single-call mode that:
- Is typically 2x faster end-to-end
- Uses 60-70% fewer tokens (lower cost)
- May produce slightly less detailed analysis
- Still follows the same structured reasoning process internally

## Component Details

### Backend

The backend provides the API layer and RAG functionality:

- **Technologies**: FastAPI, PostgreSQL with pgvector, LangChain
- **Features**: Chat, Build Arguments, Citation Graph, User Authentication
- **API Documentation**: Available at `http://localhost:8000/docs`
- **Detailed Documentation**: See [backend/README_Backend.md](backend/README_Backend.md)

### Frontend

The frontend provides the user interface:

- **Technologies**: React, Axios, React Router
- **Features**: Login, Search, Build Arguments, Citation Graph, Case Viewer
- **Development**: See [frontend/README_Frontend.md](frontend/README_Frontend.md) for development details

### Neo4j Citation Graph API

The Neo4j API server provides citation graph visualization capabilities:

- **Technologies**: Python, Flask, Neo4j
- **Features**: 
  - REST API for citation data
  - Interactive web visualizer
  - Case relationship exploration
- **Access**: Available at `http://localhost:5001/visualizer`
- **API Documentation**: Available at `http://localhost:5001/api/`

### Data Pipeline

Data flows through the system in these steps:

1. **Scraping**: Extract decisions from SAT website
2. **Processing**: Clean and structure raw data
3. **Embedding**: Generate vector embeddings for semantic search
4. **Indexing**: Store documents and embeddings in PostgreSQL, citation relationships in Neo4j
5. **Retrieval**: Query the database at runtime with vector similarity search

## 🧪 Testing

The project includes comprehensive testing tools:

- **Backend Tests**: Unit, integration, and API tests
- **Frontend Tests**: Component tests and end-to-end flows with Cypress
- **Accessibility Tests**: Using cypress-axe
- **Full-Stack Tests**: End-to-end user flow tests

For detailed testing information, see [TESTING.md](TESTING.md).

## 🔧 Troubleshooting

<details>
<summary>Expand for common troubleshooting tips</summary>

### Database Issues

```bash
# Check if PostgreSQL is running
pg_isready

# Check if pgvector extension is installed
psql -d satdata -c "SELECT * FROM pg_extension WHERE extname = 'vector';"
```

### API Connection Errors

- Check if backend is running
- Verify CORS settings in `backend/app/__init__.py`
- Check network connectivity between containers if using Docker

### Citation Graph Issues

- Verify Neo4j API is running: http://localhost:5001/api/
- Check Neo4j connection credentials in the .env file
- Ensure NEO4J_API_URL environment variable is set correctly for the backend service

### LLM API Issues

- Verify API keys in `.env` files
- Check for sufficient credits on your API accounts
- Confirm proper model names in configuration

### Docker Issues

```bash
# Rebuild containers
docker-compose down
docker-compose up -d --build

# Check container logs
docker-compose logs backend
docker-compose logs neo4j-api
```

For more detailed troubleshooting, see the respective README files in component directories.
</details>

## 👥 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details on how to contribute.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
