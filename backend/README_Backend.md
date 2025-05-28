# RAG Application Backend

This is the backend service for the RAG (Retrieval-Augmented Generation) application, providing APIs for lawyers to chat with the model, find similar cases, build arguments,  and more.

## Structure

```
backend/
├── app/
│   ├── __init__.py            # FastAPI application setup
│   ├── config.py              # Configuration and environment variables
│   ├── db/
│   │   ├── __init__.py        # Database exports
│   │   ├── database.py        # SQLAlchemy setup
│   │   └── models.py          # Database models (User, Case)
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── __init__.py    # Route exports
│   │   │   ├── chat.py        # Chat endpoint
│   │   │   ├── arguments.py   # Build arguments endpoint
│   │   │   ├── citation_graph.py # Citation graph endpoints
│   │   │   ├── users.py       # User authentication endpoints
│   │   │   └── case_chunks.py # Case chunks processing endpoints
│   │   └── schemas/
│   │       ├── __init__.py    # Schema exports
│   │       ├── chat.py        # Chat request/response models
│   │       └── arguments.py   # Argument request/response models
│   └── services/
│       ├── __init__.py        # Service exports
│       ├── chat_service.py    # Chat business logic
│       └── arguments_service.py # Arguments business logic
├── rag/
│   ├── __init__.py            # RAG component exports
│   ├── embeddings.py          # Vector embeddings generation
│   ├── retrieval.py           # Document retrieval from vector store
│   ├── generation.py          # Text generation with retrieved context
│   └── models.py              # Model loading and management
├── tests/                     # Test suite
│   ├── unit/                  # Unit tests
│   ├── integration/           # Integration tests
│   └── system/                # System tests
├── requirements.txt           # Project dependencies
└── run.py                     # Application entry point
```

## Features

- Chat: Get a response to a message in conversational format using general LLM like GPT-4o with optional RAG support
- Build Arguments: Submit case information to get legal arguments and insights with reasoning language models like deepseek-reasoner or GPT-4o
- Citation Graph: Access and visualize citation networks between cases and laws
<!-- - Case Management: Upload, create, and retrieve case documents -->

## RAG Architecture

The Retrieval-Augmented Generation (RAG) pipeline is the core of the application, particularly for the Build Arguments feature. It retrieves relevant legal cases and adds them as context to the LLM prompts.

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

The retrieval process consists of several key steps:

1. **Embedding Generation**: The user's query (case content) is converted into a vector embedding using a pre-trained embedding model.

2. **Initial Retrieval**: The system retrieves potentially relevant documents by measuring vector similarity between the query embedding and stored document embeddings.

3. **Reranking**: A more computationally intensive similarity calculation is applied to the initially retrieved documents to improve relevance ranking.

4. **Chunk Retrieval**: For longer documents, the system retrieves specific relevant chunks rather than entire documents.

5. **Threshold Filtering**: Only documents/chunks with similarity scores above certain thresholds are passed to the next stage.

### Context Formatting

Retrieved documents and chunks are formatted into a structured context that can be fed to the LLM:

```python
# Example of formatted context
formatted_context = f"""
SIMILAR CASES:
1. CASE A v. CASE B (2023)
   Key points: [summary of relevant points]
   Similarity: 0.82

2. CASE C v. CASE D (2022)
   Key points: [summary of relevant points]
   Similarity: 0.75
"""
```

### Optimized Reasoning Steps

The system uses a multi-step reasoning approach to generate legal arguments:

1. **Analyze Case & Compare**: The LLM analyzes the user's case and compares it to retrieved similar cases
2. **Identify & Evaluate Arguments**: Potential legal arguments are identified and evaluated for strength
3. **Formulate Final Arguments**: The LLM formulates the final structured arguments with supporting cases and reasoning

Each step builds on the previous ones in a chain-of-thought approach:
- **Step 1**: Receives only the original case content and retrieved context
- **Step 2**: Receives the original case content, retrieved context, AND Step 1's complete output
- **Step 3**: Receives the original case content, retrieved context, AND outputs from both Steps 1 and 2

This creates a chain of reasoning where each step builds upon previous analysis. It allows Step 3 to formulate final arguments that are informed by both the initial analysis of the case and similar precedents (Step 1) and the identification and evaluation of potential arguments (Step 2).

This approach significantly improves the quality of legal reasoning by mimicking how a lawyer might approach the problem: first understanding the case and precedents, then identifying possible arguments, and finally crafting the strongest arguments based on that analysis.

### Single-Call Alternative 

The system also supports a single-call reasoning approach that produces results with lower latency:

```
/api/v1/build-arguments?use_single_call=true
/api/v1/build-arguments/single-call  (dedicated endpoint)
```

This alternative uses one comprehensive prompt that instructs the LLM to follow the same reasoning steps internally rather than making sequential calls. The single-call approach:

- Is typically 2-3x faster end-to-end
- Uses 20-30% fewer tokens in total (lower cost)
- May produce slightly less detailed analysis in some cases
- Still follows the same structured reasoning process internally

The system records the same performance metrics for both approaches, allowing for easy comparison of speed vs. quality tradeoffs.

### Performance Metrics

The system tracks and reports detailed performance metrics for each reasoning step:

```
==== GENERATION METRICS SUMMARY ====
Total Input Tokens: 15,234
Total Output Tokens: 8,547
Total Tokens: 23,781
Total Execution Time: 87.35 seconds

Step 1 Time: 24.51s (28.1% of total)
Step 2 Time: 29.83s (34.2% of total)
Step 3 Time: 33.01s (37.7% of total)
```

These metrics include:
- **Token counts**: Input and output tokens for each step and in total
- **Execution time**: Time spent on each step and total processing time
- **Step breakdown**: Percentage of total time spent on each reasoning step

Token counting is implemented through:
- Exact token counting for OpenAI models using the `tiktoken` library
- Estimation for other models (Claude, DeepSeek) based on whitespace tokenization with appropriate multipliers

This performance tracking helps optimize the system for cost and latency while ensuring high-quality legal reasoning.

### Fallback Mechanisms

The system includes robust fallback mechanisms:

- If no documents meet the primary similarity threshold, a lower fallback threshold is used
- If a primary model fails, the system can fall back to alternative LLM providers
- The output processing includes multiple parsing strategies to handle variations in LLM output formatting

## Prerequisites

- Python 3.8 or higher
- PostgreSQL with pgvector extension (for vector search functionality)
- OpenAI API key (for GPT-4o and other OpenAI models)
- DeepSeek API key (optional, for DeepSeek models)
- [Optional] Docker for containerized deployment

## Installation

### Local Development

1. Clone the repository
2. Navigate to the backend directory:
   ```
   cd backend
   ```
3. Create a virtual environment:
   ```
   python -m venv venv
   ```
4. Activate the virtual environment:
   - On Windows:
     ```
     venv\Scripts\activate
     ```
   - On macOS/Linux:
     ```
     source venv/bin/activate
     ```
5. Install base dependencies:
   ```
   pip install -r requirements.txt
   ```
   This will install FastAPI, database drivers, and other core dependencies.

6. Install Langchain packages:
   ```
   ./install_langchain.sh
   ```
   **Important:** This script is required because langchain has complex interdependencies that need specific versions. Running this script ensures the text splitting and chunking functionality works properly. Do not skip this step.

7. Configure your environment variables by copying the `.env.example` file to `.env` and updating the values:
   ```
   cp .env.example .env
   ```
   Then edit the `.env` file with your API keys and database settings:
   ```
   # LLM API Keys
   OPENAI_API_KEY=your-openai-api-key-here
   DEEPSEEK_API_KEY=your-deepseek-api-key-here
   
   # Database Configuration
   DATABASE_URL=postgresql://username:password@localhost/satdata
   
   # Other settings as needed
   ```

8. Setup PostgreSQL with pgvector:
   Ensure the pgvector extension is enabled in your PostgreSQL database:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```

9. Verify your setup (optional):
   Run the environment test to verify your API keys are loaded correctly:
   ```
   python simple_env_test.py
   ```

## LLM Integration

This application uses:
- OpenAI API directly for OpenAI models (gpt-4o, etc.)
- OpenAI client with DeepSeek base URL for DeepSeek models

No separate DeepSeek Python package is needed as we're using the OpenAI client with a custom base URL.

## Running the Application

### Local Development

1. Start the application:
   ```
   python run.py
   ```
2. The API will be available at `http://localhost:8000`
3. API documentation is available at `http://localhost:8000/docs`

### Docker Deployment

#### Using Docker Compose (Recommended)

The project is already configured for easy deployment using Docker Compose:

1. Make sure Docker and Docker Compose are installed on your system

2. Place your `satdata.dump` file in the project root directory (if you have a database backup to restore)

3. Set up API keys by either:
   - Creating a `.env` file in the project root:
     ```
     OPENAI_API_KEY=your_openai_api_key
     DEEPSEEK_API_KEY=your_deepseek_api_key
     ```
   - Or setting environment variables directly:
     ```bash
     export OPENAI_API_KEY=your_openai_api_key
     export DEEPSEEK_API_KEY=your_deepseek_api_key
     ```

4. Start the services from the project root:
   ```bash
   docker-compose up -d
   ```

5. The API will be available at `http://localhost:8000`

The Docker Compose setup includes:
- PostgreSQL with pgvector extension
- Automatic database initialization
- Automatic restoration of the satdata.dump file (if present)
- Backend service with all dependencies

#### Using Docker Alone

If you prefer to use Docker without Docker Compose:

1. Build the backend Docker image:
   ```bash
   cd backend
   docker build -t rag-backend .
   ```

2. Run a PostgreSQL container with pgvector:
   ```bash
   docker run -d --name postgres -p 5432:5432 \
     -e POSTGRES_USER=postgres \
     -e POSTGRES_PASSWORD=postgres \
     -e POSTGRES_DB=satdata \
     pgvector/pgvector:latest
   ```

3. Initialize the pgvector extension:
   ```bash
   docker exec postgres psql -U postgres -d satdata -c "CREATE EXTENSION IF NOT EXISTS vector;"
   ```

4. Run the backend container:
   ```bash
   docker run -d --name rag-backend -p 8000:8000 \
     --link postgres:postgres \
     -e DATABASE_URL=postgresql://postgres:postgres@postgres:5432/satdata \
     -e OPENAI_API_KEY=your_openai_api_key \
     -e DEEPSEEK_API_KEY=your_deepseek_api_key \
     rag-backend
   ```

#### Docker Networking Notes

- If you're using Docker on macOS or Windows, you might need to use `host.docker.internal` instead of `localhost` to access services running on your host machine.
- If your PostgreSQL instance is external, ensure the database is accessible from the Docker network.

#### Database Notes

The Docker Compose setup is configured to:
- Enable the pgvector extension automatically
- Restore the satdata.dump file if it exists in the project root
- Persist database data in a Docker volume

If you need to manually connect to the PostgreSQL container:
```bash
docker exec -it postgres psql -U postgres -d satdata
```

## Testing

### Running Tests

The application includes a comprehensive test suite:

```bash
# Run all tests
python -m pytest

# Run only unit tests
python -m pytest tests/unit/

# Run a specific test file
python -m pytest tests/unit/rag/test_isolated_rag.py

# Run with coverage report
python -m pytest tests/unit/rag/test_isolated_rag.py --cov=rag
```

### System Tests

To run the system tests, you need to have the server running first:

1. Start the server in one terminal:
   ```bash
   python run.py
   ```

2. Run the system tests in another terminal:
   ```bash
   python -m pytest tests/system/test_e2e_direct.py -v
   ```

See the [Test Suite Documentation](tests/README.md) for more details.

## Testing with API Client

You can test the API endpoints using tools like Postman, cURL, or any HTTP client.

### Chat
```
POST http://localhost:8000/api/v1/chat
Body (JSON):
{
    "message": "What are the key legal rights of tenants in NSW?",
    "conversation_id": null,
    "llm_model": "gpt-4o",
    "use_rag": true
}
```

### Build Arguments
```
POST http://localhost:8000/api/v1/build-arguments
Body (JSON):
{
    "case_content": "I'm a tenant and my landlord has refused to fix the broken heating system for months. It's winter now and the temperature in my apartment is dropping below safe levels. I've sent multiple written requests but received no response. What are my legal rights?",
    "case_title": "Landlord refusing to make repairs",
    "case_topic": "Tenancy Law",
    "llm_model": "gpt-4o"
}
```

## API Documentation

See the [API Documentation](docs/rag_api.md) for detailed information about all available endpoints.

## Troubleshooting

### Dependency Conflicts

If you encounter dependency conflicts:

1. Try installing packages one by one with `pip install package==version`
2. Use a virtual environment to isolate dependencies
3. When upgrading, check compatibility with existing packages

### Database Issues

Ensure pgvector extension is enabled in PostgreSQL:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Make sure your PostgreSQL connection parameters in the `.env` file are correct.

### API Key Issues

If you're experiencing issues with API calls:
1. Verify your API keys are correctly set in the `.env` file
2. Check that the API keys have sufficient permissions and credits
3. Confirm network connectivity to the API services

## Deployment to AWS

For deploying to AWS, you have several options:

### Option 1: AWS Elastic Beanstalk

1. Install the EB CLI:
   ```
   pip install awsebcli
   ```
2. Initialize your EB CLI repository:
   ```
   eb init -p python-3.9 rag-backend
   ```
3. Create an environment and deploy:
   ```
   eb create rag-backend-env
   ```

### Option 2: AWS ECS with Docker

1. Create a repository in Amazon ECR
2. Build, tag, and push your Docker image
3. Create an ECS task definition and service

### Option 3: AWS Lambda with API Gateway

1. Package your application using AWS Lambda layers for dependencies
2. Define API routes using API Gateway
3. Connect to a database service like RDS or DynamoDB

## License

This project is proprietary and confidential. 