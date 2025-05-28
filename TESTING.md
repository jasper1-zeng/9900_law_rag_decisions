# Testing Documentation

This document outlines the testing strategy and instructions for running tests for the project.

## Types of Tests

### Frontend Tests

#### Cypress Component Tests
Tests individual React components in isolation using real browser environments.

**Location:** `frontend/cypress/component`

**Test files:**
- `ChatPage.cy.js` - Tests the chat interface functionality
- `LoginPage.cy.js` - Tests the login page functionality

**Run with:**
```bash
cd frontend
npx cypress open --component
```

This will open the Cypress test runner in component testing mode, allowing you to run and debug component tests in a real browser.


#### Cypress End-to-End Tests
Tests complete frontend user workflows against a mocked or real backend.

**Location:** `frontend/cypress/e2e`

**Run with:**
```bash
cd frontend
npx cypress open # For interactive mode
npx cypress run # For headless mode
```

#### Accessibility Tests
Tests for accessibility compliance using cypress-axe.

**Location:** `frontend/cypress/e2e`

**Installation:**
```bash
npm install --save-dev cypress-axe axe-core
```

**Run with:**
```bash
cd frontend
npx cypress open
```

### Backend Tests

#### API Unit Tests
Tests individual API endpoints in isolation.

**Location:** `backend/tests/unit`

**Run with:**
```bash
cd backend
python -m pytest tests/unit
```

#### Integration Tests
Tests interactions between different backend components.

**Location:** `backend/tests/integration`

**Run with:**
```bash
cd backend
python -m pytest tests/integration
```

### Full-Stack Tests

#### End-to-End User Flow Tests
Tests complete user journeys across frontend and backend.

**Location:** `frontend/cypress/e2e/flows`

**Available Flow Tests:**
- `chat-to-visualization-flow.cy.js` - Tests user journey from chat to arguments with response validation


**Important Notes:**
- These tests involve AI-generated responses which may take time (60-120 seconds)
- Tests are designed to be resilient to UI changes using multiple selector strategies
- Some tests stop after validating responses to avoid timeouts with long documents

**Run with:**
```bash
# Start backend first
cd backend
python manage.py runserver

# Then in a separate terminal, run the frontend
cd frontend
npm start

# In a third terminal, run the tests
cd frontend
npx cypress open
# Select the flows tests under E2E Testing
```

**Headless Mode (CI/CD):**
```bash
cd frontend
npx cypress run --spec "cypress/e2e/flows/**/*.cy.js"
```

#### Contract Tests
Tests to ensure API contracts between frontend and backend remain consistent.

**Installation:**
```bash
npm install --save-dev @pact-foundation/pact
```

**Run with:**
```bash
cd frontend
npm run test:pact
```



## Test Coverage

To generate coverage reports:

```bash
# Frontend
cd frontend
npx cypress run --component --coverage

# Backend
cd backend
python -m pytest --cov=app
```

