#!/usr/bin/env python3
"""
Streamlit web application for the Institutional Memory chatbot.
"""

import streamlit as st
from datetime import datetime
from vector_store import vector_store
from gemini_client import gemini_client
from logger import query_logger
from config import GEMINI_API_KEY

# Page configuration
st.set_page_config(
    page_title="Institutional Memory",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

def check_system_status():
    """Check if the system is properly configured"""
    issues = []
    
    # Check API key
    if not GEMINI_API_KEY or GEMINI_API_KEY == "your-gemini-api-key-here":
        issues.append("⚠️ Gemini API key not configured")
    
    # Check vector store
    info = vector_store.get_collection_info()
    if info['count'] == 0:
        issues.append("⚠️ No documents in knowledge base - run ingest.py first")
    
    return issues

def display_sidebar():
    """Display sidebar with system information"""
    with st.sidebar:
        st.header("🧠 Institutional Memory")
        st.markdown("---")
        
        # System status
        st.subheader("System Status")
        issues = check_system_status()
        
        if not issues:
            st.success("✅ System ready")
        else:
            for issue in issues:
                st.warning(issue)
        
        # Collection info
        info = vector_store.get_collection_info()
        st.metric("Documents in KB", info['count'])
        
        st.markdown("---")
        
        # Quick actions
        st.subheader("Quick Actions")
        
        if st.button("🔄 Refresh Status"):
            st.rerun()
        
        # Instructions
        st.markdown("---")
        st.subheader("Instructions")
        st.markdown("""
        1. **Setup**: Set `GEMINI_API_KEY` environment variable
        2. **Ingest**: Run `python ingest.py` to load documents
        3. **Chat**: Ask questions about your documentation
        4. **Reset**: Run `python reset.py` to clear the database
        """)

def display_chat_interface():
    """Display the main chat interface"""
    st.header("💬 Ask Questions About Your Documentation")
    
    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "feedback_given" not in st.session_state:
        st.session_state.feedback_given = set()
    
    # Display chat messages
    for i, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
            # Show sources if available
            if message["role"] == "assistant" and "sources" in message:
                with st.expander("📚 Sources", expanded=False):
                    for j, source in enumerate(message["sources"]):
                        st.markdown(f"""
                        **{j+1}. {source['title']}** (Score: {source['similarity_score']:.3f})
                        - Source: `{source['source']}`
                        - Chunk {source['chunk_id']} (Rank {source['rank']})
                        
                        *Preview:* {source['content'][:200]}...
                        """)
                
                # Feedback buttons (only for assistant messages)
                if i not in st.session_state.feedback_given:
                    col1, col2, col3 = st.columns([1, 1, 8])
                    with col1:
                        if st.button("👍", key=f"up_{i}"):
                            give_feedback(i, "positive", message.get("query", ""))
                    with col2:
                        if st.button("👎", key=f"down_{i}"):
                            give_feedback(i, "negative", message.get("query", ""))

def give_feedback(message_index: int, feedback_type: str, query: str):
    """Handle user feedback"""
    st.session_state.feedback_given.add(message_index)
    
    # Log feedback
    message = st.session_state.messages[message_index]
    query_logger.log_query(
        query=query,
        retrieved_chunks=message.get("sources", []),
        response=message["content"],
        feedback=feedback_type
    )
    
    st.success(f"Thanks for your {feedback_type} feedback!")
    st.rerun()

def process_query(question: str):
    """Process user query and generate response"""
    try:
        # Search for relevant chunks
        with st.spinner("Searching knowledge base..."):
            chunks = vector_store.search(question)
        
        if not chunks:
            return "I couldn't find any relevant information in the knowledge base for your question.", []
        
        # Generate response
        with st.spinner("Generating response..."):
            response = gemini_client.generate_response(question, chunks)
        
        # Log the query
        query_logger.log_query(question, chunks, response)
        
        return response, chunks
        
    except Exception as e:
        error_msg = f"Error processing query: {str(e)}"
        query_logger.log_error(error_msg, f"Query: {question}")
        return error_msg, []

def main():
    """Main application function"""
    display_sidebar()
    
    # Check system status
    issues = check_system_status()
    if issues:
        st.error("System not ready. Please check the sidebar for issues.")
        return
    
    display_chat_interface()
    
    # Chat input
    if prompt := st.chat_input("Ask a question about your documentation..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate response
        response, sources = process_query(prompt)
        
        # Add assistant response to chat history
        assistant_message = {
            "role": "assistant", 
            "content": response,
            "sources": sources,
            "query": prompt
        }
        st.session_state.messages.append(assistant_message)
        
        # Display assistant response
        with st.chat_message("assistant"):
            st.markdown(response)
            
            # Show sources
            if sources:
                with st.expander("📚 Sources", expanded=False):
                    for i, source in enumerate(sources):
                        st.markdown(f"""
                        **{i+1}. {source['title']}** (Score: {source['similarity_score']:.3f})
                        - Source: `{source['source']}`
                        - Chunk {source['chunk_id']} (Rank {source['rank']})
                        
                        *Preview:* {source['content'][:200]}...
                        """)
        
        st.rerun()

if __name__ == "__main__":
    main()
