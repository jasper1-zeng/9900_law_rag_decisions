# RAG Application API Documentation

## Overview
This API provides endpoints for the SAT Decisions RAG (Retrieval-Augmented Generation) application, focusing on legal assistance features including chat functionality and legal arguments generation.

## Base URL
```
http://localhost:8000
```

## Authentication
Currently authentication is not required for the API endpoints.

## Endpoints

### Chat

#### Chat with RAG
Get a response to a message with optional RAG (Retrieval-Augmented Generation) support.

**Endpoint:** `POST /api/v1/chat`

**Request Body:**
```json
{
    "message": "string",
    "conversation_id": null or "string",
    "llm_model": "gpt-4o",
    "use_rag": true
}
```

**Response:**
```json
{
    "response": "string",
    "conversation_id": "string"
}
```

**Sample Request:**
```json
{
    "message": "What are the key legal rights of tenants in NSW?",
    "conversation_id": null,
    "llm_model": "gpt-4o",
    "use_rag": true
}
```

**Sample Response:**
```json
{
    "response": "Tenants in NSW have several key legal rights under the Residential Tenancies Act 2010 (NSW)...",
    "conversation_id": "5f8e1f2b-7c9a-4d5e-8a3b-6f9c1d2e3f4a"
}
```

#### Chat Follow-up
Send a follow-up message in an existing conversation.

**Endpoint:** `POST /api/v1/chat`

**Request Body:**
```json
{
    "message": "string",
    "conversation_id": "string",
    "llm_model": "gpt-4o",
    "use_rag": true
}
```

**Response:** Same as Chat with RAG.

#### Chat with Streaming (Server-Side Events)
Get a streaming response to a message.

**Endpoint:** `POST /api/v1/chat/stream`

**Request Body:** Same as Chat with RAG.

**Response:** Server-sent events with chunks of the response.

### Legal Arguments

#### Build Arguments
Submit case content to get legal arguments and analysis.

**Endpoint:** `POST /api/v1/build-arguments`

**Request Body:**
```json
{
    "case_content": "string",
    "case_title": "string",
    "case_topic": "string",
    "llm_model": "gpt-4o"
}
```

**Response:**
```json
{
    "conversation_id": "string",
    "disclaimer": "string",
    "raw_content": "string"
}
```

**Sample Request:**
```json
{
    "case_content": "I'm a tenant and my landlord has refused to fix the broken heating system for months. It's winter now and the temperature in my apartment is dropping below safe levels. I've sent multiple written requests but received no response. What are my legal rights?",
    "case_title": "Landlord refusing to make repairs",
    "case_topic": "Tenancy Law",
    "llm_model": "gpt-4o"
}
```

**Sample Response:**
```json
{
    "conversation_id": "b064b5c3-4065-4b99-81e0-52b19d7d69f1",
    "disclaimer": "DISCLAIMER: Analysis generated by openai/gpt-4o. For informational purposes only.",
    "raw_content": "## Key Insights and Strengths\n\n**Key Insights:**\n1. **Landlord's Obligation:** Under Australian tenancy law, landlords are required to maintain rental properties in a habitable condition, which includes ensuring essential services like heating are functional, especially during winter months.\n2. **Tenant's Remedies:** Tenants have the right to seek remedies through the State Administrative Tribunal (SAT) when landlords fail to fulfill their obligations, including orders for urgent repairs or compensation.\n3. **SAT's Role:** The SAT has jurisdiction to resolve disputes between tenants and landlords, as demonstrated in similar cases where the tribunal has intervened to enforce landlord obligations."
}
```

#### Arguments Follow-up
Send a follow-up question for an existing legal arguments case.

**Endpoint:** `POST /api/v1/arguments/follow-up`

**Request Body:**
```json
{
    "message_content": "string",
    "conversation_id": "string",
    "llm_model": "gpt-4o"
}
```

**Response:**
```json
{
    "conversation_id": "string",
    "response": "string"
}
```

### Additional Arguments Endpoints

The following endpoints are also available for generating legal arguments:

- **Single Call Arguments:** `POST /api/v1/build-arguments/single-call`
- **Stream Arguments:** `POST /api/v1/build-arguments/stream`
- **Arguments with Reasoning:** `POST /api/v1/build-arguments/with-reasoning`

### Citation Graph API

The system also includes endpoints for accessing citation networks and case information:

- **Get Network:** `GET /api/network`
- **Search Cases:** `GET /api/cases/search`
- **Get Case by Citation:** `GET /api/cases/{citation_number}`
- **Get Cases Citing a Case:** `GET /api/cases/{citation_number}/cited_by`
- **Get Case Citation Graph:** `GET /api/cases/{citation_number}/graph`
- **Search Laws:** `GET /api/laws/search`
- **Get Law by ID:** `GET /api/laws/{law_id}`
- **Get Law Graph:** `GET /api/laws/{law_id}/graph`
- **Get Section:** `GET /api/sections/{law_id}/{section_id}`
- **Visualizer:** `GET /api/visualizer`

### Case Chunks API

For processing and searching case chunks:

- **Process Case Chunks:** `POST /api/v1/case-chunks/process`
- **Search Case Chunks:** `POST /api/v1/case-chunks/search`

### Conversations

For managing conversations:

- **Get All Conversations:** `GET /api/v1/conversations`
- **Get Conversation by ID:** `GET /api/v1/conversations/{conversation_id}`
- **Get Conversation Messages:** `GET /api/v1/conversations/{conversation_id}/messages`

### User Management

For user authentication and management:

- **User Registration:** `POST /api/v1/users/register`
- **User Login:** `POST /api/v1/users/login`
- **Forgot Password:** `POST /api/v1/users/forgot-password`
- **Reset Password:** `POST /api/v1/users/reset-password`

## Error Responses

The API may return various error responses, including:

**422 Validation Error:**
```json
{
    "detail": [
        {
            "type": "missing",
            "loc": ["body", "field_name"],
            "msg": "Field required",
            "input": {...}
        }
    ]
}
```

**404 Not Found:**
```json
{
    "detail": "Not found"
}
```

**500 Internal Server Error:**
```json
{
    "detail": "Internal server error"
}
```

## Notes

- The actual response format may vary slightly based on the specific endpoint and the data being returned.
- Some endpoints may require additional parameters not explicitly documented here.
- For streaming endpoints, responses are delivered as server-sent events.
- While authentication endpoints exist, most API endpoints currently do not require authentication.
