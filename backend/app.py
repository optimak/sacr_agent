import os
import sys
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any

# Add rag_agent paths for local Prompt Flow
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'rag_agent', 'src'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'rag_agent', 'flows'))

app = FastAPI()

# Configuration
USE_PROMPTFLOW_LOCAL = os.getenv("USE_PROMPTFLOW_LOCAL", "true").lower() == "true"
PROMPTFLOW_ENDPOINT = os.getenv("PROMPTFLOW_ENDPOINT")
PROMPTFLOW_KEY = os.getenv("PROMPTFLOW_KEY")

# Local Prompt Flow imports
if USE_PROMPTFLOW_LOCAL:
    try:
        from promptflow import PFClient
        # Import the tool functions from the flows
        from rag_agent.flows.Search_Documents import search_documents
        from rag_agent.flows.Prepare_context import prepare_context
        from rag_agent.flows.Format_Final_Response import format_final_response
        local_pf_available = True
        print("✅ Local Prompt Flow loaded successfully")
    except ImportError as e:
        print(f"❌ CRITICAL ERROR: USE_PROMPTFLOW_LOCAL=true but local Prompt Flow is not available!")
        print(f"Error: {e}")
        print("Backend cannot start without local Prompt Flow. Exiting...")
        sys.exit(1)
else:
    local_pf_available = False
    print("ℹ️ Using remote Prompt Flow mode")

class QueryRequest(BaseModel):
    query: str

@app.get("/")
def root():
    # Determine vector DB mode
    vector_db_mode = "ChromaDB" if os.getenv("USE_LOCAL_VECTOR_DB", "false").lower() == "true" else "Azure AI Search"
    
    return {
        "message": "Backend is running",
        "promptflow_mode": "local" if USE_PROMPTFLOW_LOCAL else "remote",
        "local_pf_available": local_pf_available,
        "vector_db_mode": vector_db_mode
    }

@app.get("/health") 
def health():
    return {"status": "healthy"}

@app.post("/ask")
async def ask_question(request: QueryRequest):
    """Handle query requests using local or remote Prompt Flow"""
    
    if USE_PROMPTFLOW_LOCAL and local_pf_available:
        return await _handle_local_promptflow(request.query)
    elif PROMPTFLOW_ENDPOINT and PROMPTFLOW_KEY:
        return await _handle_remote_promptflow(request.query)
    else:
        raise HTTPException(
            status_code=500, 
            detail="No Prompt Flow configuration available"
        )

async def _handle_local_promptflow(query: str) -> Dict[str, Any]:
    """Handle query using local Prompt Flow"""
    try:
        # Step 1: Search documents
        search_results = search_documents(query, top_k=5)
        
        if not search_results or (len(search_results) == 1 and "error" in search_results[0]):
            return {
                "answer": {
                    "answer": "I couldn't find relevant information to answer your question.",
                    "sources": []
                }
            }
        
        # Step 2: Prepare context
        context = prepare_context(search_results)
        
        # Step 3: Generate response using Azure OpenAI directly
        # Since Generate_Response is a Jinja2 template, we'll use Azure OpenAI directly
        from openai import AzureOpenAI
        import os
        
        client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_KEY"),
            api_version="2024-02-01",
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT") or os.getenv("AZURE_ENDPOINT")
        )
        
        # Use the same prompt template as in Generate_Response.jinja2
        system_prompt = """You are a cybersecurity expert assistant. Your role is to help users understand cybersecurity threats, vulnerabilities, and best practices based on the provided knowledge base.
Be as succinct as possible, avoiding unnecessary detail, filler, or repetition.

Guidelines:
1. Answer questions using ONLY the provided context from the cybersecurity knowledge base. Do not use any prior knowledge.
2. Provide succinct, yet detailed explanations for specific threats, companies, or vulnerabilities mentioned in the context.
3. If the context lacks sufficient information, clearly state this limitation.
4. For questions about implementation or remediation, give specific, actionable advice if available in the context.
5. Always check the context for any images, charts, diagrams, or links. If present, reference them directly: "See chart here: <URL>" or "Image: <alt text>, URL: <URL>". If an image is included but has no explanation, provide a short summary of what it depicts. Do not ignore images or links even if the majority of context is text.
6. Maintain professional, clear language, but include relevant visual references to support explanations.

Remember: You are helping security professionals create accurate, well-sourced reports based on threat intelligence data."""
        
        user_prompt = f"Context: {context}\n\nUser Question: {query}\n\nPlease provide an answer using the provided sources. Use natural phrasing like \"The sources indicate...\" or \"According to the data...\" instead of always saying \"based on the context.\""
        
        response = client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT") or os.getenv("GPT4O_DEPLOYMENT") or os.getenv("GPT4O_MINI_DEPLOYMENT"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1
        )
        
        # Step 4: Format final response to match remote Prompt Flow format
        formatted_response = format_final_response(response.choices[0].message.content, search_results)
        
        # Convert to the same format as remote Prompt Flow
        return {
            "answer": {
                "answer": formatted_response["answer"],
                "sources": formatted_response["sources"]
            }
        }
        
    except Exception as e:
        return {
            "answer": {
                "answer": f"Error processing query: {str(e)}",
                "sources": []
            }
        }

async def _handle_remote_promptflow(query: str) -> Dict[str, Any]:
    """Handle query using remote Prompt Flow"""
    try:
        headers = {
            "Authorization": f"Bearer {PROMPTFLOW_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {"query": query}
        response = requests.post(PROMPTFLOW_ENDPOINT, headers=headers, json=payload)
        response.raise_for_status()
        
        return response.json()
        
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=500,
            detail=f"Remote Prompt Flow error: {str(e)}"
        )
