"""
Enhanced RAG Pipeline with Chroma, Auto-Discovery, and Multimodal Processing
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from config import *
from notion_discovery import NotionDiscovery
from image_processor import ImageProcessor
from chroma_service import ChromaService

logger = logging.getLogger(__name__)

class EnhancedRAGPipeline:
    def __init__(self):
        """Initialize enhanced RAG pipeline"""
        validate_config()
        
        # Initialize services
        self.notion_discovery = NotionDiscovery()
        self.image_processor = ImageProcessor()
        self.chroma_service = ChromaService()
        
        # Get or discover database ID
        self.database_id = self._get_or_discover_database_id()
        
        # Load caches
        self.ocr_cache = self._load_cache('ocr_cache.json')
        self.processing_cache = self._load_cache('processing_cache.json')
        
        logger.info("Enhanced RAG Pipeline initialized")
    
    def _get_or_discover_database_id(self) -> str:
        """Get database ID from cache or auto-discover"""
        # Try to get from cache first
        cached_id = get_database_id()
        if cached_id:
            logger.info(f"Using cached database ID: {cached_id}")
            return cached_id
        
        # Auto-discover database
        logger.info(f"Auto-discovering database: {NOTION_DATABASE_NAME}")
        
        # Try to find by name first
        discovered_id = self.notion_discovery.find_database_by_name(NOTION_DATABASE_NAME)
        
        if not discovered_id:
            # If not found, try with parent page ID if available
            parent_page_id = os.getenv('PARENT_PAGE_ID')
            if parent_page_id:
                discovered_id = self.notion_discovery.find_database_by_name(
                    NOTION_DATABASE_NAME, parent_page_id
                )
        
        if not discovered_id:
            # Create database if it doesn't exist
            parent_page_id = os.getenv('PARENT_PAGE_ID')
            if not parent_page_id:
                raise ValueError("PARENT_PAGE_ID required to create new database")
            
            discovered_id = self.notion_discovery.create_database_if_not_exists(
                NOTION_DATABASE_NAME, parent_page_id
            )
        
        # Cache the discovered ID
        cache_database_id(discovered_id)
        logger.info(f"Discovered and cached database ID: {discovered_id}")
        
        return discovered_id
    
    def _load_cache(self, cache_filename: str) -> Dict:
        """Load cache from file"""
        cache_file = os.path.join(OUTPUT_DIR, cache_filename)
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading cache {cache_filename}: {e}")
        return {}
    
    def _save_cache(self, cache: Dict, cache_filename: str):
        """Save cache to file"""
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        cache_file = os.path.join(OUTPUT_DIR, cache_filename)
        try:
            with open(cache_file, 'w') as f:
                json.dump(cache, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving cache {cache_filename}: {e}")
    
    def run_full_pipeline(self) -> Dict[str, Any]:
        """Run the complete enhanced RAG pipeline"""
        logger.info("Starting Enhanced RAG Pipeline...")
        
        try:
            # Step 1: Get Notion pages
            logger.info("Step 1: Fetching Notion pages...")
            pages = self._get_notion_pages()
            
            if not pages:
                logger.warning("No pages found in Notion database")
                return {'status': 'no_pages', 'message': 'No pages found'}
            
            # Step 2: Process pages to chunks with enhanced image processing
            logger.info("Step 2: Processing pages to chunks with multimodal image processing...")
            chunks = self._process_pages_to_chunks(pages)
            
            if not chunks:
                logger.warning("No chunks created from pages")
                return {'status': 'no_chunks', 'message': 'No chunks created'}
            
            # Step 3: Add to vector database
            logger.info("Step 3: Adding chunks to vector database...")
            self._add_chunks_to_vector_db(chunks)
            
            # Step 4: Save caches and results
            logger.info("Step 4: Saving caches and results...")
            self._save_caches_and_results(chunks)
            
            logger.info("Enhanced RAG Pipeline completed successfully!")
            return {
                'status': 'success',
                'pages_processed': len(pages),
                'chunks_created': len(chunks),
                'database_id': self.database_id
            }
            
        except Exception as e:
            logger.error(f"Enhanced RAG Pipeline failed: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def _get_notion_pages(self) -> List[Dict]:
        """Get pages from Notion database"""
        try:
            from notion_client import Client
            notion = Client(auth=NOTION_TOKEN)
            
            response = notion.databases.query(
                database_id=self.database_id,
                page_size=min(MAX_PAGES_TO_PROCESS, 100)
            )
            
            pages = []
            for page in response.get('results', []):
                # Get page blocks
                blocks_response = notion.blocks.children.list(block_id=page['id'])
                
                page_data = {
                    'id': page['id'],
                    'title': self._extract_title(page),
                    'properties': page.get('properties', {}),
                    'blocks': blocks_response.get('results', []),
                    'created_time': page.get('created_time', ''),
                    'last_edited_time': page.get('last_edited_time', '')
                }
                pages.append(page_data)
            
            logger.info(f"Retrieved {len(pages)} pages from Notion")
            return pages
            
        except Exception as e:
            logger.error(f"Error getting Notion pages: {e}")
            return []
    
    def _extract_title(self, page: Dict) -> str:
        """Extract title from Notion page"""
        title_property = page.get('properties', {}).get('Title', {})
        if title_property.get('title'):
            return title_property['title'][0].get('plain_text', '')
        return 'Untitled'
    
    def _process_pages_to_chunks(self, pages: List[Dict]) -> List[Dict]:
        """Process pages into chunks with enhanced image processing"""
        chunks = []
        sequence_number = 1
        
        for page in pages:
            logger.info(f"Processing page: {page['title']}")
            
            # Extract text and images from blocks
            text_blocks, image_data = self._extract_content_from_blocks(page['blocks'])
            
            # Process images if any
            processed_images = []
            if image_data and (ENABLE_IMAGE_OCR or ENABLE_IMAGE_UNDERSTANDING):
                processed_images = self.image_processor.batch_process_images(
                    image_data, self.ocr_cache
                )
            
            # Create chunks from text blocks
            page_chunks = self._create_chunks_from_text(
                text_blocks, page, processed_images, sequence_number
            )
            
            chunks.extend(page_chunks)
            sequence_number += len(page_chunks)
        
        logger.info(f"Created {len(chunks)} chunks from {len(pages)} pages")
        return chunks
    
    def _extract_content_from_blocks(self, blocks: List[Dict]) -> tuple:
        """Extract text and image data from Notion blocks"""
        text_blocks = []
        image_data = []
        
        for block in blocks:
            block_type = block.get('type', '')
            
            if block_type == 'paragraph':
                text = self._extract_text_from_rich_text(block.get('paragraph', {}).get('rich_text', []))
                if text:
                    text_blocks.append({'type': 'paragraph', 'text': text})
            
            elif block_type == 'heading_1':
                text = self._extract_text_from_rich_text(block.get('heading_1', {}).get('rich_text', []))
                if text:
                    text_blocks.append({'type': 'heading_1', 'text': text})
            
            elif block_type == 'heading_2':
                text = self._extract_text_from_rich_text(block.get('heading_2', {}).get('rich_text', []))
                if text:
                    text_blocks.append({'type': 'heading_2', 'text': text})
            
            elif block_type == 'image':
                image_info = block.get('image', {})
                if image_info.get('type') == 'external':
                    image_data.append({
                        'url': image_info['external']['url'],
                        'alt_text': self._extract_text_from_rich_text(image_info.get('caption', []))
                    })
        
        return text_blocks, image_data
    
    def _extract_text_from_rich_text(self, rich_text: List[Dict]) -> str:
        """Extract plain text from Notion rich text"""
        return ''.join([item.get('plain_text', '') for item in rich_text])
    
    def _create_chunks_from_text(self, text_blocks: List[Dict], page: Dict, 
                                processed_images: List[Dict], start_sequence: int) -> List[Dict]:
        """Create chunks from text blocks with image data"""
        chunks = []
        
        # Combine all text
        full_text = '\n'.join([block['text'] for block in text_blocks])
        
        # Simple chunking (can be enhanced with semantic chunking)
        words = full_text.split()
        chunk_size = MAX_TOKENS_PER_CHUNK * 2  # Rough word estimate
        
        for i in range(0, len(words), chunk_size):
            chunk_words = words[i:i + chunk_size]
            chunk_text = ' '.join(chunk_words)
            
            # Create chunk with image data
            chunk = {
                'sequence_number': start_sequence + len(chunks),
                'title': page['title'],
                'text_content': chunk_text,
                'notion_page_id': page['id'],
                'chunk_index': len(chunks),
                'total_chunks': (len(words) + chunk_size - 1) // chunk_size,
                'created_time': page['created_time'],
                'last_edited_time': page['last_edited_time']
            }
            
            # Add image data if available
            if processed_images:
                chunk['image_urls'] = [img['url'] for img in processed_images]
                chunk['image_ocr_text'] = '\n'.join([img['ocr_text'] for img in processed_images if img['ocr_text']])
                chunk['image_semantic_understanding'] = '\n'.join([img['semantic_understanding'] for img in processed_images if img['semantic_understanding']])
            
            chunks.append(chunk)
        
        return chunks
    
    def _add_chunks_to_vector_db(self, chunks: List[Dict]):
        """Add chunks to vector database"""
        if USE_LOCAL_VECTOR_DB:
            self.chroma_service.add_documents(chunks)
        elif USE_AZURE_AI_SEARCH:
            # Keep existing Azure AI Search logic
            logger.info("Azure AI Search integration not implemented in this enhanced version")
        else:
            logger.warning("No vector database configured")
    
    def _save_caches_and_results(self, chunks: List[Dict]):
        """Save caches and processing results"""
        # Save OCR cache
        self._save_cache(self.ocr_cache, 'ocr_cache.json')
        
        # Save processing results
        results = {
            'chunks': chunks,
            'processing_time': datetime.now().isoformat(),
            'total_chunks': len(chunks)
        }
        self._save_cache(results, 'processing_results.json')
        
        # Save summary
        summary = {
            'total_chunks': len(chunks),
            'pages_processed': len(set(chunk['notion_page_id'] for chunk in chunks)),
            'images_processed': len([chunk for chunk in chunks if chunk.get('image_urls')]),
            'processing_time': datetime.now().isoformat()
        }
        self._save_cache(summary, 'processing_summary.json')
    
    def search(self, query: str, top_k: int = None) -> List[Dict]:
        """Search the vector database"""
        top_k = top_k or TOP_K
        
        if USE_LOCAL_VECTOR_DB:
            return self.chroma_service.search(query, top_k)
        else:
            logger.warning("Search not implemented for current vector database configuration")
            return []
