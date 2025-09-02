# Institutional Memory - RAG Chatbot

A lightweight web-based chatbot that answers operational and developer questions using a knowledge base of technical documentation. Built with Python, Streamlit, ChromaDB, and Google's Gemini API.

## Features

- 📚 **Document Ingestion**: Load Markdown, HTML, and text files into a searchable knowledge base
- 🔍 **Semantic Search**: Uses vector embeddings for intelligent document retrieval
- 🤖 **RAG Pipeline**: Retrieval-Augmented Generation with Gemini API for grounded responses
- 💬 **Web Chat Interface**: Clean Streamlit-based chat interface
- 📝 **Source Citations**: Shows which documents and chunks were used for each answer
- 📊 **Feedback System**: Thumbs up/down feedback for response quality
- 🔄 **Easy Reset**: Clear and restart the knowledge base as needed

## Prerequisites

- Python 3.8+
- Google Gemini API key

## Setup

1. **Clone and navigate to the project directory**

2. **Install dependencies** (requirements will be handled separately)

3. **Set up your Gemini API key**:
   ```bash
   export GEMINI_API_KEY="your-actual-api-key-here"
   ```

4. **Add your documentation**:
   - Place Markdown (`.md`), HTML (`.html`), or text (`.txt`) files in the `data/` directory
   - Sample file `data/jboss_restart.md` is included for testing

5. **Ingest documents into the knowledge base**:
   ```bash
   python ingest.py
   ```

6. **Start the web application**:
   ```bash
   python app.py
   ```
   
   Or using streamlit directly:
   ```bash
   streamlit run app.py --server.port 5000
   ```

7. **Open your browser** and navigate to `http://localhost:5000`

## Usage

### Document Ingestion
```bash
# Process all documents in data/ directory
python ingest.py

# Check ingestion status - look for "✅ Ingestion completed successfully!"
