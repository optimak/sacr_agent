import os
import re
import requests
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "https://sacr-backend.onrender.com") + "/ask"

# Initialize session state
if "is_busy" not in st.session_state:
    st.session_state.is_busy = False
if "result_data" not in st.session_state:
    st.session_state.result_data = None

st.title("Cybersecurity Blog Agent")

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
    elif "answer" in data and "answer" in data["answer"]:
        main_answer = data["answer"]["answer"]

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
