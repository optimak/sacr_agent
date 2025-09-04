"""Configuration management using environment variables"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Notion API Configuration
NOTION_TOKEN = os.getenv('NOTION_TOKEN')
PARENT_PAGE_ID = os.getenv('PARENT_PAGE_ID')
DATABASE_NAME = os.getenv('DATABASE_NAME', 'CyberSecurity Database 2')

# Scraper Configuration
MAX_POSTS_PER_SCRAPER = int(os.getenv('MAX_POSTS_PER_SCRAPER', 5))
DELAY_BETWEEN_REQUESTS = float(os.getenv('DELAY_BETWEEN_REQUESTS', 1.0))
DELAY_BETWEEN_SCRAPERS = float(os.getenv('DELAY_BETWEEN_SCRAPERS', 2.0))
REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', 10))

# Individual scraper settings (with fallback to global setting)
OKTA_MAX_POSTS = int(os.getenv('OKTA_MAX_POSTS', MAX_POSTS_PER_SCRAPER))
MANDIANT_MAX_POSTS = int(os.getenv('MANDIANT_MAX_POSTS', MAX_POSTS_PER_SCRAPER))
PALOALTO_MAX_POSTS = int(os.getenv('PALOALTO_MAX_POSTS', MAX_POSTS_PER_SCRAPER))
CROWDSTRIKE_MAX_POSTS = int(os.getenv('CROWDSTRIKE_MAX_POSTS', MAX_POSTS_PER_SCRAPER))

# Logging Configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()

def validate_config():
    """Validate that required configuration is present"""
    if not NOTION_TOKEN:
        raise ValueError("NOTION_TOKEN environment variable is required")
    
    if not PARENT_PAGE_ID:
        raise ValueError("PARENT_PAGE_ID environment variable is required")
    
    return True

def get_scraper_config(scraper_name):
    """Get configuration for a specific scraper"""
    config_map = {
        'Okta': OKTA_MAX_POSTS,
        'Mandiant': MANDIANT_MAX_POSTS, 
        'Palo Alto': PALOALTO_MAX_POSTS,
        'CrowdStrike': CROWDSTRIKE_MAX_POSTS
    }
    
    return {
        'max_posts': config_map.get(scraper_name, MAX_POSTS_PER_SCRAPER),
        'delay_between_requests': DELAY_BETWEEN_REQUESTS,
        'request_timeout': REQUEST_TIMEOUT
    }