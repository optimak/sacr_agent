"""Configuration management for RAG Agent using environment variables"""

import os
from dotenv import load_dotenv
import nltk

# Load environment variables from .env file
load_dotenv()

# Notion Configuration
NOTION_TOKEN = os.getenv('NOTION_TOKEN')
DATABASE_ID = os.getenv('DATABASE_ID')

# Azure OpenAI Configuration
AZURE_OPENAI_KEY = os.getenv('AZURE_OPENAI_KEY')
AZURE_ENDPOINT = os.getenv('AZURE_ENDPOINT')
EMBEDDING_DEPLOYMENT = os.getenv('EMBEDDING_DEPLOYMENT', 'text-embedding-3-small')
GPT4O_DEPLOYMENT = os.getenv('GPT4O_DEPLOYMENT', 'gpt-4o')

# Azure AI Search Configuration
SEARCH_SERVICE_NAME = os.getenv('AZURE_SEARCH_SERVICE_NAME')
SEARCH_API_KEY = os.getenv('AZURE_SEARCH_API_KEY')
INDEX_NAME = os.getenv('INDEX_NAME', 'sacr-rag')

# Processing Configuration
MAX_PAGES_TO_PROCESS = int(os.getenv('MAX_PAGES_TO_PROCESS', 100))
MAX_TOKENS_PER_CHUNK = int(os.getenv('MAX_TOKENS_PER_CHUNK', 380))
OVERLAP_TOKENS = int(os.getenv('OVERLAP_TOKENS', 40))

# Output Configuration
OUTPUT_DIR = os.getenv('OUTPUT_DIR', 'rag_output')

def validate_config():
    """Validate that required configuration is present"""
    required_vars = {
        'NOTION_TOKEN': NOTION_TOKEN,
        'DATABASE_ID': DATABASE_ID,
        'AZURE_OPENAI_KEY': AZURE_OPENAI_KEY,
        'AZURE_ENDPOINT': AZURE_ENDPOINT,
        'SEARCH_SERVICE_NAME': SEARCH_SERVICE_NAME,
        'SEARCH_API_KEY': SEARCH_API_KEY
    }
    
    missing_vars = [var for var, value in required_vars.items() if not value]
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    return True

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