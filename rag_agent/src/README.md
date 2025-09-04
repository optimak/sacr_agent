# RAG Agent - Notion to Azure AI Search Pipeline

A comprehensive RAG (Retrieval-Augmented Generation) pipeline that extracts content from Notion databases, processes it with OCR for images, chunks it intelligently, and uploads it to Azure AI Search for hybrid retrieval.

## Features

- **Notion Integration**: Extracts pages with full metadata and content blocks
- **Image OCR**: Uses GPT-4o to extract text from images and diagrams
- **Smart Chunking**: Creates semantic chunks with configurable token limits and overlap
- **Incremental Processing**: Only processes new/updated pages on subsequent runs
- **Azure AI Search**: Creates hybrid search index with semantic search capabilities
- **Caching**: OCR results cached to avoid reprocessing images

## Project Structure

```
rag_agent/src/
├── config.py                 # Environment configuration
├── notion_rag_pipeline.py    # Main pipeline for Notion processing
├── ai_search_setup.py        # Azure AI Search index setup
├── requirements.txt          # Python dependencies
├── .env.template            # Environment variables template
├── README.md               # This file
└── rag_output/             # Generated output files (created automatically)
    ├── processed_pages.json    # Tracking which pages were processed
    ├── ocr_cache.json         # Cached image OCR results
    ├── embedded_chunks.json   # Full chunk data with embeddings
    ├── ai_search_documents.json # Ready for AI Search upload
    ├── chunks_summary.csv     # Summary table for analysis
    └── sample_chunks.txt      # Sample content for inspection
```

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy the template and fill in your credentials:

```bash
cp .env.template .env
```

Edit `.env` with your actual values:

```bash
# Notion Configuration
NOTION_TOKEN=secret_xyz123...                    # From https://www.notion.so/my-integrations
DATABASE_ID=abc123def456...                      # From your database URL

# Azure OpenAI Configuration  
AZURE_OPENAI_KEY=your_key_here
AZURE_ENDPOINT=https://your-resource.openai.azure.com/
EMBEDDING_DEPLOYMENT=text-embedding-3-small
GPT4O_DEPLOYMENT=gpt-4o

# Azure AI Search Configuration
AZURE_SEARCH_SERVICE_NAME=your_search_service
AZURE_SEARCH_API_KEY=your_search_key
INDEX_NAME=sacr-rag

# Processing Configuration (optional)
MAX_PAGES_TO_PROCESS=100
MAX_TOKENS_PER_CHUNK=380
OVERLAP_TOKENS=40
OUTPUT_DIR=rag_output
```

### 3. Notion Setup

1. Create integration at https://www.notion.so/my-integrations
2. Share your database with the integration
3. Get database ID from URL: `https://notion.so/Database-Name-DATABASE_ID?v=...`

### 4. Azure Setup

**Azure OpenAI**: Deploy `text-embedding-3-small` and `gpt-4o` models
**Azure AI Search**: Create a search service (Basic tier or higher recommended)

## Usage

### Phase 1: Process Notion Content

```python
from notion_rag_pipeline import NotionRAGPipeline

# Initialize pipeline
pipeline = NotionRAGPipeline()

# Load existing data
existing_chunks = pipeline.load_existing_chunks()
processing_tracker = pipeline.load_processing_tracker()
ocr_cache = pipeline.load_ocr_cache()

# Fetch and filter pages
all_pages = pipeline.get_notion_pages(limit=100)
pages_to_process = pipeline.filter_pages_to_process(all_pages, processing_tracker)

# Process pages to chunks with OCR
start_sequence = pipeline.get_next_sequence_number(existing_chunks)
new_chunks = pipeline.process_pages_to_chunks(pages_to_process, start_sequence, ocr_cache)

# Generate embeddings (optional - AI Search can handle this)
embedded_chunks = pipeline.generate_embeddings(new_chunks)

# Combine with existing and save
all_chunks = existing_chunks + embedded_chunks
pipeline.save_results(all_chunks)
```

### Phase 2: Set Up AI Search (TODO - Complete ai_search_setup.py)

The AI Search setup will:
- Create hybrid search index with vector, semantic, and keyword search
- Upload processed documents
- Test search functionality

## Data Processing Pipeline

1. **Extract**: Fetch pages from Notion database with all blocks and metadata
2. **OCR**: Process images using GPT-4o vision to extract text content
3. **Chunk**: Create semantic chunks with configurable token limits and overlap
4. **Embed**: Generate embeddings using Azure OpenAI (optional)
5. **Index**: Upload to Azure AI Search for hybrid retrieval
6. **Cache**: Save processing state and OCR results for incremental updates

## Output Files

- **`embedded_chunks.json`**: Complete chunk data with metadata and embeddings
- **`ai_search_documents.json`**: Cleaned format ready for AI Search upload
- **`chunks_summary.csv`**: Summary table for analysis and debugging
- **`sample_chunks.txt`**: Human-readable samples of processed content
- **`processed_pages.json`**: Tracks which pages have been processed
- **`ocr_cache.json`**: Cached OCR results to avoid reprocessing images

## Key Features

### Incremental Processing
- Only processes new or updated Notion pages
- Caches OCR results to avoid reprocessing images
- Maintains processing history for efficient updates

### Enhanced Image Processing
- Uses GPT-4o vision to extract text from images, charts, and diagrams
- Processes captions and alt text
- Includes image content in searchable text while preserving original formatting

### Smart Chunking
- Respects semantic boundaries (headings, paragraphs)
- Configurable token limits with overlap for context preservation
- Maintains metadata linking chunks to original pages

### Search-Optimized Output
- Hybrid search ready (keyword + semantic + vector)
- Proper field mapping for Azure AI Search
- Facetable fields for filtering (company, date, content type)

## Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_PAGES_TO_PROCESS` | 100 | Maximum pages to process per run |
| `MAX_TOKENS_PER_CHUNK` | 380 | Maximum tokens per chunk |
| `OVERLAP_TOKENS` | 40 | Token overlap between chunks |
| `OUTPUT_DIR` | `rag_output` | Directory for output files |

## Troubleshooting

### Common Issues

1. **Notion API Errors**: Verify token and database sharing
2. **Azure OpenAI Rate Limits**: Pipeline includes automatic rate limiting
3. **Image Processing Failures**: Cached in OCR cache, won't retry failed images
4. **Memory Issues**: Process pages in smaller batches by reducing `MAX_PAGES_TO_PROCESS`

### Debugging

Enable verbose logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Check output files:
- Review `sample_chunks.txt` for content quality
- Check `chunks_summary.csv` for statistics
- Inspect `processed_pages.json` for processing status

### Performance Tips

- **First Run**: May take several minutes due to image OCR processing
- **Subsequent Runs**: Much faster due to incremental processing and OCR caching
- **Large Databases**: Consider processing in batches of 50-100 pages
- **Image-Heavy Content**: OCR processing is the main bottleneck

## Next Steps

After running this pipeline:

1. **Complete AI Search Setup**: Finish `ai_search_setup.py` implementation
2. **Build Query Interface**: Create search and chat functionality
3. **Add Monitoring**: Track search performance and user queries
4. **Optimize Chunks**: Analyze search results and adjust chunking strategy

## API References

- [Notion API](https://developers.notion.com/)
- [Azure OpenAI](https://docs.microsoft.com/en-us/azure/cognitive-services/openai/)
- [Azure AI Search](https://docs.microsoft.com/en-us/azure/search/)