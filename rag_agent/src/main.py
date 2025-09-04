#!/usr/bin/env python3
"""
Main runner for the Notion RAG Pipeline
Orchestrates the complete workflow from Notion extraction to AI Search setup
"""

import logging
from datetime import datetime
from notion_rag_pipeline import NotionRAGPipeline
from config import validate_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_notion_processing_pipeline():
    """Run the complete Notion processing pipeline"""
    try:
        logger.info("="*60)
        logger.info("Starting Notion RAG Pipeline - Enhanced with Image OCR")
        logger.info("="*60)

        # Initialize pipeline
        pipeline = NotionRAGPipeline()

        # Step 1: Load existing data
        logger.info("Step 1: Loading existing data...")
        existing_chunks = pipeline.load_existing_chunks()
        processing_tracker = pipeline.load_processing_tracker()
        ocr_cache = pipeline.load_ocr_cache()
        logger.info(f"Loaded {len(existing_chunks)} existing chunks")
        logger.info(f"Loaded processing history for {len(processing_tracker)} pages")
        logger.info(f"Loaded OCR cache with {len(ocr_cache)} entries")

        # Step 2: Fetch all pages from Notion
        logger.info("\nStep 2: Fetching pages from Notion...")
        all_pages = pipeline.get_notion_pages()
        if not all_pages:
            logger.warning("No pages found. Check your database ID and API key.")
            return False

        # Step 3: Filter to only new/updated pages
        logger.info("\nStep 3: Filtering pages to process...")
        pages_to_process = pipeline.filter_pages_to_process(all_pages, processing_tracker)
        if not pages_to_process:
            logger.info("No new or updated pages to process!")
            logger.info("Existing chunks and AI Search documents are ready for upload.")
            return True

        # Step 4: Get next sequence number
        start_sequence = pipeline.get_next_sequence_number(existing_chunks)
        logger.info(f"\nStep 4: Starting sequence number: {start_sequence}")

        # Step 5: Process new pages to chunks with image OCR
        logger.info("\nStep 5: Processing pages to chunks with OCR...")
        new_chunks = pipeline.process_pages_to_chunks(pages_to_process, start_sequence, ocr_cache)
        if not new_chunks:
            logger.warning("No new chunks created.")
            return False

        # Step 6: Generate embeddings (optional - AI Search can handle this)
        logger.info("\nStep 6: Skipping local embedding generation...")
        logger.info("Note: AI Search will handle embeddings for better hybrid search performance")
        embedded_new_chunks = new_chunks

        # Step 7: Combine with existing chunks
        logger.info("\nStep 7: Combining with existing chunks...")
        all_chunks = existing_chunks + embedded_new_chunks

        # Step 8: Update processing tracker
        logger.info("\nStep 8: Updating processing tracker...")
        for i, page in enumerate(pages_to_process):
            processing_tracker[page['notion_page_id']] = {
                'sequence_number': start_sequence + i,
                'title': page['title'],
                'last_edited_time': page['last_edited_time'],
                'processed_time': datetime.now().isoformat()
            }

        pipeline.save_processing_tracker(processing_tracker)
        pipeline.save_ocr_cache(ocr_cache)

        # Step 9: Save all results
        logger.info("\nStep 9: Saving results...")
        pipeline.save_results(all_chunks)

        # Success summary
        logger.info("="*60)
        logger.info("Pipeline completed successfully!")
        logger.info(f"✓ Processed {len(pages_to_process)} new/updated pages")
        logger.info(f"✓ Created {len(embedded_new_chunks)} new enhanced chunks")
        logger.info(f"✓ Total chunks in database: {len(all_chunks)}")
        logger.info(f"✓ Files saved to: {pipeline.output_dir}/")
        
        logger.info("\nGenerated Files:")
        logger.info("- embedded_chunks.json: Full data with metadata")
        logger.info("- ai_search_documents.json: Ready for AI Search upload")
        logger.info("- chunks_summary.csv: Analysis summary")
        logger.info("- sample_chunks.txt: Content samples")
        
        logger.info("\nNext Steps:")
        logger.info("1. Review generated files in the output directory")
        logger.info("2. Run AI Search setup (when ai_search_setup.py is completed)")
        logger.info("3. Upload documents to Azure AI Search")
        logger.info("4. Build query/chat interface")
        
        return True

    except Exception as e:
        logger.error(f"Pipeline failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main entry point"""
    try:
        # Validate configuration
        validate_config()
        logger.info("Configuration validated successfully")
        
        # Run the pipeline
        success = run_notion_processing_pipeline()
        
        if success:
            logger.info("\n🎉 All processing completed successfully!")
            logger.info("Check the output directory for generated files.")
        else:
            logger.error("\n❌ Pipeline execution failed.")
            logger.error("Check the logs above for specific error details.")
            
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        logger.error("Please check your .env file and ensure all required variables are set")
        logger.error("Required variables: NOTION_TOKEN, DATABASE_ID, AZURE_OPENAI_KEY, etc.")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()