"""
Notion Database Discovery Service
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional
import notion_client
from config import *

logger = logging.getLogger(__name__)

class NotionDiscovery:
    def __init__(self):
        """Initialize Notion client"""
        self.notion = notion_client.Client(auth=NOTION_TOKEN)
    
    def find_database_by_name(self, database_name: str, parent_page_id: str = None) -> Optional[str]:
        """
        Find database by name, optionally within a specific parent page
        
        Args:
            database_name: Name of the database to find
            parent_page_id: Optional parent page ID to search within
            
        Returns:
            Database ID if found, None otherwise
        """
        try:
            if parent_page_id:
                # Search within specific parent page
                return self._search_in_parent_page(database_name, parent_page_id)
            else:
                # Search all accessible pages
                return self._search_all_pages(database_name)
                
        except Exception as e:
            logger.error(f"Error finding database by name: {e}")
            return None
    
    def _search_in_parent_page(self, database_name: str, parent_page_id: str) -> Optional[str]:
        """Search for database within a specific parent page"""
        try:
            # Get child pages of the parent
            response = self.notion.blocks.children.list(block_id=parent_page_id)
            
            for block in response.get('results', []):
                if block.get('type') == 'child_database':
                    db_title = self._get_database_title(block)
                    if db_title and database_name.lower() in db_title.lower():
                        logger.info(f"Found database '{db_title}' in parent page")
                        return block['id']
            
            logger.warning(f"Database '{database_name}' not found in parent page")
            return None
            
        except Exception as e:
            logger.error(f"Error searching in parent page: {e}")
            return None
    
    def _search_all_pages(self, database_name: str) -> Optional[str]:
        """Search for database across all accessible pages"""
        try:
            # Search for pages with database_name in title
            response = self.notion.search(
                query=database_name,
                filter={"property": "object", "value": "database"}
            )
            
            databases = []
            for result in response.get('results', []):
                if result.get('object') == 'database':
                    db_title = self._get_database_title(result)
                    if db_title:
                        databases.append({
                            'id': result['id'],
                            'title': db_title,
                            'created_time': result.get('created_time', ''),
                            'last_edited_time': result.get('last_edited_time', '')
                        })
            
            if not databases:
                logger.warning(f"No databases found matching '{database_name}'")
                return None
            
            # Sort by last edited time (most recent first) and return the first match
            databases.sort(key=lambda x: x['last_edited_time'], reverse=True)
            selected_db = databases[0]
            
            logger.info(f"Found database '{selected_db['title']}' (most recent)")
            return selected_db['id']
            
        except Exception as e:
            logger.error(f"Error searching all pages: {e}")
            return None
    
    def _get_database_title(self, database_obj: Dict) -> str:
        """Extract title from database object"""
        try:
            title_property = database_obj.get('title', [])
            if title_property:
                return title_property[0].get('plain_text', '')
            return ''
        except Exception:
            return ''
    
    def create_database_if_not_exists(self, database_name: str, parent_page_id: str) -> str:
        """
        Create database if it doesn't exist, return the database ID
        
        Args:
            database_name: Name of the database to create
            parent_page_id: Parent page ID where to create the database
            
        Returns:
            Database ID (existing or newly created)
        """
        try:
            # First try to find existing database
            existing_id = self.find_database_by_name(database_name, parent_page_id)
            if existing_id:
                logger.info(f"Using existing database: {database_name}")
                return existing_id
            
            # Create new database
            logger.info(f"Creating new database: {database_name}")
            
            database_properties = {
                "Title": {"title": {}},
                "Company": {"rich_text": {}},
                "Date Published": {"date": {}},
                "Date Pulled": {"date": {}},
                "Webpage URL": {"url": {}},
                "Image URLs": {"files": {}},
                "Outbound Links": {"rich_text": {}}
            }
            
            response = self.notion.databases.create(
                parent={"page_id": parent_page_id},
                title=[{"type": "text", "text": {"content": database_name}}],
                properties=database_properties
            )
            
            database_id = response['id']
            logger.info(f"Created database '{database_name}' with ID: {database_id}")
            return database_id
            
        except Exception as e:
            logger.error(f"Error creating database: {e}")
            raise
    
    def get_database_info(self, database_id: str) -> Dict[str, Any]:
        """Get information about a database"""
        try:
            response = self.notion.databases.retrieve(database_id=database_id)
            return {
                'id': response['id'],
                'title': self._get_database_title(response),
                'created_time': response.get('created_time', ''),
                'last_edited_time': response.get('last_edited_time', ''),
                'properties': list(response.get('properties', {}).keys())
            }
        except Exception as e:
            logger.error(f"Error getting database info: {e}")
            return {}
