from promptflow import tool
import re

@tool
def format_final_response(llm_response: str, search_results: list) -> dict:
    """
    Format the final response with metadata, source citations, and only the images
    actually referenced in the LLM's answer.
    """
    sources = []
    for i, result in enumerate(search_results, 1):
        # Extract all image URLs in this chunk
        image_urls = []
        if result.get("has_images") and "content" in result:
            matches = re.findall(r'Alt text:\s*(https?://\S+)', result["content"])
            image_urls.extend(matches)

        # Filter image URLs to only those mentioned in the LLM's answer
        used_image_urls = [url for url in image_urls if url in llm_response]

        sources.append({
            "source_number": i,
            "chunk_id": result["chunk_id"],
            "title": result["title"],
            "company": result["company"],
            "source_url": result["source_url"],
            "relevance_score": result.get("score", 0),
            "has_images": result.get("has_images", False),
            "image_urls": used_image_urls  # only include LLM-referenced images
        })

    final_response = {
        "answer": llm_response,
        "sources_used": len(sources),
        "sources": sources,
        "search_query": "${inputs.query}",
        "response_metadata": {
            "total_sources_found": len(search_results),
            "sources_with_images": sum(1 for s in sources if s["image_urls"]),
            "companies_referenced": list(set([s["company"] for s in sources])),
            "avg_relevance_score": sum([s["relevance_score"] for s in sources]) / len(sources) if sources else 0
        }
    }

    return final_response
