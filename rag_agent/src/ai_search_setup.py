"""
AI Search Setup - Create index and upload documents
"""

import os
import json
from typing import List, Dict, Any
from datetime import datetime
import logging

from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.models import VectorizedQuery
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    SimpleField,
    SearchableField,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
    SemanticConfiguration,
    SemanticPrioritizedFields,
    SemanticField,
    SemanticSearch
)
from azure.core.credentials import AzureKeyCredential
from openai import AzureOpenAI
from tenacity import retry, stop_after_attempt, wait_random_exponential


from config import *

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AISearchSetup:
    def __init__(self):
        """Initialize AI Search setup with configuration"""
        validate_config()
        
        self.search_service_name = SEARCH_SERVICE_NAME
        self.search_endpoint = get_search_endpoint()
        self.search_credential = AzureKeyCredential(SEARCH_API_KEY)

        # Initialize clients
        self.index_client = SearchIndexClient(
            endpoint=self.search_endpoint,
            credential=self.search_credential
        )

        # Azure OpenAI for embedding generation during search
        self.azure_client = AzureOpenAI(
            api_key=AZURE_OPENAI_KEY,
            api_version="2024-02-01",
            azure_endpoint=get_azure_openai_endpoint()
        )
        self.embedding_deployment = EMBEDDING_DEPLOYMENT
        self.index_name = INDEX_NAME
        self.output_dir = OUTPUT_DIR

    def create_hybrid_search_index(self, index_name: str = None) -> bool:
        """Create a hybrid search index optimized for RAG with semantic search"""
        index_name = index_name or self.index_name
        logger.info(f"Creating hybrid search index: {index_name}")

        try:
            # Define the vector search configuration
            vector_search = VectorSearch(
                algorithms=[
                    HnswAlgorithmConfiguration(name="myHnsw")
                ],
                profiles=[
                    VectorSearchProfile(
                        name="myHnswProfile",
                        algorithm_configuration_name="myHnsw"
                    )
                ]
            )

            # Define semantic search configuration
            semantic_config = SemanticConfiguration(
                name="my-semantic-config",
                prioritized_fields=SemanticPrioritizedFields(
                    content_fields=[SemanticField(field_name="content")],
                    keywords_fields=[
                        SemanticField(field_name="title"),
                        SemanticField(field_name="company")
                    ]
                )
            )

            semantic_search = SemanticSearch(configurations=[semantic_config])

            # Define index fields
            fields = [
                # Primary key
                SimpleField(
                    name="id",
                    type=SearchFieldDataType.String,
                    key=True,
                    filterable=True
                ),

                # Content fields for search
                SearchableField(
                    name="content",
                    type=SearchFieldDataType.String,
                    searchable=True,
                    analyzer_name="en.microsoft"
                ),
                SearchableField(
                    name="title",
                    type=SearchFieldDataType.String,
                    searchable=True,
                    analyzer_name="en.microsoft"
                ),
                SearchableField(
                    name="company",
                    type=SearchFieldDataType.String,
                    searchable=True,
                    facetable=True,
                    filterable=True
                ),

                # Vector field for semantic search
                SearchField(
                    name="content_vector",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    searchable=True,
                    vector_search_dimensions=1536,  # text-embedding-3-small dimension
                    vector_search_profile_name="myHnswProfile"
                ),

                # Filterable/Facetable fields
                SimpleField(
                    name="date_published",
                    type=SearchFieldDataType.String,
                    filterable=True,
                    sortable=True,
                    facetable=True
                ),
                SimpleField(
                    name="date_pulled",
                    type=SearchFieldDataType.String,
                    filterable=True,
                    sortable=True
                ),
                SimpleField(
                    name="has_images",
                    type=SearchFieldDataType.Boolean,
                    filterable=True,
                    facetable=True
                ),
                SimpleField(
                    name="page_sequence",
                    type=SearchFieldDataType.Int32,
                    filterable=True,
                    sortable=True
                ),
                SimpleField(
                    name="token_count",
                    type=SearchFieldDataType.Int32,
                    filterable=True,
                    sortable=True
                ),

                # Metadata fields (stored only)
                SimpleField(
                    name="chunk_id",
                    type=SearchFieldDataType.String,
                    retrievable=True
                ),
                SimpleField(
                    name="notion_page_id",
                    type=SearchFieldDataType.String,
                    retrievable=True
                ),
                SimpleField(
                    name="webpage_url",
                    type=SearchFieldDataType.String,
                    retrievable=True
                ),
                SearchableField(
                    name="content_types",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.String),
                    retrievable=True,
                    facetable=True
                )
            ]

            # Create the index
            index = SearchIndex(
                name=index_name,
                fields=fields,
                vector_search=vector_search,
                semantic_search=semantic_search
            )

            result = self.index_client.create_or_update_index(index)
            logger.info(f"Successfully created index: {result.name}")
            return True

        except Exception as e:
            logger.error(f"Error creating index: {e}")
            return False
        
    @retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
    def _create_embedding(self, content: str) -> List[float]:
        """Helper to create embeddings with retry logic."""
        response = self.azure_client.embeddings.create(
            input=content,
            model=self.embedding_deployment,
            timeout=120  # Set a timeout in seconds
        )
        return response.data[0].embedding
    
    def generate_embeddings_for_documents(self, documents: List[Dict]) -> List[Dict]:
            """Generate embeddings for documents that don't have them"""
            logger.info(f"Generating embeddings for {len(documents)} documents...")

            enhanced_docs = []

            for i, doc in enumerate(documents):
                logger.info(f"Processing document {i+1}/{len(documents)}: {doc['chunk_id']}")

                try:
                    # Use the new helper function with retry logic
                    doc['content_vector'] = self._create_embedding(doc['content'])
                    enhanced_docs.append(doc)

                except Exception as e:
                    logger.error(f"Error generating embedding for {doc['chunk_id']}: {e}")
                    continue

            logger.info(f"Generated embeddings for {len(enhanced_docs)} documents")
            return enhanced_docs


    def prepare_documents_for_upload(self, documents: List[Dict]) -> List[Dict]:
        """Clean and prepare documents for AI Search upload"""
        prepared_docs = []

        for doc in documents:
            # Create a clean copy
            clean_doc = {
                'id': str(doc['id']).replace('_', '-'),
                'chunk_id': str(doc['chunk_id']),
                'content': str(doc['content']),
                'title': str(doc['title']),
                'company': str(doc['company']),
                'date_published': str(doc['date_published']) if doc['date_published'] else None,
                'date_pulled': str(doc['date_pulled']) if doc['date_pulled'] else None,
                'webpage_url': str(doc['webpage_url']) if doc['webpage_url'] else None,
                'notion_page_id': str(doc['notion_page_id']),
                'page_sequence': int(doc['page_sequence']),
                'has_images': bool(doc['has_images']),
                'token_count': int(doc['token_count']),
                'content_vector': doc['content_vector']
            }
        # 🔑 Flatten content_types (list → string)
            ct = doc.get("content_types")
            if isinstance(ct, list):
                clean_doc["content_types"] = ", ".join(ct)
            else:
                clean_doc["content_types"] = ct or ""


            prepared_docs.append(clean_doc)

        return prepared_docs
    def upload_documents(self, documents: List[Dict], index_name: str = None) -> bool:
        """Upload documents to AI Search index"""
        index_name = index_name or self.index_name
        logger.info(f"Uploading {len(documents)} documents to index: {index_name}")

        try:
            search_client = SearchClient(
                endpoint=self.search_endpoint,
                index_name=index_name,
                credential=self.search_credential
            )

            # Upload in batches to avoid timeouts
            batch_size = 100
            total_uploaded = 0

            for i in range(0, len(documents), batch_size):
                batch = documents[i:i + batch_size]
                logger.info(f"Uploading batch {i//batch_size + 1}, documents {i+1}-{min(i+batch_size, len(documents))}")

                try:
                    result = search_client.upload_documents(documents=batch)
                    successful = sum(1 for r in result if r.succeeded)
                    total_uploaded += successful

                    if successful < len(batch):
                        failed = len(batch) - successful
                        logger.warning(f"{failed} documents failed in this batch")

                except Exception as batch_error:
                    logger.error(f"Batch upload failed: {batch_error}")
                    continue

            logger.info(f"Successfully uploaded {total_uploaded}/{len(documents)} documents")
            return total_uploaded == len(documents)

        except Exception as e:
            logger.error(f"Error uploading documents: {e}")
            return False

    def test_search_functionality(self, index_name: str = None) -> bool:
        """Test different search capabilities"""
        index_name = index_name or self.index_name
        logger.info(f"Testing search functionality on index: {index_name}")

        try:
            search_client = SearchClient(
                endpoint=self.search_endpoint,
                index_name=index_name,
                credential=self.search_credential
            )

            # Test 1: Simple text search
            logger.info("\nTest 1: Simple text search for 'security'")
            results = search_client.search(
                search_text="security",
                top=3,
                select=["chunk_id", "title", "company", "has_images"]
            )

            for result in results:
                logger.info(f"  - {result['chunk_id']}: {result['title'][:60]}...")

            # Test 2: Semantic search
            logger.info("\nTest 2: Semantic search for 'cybersecurity threats'")
            results = search_client.search(
                search_text="cybersecurity threats",
                query_type="semantic",
                semantic_configuration_name="my-semantic-config",
                top=3,
                select=["chunk_id", "title", "company"]
            )

            for result in results:
                logger.info(f"  - {result['chunk_id']}: {result['title'][:60]}...")

            # Test 3: Filtered search
            logger.info("\nTest 3: Filtered search (documents with images)")
            results = search_client.search(
                search_text="*",
                filter="has_images eq true",
                top=3,
                select=["chunk_id", "title", "has_images"]
            )

            for result in results:
                logger.info(f"  - {result['chunk_id']}: {result['title'][:60]}... (has_images: {result['has_images']})")

            # Test 4: Vector search
            logger.info("\nTest 4: Vector similarity search")
            query_vector = self.azure_client.embeddings.create(
                input="identity security best practices",
                model=self.embedding_deployment
            ).data[0].embedding

            results = search_client.search(
                search_text=None,
                vector_queries=[VectorizedQuery(vector=query_vector, k_nearest_neighbors=3, fields="content_vector")],
                select=["chunk_id", "title", "company"]
            )

            for result in results:
                logger.info(f"  - {result['chunk_id']}: {result['title'][:60]}...")

            logger.info("\nAll search tests completed successfully!")
            return True

        except Exception as e:
            logger.error(f"Error testing search functionality: {e}")
            return False

    def get_index_statistics(self, index_name: str = None) -> Dict:
        """Get statistics about the search index"""
        index_name = index_name or self.index_name
        
        try:
            search_client = SearchClient(
                endpoint=self.search_endpoint,
                index_name=index_name,
                credential=self.search_credential
            )

            # Get total document count
            results = search_client.search(search_text="*", include_total_count=True, top=0)
            total_docs = results.get_count()

            # Get documents with images count
            results = search_client.search(
                search_text="*",
                filter="has_images eq true",
                include_total_count=True,
                top=0
            )
            docs_with_images = results.get_count()

            # Get company distribution
            results = search_client.search(
                search_text="*",
                facets=["company"],
                top=0
            )

            company_facets = results.get_facets().get("company", [])

            stats = {
                "total_documents": total_docs,
                "documents_with_images": docs_with_images,
                "documents_text_only": total_docs - docs_with_images,
                "companies": {facet["value"]: facet["count"] for facet in company_facets}
            }

            return stats

        except Exception as e:
            logger.error(f"Error getting index statistics: {e}")
            return {}

def load_ai_search_documents(file_path: str = None) -> List[Dict]:
    """Load AI Search ready documents from the pipeline output"""
    if not file_path:
        file_path = os.path.join(OUTPUT_DIR, "ai_search_documents.json")
    
    try:
        with open(file_path, 'r') as f:
            documents = json.load(f)

        # Flatten the 'content_types' field for each document
        for doc in documents:
            if 'content_types' in doc and isinstance(doc['content_types'], list):
                # Keep as list for Azure AI Search
                doc['content_types'] = [str(ct) for ct in doc['content_types']]

        logger.info(f"Loaded {len(documents)} documents from {file_path}")
        return documents
    except Exception as e:
        logger.error(f"Error loading documents: {e}")
        return []

def main():
    """Main function to set up AI Search index and upload documents"""
    try:
        logger.info("="*60)
        logger.info("Starting Azure AI Search Setup")
        logger.info("="*60)

        # Initialize AI Search setup
        ai_search = AISearchSetup()

        # Step 1: Create the hybrid search index
        logger.info("Step 1: Creating hybrid search index...")
        if not ai_search.create_hybrid_search_index():
            logger.error("Failed to create index. Exiting.")
            return False

        # Step 2: Load documents from pipeline output
        logger.info("\nStep 2: Loading documents from pipeline output...")
        documents = load_ai_search_documents()
        if not documents:
            logger.error("No documents found. Run main.py first to process Notion content.")
            return False

        # Step 3: Generate embeddings
        logger.info("\nStep 3: Generating embeddings for documents...")
        enhanced_docs = ai_search.generate_embeddings_for_documents(documents)
        if not enhanced_docs:
            logger.error("Failed to generate embeddings. Exiting.")
            return False

        # Step 4: Prepare documents for upload
        logger.info("\nStep 4: Preparing documents for upload...")
        prepared_docs = ai_search.prepare_documents_for_upload(enhanced_docs)

        # Step 5: Upload documents to index
        logger.info(f"\nStep 5: Uploading documents to AI Search...")
        if not ai_search.upload_documents(prepared_docs):
            logger.error("Document upload failed.")
            return False

        # Step 6: Test search functionality
        logger.info(f"\nStep 6: Testing search functionality...")
        if not ai_search.test_search_functionality():
            logger.warning("Some search tests failed, but index is created.")

        # Step 7: Display index statistics
        logger.info(f"\nStep 7: Index Statistics")
        stats = ai_search.get_index_statistics()
        if stats:
            logger.info(f"Total Documents: {stats['total_documents']}")
            logger.info(f"Documents with Images: {stats['documents_with_images']}")
            logger.info(f"Text-only Documents: {stats['documents_text_only']}")
            logger.info("Companies:")
            for company, count in stats['companies'].items():
                logger.info(f"  - {company}: {count} documents")

        logger.info("\n" + "="*60)
        logger.info("AI Search setup completed successfully!")
        logger.info(f"Search endpoint: {ai_search.search_endpoint}")
        logger.info(f"Index name: {ai_search.index_name}")
        logger.info("\nNext steps:")
        logger.info("1. Test search queries in Azure portal")
        logger.info("2. Build query/chat interface")
        logger.info("3. Monitor search performance")

        return True

    except Exception as e:
        logger.error(f"AI Search setup failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        exit(1)