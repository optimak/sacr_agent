"""
Enhanced Image Processing Service with OCR and Multimodal Understanding
"""

import os
import json
import logging
import time
from typing import Dict, Any, Optional, Tuple, List
from openai import AzureOpenAI
from config import *

logger = logging.getLogger(__name__)

class ImageProcessor:
    def __init__(self):
        """Initialize image processor with Azure OpenAI client"""
        self.azure_client = AzureOpenAI(
            api_key=AZURE_OPENAI_KEY,
            api_version="2024-02-01",
            azure_endpoint=get_azure_openai_endpoint()
        )
        self.gpt4o_deployment = GPT4O_DEPLOYMENT
        self.gpt4o_mini_deployment = GPT4O_MINI_DEPLOYMENT
        
    def process_image(self, image_url: str, alt_text: str = "", cache: Dict = None) -> Dict[str, str]:
        """
        Process image with both OCR and semantic understanding
        
        Returns:
            Dict with 'ocr_text' and 'semantic_understanding' keys
        """
        # Check cache first
        if cache and image_url in cache:
            logger.info("Using cached image processing results")
            return cache[image_url]
        
        result = {
            'ocr_text': '',
            'semantic_understanding': '',
            'alt_text': alt_text,
            'processed_time': time.time()
        }
        
        # Process OCR if enabled
        if ENABLE_IMAGE_OCR:
            result['ocr_text'] = self._extract_ocr_text(image_url, alt_text)
        
        # Process semantic understanding if enabled
        if ENABLE_IMAGE_UNDERSTANDING:
            result['semantic_understanding'] = self._extract_semantic_understanding(image_url, alt_text)
        
        # Cache the result
        if cache is not None:
            cache[image_url] = result
        
        return result
    
    def _extract_ocr_text(self, image_url: str, alt_text: str = "") -> str:
        """Extract text from image using GPT-4o vision (OCR)"""
        try:
            logger.info(f"Processing OCR for image: {alt_text[:50]}...")
            
            prompt = """Extract all text from this image. If it contains diagrams, charts, or technical content, also describe the key information shown.

Format your response as:
TEXT: [extracted text here]
DESCRIPTION: [brief description of visual content if relevant]

If no text is found, just provide the description."""

            response = self.azure_client.chat.completions.create(
                model=self.gpt4o_deployment,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": image_url}}
                        ]
                    }
                ],
                max_tokens=1000,
                temperature=0.1
            )

            extracted_content = response.choices[0].message.content
            time.sleep(0.5)  # Rate limiting
            return extracted_content

        except Exception as e:
            logger.error(f"Error processing OCR for image: {e}")
            return f"[IMAGE OCR ERROR: {alt_text}]" if alt_text else "[IMAGE OCR ERROR]"
    
    def _extract_semantic_understanding(self, image_url: str, alt_text: str = "") -> str:
        """Extract semantic understanding from image using GPT-4o-mini"""
        try:
            logger.info(f"Processing semantic understanding for image: {alt_text[:50]}...")
            
            prompt = """Analyze this image and provide a semantic understanding of its content. Focus on:
1. What the image shows (objects, people, scenes)
2. The context and meaning
3. Any technical or cybersecurity relevance
4. Key concepts or themes

Provide a concise but comprehensive description that would help in search and retrieval."""

            response = self.azure_client.chat.completions.create(
                model=self.gpt4o_mini_deployment,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": image_url}}
                        ]
                    }
                ],
                max_tokens=500,
                temperature=0.3
            )

            semantic_content = response.choices[0].message.content
            time.sleep(0.5)  # Rate limiting
            return semantic_content

        except Exception as e:
            logger.error(f"Error processing semantic understanding for image: {e}")
            return f"[IMAGE SEMANTIC ERROR: {alt_text}]" if alt_text else "[IMAGE SEMANTIC ERROR]"
    
    def batch_process_images(self, image_data: List[Dict], cache: Dict = None) -> List[Dict]:
        """Process multiple images in batch"""
        results = []
        
        for i, img_data in enumerate(image_data):
            image_url = img_data.get('url', '')
            alt_text = img_data.get('alt_text', '')
            
            logger.info(f"Processing image {i+1}/{len(image_data)}: {alt_text[:30]}...")
            
            result = self.process_image(image_url, alt_text, cache)
            results.append({
                'url': image_url,
                'alt_text': alt_text,
                'ocr_text': result['ocr_text'],
                'semantic_understanding': result['semantic_understanding']
            })
            
            # Add delay between images to respect rate limits
            if i < len(image_data) - 1:
                time.sleep(1.0)
        
        return results
