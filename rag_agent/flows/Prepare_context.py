from promptflow import tool
import re

@tool
def prepare_context(search_results: list, max_context_length: int = 4000) -> str:
    """
    Prepare context from search results for LLM, including image URLs
    """
    if not search_results:
        return "No relevant information found in the cybersecurity knowledge base."
    
    context_parts = []
    current_length = 0
    
    for i, result in enumerate(search_results, 1):
        # Extract image URLs if any
        image_urls = []
        if result.get("has_images"):
            # Extract URLs ending with common image extensions
            image_urls = re.findall(r'https?://\S+\.(?:jpg|jpeg|png|webp|gif)', result["content"])
        
        # Prepare image text for context
        images_text = ""
        if image_urls:
            images_text = "Images in this chunk: " + ", ".join(image_urls) + "\n"
        
        # Create context entry
        entry = f"""
SOURCE {i}:
Title: {result['title']}
Company: {result['company']}
{images_text}Content: {result['content'][:1000]}...
Source URL: {result['source_url']}
Relevance Score: {result['score']:.3f}

---
"""
        # Check length limit
        if current_length + len(entry) > max_context_length:
            break
            
        context_parts.append(entry)
        current_length += len(entry)
    
    context = "\n".join(context_parts)
    
    return f"""
CYBERSECURITY KNOWLEDGE BASE CONTEXT:

{context}

Please use this information to answer the user's question. If the information is not sufficient, please indicate what additional information might be needed.
"""
