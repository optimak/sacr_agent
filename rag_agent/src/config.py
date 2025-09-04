"""Configuration management for RAG Agent using environment variables"""

import os
import json
from dotenv import load_dotenv
import nltk

# Load environment variables from .env file
load_dotenv()

# Notion Configuration
NOTION_TOKEN = os.getenv('NOTION_TOKEN')
NOTION_DATABASE_NAME = os.getenv('NOTION_DATABASE_NAME', 'CyberSecurity Database')
DATABASE_ID = os.getenv('DATABASE_ID')  # Will be auto-discovered and cached

# Vector Database Configuration
USE_LOCAL_VECTOR_DB = os.getenv('USE_LOCAL_VECTOR_DB', 'true').lower() == 'true'
USE_AZURE_AI_SEARCH = os.getenv('USE_AZURE_AI_SEARCH', 'false').lower() == 'true'
LOCAL_VECTOR_DB_ENGINE = os.getenv('LOCAL_VECTOR_DB_ENGINE', 'chroma')

# Azure OpenAI Configuration
AZURE_OPENAI_KEY = os.getenv('AZURE_OPENAI_KEY')
AZURE_ENDPOINT = os.getenv('AZURE_ENDPOINT')
EMBEDDING_DEPLOYMENT = os.getenv('EMBEDDING_DEPLOYMENT', 'text-embedding-3-small')
GPT4O_DEPLOYMENT = os.getenv('GPT4O_DEPLOYMENT', 'gpt-4o')
GPT4O_MINI_DEPLOYMENT = os.getenv('GPT4O_MINI_DEPLOYMENT', 'gpt-4o-mini')

# Azure AI Search Configuration
SEARCH_SERVICE_NAME = os.getenv('AZURE_SEARCH_SERVICE_NAME')
SEARCH_API_KEY = os.getenv('AZURE_SEARCH_API_KEY')
INDEX_NAME = os.getenv('INDEX_NAME', 'sacr-rag')

# Prompt Flow Configuration
USE_PROMPTFLOW_LOCAL = os.getenv('USE_PROMPTFLOW_LOCAL', 'true').lower() == 'true'
PROMPTFLOW_ENDPOINT = os.getenv('PROMPTFLOW_ENDPOINT')
PROMPTFLOW_KEY = os.getenv('PROMPTFLOW_KEY')

# Image Processing Configuration
ENABLE_IMAGE_OCR = os.getenv('ENABLE_IMAGE_OCR', 'true').lower() == 'true'
ENABLE_IMAGE_UNDERSTANDING = os.getenv('ENABLE_IMAGE_UNDERSTANDING', 'false').lower() == 'true'

# Processing Configuration
MAX_PAGES_TO_PROCESS = int(os.getenv('MAX_PAGES_TO_PROCESS', 100))
MAX_TOKENS_PER_CHUNK = int(os.getenv('MAX_TOKENS_PER_CHUNK', 380))
OVERLAP_TOKENS = int(os.getenv('OVERLAP_TOKENS', 40))
TOP_K = int(os.getenv('TOP_K', 5))

# Output Configuration
OUTPUT_DIR = os.getenv('OUTPUT_DIR', 'rag_output')
CACHE_DIR = os.getenv('CACHE_DIR', 'cache')

def validate_config():
    """Validate that required configuration is present"""
    required_vars = {
        'NOTION_TOKEN': NOTION_TOKEN,
        'AZURE_OPENAI_KEY': AZURE_OPENAI_KEY,
        'AZURE_ENDPOINT': AZURE_ENDPOINT,
    }
    
    # Add Azure AI Search requirements only if using Azure AI Search
    if USE_AZURE_AI_SEARCH:
        required_vars.update({
            'SEARCH_SERVICE_NAME': SEARCH_SERVICE_NAME,
            'SEARCH_API_KEY': SEARCH_API_KEY
        })
    
    # Add Prompt Flow requirements only if using remote Prompt Flow
    if not USE_PROMPTFLOW_LOCAL:
        required_vars.update({
            'PROMPTFLOW_ENDPOINT': PROMPTFLOW_ENDPOINT,
            'PROMPTFLOW_KEY': PROMPTFLOW_KEY
        })
    
    missing_vars = [var for var, value in required_vars.items() if not value]
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    return True

def get_database_id():
    """Get database ID from cache or auto-discover"""
    cache_file = os.path.join(CACHE_DIR, 'notion_cache.json')
    
    # Try to load from cache first
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r') as f:
                cache = json.load(f)
                if 'database_id' in cache:
                    return cache['database_id']
        except (json.JSONDecodeError, KeyError):
            pass
    
    # If not in cache, return None (will be auto-discovered)
    return None

def cache_database_id(database_id):
    """Cache the discovered database ID"""
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_file = os.path.join(CACHE_DIR, 'notion_cache.json')
    
    cache = {'database_id': database_id}
    with open(cache_file, 'w') as f:
        json.dump(cache, f)

def setup_nltk():
    """Download required NLTK data if not present"""
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        print("Downloading required NLTK data...")
        nltk.download('punkt', quiet=True)
        nltk.download('stopwords', quiet=True)
        print("NLTK data downloaded successfully")

def get_azure_openai_endpoint():
    """Get the formatted Azure OpenAI endpoint"""
    return AZURE_ENDPOINT

def get_search_endpoint():
    """Get the formatted Azure Search endpoint"""
    return f"https://{SEARCH_SERVICE_NAME}.search.windows.net"

# Initialize NLTK on import
setup_nltk()