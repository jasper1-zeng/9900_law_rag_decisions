[![Open in Visual Studio Code](https://classroom.github.com/assets/open-in-vscode-2e0aaae1b6195c2367325f4f02e2d04e9abb55f0b24a779b69b11b9e10269abc.svg)](https://classroom.github.com/online_ide?assignment_repo_id=18241161&assignment_repo_type=AssignmentRepo)

# SAT Decisions Frontend

## Overview

This is the frontend application for the SAT Decisions RAG system. It provides a user-friendly interface for searching, analyzing, and exploring State Administrative Tribunal (SAT) decisions using AI and semantic search.

## Technologies

- **React 19.0.0**: Core UI library
- **React Router**: For navigation and routing
- **Axios**: For API requests
- **CSS Modules**: For component styling

## Directory Structure

```
frontend/
├── public/                   # Static files
│   ├── index.html           # HTML template
│   └── assets/              # Images and other assets
├── src/                      # Source code
│   ├── index.js             # Application entry point
│   ├── App.js               # Main application component
│   ├── components/          # UI components
│   │   ├── Auth/            # Authentication components
│   │   ├── Search/          # Search components
│   │   ├── Case/            # Case viewing components
│   │   ├── ChatPage/        # Chat interface
│   │   └── Layout/          # Layout components
│   ├── services/            # API communication
│   │   ├── api.js           # API client
│   │   ├── auth.js          # Authentication service
│   │   └── search.js        # Search service
│   ├── contexts/            # React contexts
│   │   └── AuthContext.js   # Authentication context
│   └── styles/              # CSS styles
├── cypress/                  # Tests (Component and E2E)
├── package.json              # Dependencies and scripts
└── .env                      # Environment configuration
```

## Installation

1. Make sure you have Node.js (v18+) installed
2. Install dependencies:
```bash
npm install
```

## Running the Application

### Development Mode

```bash
npm start
```

The application will be available at http://localhost:3000

### Production Build

```bash
npm run build
```

This will create a production-ready build in the `build` directory.

## Key Features

### 1. Authentication
- Login page for user authentication
- Protected routes for authorized users only
- JWT token-based authentication

### 2. Search Interface
- Semantic search input with autosuggestions
- Advanced filtering options
- Search results with relevance indicators

### 3. Case Viewer
- Full-text case document viewing
- Citation highlighting
- Related cases sidebar

### 4. Argument Builder
- Interface for analyzing case descriptions
- Legal argument generation
- Citation integration

### 5. Chat Interface
- Conversational UI for legal queries
- History tracking
- Document upload capability

### 6. Citation Graph
- Interactive visualization of case relationships
- Filtering and exploration tools
- Integration with search results

## Environment Configuration

Create a `.env` file in the frontend root directory with the following variables:

```
REACT_APP_API_URL=http://localhost:8000
REACT_APP_TITLE=SAT Decisions RAG
```

## API Integration

The frontend communicates with the backend API using services defined in the `src/services` directory. The main API client is configured in `src/services/api.js`.

Example API usage:

```javascript
import api from '../services/api';

// Fetch search results
const searchResults = await api.post('/api/search', { query: 'commercial tenancy dispute' });

// Get case details
const caseDetails = await api.get(`/api/cases/${caseId}`);
```
