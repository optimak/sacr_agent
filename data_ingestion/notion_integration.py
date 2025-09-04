"""Notion database integration module"""
import os
import notion_client
import re
import json
import unicodedata

def has_bad_unicode(url: str) -> bool:
    """Check if URL contains disallowed unicode characters (breaking Notion links)."""
    if not url:
        return False
    # Add other space-like or invisible characters if needed
    bad_chars = [
        "\u202f",  # narrow no-break space
        "\u200b",  # zero-width space
        "\ufeff",  # BOM
        "\u200e",  # LTR mark
        "\u200f",  # RTL mark
        "\u2060",  # word joiner
        "\u00a0",  # non-breaking space
        "\u3000",  # ideographic space
    ]
    return any(c in url for c in bad_chars)

def sanitize_url(url: str) -> str:
    """Clean URL: normalize, remove bad unicode, and drop invalid ones."""
    if not url or has_bad_unicode(url):
        print(f"⚠️ Dropping bad URL: {url}")
        return ""
    url = unicodedata.normalize("NFC", url.strip())
    if not url.startswith(("http://", "https://")):
        url = "https://" + url.lstrip("/")
    return url

def check_page_exists(notion_client, database_id, title, date_published):
    """Checks if a page with the same title and date published already exists."""
    try:
        # Search for pages with the matching title
        filter_title = {
            "property": "Title",
            "title": {
                "equals": title
            }
        }
        
        # Search for pages with the matching date published
        filter_date = {
            "property": "Date Published",
            "date": {
                "equals": date_published
            }
        }
        
        # Combine filters to check for both title and date
        search_results = notion_client.databases.query(
            database_id=database_id,
            filter={
                "and": [filter_title, filter_date]
            }
        )
        
        return len(search_results['results']) > 0
    except Exception as e:
        print(f"Error checking for existing page: {e}")
        return False

def markdown_to_notion_blocks(markdown_list):
    blocks = []
    image_regex = r'!\[([^\]]*)\]\((.*?)\)'
    heading_regex = r'^(#{1,6})\s+(.*)'
    link_regex = r'\[([^\]]+)\]\(([^)]+)\)'

    def parse_rich_text_with_links(text):
        rich_text = []
        last_end = 0
        
        for match in re.finditer(link_regex, text):
            start, end = match.span()
            link_text, link_url = match.group(1), match.group(2)
            
            if start > last_end:
                before_text = text[last_end:start]
                if before_text:
                    # Chunk text that's too long
                    if len(before_text) > 1900:
                        chunks = [before_text[i:i+1900] for i in range(0, len(before_text), 1900)]
                        for chunk in chunks:
                            rich_text.append({"text": {"content": chunk}})
                    else:
                        rich_text.append({"text": {"content": before_text}})
            
            # Ensure link text isn't too long
            if len(link_text) > 1900:
                link_text = link_text[:1897] + "..."
                
            rich_text.append({
                "text": {"content": link_text, "link": {"url": link_url}}
            })
            last_end = end
        
        if last_end < len(text):
            remaining_text = text[last_end:]
            if remaining_text:
                # Chunk remaining text
                if len(remaining_text) > 1900:
                    chunks = [remaining_text[i:i+1900] for i in range(0, len(remaining_text), 1900)]
                    for chunk in chunks:
                        rich_text.append({"text": {"content": chunk}})
                else:
                    rich_text.append({"text": {"content": remaining_text}})
        
        if not rich_text:
            # Handle case where original text is too long
            if len(text) > 1900:
                chunks = [text[i:i+1900] for i in range(0, len(text), 1900)]
                for chunk in chunks:
                    rich_text.append({"text": {"content": chunk}})
            else:
                rich_text = [{"text": {"content": text}}]
        
        return rich_text

    for item in markdown_list:
        remaining_text = item
        
        while remaining_text:
            # Check for an image at the current position
            image_match = re.search(image_regex, remaining_text)
            
            # Check for a heading at the current position
            heading_match = re.match(heading_regex, remaining_text.strip())
            
            # Priority: Heading, then Image, then Paragraph
            
            if heading_match:
                # Process heading first
                heading_text = heading_match.group(2).strip()
                heading_end = heading_match.end()
                
                # Check for remaining text after the heading on the same line
                body_text = remaining_text[heading_end:].strip()
                
                heading_rich_text = parse_rich_text_with_links(heading_text)
                for t in heading_rich_text:
                    t["annotations"] = {"bold": True}
                
                if body_text:
                    heading_rich_text.append({"text": {"content": "\n"}})
                    heading_rich_text.extend(parse_rich_text_with_links(body_text))
                
                if len(heading_rich_text[0]["text"]["content"]) > 1900:
                    # Special handling for very long headings/combined text
                    # This logic needs to be more robust, but here's a simplification
                    blocks.append({"object": "block", "type": "paragraph", "paragraph": {"rich_text": heading_rich_text[:1]}})
                    blocks.append({"object": "block", "type": "paragraph", "paragraph": {"rich_text": heading_rich_text[1:]}})
                else:
                    blocks.append({"object": "block", "type": "paragraph", "paragraph": {"rich_text": heading_rich_text}})
                
                remaining_text = "" # Processed the whole item as a heading
                
            elif image_match:
                # Process text before the image
                pre_image_text = remaining_text[:image_match.start()]
                if pre_image_text.strip():
                    if len(pre_image_text) > 2000:
                        chunks = [pre_image_text[i:i+2000] for i in range(0, len(pre_image_text), 2000)]
                        for chunk in chunks:
                            blocks.append({"object": "block", "type": "paragraph", "paragraph": {"rich_text": parse_rich_text_with_links(chunk)}})
                    else:
                        blocks.append({"object": "block", "type": "paragraph", "paragraph": {"rich_text": parse_rich_text_with_links(pre_image_text)}})
                
                # Process the image block
                alt_text, image_url = image_match.group(1), image_match.group(2)
                clean_url = sanitize_url(image_url)
                if clean_url:
                    blocks.append({
                        "object": "block",
                        "type": "image",
                        "image": {
                            "type": "external",
                            "external": {"url": clean_url},
                            "caption": [{"text": {"content": alt_text}}]
                        }
                    })
                
                # Update the remaining text to continue processing after the image
                remaining_text = remaining_text[image_match.end():]
                
            else:
                # Process as a regular paragraph
                if remaining_text.strip():
                    if len(remaining_text) > 2000:
                        chunks = [remaining_text[i:i+2000] for i in range(0, len(remaining_text), 2000)]
                        for chunk in chunks:
                            blocks.append({"object": "block", "type": "paragraph", "paragraph": {"rich_text": parse_rich_text_with_links(chunk)}})
                    else:
                        blocks.append({"object": "block", "type": "paragraph", "paragraph": {"rich_text": parse_rich_text_with_links(remaining_text)}})
                
                remaining_text = "" # Processed the whole item as a paragraph
                
    return blocks

def truncate_filename(text, max_length=100):
    if len(text) <= max_length:
        return text
    truncated = text[:max_length]
    last_space = truncated.rfind(' ')
    if last_space > max_length * 0.8:
        return truncated[:last_space] + "..."
    return truncated[:max_length-3] + "..."

def create_notion_database_and_pages(data_list, notion_api_key, parent_page_id, database_name):
    notion = notion_client.Client(auth=notion_api_key)
    try:
        search_results = notion.search(query=database_name, filter={"property": "object", "value": "database"})
        database_id = None
        for result in search_results['results']:
            if result.get('title') and result['title'][0]['plain_text'] == database_name:
                database_id = result['id']
                print(f"Found existing database: {database_id}")
                database_info = notion.databases.retrieve(database_id=database_id)
                required_properties = {"Title", "Company", "Date Published", "Date Pulled", "Webpage URL", "Image URLs", "Outbound Links?"}
                if required_properties.issubset(set(database_info['properties'].keys())):
                    break
                database_id = None
        if not database_id:
            database_properties = {
                "Title": {"title": {}},
                "Company": {"rich_text": {}},
                "Date Published": {"date": {}},
                "Date Pulled": {"date": {}},
                "Webpage URL": {"url": {}},
                "Image URLs": {"files": {}},
                "Outbound Links?": {"rich_text": {}}
            }
            new_database = notion.databases.create(
                parent={"page_id": parent_page_id},
                title=[{"type": "text", "text": {"content": database_name}}],
                properties=database_properties
            )
            database_id = new_database["id"]

    except Exception as e:
        print(f"Database creation/search error: {e}")
        return {"error": str(e)}

    for item in data_list:
        try:
            if check_page_exists(notion, database_id, item['title'], item['date_published']):
                print(f"Page '{item['title']}' already exists. Skipping.")
                continue  # Skip to the next item in the loop

            has_outbound_links = bool(item.get('outbound_links') and any(link.strip() for link in item['outbound_links']))
            valid_images = [
                {"img_url": clean_url, "alt_text": img.get('alt_text', '')}
                for img in item.get('img_urls', [])
                if (clean_url := sanitize_url(img.get('img_url')))
            ]
            properties = {
                "Title": {"title": [{"text": {"content": item['title']}}]},
                "Company": {"rich_text": [{"text": {"content": item['company']}}]},
                "Date Published": {"date": {"start": item['date_published']}},
                "Date Pulled": {"date": {"start": item['date_pulled']}},
                "Webpage URL": {"url": item['webpage_url']},
                "Image URLs": {"files": [
                    {"type": "external", "name": truncate_filename(img['alt_text']), "external": {"url": img['img_url']}}
                    for img in valid_images
                ]},
                "Outbound Links?": {"rich_text": [{"text": {"content": "Yes" if has_outbound_links else "No"}}]}
            }
            children_blocks = markdown_to_notion_blocks(item.get('text_content', []))
            if has_outbound_links:
                outbound_links_text = "Outbound Links:\n" + "\n".join(item['outbound_links'])
                children_blocks.append({"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"text": {"content": outbound_links_text}}]}})

            notion.pages.create(parent={"database_id": database_id}, properties=properties, children=children_blocks)
            print(f"Page '{item['title']}' created successfully.")

        except Exception as e:
            print(f"Failed to create page for '{item.get('title', 'Unknown')}': {e}")
            continue

    return {"status": "success", "database_id": database_id}