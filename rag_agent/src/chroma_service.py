"""
Chroma Vector Database Service
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from config import *

logger = logging.getLogger(__name__)

class ChromaService:
    def __init__(self, collection_name: str = "sacr_documents"):
        """Initialize Chroma client and collection"""
        self.collection_name = collection_name
        self.persist_directory = os.path.join(os.path.dirname(__file__), OUTPUT_DIR, "chroma_db")
        
        # Create Chroma client with persistent storage
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Get or create collection
        try:
            collections = self.client.list_collections()
            logger.info(f"Found {len(collections)} collections")
            
            # Try to get existing collection by name
            for col in collections:
                if col.name == collection_name:
                    self.collection = col
                    logger.info(f"Found existing collection: {self.collection.name} (ID: {self.collection.id})")
                    break
            else:
                # Create new collection if none exists
                self.collection = self.client.create_collection(
                    name=collection_name,
                    metadata={"description": "SACR cybersecurity blog documents"}
                )
                logger.info(f"Created new collection: {self.collection.name} (ID: {self.collection.id})")
                
        except Exception as e:
            logger.error(f"Error with collections: {e}")
            raise Exception(f"Could not access collections: {e}")
    
    def add_documents(self, documents: List[Dict[str, Any]]):
        """Add documents to Chroma collection"""
        if not documents:
            logger.warning("No documents to add")
            return
        
        # Prepare data for Chroma
        ids = []
        texts = []
        metadatas = []
        
        for doc in documents:
            # Create unique ID
            doc_id = f"doc_{doc.get('sequence_number', len(ids))}"
            ids.append(doc_id)
            
            # Combine text content
            text_content = doc.get('text_content', '')
            if doc.get('image_ocr_text'):
                text_content += f"\n[Image OCR: {doc['image_ocr_text']}]"
            if doc.get('image_semantic_understanding'):
                text_content += f"\n[Image Description: {doc['image_semantic_understanding']}]"
            
            texts.append(text_content)
            
            # Prepare metadata
            metadata = {
                'title': doc.get('title', ''),
                'company': doc.get('company', ''),
                'date_published': doc.get('date_published', ''),
                'date_pulled': doc.get('date_pulled', ''),
                'webpage_url': doc.get('webpage_url', ''),
                'notion_page_id': doc.get('notion_page_id', ''),
                'chunk_index': doc.get('chunk_index', 0),
                'total_chunks': doc.get('total_chunks', 1),
                'has_images': bool(doc.get('image_urls')),
                'image_count': len(doc.get('image_urls', [])),
                'sequence_number': doc.get('sequence_number', 0)
            }
            
            # Add image URLs if present
            if doc.get('image_urls'):
                metadata['image_urls'] = json.dumps(doc['image_urls'])
            
            metadatas.append(metadata)
        
        # Add to collection
        try:
            self.collection.add(
                ids=ids,
                documents=texts,
                metadatas=metadatas
            )
            logger.info(f"Added {len(documents)} documents to Chroma collection")
        except Exception as e:
            logger.error(f"Error adding documents to Chroma: {e}")
            raise
    
    def search(self, query: str, top_k: int = 5, filter_metadata: Dict = None) -> List[Dict[str, Any]]:
        """Search for similar documents"""
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k,
                where=filter_metadata
            )
            
            # Format results
            formatted_results = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    result = {
                        'content': doc,
                        'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                        'distance': results['distances'][0][i] if results['distances'] else 0.0,
                        'id': results['ids'][0][i] if results['ids'] else f"result_{i}"
                    }
                    formatted_results.append(result)
            
            logger.info(f"Found {len(formatted_results)} results for query")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error searching Chroma: {e}")
            return []
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics"""
        try:
            count = self.collection.count()
            return {
                'total_documents': count,
                'collection_name': self.collection_name,
                'persist_directory': self.persist_directory
            }
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {'total_documents': 0}
    
    def reset_collection(self):
        """Reset the collection (delete all documents)"""
        try:
            self.client.delete_collection(name=self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "SACR cybersecurity blog documents"}
            )
            logger.info(f"Reset collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Error resetting collection: {e}")
            raise
