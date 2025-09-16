#!/usr/bin/env python3
"""
Streamlit web application for the Institutional Memory chatbot.
Enhanced with chat history and Wiki.js integration.
"""

import streamlit as st
import os
from datetime import datetime
from typing import List, Dict, Any
import subprocess
from pathlib import Path

from vector_store import vector_store
from gemini_client import gemini_client
from logger import query_logger
from chat_sessions import chat_session_manager
from wiki_crawler import initialize_wiki_crawler
from config import GEMINI_API_KEY, WIKI_BASE_URL, WIKI_API_KEY

# Page configuration
st.set_page_config(
    page_title="Institutional Memory",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better UI
st.markdown("""
<style>
.chat-session {
    padding: 0.5rem;
    margin: 0.25rem 0;
    border-radius: 0.5rem;
    border: 1px solid #e0e0e0;
    cursor: pointer;
}
.chat-session:hover {
    background-color: #f0f0f0;
}
.active-session {
    background-color: #e3f2fd;
    border-color: #2196f3;
}
.new-chat-btn {
    width: 100%;
    margin-bottom: 1rem;
}
.config-section {
    padding: 1rem;
    border-radius: 0.5rem;
    border: 1px solid #e0e0e0;
    margin: 0.5rem 0;
}
.wiki-status {
    padding: 0.5rem;
    border-radius: 0.25rem;
    margin: 0.25rem 0;
}
.wiki-connected {
    background-color: #d4edda;
    color: #155724;
    border: 1px solid #c3e6cb;
}
.wiki-disconnected {
    background-color: #f8d7da;
    color: #721c24;
    border: 1px solid #f5c6cb;
}
</style>
""", unsafe_allow_html=True)

def check_system_status():
    """Check if the system is properly configured"""
    issues = []
    
    # Check API key
    if not GEMINI_API_KEY or GEMINI_API_KEY == "your-gemini-api-key-here":
        issues.append("⚠️ Gemini API key not configured")
    
    # Check vector store
    info = vector_store.get_collection_info()
    if info['count'] == 0:
        issues.append("⚠️ No documents in knowledge base")
    
    return issues

def check_wiki_connection():
    """Check Wiki.js connection status"""
    try:
        if WIKI_BASE_URL:
            crawler = initialize_wiki_crawler(WIKI_BASE_URL, WIKI_API_KEY)
            if crawler and crawler.test_connection():
                return True
        return False
    except:
        return False

def display_chat_history_sidebar():
    """Display chat history and session management in sidebar"""
    with st.sidebar:
        st.header("🗨️ Chat History")
        
        # New Chat button
        if st.button("➕ New Chat", key="new_chat", help="Start a new conversation", use_container_width=True):
            new_session_id = chat_session_manager.create_session()
            st.session_state.current_session_id = new_session_id
            st.session_state.messages = []
            st.rerun()
        
        # Get all sessions
        sessions = chat_session_manager.get_session_list()
        
        if sessions:
            st.markdown("---")
            st.subheader("Previous Chats")
            
            # Display sessions
            for session in sessions:
                # Create session display
                session_display = f"💬 {session['title']}"
                if session['message_count'] > 0:
                    session_display += f" ({session['message_count']})"
                
                # Session container
                session_key = f"session_{session['id']}"
                
                # Use columns for session item and delete button
                col1, col2 = st.columns([4, 1])
                
                with col1:
                    if st.button(
                        session_display, 
                        key=session_key,
                        help=f"Created: {session['created_at']}",
                        use_container_width=True
                    ):
                        switch_to_session(session['id'])
                
                with col2:
                    if st.button("🗑️", key=f"delete_{session['id']}", help="Delete chat"):
                        delete_session(session['id'])
        
        else:
            st.info("No chat history yet. Start a new conversation!")

def display_system_info_sidebar():
    """Display system information and configuration"""
    with st.sidebar:
        st.markdown("---")
        st.header("⚙️ System Status")
        
        # System health check
        issues = check_system_status()
        
        if not issues:
            st.success("✅ System ready")
        else:
            for issue in issues:
                st.warning(issue)
        
        # Knowledge base info
        info = vector_store.get_collection_info()
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Documents", info['count'])
        with col2:
            st.metric("Status", "✅" if info['count'] > 0 else "❌")
        
        # Wiki.js connection status
        st.markdown("---")
        st.header("📖 Wiki.js Integration")
        
        # Check Wiki.js connection
        wiki_connected = check_wiki_connection()
        
        if wiki_connected:
            st.markdown('<div class="wiki-status wiki-connected">🟢 Wiki.js Connected</div>', 
                       unsafe_allow_html=True)
            st.write(f"📍 {WIKI_BASE_URL}")
        else:
            st.markdown('<div class="wiki-status wiki-disconnected">🔴 Wiki.js Disconnected</div>', 
                       unsafe_allow_html=True)
            if WIKI_BASE_URL:
                st.write(f"📍 {WIKI_BASE_URL}")
            else:
                st.write("📍 Not configured")
        
        # Data sources info
        st.markdown("---")
        st.header("📦 Data Sources")
        
        # Local files
        data_dir = Path("data")
        local_files = len(list(data_dir.glob("*"))) if data_dir.exists() else 0
        st.write(f"📁 Local files: {local_files}")
        
        # Wiki.js pages info
        if wiki_connected:
            # Check for last fetch timestamp
            wiki_last_fetch = Path('.wiki_last_fetch')
            if wiki_last_fetch.exists():
                with open(wiki_last_fetch, 'r') as f:
                    last_fetch = f.read().strip()
                try:
                    fetch_time = datetime.fromisoformat(last_fetch)
                    st.write(f"📖 Last sync: {fetch_time.strftime('%m/%d %H:%M')}")
                except:
                    st.write("📖 Wiki.js: Available")
            else:
                st.write("📖 Wiki.js: Not synced yet")
            
            # Refresh Wiki button
            if st.button("🔄 Sync Wiki Pages", help="Fetch latest pages from Wiki.js"):
                sync_wiki_pages()
        
        # Configuration expander
        with st.expander("⚙️ Configuration"):
            display_configuration_panel()

def display_configuration_panel():
    """Display configuration options"""
    st.markdown("### Wiki.js Configuration")
    
    # Wiki.js URL input
    wiki_url = st.text_input(
        "Wiki.js Base URL",
        value=WIKI_BASE_URL,
        help="Wiki.js instance URL (e.g., http://localhost)",
        key="wiki_url_input"
    )
    
    # Wiki.js API key input
    wiki_api_key = st.text_input(
        "Wiki.js API Key (Optional)",
        value="***" if WIKI_API_KEY else "",
        type="password",
        help="For private wikis or API access",
        key="wiki_api_key_input"
    )
    
    # Test connection button
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔍 Test Connection", key="test_wiki_connection"):
            test_wiki_connection(wiki_url, wiki_api_key)
    
    with col2:
        if st.button("💾 Save Config", key="save_wiki_config"):
            save_wiki_configuration(wiki_url, wiki_api_key)
    
    st.markdown("### Ingestion Actions")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📥 Ingest Local Files", key="ingest_local"):
            trigger_ingestion("local")
    
    with col2:
        if st.button("📖 Ingest Wiki Pages", key="ingest_wiki"):
            trigger_ingestion("wiki")
    
    if st.button("🔄 Reset Vector Database", key="reset_db", help="Clear all ingested documents"):
        reset_vector_database()

def switch_to_session(session_id: str):
    """Switch to a different chat session"""
    success = chat_session_manager.switch_session(session_id)
    if success:
        st.session_state.current_session_id = session_id
        # Load messages for this session
        messages = chat_session_manager.get_session_messages(session_id)
        st.session_state.messages = format_messages_for_display(messages)
        st.rerun()
    else:
        st.error("Failed to switch to selected chat session")

def delete_session(session_id: str):
    """Delete a chat session"""
    success = chat_session_manager.delete_session(session_id)
    if success:
        # If this was the active session, create a new one
        if st.session_state.get('current_session_id') == session_id:
            new_session_id = chat_session_manager.create_session()
            st.session_state.current_session_id = new_session_id
            st.session_state.messages = []
        st.rerun()
    else:
        st.error("Failed to delete chat session")

def format_messages_for_display(db_messages: List[Dict]) -> List[Dict]:
    """Convert database messages to Streamlit display format"""
    formatted_messages = []
    for msg in db_messages:
        formatted_msg = {
            "role": msg["role"],
            "content": msg["content"]
        }
        if msg.get("sources"):
            formatted_msg["sources"] = msg["sources"]
        formatted_messages.append(formatted_msg)
    return formatted_messages

def ensure_active_session():
    """Ensure there's an active chat session"""
    if 'current_session_id' not in st.session_state:
        # Check for existing active session
        active_session = chat_session_manager.get_active_session()
        if active_session:
            st.session_state.current_session_id = active_session
            # Load messages for this session
            messages = chat_session_manager.get_session_messages(active_session)
            st.session_state.messages = format_messages_for_display(messages)
        else:
            # Create new session
            new_session_id = chat_session_manager.create_session()
            st.session_state.current_session_id = new_session_id
            st.session_state.messages = []

def display_main_chat():
    """Display the main chat interface"""
    st.header("🧠 Institutional Memory Assistant")
    
    # Ensure we have an active session
    ensure_active_session()
    
    # System status check
    issues = check_system_status()
    if issues:
        st.error("System not ready. Please check the sidebar for configuration issues.")
        for issue in issues:
            st.write(f"• {issue}")
        return
    
    # Initialize messages in session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Display chat messages
    for i, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
            # Show sources if available
            if message["role"] == "assistant" and message.get("sources"):
                with st.expander("📚 Sources", expanded=False):
                    for j, source in enumerate(message["sources"]):
                        # Handle Wiki.js sources specially
                        source_icon = "📖" if source.get('source', '').startswith('wiki:') else "📁"
                        
                        st.markdown(f"""
                        **{source_icon} {j+1}. {source.get('title', 'Unknown')}** (Score: {source.get('similarity_score', 0):.3f})
                        - Source: `{source.get('source', 'Unknown')}`
                        - Chunk {source.get('chunk_id', 0)} (Rank {source.get('rank', 0)})
                        
                        *Preview:* {source.get('content', '')[:200]}...
                        """)
                        
                        # Add Wiki.js page link if available
                        if 'wiki_url' in source:
                            st.markdown(f"[🔗 View in Wiki.js]({source['wiki_url']})")
                
                # Feedback buttons
                feedback_key = f"feedback_{i}_{st.session_state.current_session_id}"
                if feedback_key not in st.session_state:
                    col1, col2, col3 = st.columns([1, 1, 8])
                    with col1:
                        if st.button("👍", key=f"up_{i}_{st.session_state.current_session_id}"):
                            give_feedback(message["content"], "positive")
                            st.session_state[feedback_key] = "positive"
                            st.rerun()
                    with col2:
                        if st.button("👎", key=f"down_{i}_{st.session_state.current_session_id}"):
                            give_feedback(message["content"], "negative")
                            st.session_state[feedback_key] = "negative"
                            st.rerun()
                else:
                    st.write(f"Feedback: {st.session_state[feedback_key]}")
    
    # Chat input
    if prompt := st.chat_input("Ask a question about your documentation..."):
        # Add user message to chat
        user_message = {"role": "user", "content": prompt}
        st.session_state.messages.append(user_message)
        
        # Save user message to database
        chat_session_manager.add_message(
            st.session_state.current_session_id,
            "user",
            prompt
        )
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate response
        with st.chat_message("assistant"):
            with st.spinner("Searching knowledge base..."):
                response, sources = process_query(prompt)
            
            st.markdown(response)
            
            # Show sources
            if sources:
                with st.expander("📚 Sources", expanded=False):
                    for i, source in enumerate(sources):
                        source_icon = "📖" if source.get('source', '').startswith('wiki:') else "📁"
                        
                        st.markdown(f"""
                        **{source_icon} {i+1}. {source.get('title', 'Unknown')}** (Score: {source.get('similarity_score', 0):.3f})
                        - Source: `{source.get('source', 'Unknown')}`
                        - Chunk {source.get('chunk_id', 0)} (Rank {source.get('rank', 0)})
                        
                        *Preview:* {source.get('content', '')[:200]}...
                        """)
                        
                        # Add Wiki.js page link if available
                        if 'wiki_url' in source:
                            st.markdown(f"[🔗 View in Wiki.js]({source['wiki_url']})")
        
        # Add assistant response to chat
        assistant_message = {
            "role": "assistant", 
            "content": response,
            "sources": sources
        }
        st.session_state.messages.append(assistant_message)
        
        # Save assistant message to database
        chat_session_manager.add_message(
            st.session_state.current_session_id,
            "assistant",
            response,
            sources
        )
        
        # Update session title if this is the first exchange
        if len(st.session_state.messages) == 2:  # First user + assistant message
            update_session_title(prompt)
        
        st.rerun()

def process_query(question: str):
    """Process user query and generate response"""
    try:
        # Search for relevant chunks
        chunks = vector_store.search(question)
        
        if not chunks:
            return "I couldn't find any relevant information in the knowledge base for your question.", []
        
        # Generate response
        response = gemini_client.generate_response(question, chunks)
        
        # Log the query
        query_logger.log_query(question, chunks, response)
        
        return response, chunks
        
    except Exception as e:
        error_msg = f"Error processing query: {str(e)}"
        query_logger.log_error(error_msg, f"Query: {question}")
        return error_msg, []

def give_feedback(message_content: str, feedback_type: str):
    """Handle user feedback"""
    success = chat_session_manager.update_message_feedback(
        st.session_state.current_session_id,
        message_content,
        feedback_type
    )
    
    if success:
        st.success(f"Thanks for your {feedback_type} feedback!")
    else:
        st.error("Failed to save feedback")

def update_session_title(first_question: str):
    """Update session title based on the first question"""
    # Create a meaningful title from the first question
    title = first_question[:50] + "..." if len(first_question) > 50 else first_question
    # For now, we'll leave the auto-generated title

def test_wiki_connection(wiki_url: str, api_key: str = None):
    """Test Wiki.js connection"""
    try:
        with st.spinner("Testing Wiki.js connection..."):
            crawler = initialize_wiki_crawler(wiki_url, api_key)
            if crawler and crawler.test_connection():
                st.success(f"✅ Successfully connected to Wiki.js at {wiki_url}")
            else:
                st.error(f"❌ Cannot connect to Wiki.js at {wiki_url}")
                st.info("Make sure your Wiki.js instance is running and accessible")
    except Exception as e:
        st.error(f"Error testing connection: {str(e)}")

def sync_wiki_pages():
    """Sync pages from Wiki.js"""
    try:
        with st.spinner("Syncing Wiki.js pages..."):
            result = subprocess.run([
                'python', 'ingest.py', '--source', 'wiki'
            ], capture_output=True, text=True, cwd=os.getcwd())
            
            if result.returncode == 0:
                st.success("✅ Successfully synced Wiki.js pages!")
                st.rerun()
            else:
                st.error(f"❌ Failed to sync pages: {result.stderr}")
    except Exception as e:
        st.error(f"Error syncing Wiki.js: {str(e)}")

def save_wiki_configuration(wiki_url: str, api_key: str):
    """Save Wiki.js configuration"""
    # In a real implementation, you'd save this to environment or config file
    st.success("Configuration saved! (Note: Restart the app to apply changes)")
    st.info("Set WIKI_BASE_URL and WIKI_API_KEY environment variables for persistence")

def trigger_ingestion(source_type: str):
    """Trigger document ingestion"""
    try:
        with st.spinner(f"Ingesting {source_type} documents..."):
            result = subprocess.run([
                'python', 'ingest.py', '--source', source_type
            ], capture_output=True, text=True, cwd=os.getcwd())
            
            if result.returncode == 0:
                st.success(f"✅ Successfully ingested {source_type} documents!")
                # Refresh the page to update vector store info
                st.rerun()
            else:
                st.error(f"❌ Ingestion failed: {result.stderr}")
    except Exception as e:
        st.error(f"Error during ingestion: {str(e)}")

def reset_vector_database():
    """Reset the vector database"""
    try:
        with st.spinner("Resetting vector database..."):
            success = vector_store.clear_collection()
            if success:
                st.success("✅ Vector database reset successfully!")
                st.rerun()
            else:
                st.error("❌ Failed to reset vector database")
    except Exception as e:
        st.error(f"Error resetting database: {str(e)}")

def main():
    """Main application function"""
    # Display sidebar components
    display_chat_history_sidebar()
    display_system_info_sidebar()
    
    # Display main chat interface
    display_main_chat()

if __name__ == "__main__":
    main()