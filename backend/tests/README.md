# SAT Decisions RAG System - Test Suite

## Summary

This test suite provides comprehensive testing for the SAT Decisions Retrieval Augmented Generation (RAG) system. The test suite includes:

- 35 isolated tests for the RAG components with 54% overall code coverage
- 5 integration tests for database interactions (skipped by default)
- 4 simple module existence tests
- 12 RAG component tests with looser mocking
- 5 chat service tests
- 7 system tests for end-to-end functionality

All tests can be run with minimal dependencies because the isolated tests use extensive mocking to avoid external dependencies like database connections or API calls.

## Test Directory Structure

The tests are organized into a directory structure:

```
backend/tests/
├── unit/
│   ├── api/               # API route tests
│   ├── services/          # Service layer tests 
│   │   └── test_chat_service.py
│   └── rag/               # RAG component unit tests
│       ├── test_isolated_rag.py
│       ├── test_rag_components.py
│       └── test_simple.py
├── integration/           # Integration tests directory
│   └── test_rag_integration.py
└── system/                # System tests directory
    ├── test_e2e_arguments.py # Arguments API tests
    ├── test_e2e_chat.py     # Chat API tests
    └── test_e2e_direct.py   # Direct HTTP request tests
```

## Test Files

Key test files include:

- `unit/rag/test_isolated_rag.py` - Isolated tests for the RAG components that avoid dependencies on database connections or application configuration.
- `unit/rag/test_rag_components.py` - Unit tests for individual RAG components (embeddings, retrieval, generation)
- `integration/test_rag_integration.py` - Integration tests that test the RAG system with a real database
- `unit/services/test_chat_service.py` - Tests for the chat service that uses the RAG components
- `system/test_e2e_direct.py` - End-to-end tests using direct HTTP requests to the running server
- `conftest.py` - Shared fixtures and test setup

## Test Structure

The tests are organized into several classes, each corresponding to a major component of the RAG system:

- `TestEmbeddings`: Tests for embedding generation functionality
- `TestRetrieval`: Tests for document retrieval functionality
- `TestGeneration`: Tests for response generation functionality
- `TestRAGModels`: Tests for the models module
- `TestRAGAdditional`: Supplementary tests for vector search, model loading, and other RAG components
- `TestRAGInit`: Tests for the RAG initialization functionality
- `TestGenerationComponent`: Focused tests for the generation module with higher coverage

## Test Coverage

Current test coverage for the RAG components is approximately 72%, with breakdown by module:

- rag/__init__.py: 100%
- rag/embeddings.py: 93%
- rag/generation.py: 65%
- rag/llm_providers.py: 55%
- rag/models.py: 62%
- rag/retrieval.py: 98%

To see the coverage report, run:

```
python -m pytest tests/unit/rag/test_isolated_rag.py --cov=rag
```

## Running the Tests

To run all the tests:

```bash
python -m pytest
```

To run all unit tests:

```bash
python -m pytest tests/unit/
```

To run all RAG unit tests:

```bash
python -m pytest tests/unit/rag/
```

To run a specific test class:

```bash
python -m pytest tests/unit/rag/test_isolated_rag.py::TestEmbeddings
```

To run a specific test:

```bash
python -m pytest tests/unit/rag/test_isolated_rag.py::TestEmbeddings::test_generate_embeddings
```

## Mocking Approach

The tests use a variety of mocking strategies to avoid external dependencies:

1. **Sentence Transformers**: The embedding generation model is mocked to avoid loading the actual model, which would be slow and unnecessary for testing.
2. **Database Connections**: All database connections are mocked to avoid requiring a real database for testing.
3. **LLM Providers**: LLM providers like OpenAI are mocked to avoid requiring API keys and making actual API calls.
4. **HTTP Requests**: HTTP clients are patched to avoid making actual network requests.

This approach allows the tests to run quickly and reliably without external dependencies.

## Test Strategy

The tests follow these principles:

1. **Isolation**: Tests are isolated from external dependencies (database, models, etc.) using mocks.
2. **Comprehensive Coverage**: Tests cover normal cases, edge cases, and error handling.
3. **Non-Invasive**: Tests don't modify the RAG logic but verify its behavior through well-defined interfaces.
4. **Organized Structure**: Tests are organized by layer (unit, integration, system) and component (api, services, rag).

## Test Categories

### Unit Tests

These tests use mocks to isolate specific components and test their functionality without dependencies. Located in the `tests/unit/` directory.

### Integration Tests

These tests require a connection to the actual PostgreSQL database with the pgvector extension and test data. Located in the `tests/integration/` directory. They will be skipped if the database is not available.

### System Tests

Full end-to-end tests that verify multiple components working together. Located in the `tests/system/` directory.

#### End-to-End Tests

The system directory includes three types of end-to-end tests:

1. **TestClient-based tests**: `test_e2e_arguments.py` and `test_e2e_chat.py` use FastAPI's TestClient to test the API endpoints directly. These tests will be skipped if the app cannot be imported.

2. **Direct HTTP request tests**: `test_e2e_direct.py` makes direct HTTP requests to the running server. This test will be skipped if the server is not running. It includes:
   - `test_chat_with_no_rag`: Tests the chat functionality without RAG
   - `test_build_arguments`: Tests the arguments builder for legal case analysis

To run the system tests with direct HTTP requests, first ensure the server is running:

```bash
# Start the backend server in one terminal
python run.py

# Run the tests in another terminal
python -m pytest tests/system/test_e2e_direct.py -v
```

### Prerequisites

1. Make sure you have the required Python packages installed:

```bash
pip install pytest pytest-asyncio pytest-cov
```

2. For integration tests: Make sure your PostgreSQL database with pgvector extension is running and properly seeded with SAT decision data.

## Specific Case Tests

Some tests in `integration/test_rag_integration.py` are designed to test specific cases in your database. These are disabled by default and can be enabled by setting the environment variable:

```bash
export ENABLE_SPECIFIC_CASE_TESTS=true
```

You will need to modify the expected case IDs in these tests to match the actual case IDs in your database.

## Sample Test Data

The tests use sample queries about various legal topics, such as:

- Commercial lease termination
- Eviction notices
- Guardianship cases
- Appeals
- Building defects

## Extending the Tests

To extend the tests:

1. Add new test methods to existing test classes for new functionality
2. Add new test classes for new components
3. Add tests for edge cases and error conditions
4. Place tests in the appropriate directory based on their type (unit, integration, system)

## Notes

- The tests use extensive mocking to avoid external dependencies like API calls or database connections.
- You may see some warnings about deprecated functions during test runs. These are related to underlying libraries and don't affect the test results.
- These tests focus solely on RAG functionality and do not cover the API or other application components.
- When running the integration tests, you may see output indicating that tests were skipped if the database is not available. This is expected behavior.

## Recent Improvements

- Added new system tests using direct HTTP requests to test end-to-end functionality without TestClient dependency
- Created `test_e2e_direct.py` to directly test the running server with real HTTP requests
- Fixed import issues in existing system tests to properly import the app
- Reorganized the test suite into a more maintainable directory structure with separate folders for unit, integration, and system tests
- Fixed and enhanced LLM provider tests to properly mock the OpenAI import, increasing coverage from 30% to 55% for the llm_providers module
- Implemented a more robust approach for testing provider selection logic without relying on direct patching of imports
- Added proper attribute mocking in the MockSettings class to support all test scenarios
- Overall test coverage improved from 44% to 54%

All tests are now passing successfully in their new organized locations.

## Troubleshooting

If you're having trouble with the tests:

1. Check that your database connection is working
2. Verify that the pgvector extension is installed
3. Make sure your test data is properly loaded
4. Check the Python package versions match requirements
5. Examine the logs for specific error messages 