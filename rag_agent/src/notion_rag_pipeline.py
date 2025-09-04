"""
Notion RAG Pipeline - Extract, chunk, and process Notion content with OCR
"""

import os
import json
import pandas as pd
import tiktoken
from datetime import datetime
from typing import List, Dict, Any
import time
import logging

import notion_client
from openai import AzureOpenAI
from config import *

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NotionRAGPipeline:
    def __init__(self):
        """Initialize the pipeline with configuration from environment variables"""
        validate_config()
        
        self.notion = notion_client.Client(auth=NOTION_TOKEN)
        self.azure_client = AzureOpenAI(
            api_key=AZURE_OPENAI_KEY,
            api_version="2024-02-01",
            azure_endpoint=get_azure_openai_endpoint()
        )
        self.embedding_deployment = EMBEDDING_DEPLOYMENT
        self.gpt4o_deployment = GPT4O_DEPLOYMENT
        self.database_id = DATABASE_ID
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        self.max_tokens = MAX_TOKENS_PER_CHUNK
        self.overlap_tokens = OVERLAP_TOKENS
        self.output_dir = OUTPUT_DIR

    def get_notion_pages(self, limit: int = None) -> List[Dict]:
        """Fetch pages from Notion database with all properties and blocks"""
        limit = limit or MAX_PAGES_TO_PROCESS
        logger.info(f"Fetching up to {limit} pages from Notion database...")

        try:
            response = self.notion.databases.query(
                database_id=self.database_id,
                page_size=min(limit, 100)  # Notion API limit
            )

            pages_data = []
            for page in response['results']:
                page_title = self._safe_get_title(page)
                logger.info(f"Processing page: {page_title}")

                page_info = self._extract_page_properties(page)
                blocks = self._get_page_blocks(page['id'])
                page_info['blocks'] = blocks
                pages_data.append(page_info)

                if len(pages_data) >= limit:
                    break

            logger.info(f"Successfully fetched {len(pages_data)} pages")
            return pages_data

        except Exception as e:
            logger.error(f"Error fetching Notion pages: {e}")
            return []

    def _safe_get_title(self, page: Dict) -> str:
        """Safely extract title from page"""
        try:
            return page['properties']['Title']['title'][0]['plain_text']
        except (KeyError, IndexError, TypeError):
            return f"Page {page['id'][:8]}"

    def _extract_page_properties(self, page: Dict) -> Dict:
        """Extract properties from Notion page"""
        props = page['properties']

        def safe_get_text(prop_data):
            try:
                return prop_data['rich_text'][0]['plain_text'] if prop_data['rich_text'] else ''
            except (KeyError, IndexError, TypeError):
                return ''

        def safe_get_date(prop_data):
            try:
                return prop_data['date']['start'] if prop_data['date'] else ''
            except (KeyError, TypeError):
                return ''

        def safe_get_url(prop_data):
            try:
                return prop_data['url'] if prop_data['url'] else ''
            except (KeyError, TypeError):
                return ''

        return {
            'notion_page_id': page['id'],
            'title': self._safe_get_title(page),
            'company': safe_get_text(props.get('Company', {})),
            'date_published': safe_get_date(props.get('Date Published', {})),
            'date_pulled': safe_get_date(props.get('Date Pulled', {})),
            'webpage_url': safe_get_url(props.get('Webpage URL', {})),
            'created_time': page['created_time'],
            'last_edited_time': page['last_edited_time']
        }

    def _get_page_blocks(self, page_id: str) -> List[Dict]:
        """Retrieve all blocks from a Notion page"""
        blocks = []
        start_cursor = None

        while True:
            try:
                response = self.notion.blocks.children.list(
                    block_id=page_id,
                    start_cursor=start_cursor,
                    page_size=100
                )
                blocks.extend(response['results'])

                if not response['has_more']:
                    break
                start_cursor = response['next_cursor']

            except Exception as e:
                logger.error(f"Error fetching blocks for page {page_id}: {e}")
                break

        return blocks

    def load_processing_tracker(self, tracker_file: str = None) -> Dict:
        """Load the processing tracker"""
        tracker_file = tracker_file or os.path.join(self.output_dir, "processed_pages.json")
        
        if os.path.exists(tracker_file):
            try:
                with open(tracker_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading processing tracker: {e}")
                return {}
        return {}

    def save_processing_tracker(self, tracker: Dict, tracker_file: str = None):
        """Save the processing tracker"""
        tracker_file = tracker_file or os.path.join(self.output_dir, "processed_pages.json")
        os.makedirs(os.path.dirname(tracker_file), exist_ok=True)
        
        with open(tracker_file, 'w') as f:
            json.dump(tracker, f, indent=2)

    def load_ocr_cache(self, cache_file: str = None) -> Dict:
        """Load cached OCR results"""
        cache_file = cache_file or os.path.join(self.output_dir, "ocr_cache.json")
        
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading OCR cache: {e}")
                return {}
        return {}

    def save_ocr_cache(self, cache: Dict, cache_file: str = None):
        """Save OCR cache"""
        cache_file = cache_file or os.path.join(self.output_dir, "ocr_cache.json")
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)
        
        with open(cache_file, 'w') as f:
            json.dump(cache, f, indent=2)

    def filter_pages_to_process(self, pages: List[Dict], tracker: Dict) -> List[Dict]:
        """Filter pages that need processing"""
        pages_to_process = []

        for page in pages:
            page_id = page['notion_page_id']
            last_edited = page['last_edited_time']

            if page_id not in tracker:
                pages_to_process.append(page)
                logger.info(f"New page to process: {page['title']}")
            elif tracker[page_id]['last_edited_time'] != last_edited:
                pages_to_process.append(page)
                logger.info(f"Updated page to process: {page['title']}")
            else:
                logger.info(f"Skipping unchanged page: {page['title']}")

        return pages_to_process

    def extract_image_text_with_gpt4o(self, image_url: str, alt_text: str = "", ocr_cache: Dict = None) -> str:
        """Extract text from image using GPT-4o vision capabilities"""
        if ocr_cache and image_url in ocr_cache:
            logger.info("Using cached OCR for image")
            return ocr_cache[image_url]['extracted_text']

        try:
            logger.info(f"Processing image with GPT-4o: {alt_text[:50]}...")

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

            if ocr_cache is not None:
                ocr_cache[image_url] = {
                    'extracted_text': extracted_content,
                    'alt_text': alt_text,
                    'processed_time': datetime.now().isoformat()
                }

            time.sleep(0.5)  # Rate limiting
            return extracted_content

        except Exception as e:
            logger.error(f"Error processing image with GPT-4o: {e}")
            return f"[IMAGE: {alt_text}]" if alt_text else "[IMAGE]"

    def process_pages_to_chunks(self, pages: List[Dict], start_sequence: int = 1, ocr_cache: Dict = None) -> List[Dict]:
        """Process Notion pages into semantic chunks with image OCR"""
        logger.info("Processing pages into semantic chunks with image OCR...")

        sorted_pages = sorted(pages, key=lambda x: x['date_published'] or '1900-01-01')
        logger.info(f"Sorted {len(sorted_pages)} pages by publication date")

        all_chunks = []

        for i, page in enumerate(sorted_pages):
            seq_num = start_sequence + i
            page_short_id = page['notion_page_id'][:8]
            logger.info(f"Chunking page {seq_num}: {page['title']} (ID: {page_short_id})")

            text_blocks = self._extract_text_from_blocks(page['blocks'], ocr_cache)
            chunks = self._create_semantic_chunks(text_blocks, page, page_short_id, seq_num)
            all_chunks.extend(chunks)

        logger.info(f"Created {len(all_chunks)} total chunks")
        return all_chunks

    def _extract_text_from_blocks(self, blocks: List[Dict], ocr_cache: Dict = None) -> List[Dict]:
        """Extract text content from Notion blocks with image OCR"""
        text_blocks = []

        for i, block in enumerate(blocks):
            block_type = block['type']
            block_info = {
                'block_index': i,
                'block_id': block['id'],
                'block_type': block_type,
                'text': '',
                'enhanced_text': '',
                'is_heading': False,
                'heading_level': 0
            }

            # Extract text based on block type
            if block_type == 'paragraph' and 'paragraph' in block:
                text = self._extract_rich_text(block['paragraph'].get('rich_text', []))
                block_info['text'] = text
                block_info['enhanced_text'] = text

            elif block_type.startswith('heading_') and block_type in block:
                level = int(block_type.split('_')[1])
                text = self._extract_rich_text(block[block_type].get('rich_text', []))
                block_info['text'] = text
                block_info['enhanced_text'] = text
                block_info['is_heading'] = True
                block_info['heading_level'] = level

            elif block_type == 'image' and 'image' in block:
                image_info = block['image']
                alt_text = self._extract_rich_text(image_info.get('caption', []))
                
                image_url = ''
                if image_info.get('type') == 'external':
                    image_url = image_info['external']['url']
                elif image_info.get('type') == 'file':
                    image_url = image_info['file']['url']

                if image_url:
                    extracted_text = self.extract_image_text_with_gpt4o(image_url, alt_text, ocr_cache)
                    block_info['enhanced_text'] = f"[IMAGE CONTENT]\nAlt text: {alt_text}\nExtracted content: {extracted_text}"
                    block_info['text'] = f"[IMAGE: {alt_text}]" if alt_text else "[IMAGE]"
                    block_info['image_url'] = image_url
                    block_info['alt_text'] = alt_text
                else:
                    block_info['text'] = f"[IMAGE: {alt_text}]" if alt_text else "[IMAGE]"
                    block_info['enhanced_text'] = block_info['text']

            if block_info['enhanced_text'].strip():
                text_blocks.append(block_info)

        return text_blocks

    def _extract_rich_text(self, rich_text: List[Dict]) -> str:
        """Extract plain text from Notion rich text objects"""
        try:
            return ''.join([text_obj['text']['content'] for text_obj in rich_text])
        except (KeyError, TypeError):
            return ''

    def _create_semantic_chunks(self, text_blocks: List[Dict], page_metadata: Dict, page_short_id: str, seq_num: int) -> List[Dict]:
        """Create semantic chunks from text blocks"""
        chunks = []
        current_chunk = {
            'text': '',
            'enhanced_text': '',
            'blocks': [],
            'has_images': False
        }

        for block in text_blocks:
            potential_enhanced = current_chunk['enhanced_text'] + '\n\n' + block['enhanced_text'] if current_chunk['enhanced_text'] else block['enhanced_text']
            token_count = len(self.tokenizer.encode(potential_enhanced))

            if token_count > self.max_tokens and current_chunk['enhanced_text'].strip():
                chunk = self._finalize_chunk(current_chunk, page_metadata, chunks, page_short_id, seq_num)
                if chunk:
                    chunks.append(chunk)

                overlap_text = self._get_overlap_text(current_chunk['text'], self.overlap_tokens)
                overlap_enhanced = self._get_overlap_text(current_chunk['enhanced_text'], self.overlap_tokens)
                overlap_has_images = '[IMAGE' in overlap_enhanced if overlap_enhanced else False

                current_chunk = {
                    'text': overlap_text + '\n\n' + block['text'] if overlap_text else block['text'],
                    'enhanced_text': overlap_enhanced + '\n\n' + block['enhanced_text'] if overlap_enhanced else block['enhanced_text'],
                    'blocks': [block],
                    'has_images': overlap_has_images or (block.get('image_url') is not None)
                }
            else:
                if current_chunk['text']:
                    current_chunk['text'] += '\n\n' + block['text']
                    current_chunk['enhanced_text'] += '\n\n' + block['enhanced_text']
                else:
                    current_chunk['text'] = block['text']
                    current_chunk['enhanced_text'] = block['enhanced_text']

                current_chunk['blocks'].append(block)
                if block.get('image_url'):
                    current_chunk['has_images'] = True

        if current_chunk['enhanced_text'].strip():
            chunk = self._finalize_chunk(current_chunk, page_metadata, chunks, page_short_id, seq_num)
            if chunk:
                chunks.append(chunk)

        return chunks

    def _get_overlap_text(self, text: str, overlap_tokens: int) -> str:
        """Get the last N tokens of text for overlap"""
        tokens = self.tokenizer.encode(text)
        if len(tokens) <= overlap_tokens:
            return text

        overlap_tokens_list = tokens[-overlap_tokens:]
        return self.tokenizer.decode(overlap_tokens_list)

    def _finalize_chunk(self, chunk_data: Dict, page_metadata: Dict, existing_chunks: List, page_short_id: str, seq_num: int) -> Dict:
        """Create final chunk with metadata"""
        chunk_num = len(existing_chunks) + 1
        chunk_id = f"{page_short_id}-{seq_num}_chunk_{chunk_num}"

        return {
            'chunk_id': chunk_id,
            'text': chunk_data['text'],
            'enhanced_content': chunk_data['enhanced_text'],
            'token_count': len(self.tokenizer.encode(chunk_data['enhanced_text'])),
            'metadata': {
                'page_level': {
                    'notion_page_id': page_metadata['notion_page_id'],
                    'page_sequence': seq_num,
                    'title': page_metadata['title'],
                    'company': page_metadata['company'],
                    'date_published': page_metadata['date_published'],
                    'date_pulled': page_metadata['date_pulled'],
                    'webpage_url': page_metadata['webpage_url']
                },
                'chunk_level': {
                    'chunk_id': chunk_id,
                    'has_images': chunk_data['has_images'],
                    'block_count': len(chunk_data['blocks']),
                    'content_types': list(set([block['block_type'] for block in chunk_data['blocks']]))
                }
            }
        }

    def generate_embeddings(self, chunks: List[Dict], use_enhanced_content: bool = True) -> List[Dict]:
        """Generate Azure OpenAI embeddings for chunks"""
        logger.info(f"Generating embeddings for {len(chunks)} chunks...")

        embedded_chunks = []

        for i, chunk in enumerate(chunks):
            logger.info(f"Embedding chunk {i+1}/{len(chunks)}: {chunk['chunk_id']}")

            try:
                content_to_embed = chunk['enhanced_content'] if use_enhanced_content else chunk['text']

                response = self.azure_client.embeddings.create(
                    input=content_to_embed,
                    model=self.embedding_deployment
                )

                chunk['embedding'] = response.data[0].embedding
                chunk['embedding_model'] = self.embedding_deployment
                chunk['embedding_created'] = datetime.now().isoformat()
                chunk['embedding_enhanced'] = use_enhanced_content

                embedded_chunks.append(chunk)

            except Exception as e:
                logger.error(f"Error generating embedding for chunk {chunk['chunk_id']}: {e}")
                continue

        logger.info(f"Successfully generated {len(embedded_chunks)} embeddings")
        return embedded_chunks

    def load_existing_chunks(self, chunks_file: str = None) -> List[Dict]:
        """Load existing embedded chunks"""
        chunks_file = chunks_file or os.path.join(self.output_dir, "embedded_chunks.json")
        
        if os.path.exists(chunks_file):
            try:
                with open(chunks_file, 'r') as f:
                    existing_chunks = json.load(f)
                logger.info(f"Loaded {len(existing_chunks)} existing chunks")
                return existing_chunks
            except Exception as e:
                logger.error(f"Error loading existing chunks: {e}")
                return []
        return []

    def get_next_sequence_number(self, existing_chunks: List[Dict]) -> int:
        """Get the next sequence number for processing new pages"""
        if not existing_chunks:
            return 1

        max_seq = 0
        for chunk in existing_chunks:
            seq = chunk.get('metadata', {}).get('page_level', {}).get('page_sequence', 0)
            max_seq = max(max_seq, seq)

        return max_seq + 1

    def save_results(self, all_chunks: List[Dict]):
        """Save processed chunks to files"""
        os.makedirs(self.output_dir, exist_ok=True)

        # Save full data as JSON
        with open(os.path.join(self.output_dir, "embedded_chunks.json"), 'w') as f:
            json.dump(all_chunks, f, indent=2, default=str)

        # Create AI Search ready format
        ai_search_docs = []
        for chunk in all_chunks:
            doc = {
                'id': chunk['chunk_id'].replace('_', '-'),
                'chunk_id': chunk['chunk_id'],
                'content': chunk['enhanced_content'],
                'title': chunk['metadata']['page_level']['title'],
                'company': chunk['metadata']['page_level']['company'],
                'date_published': chunk['metadata']['page_level']['date_published'],
                'date_pulled': chunk['metadata']['page_level']['date_pulled'],
                'webpage_url': chunk['metadata']['page_level']['webpage_url'],
                'notion_page_id': chunk['metadata']['page_level']['notion_page_id'],
                'page_sequence': chunk['metadata']['page_level']['page_sequence'],
                'has_images': chunk['metadata']['chunk_level']['has_images'],
                'content_types': chunk['metadata']['chunk_level']['content_types'],
                'token_count': chunk['token_count']
            }
            ai_search_docs.append(doc)

        # Save AI Search ready format
        with open(os.path.join(self.output_dir, "ai_search_documents.json"), 'w') as f:
            json.dump(ai_search_docs, f, indent=2)

        # Create summary DataFrame
        summary_data = []
        for chunk in all_chunks:
            summary_data.append({
                'chunk_id': chunk['chunk_id'],
                'page_sequence': chunk['metadata']['page_level'].get('page_sequence', 'N/A'),
                'title': chunk['metadata']['page_level']['title'],
                'company': chunk['metadata']['page_level']['company'],
                'token_count': chunk['token_count'],
                'has_images': chunk['metadata']['chunk_level']['has_images'],
                'text_preview': chunk['enhanced_content'][:200] + "..." if len(chunk['enhanced_content']) > 200 else chunk['enhanced_content']
            })

        df = pd.DataFrame(summary_data)
        df.to_csv(os.path.join(self.output_dir, "chunks_summary.csv"), index=False)

        # Save text samples
        with open(os.path.join(self.output_dir, "sample_chunks.txt"), 'w', encoding='utf-8') as f:
            for i, chunk in enumerate(all_chunks[-3:]):  # Last 3 chunks
                f.write(f"=== CHUNK {i+1}: {chunk['chunk_id']} ===\n")
                f.write(f"Page Sequence: {chunk['metadata']['page_level'].get('page_sequence', 'N/A')}\n")
                f.write(f"Title: {chunk['metadata']['page_level']['title']}\n")
                f.write(f"Tokens: {chunk['token_count']}\n")
                f.write(f"Has Images: {chunk['metadata']['chunk_level']['has_images']}\n")
                f.write(f"Enhanced Content:\n{chunk['enhanced_content']}\n")
                f.write("\n" + "="*80 + "\n\n")

        logger.info(f"Results saved to {self.output_dir}/")
        logger.info("- embedded_chunks.json: Full data with embeddings")
        logger.info("- ai_search_documents.json: Ready for AI Search upload")
        logger.info("- chunks_summary.csv: Summary table")
        logger.info("- sample_chunks.txt: Enhanced content samples")