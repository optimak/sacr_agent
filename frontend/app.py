import os
import re
import requests
import streamlit as st

# Use localhost when running locally, backend when in Docker
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000") + "/ask"

# Initialize session state
if "is_busy" not in st.session_state:
    st.session_state.is_busy = False
if "result_data" not in st.session_state:
    st.session_state.result_data = None

st.title("Cybersecurity Blog Agent")

# System Status Section - Show for local development
backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")

# Always show status section for now (can be made conditional later)
show_status = True

if show_status:
    st.subheader("🔍 System Status")
    
    # Real-time status check
    backend_ready = False
    data_ready = False
    chromadb_ready = False

    # Check backend connectivity
    try:
        backend_health = requests.get(backend_url.replace("/ask", "") + "/health", timeout=3)
        if backend_health.status_code == 200:
            backend_ready = True
    except:
        backend_ready = False

    # Check if backend can actually process queries (test with a simple query)
    if backend_ready:
        try:
            test_response = requests.post(
                backend_url + "/ask", 
                json={"query": "test"}, 
                timeout=5
            )
            if test_response.status_code == 200:
                data_ready = True
        except:
            data_ready = False

    # Check ChromaDB availability
    if data_ready:
        try:
            # Try to get backend info to see if ChromaDB is working
            backend_info = requests.get(backend_url.replace("/ask", "") + "/", timeout=3)
            if backend_info.status_code == 200:
                info_data = backend_info.json()
                if info_data.get("local_pf_available") and info_data.get("vector_db_mode") == "ChromaDB":
                    chromadb_ready = True
        except:
            chromadb_ready = False

    # Display status
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if backend_ready:
            st.success("✅ Backend: Online")
        else:
            st.error("❌ Backend: Offline")

    with col2:
        if data_ready:
            st.success("✅ Data: Ready")
        else:
            st.warning("⚠️ Data: Not Ready")

    with col3:
        if chromadb_ready:
            st.success("✅ ChromaDB: Ready")
        else:
            st.warning("⚠️ ChromaDB: Not Ready")

    with col4:
        if backend_ready and data_ready and chromadb_ready:
            st.success("🚀 App: Ready!")
        else:
            st.error("⏳ App: Starting...")

    # Show detailed status if not ready
    if not (backend_ready and data_ready and chromadb_ready):
        st.info("💡 **App is still starting up. Please wait a moment and refresh the page.**")
        st.write("**What's happening:**")
        if not backend_ready:
            st.write("• Backend service is starting up...")
        elif not data_ready:
            st.write("• Data processing is in progress...")
        elif not chromadb_ready:
            st.write("• Vector database is being initialized...")
    else:
        st.success("🎉 **Your AI Agent is ready to answer cybersecurity questions!**")
else:
    # Production/Remote mode - show simple ready message
    st.success("🎉 **Your AI Agent is ready to answer cybersecurity questions!**")

st.divider()

# Add refresh button for status (only in local development)
if show_status:
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🔄 Refresh Status", help="Check if the app is ready"):
            st.rerun()
    with col1:
        query = st.text_input("Ask me something:", disabled=st.session_state.is_busy)
else:
    query = st.text_input("Ask me something:", disabled=st.session_state.is_busy)
submit_button = st.button("Submit", disabled=st.session_state.is_busy)

if submit_button:
    st.session_state.is_busy = True
    st.session_state.result_data = None
    st.rerun()

if st.session_state.is_busy:
    try:
        with st.spinner("Processing your request..."):
            response = requests.post(BACKEND_URL, json={"query": query})

        if response.status_code == 200:
            st.session_state.result_data = response.json()
        else:
            st.session_state.result_data = {
                "error": True,
                "status_code": response.status_code,
                "text": response.text
            }
    except requests.exceptions.RequestException as e:
        st.session_state.result_data = {
            "error": True,
            "message": str(e)
        }
    finally:
        st.session_state.is_busy = False
        st.rerun()

# Display results
if st.session_state.result_data:
    data = st.session_state.result_data
    if "error" in data:
        st.error(f"Error from backend: Status code {data.get('status_code', 'N/A')}")
        st.write(data.get("text", ""))
    elif "answer" in data:
        # Handle both response formats
        if isinstance(data["answer"], dict) and "answer" in data["answer"]:
            main_answer = data["answer"]["answer"]
            sources = data["answer"].get("sources", [])
        else:
            # Direct answer format
            main_answer = data["answer"]
            sources = data.get("sources", [])

        # Split answer into text segments and images inline
        # Regex to find any image URL (common image extensions)
        image_pattern = r"(https?://\S+\.(?:png|jpg|jpeg|gif|webp|svg))"
        parts = re.split(image_pattern, main_answer)

        for part in parts:
            if re.match(image_pattern, part):
                st.write(part)
                st.image(part, caption="Relevant chart/figure")
            else:
                st.write(part)

        # Show sources
        if "sources" in data["answer"]:
            st.markdown("---")
            st.subheader("Sources")
            seen_titles = set()
            unique_sources = []

            for source in data["answer"]["sources"]:
                if "title" in source and source["title"] not in seen_titles:
                    seen_titles.add(source["title"])
                    unique_sources.append(source)

            for source in unique_sources:
                if "title" in source and "source_url" in source:
                    st.markdown(f"- [{source['title']}]({source['source_url']})")
    else:
        st.error("Invalid response format from the backend.")
