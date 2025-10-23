# Dataelan - AI-Powered Chat Platform

Dataelan is a comprehensive AI-powered platform that integrates multiple language models and provides a seamless chat experience with streaming responses. The platform consists of a Django backend and a Next.js frontend, designed for high performance and scalability.

## Table of Contents

- [Project Overview](#project-overview)
- [Architecture](#architecture)
- [Backend](#backend)
  - [Key Components](#key-components)
  - [Streaming AI Responses](#streaming-ai-responses)
  - [WebSocket Implementation](#websocket-implementation)
- [Frontend](#frontend)
  - [Key Components](#key-components-1)
  - [Chat Implementation](#chat-implementation)
- [Setup and Installation](#setup-and-installation)
  - [Backend Setup](#backend-setup)
  - [Frontend Setup](#frontend-setup)
- [Development](#development)
- [API Documentation](#api-documentation)
- [Environment Variables](#environment-variables)

## Project Overview

Dataelan is designed to provide an AI-powered chat platform with the following features:

- Real-time chat with AI models via WebSockets
- Support for multiple AI providers (OpenAI, Anthropic, etc.)
- Streaming AI responses for better user experience
- Project management and organization
- User authentication and authorization
- Workflow management
- Agent-based interactions
- Template library for common use cases

## Architecture

The project follows a client-server architecture:

- **Backend**: Django with Django Channels for WebSocket support
- **Frontend**: Next.js with React for the user interface
- **Database**: PostgreSQL for data storage
- **WebSockets**: For real-time communication between frontend and backend
- **Celery**: For asynchronous task processing

## Backend

The backend is built with Django and includes several apps that handle different aspects of the platform.

### Key Components

1. **Core**: User authentication, permissions, and base models
2. **Projects**: Project management and organization
3. **Prompt**: Chat sessions, message handling, and AI interactions
4. **Modelhub**: Integration with various AI providers (OpenAI, Anthropic, etc.)
5. **Workflows**: Workflow management and execution
6. **Agents**: Agent-based interactions and automation
7. **Template Library**: Reusable templates for common use cases
8. **Model Tester**: Tools for comparing and testing different AI models

### Streaming AI Responses

The backend supports streaming AI responses through the following components:

1. **UnifiedLLMClient**: A unified client that supports multiple AI providers and streaming responses
2. **ChatConsumer**: A WebSocket consumer that handles chat messages and streams AI responses
3. **LLMResponse**: A class that represents AI responses, including streaming support

The streaming process works as follows:

1. The frontend sends a chat message to the backend via WebSocket
2. The backend processes the message and calls the appropriate AI provider with streaming enabled
3. The AI provider returns a stream of response chunks
4. The backend sends these chunks to the frontend in real-time via WebSocket
5. The frontend renders the response incrementally as chunks arrive

### WebSocket Implementation

The WebSocket implementation uses Django Channels and includes:

1. **ASGI Configuration**: Sets up the ASGI application with WebSocket support
2. **Token Authentication**: Authenticates WebSocket connections using tokens
3. **ChatConsumer**: Handles WebSocket connections and messages
4. **Message Types**: Different message types for different purposes (e.g., `ai_response_start`, `ai_response_chunk`, `ai_response_end`)

## Frontend

The frontend is built with Next.js and React, providing a modern and responsive user interface.

### Key Components

1. **Chat Service**: Handles WebSocket connections and message processing
2. **Chat Context**: Provides chat state and functions to React components
3. **Chat UI**: Renders chat messages and provides user interaction
4. **Authentication**: Handles user authentication and session management
5. **Project Management**: Allows users to manage projects and sessions

### Chat Implementation

The chat implementation includes:

1. **ChatWebSocketService**: A service that handles WebSocket connections and message processing
2. **Chat Sidebar**: A UI component that displays chat messages and allows user interaction
3. **Message Rendering**: Renders chat messages with support for streaming responses
4. **Event Handling**: Handles different types of events (e.g., `message`, `streamChunk`, `error`)

## Setup and Installation

### Backend Setup

1. Create and activate a virtual environment:
   ```bash
   python3 -m venv dataelan_env
   source dataelan_env/bin/activate
   ```

2. Install dependencies:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. Set up the database:
   ```bash
   # Using Docker (recommended)
   docker-compose up -d postgres
   
   # Or manually set up PostgreSQL
   # Create a database named 'dataelan'
   # Create a user 'dataelan' with password 'dataelan'
   # Grant all privileges on the database to the user
   ```

4. Run migrations:
   ```bash
   python manage.py migrate
   ```

5. Create a superuser:
   ```bash
   python manage.py createsuperuser
   ```

6. Start the development server:
   ```bash
   python manage.py runserver
   ```

### Frontend Setup

1. Install dependencies:
   ```bash
   cd dataelan-frontend
   npm install
   ```

2. Start the development server:
   ```bash
   npm run dev
   ```

3. Open [http://localhost:3000](http://localhost:3000) in your browser

## Development

### Running the Full Stack

1. Start the backend server:
   ```bash
   cd backend
   python manage.py runserver
   ```

2. Start the frontend server:
   ```bash
   cd dataelan-frontend
   npm run dev
   ```

3. Access the application at [http://localhost:3000](http://localhost:3000)

### API Keys

To use the AI providers, you need to set up API keys:

1. Create API keys for the providers you want to use (OpenAI, Anthropic, etc.)
2. Add these keys to the database through the admin interface or API

## API Documentation

The API documentation is available at `/api/schema/swagger-ui/` when the backend server is running.

## Environment Variables

### Backend

- `DJANGO_SETTINGS_MODULE`: The Django settings module to use
- `POSTGRES_NAME`: PostgreSQL database name
- `POSTGRES_USER`: PostgreSQL username
- `POSTGRES_PASSWORD`: PostgreSQL password
- `POSTGRES_HOST`: PostgreSQL host
- `POSTGRES_PORT`: PostgreSQL port
- `DJANGO_LOG_LEVEL`: Log level for Django (default: INFO)
- `SECRET_KEY`: Django secret key

### Frontend

- `NEXT_PUBLIC_API_URL`: URL of the backend API
- `NEXT_PUBLIC_WS_URL`: URL of the WebSocket endpoint
