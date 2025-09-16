# Institutional Memory - RAG Chatbot

## Overview

Institutional Memory is a lightweight web-based chatbot that answers operational and developer questions using a knowledge base of technical documentation. The system implements a Retrieval-Augmented Generation (RAG) pipeline to provide grounded, accurate responses with source citations. Built with Python, it features document ingestion from Markdown/HTML/text files, semantic search using vector embeddings, and a clean web chat interface powered by Streamlit.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Web Interface**: Streamlit-based single-page application providing a clean chat interface
- **User Experience**: Real-time chat with response streaming, source citations display, and thumbs up/down feedback system
- **Status Dashboard**: Sidebar showing system health, API configuration status, and knowledge base statistics

### Backend Architecture
- **Modular Design**: Separated concerns with dedicated modules for document processing, vector operations, LLM interactions, and logging
- **RAG Pipeline**: Three-stage process of retrieval (vector similarity search), augmentation (context formatting), and generation (LLM response)
- **Document Processing**: Supports multiple formats (Markdown, HTML, text) with intelligent parsing and chunking strategies
- **Vector Store**: ChromaDB for persistent vector storage with configurable similarity thresholds and retrieval parameters

### Data Storage Solutions
- **Vector Database**: ChromaDB with persistent storage for document embeddings and metadata
- **Local File System**: Direct file-based storage for source documents in `data/` directory
- **Structured Logging**: JSON and text-based logging for queries, responses, and user feedback

### Authentication and Authorization
- **API Key Management**: Environment variable-based configuration for Google Gemini API access
- **No User Authentication**: Simple single-user deployment model for MVP implementation

### External Dependencies
- **Google Gemini API**: Primary LLM for both embeddings generation and response generation
- **ChromaDB**: Vector database for semantic search capabilities
- **Streamlit**: Web framework for rapid UI development
- **Document Parsing**: BeautifulSoup for HTML processing, Python markdown library for Markdown files

## External Dependencies

### APIs and Services
- **Google Gemini API**: Core dependency for text embeddings (`text-embedding-004` model) and response generation (`gemini-2.5-flash` model)
- **Environment Configuration**: Requires `GEMINI_API_KEY` environment variable

### Python Libraries
- **Web Framework**: Streamlit for the web interface
- **Vector Database**: ChromaDB for persistent vector storage and similarity search
- **Document Processing**: BeautifulSoup4 for HTML parsing, markdown library for Markdown processing
- **AI/ML**: Google GenerativeAI library for Gemini API integration

### File System Dependencies
- **Data Directory**: `data/` for source documents (Markdown, HTML, text files)
- **Vector Storage**: `chroma_db/` for persistent ChromaDB storage
- **Logging**: `logs/` directory for query logs and system events

### Configuration Management
- **Environment Variables**: API keys and optional configuration overrides
- **Config Module**: Centralized configuration for chunk sizes, retrieval parameters, model names, and system prompts
- **Directory Structure**: Automated creation of required directories on startup