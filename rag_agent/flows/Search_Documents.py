from promptflow import tool
from promptflow.connections import CustomConnection, AzureOpenAIConnection 
import os
import sys

# Add the src directory to the path to import our services
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from chroma_service import ChromaService
from config import USE_LOCAL_VECTOR_DB, USE_AZURE_AI_SEARCH

@tool
def search_documents(
    query: str, 
    search_connection: CustomConnection = None,
    openai_connection: AzureOpenAIConnection = None, 
    top_k: int = 5
) -> list:
    """Search cybersecurity documents using Chroma or Azure AI Search"""
    
    try:
        if USE_LOCAL_VECTOR_DB:
            # Use Chroma for local vector search
            chroma_service = ChromaService()
            results = chroma_service.search(query, top_k)
            
            # Format results for compatibility
            search_results = []
            for result in results:
                metadata = result.get('metadata', {})
                search_results.append({
                    "chunk_id": result.get('id', ''),
                    "content": result.get('content', ''),
                    "title": metadata.get('title', ''),
                    "company": metadata.get('company', ''),
                    "source_url": metadata.get('webpage_url', ''),
                    "has_images": metadata.get('has_images', False),
                    "score": 1.0 - result.get('distance', 0.0)  # Convert distance to score
                })
            
            return search_results
            
        elif USE_AZURE_AI_SEARCH and search_connection and openai_connection:
            # Use Azure AI Search (original implementation)
            from azure.search.documents import SearchClient
            from azure.core.credentials import AzureKeyCredential
            from azure.search.documents.models import VectorizedQuery
            from openai import AzureOpenAI
            
            # Initialize search client from custom connection
            search_client = SearchClient(
                endpoint=search_connection.endpoint,
                index_name=search_connection.index_name,
                credential=AzureKeyCredential(search_connection.api_key)
            )
            
            # Use existing OpenAI connection for embeddings
            azure_client = AzureOpenAI(
                api_key=openai_connection.api_key,
                api_version="2024-02-01", 
                azure_endpoint=openai_connection.api_base
            )
            
            # Generate query embedding
            query_embedding = azure_client.embeddings.create(
                input=query,
                model="text-embedding-3-small"  # Your deployment name
            ).data[0].embedding
            
            # Perform hybrid search
            results = search_client.search(
                search_text=query,
                vector_queries=[
                    VectorizedQuery(
                        vector=query_embedding, 
                        k_nearest_neighbors=top_k, 
                        fields="content_vector"
                    )
                ],
                top=top_k,
                select=["chunk_id", "content", "title", "company", "webpage_url", "has_images"]
            )
            
            # Format results
            search_results = []
            for result in results:
                search_results.append({
                    "chunk_id": result["chunk_id"],
                    "content": result["content"],
                    "title": result["title"], 
                    "company": result["company"],
                    "source_url": result["webpage_url"],
                    "has_images": result["has_images"],
                    "score": result.get("@search.score", 0)
                })
            
            return search_results
            
        else:
            return [{"error": "No vector database configured or missing connections"}]
        
    except Exception as e:
        return [{"error": f"Search failed: {str(e)}"}]