# CyberSecurity Web Scrapers

A collection of web scrapers for cybersecurity company blogs that automatically extract content and populate a Notion database.

## Supported Sources

- **Okta** - Blog and newsroom articles
- **Mandiant** (Google) - Security research blog
- **Palo Alto Networks** - Blog articles
- **CrowdStrike** - Recent articles

## Project Structure

```
cybersecurity-scrapers/
├── requirements.txt          # Python dependencies
├── config.py                 # Configuration file
├── main_scraper.py          # Main coordinator script
├── notion_integration.py    # Notion database integration
├── okta_scraper.py          # Okta blog scraper
├── mandiant_scraper.py      # Mandiant/Google scraper
├── paloalto_scraper.py      # Palo Alto Networks scraper
├── crowdstrike_scraper.py   # CrowdStrike scraper
└── README.md               # This file
```

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Notion Setup

**Get your Notion Integration Token:**
1. Go to https://www.notion.so/my-integrations
2. Click "New integration"
3. Give it a name and select your workspace
4. Copy the "Internal Integration Token" (starts with `secret_`)

**Get your Parent Page ID:**
1. Open Notion in your browser
2. Go to the page where you want the database created (or use your home page)
3. Copy the page ID from the URL:
   - URL looks like: `https://www.notion.so/Your-Page-Name-abc123def456...`
   - The page ID is the long string after the last dash: `abc123def456...`
4. **Important**: Share this page with your integration:
   - Click "Share" on the page
   - Click "Invite" and select your integration
   - Give it "Full access"

**Quick setup:** Use your Notion home page as the parent - just grab its ID from the URL when you're on your home page.

### 3. Configure Environment Variables

Option A: Set environment variables
```bash
export NOTION_TOKEN="your_notion_integration_token"
export PARENT_PAGE_ID="your_parent_page_id"
```

Option B: Edit config.py
```python
NOTION_TOKEN = "your_notion_integration_token"
PARENT_PAGE_ID = "your_parent_page_id"
```

### 4. Run the Scrapers

Run all scrapers:
```bash
python main_scraper.py
```

Run individual scrapers:
```python
from main_scraper import CyberSecurityScraper

scraper = CyberSecurityScraper(notion_token, parent_page_id)

# Run single scraper
okta_posts = scraper.run_single_scraper('Okta')
scraper.send_to_notion(okta_posts)
```

## Usage Examples

### Running Individual Scrapers

```python
from okta_scraper import OktaScraper
from notion_integration import create_notion_database_and_pages

# Initialize scraper
scraper = OktaScraper()

# Scrape posts
posts = scraper.scrape_all_posts()

# Send to Notion
create_notion_database_and_pages(
    posts, 
    notion_token, 
    parent_page_id, 
    "My Database"
)
```

### Customizing Scrapers

Each scraper class has configurable parameters:

```python
class OktaScraper:
    BASE_URL = "https://www.okta.com/blog/"
    MAX_POSTS = 5  # Change this to scrape more/fewer posts
    DOMAIN = "Okta"
```

## Data Structure

Each scraper returns data in this format:

```python
{
    "company": "Company Name",
    "title": "Article Title",
    "date_published": "2024-01-01",
    "webpage_url": "https://example.com/article",
    "date_pulled": "2024-01-01",
    "text_content": ["Section 1", "Section 2", ...],
    "img_urls": [{"img_url": "url", "alt_text": "description"}],
    "outbound_links": ["url1", "url2", ...]
}
```

## Notion Database Schema

The created database has these properties:

- **Title** (Title): Article title
- **Company** (Rich Text): Source company
- **Date Published** (Date): Publication date
- **Date Pulled** (Date): Scraping date
- **Webpage URL** (URL): Original article URL
- **Image URLs** (Files): Article images
- **Outbound Links?** (Rich Text): Yes/No indicator

## Features

- **Duplicate Detection**: Prevents re-scraping existing articles
- **Content Processing**: Converts HTML to structured Markdown
- **Image Extraction**: Captures and catalogs all article images
- **Link Analysis**: Identifies outbound links for research purposes
- **Error Handling**: Robust error handling and logging
- **Rate Limiting**: Respectful delays between requests

## Troubleshooting

### Common Issues

1. **Module Import Errors**: Ensure all files are in the same directory
2. **Notion API Errors**: Verify token and page permissions
3. **Scraping Failures**: Check if website structure has changed
4. **Unicode Errors**: URLs with special characters are automatically sanitized

### Debugging

Enable verbose logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Rate Limiting

If you encounter rate limiting:
- Increase delays in config.py
- Reduce MAX_POSTS in scraper classes
- Run scrapers individually with delays

## Extending the System

### Adding New Scrapers

1. Create a new scraper file (e.g., `new_company_scraper.py`)
2. Follow the pattern from existing scrapers
3. Implement these methods:
   - `get_latest_post_links()`
   - `parse_post(url)`
   - `scrape_all_posts()`
4. Add to main_scraper.py

### Customizing Output

Modify `notion_integration.py` to change:
- Database schema
- Content processing
- Block formatting

## Legal Notes

- Respect robots.txt and terms of service
- This is for research/analysis purposes
- Add appropriate delays between requests
- Monitor for changes in website structure