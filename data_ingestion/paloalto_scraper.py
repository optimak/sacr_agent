import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime
import pytz
import logging
import re
import time

# Configure logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class PaloAltoScraper:
    BASE_URL = "https://www.paloaltonetworks.com"
    BLOG_URL = "https://www.paloaltonetworks.com/blog/"
    DOMAIN = "Palo Alto Networks"

    def __init__(self, config=None):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
        if config:
            self.MAX_POSTS = config.get('max_posts', 5)
            self.REQUEST_TIMEOUT = config.get('request_timeout', 10)
            self.DELAY_BETWEEN_REQUESTS = config.get('delay_between_requests', 1)
        else:
            self.MAX_POSTS = 5
            self.REQUEST_TIMEOUT = 10
            self.DELAY_BETWEEN_REQUESTS = 1
        self.all_links = []

    def fetch_page(self, url):
        try:
            resp = self.session.get(url, timeout=self.REQUEST_TIMEOUT)
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return None

    def get_latest_post_links(self):
        """Scrape blog homepage for latest post URLs"""
        html = self.fetch_page(self.BLOG_URL)
        if not html:
            return []

        soup = BeautifulSoup(html, 'html.parser')
        blog_links = []

        # Get the most recent post from the first synopsis div
        first_synopsis = soup.find('div', class_='synopsis')
        if first_synopsis:
            first_link = first_synopsis.find('a', href=True)
            if first_link and first_link.get('href'):
                href = urljoin(self.BASE_URL, first_link['href'])
                blog_links.append(href)
                logger.info(f"Found featured post: {href}")

        # Get the next 4 posts from latest-articles section
        latest_articles = soup.find('section', class_='latest-articles')
        if latest_articles:
            article_titles = latest_articles.find_all('h2', class_='title')
            for title in article_titles[:self.MAX_POSTS - len(blog_links)]:
                link = title.find('a', href=True)
                if link and link.get('href'):
                    href = urljoin(self.BASE_URL, link['href'])
                    blog_links.append(href)
                    logger.info(f"Found recent post: {href}")

        logger.info(f"Found {len(blog_links)} latest posts")
        return blog_links

    def process_text_content(self, soup):
        """Process text content from the article, organizing by sections"""
        text_sections = []
        img_urls = []
        outbound_links = []
        processed_content = set()

        article_section = soup.find('section', class_='article')
        if not article_section:
            return [], [], []

        # Remove tags div
        tags_div = article_section.find('div', class_='tags')
        if tags_div:
            tags_div.decompose()

        current_section_text = ""
        for element in article_section.find_all(
            ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'ul', 'ol', 'blockquote', 'table', 'figure', 'pre', 'div'],
            recursive=False
        ):
            text_to_add = ""
            if element.name in ['h2', 'h3']:
                if current_section_text.strip():
                    text_sections.append(current_section_text.strip())
                current_section_text = f"## {element.get_text(strip=True)}\n"
            elif element.name in ['h4', 'h5', 'h6']:
                text_to_add = f"**{element.get_text(strip=True)}**\n"
            elif element.name == 'p':
                text_to_add = self.process_paragraph(element, img_urls, outbound_links) + "\n"
            elif element.name in ['ul', 'ol']:
                text_to_add = self.process_list(element, outbound_links) + "\n"
            elif element.name == 'blockquote':
                text_to_add = f'"{element.get_text(separator=" ").strip()}"\n'
            elif element.name == 'table':
                text_to_add = self.process_table(element, outbound_links) + "\n"
            elif element.name == 'figure':
                text_to_add = self.process_figure(element, img_urls, outbound_links)
            elif element.name == 'pre':
                text_to_add = self.process_code_block(element) + "\n"
            elif element.name == 'div' and element.get_text(separator=' ').strip():
                text_to_add = element.get_text(separator=' ').strip() + "\n"

            if text_to_add and text_to_add.strip() not in processed_content:
                processed_content.add(text_to_add.strip())
                current_section_text += text_to_add

        if current_section_text.strip():
            text_sections.append(current_section_text.strip())

        return text_sections, img_urls, outbound_links

    def process_paragraph(self, p_element, img_urls, outbound_links):
        text = ""
        for element in p_element.children:
            if hasattr(element, 'name'):
                if element.name == 'a':
                    link_text, link_url = self.process_link(element, outbound_links)
                    text += f"[{link_text}]({link_url})"
                elif element.name == 'img':
                    img_data = self.process_image(element)
                    if img_data:
                        # Check for duplicates before appending
                        if not any(d['img_url'] == img_data['img_url'] for d in img_urls):
                            img_urls.append(img_data)
                        text += f"![{img_data['alt_text']}]({img_data['img_url']})"
                elif element.name == 'code':
                    text += f"`{element.get_text(separator=' ').strip()}`"
                elif element.name == 'strong':
                    text += f"**{element.get_text(separator=' ').strip()}**"
                else:
                    text += element.get_text(separator=' ')
            else:
                text += str(element)
        return text.strip()

    def process_list(self, list_element, outbound_links):
        list_text = ""
        for li in list_element.find_all('li', recursive=False):
            li_text = ""
            for element in li.children:
                if hasattr(element, 'name'):
                    if element.name == 'a':
                        link_text, link_url = self.process_link(element, outbound_links)
                        li_text += f"[{link_text}]({link_url})"
                    elif element.name == 'code':
                        li_text += f"`{element.get_text(separator=' ').strip()}`"
                    elif element.name == 'strong':
                        li_text += f"**{element.get_text(separator=' ').strip()}**"
                    else:
                        li_text += element.get_text(separator=' ')
                else:
                    li_text += str(element)
            if li_text.strip():
                list_text += f"• {li_text.strip()}\n"
        return list_text

    def process_code_block(self, pre_element):
        code_element = pre_element.find('code')
        code_text = code_element.get_text() if code_element else pre_element.get_text()
        return f"```\n{code_text}\n```"

    def process_table(self, table_element, outbound_links):
        table_text = ""
        rows = table_element.find_all('tr')
        if not rows:
            return ""

        header_row = rows[0]
        headers = [self.process_link_in_element(th, outbound_links) for th in header_row.find_all(['th', 'td'])]
        table_text += "| " + " | ".join(headers) + " |\n"
        table_text += "| " + " | ".join(["---"] * len(headers)) + " |\n"

        for row in rows[1:]:
            cells = [self.process_link_in_element(td, outbound_links) for td in row.find_all(['td', 'th'])]
            if cells:
                table_text += "| " + " | ".join(cells) + " |\n"
        return table_text

    def process_link_in_element(self, element, outbound_links):
        text = ""
        for child in element.children:
            if hasattr(child, 'name') and child.name == 'a':
                link_text, link_url = self.process_link(child, outbound_links)
                text += f"[{link_text}]({link_url})"
            elif hasattr(child, 'name') and child.name == 'code':
                text += f"`{child.get_text(separator=' ').strip()}`"
            else:
                text += child.get_text(separator=' ').strip()
        return text.strip()

    def process_figure(self, figure_element, img_urls, outbound_links):
        figure_text = ""
        img = figure_element.find('img')
        if img:
            img_data = self.process_image(img)
            if img_data:
                if not any(d['img_url'] == img_data['img_url'] for d in img_urls):
                    img_urls.append(img_data)
                figure_text += f"![{img_data.get('alt_text', '')}]({img_data.get('img_url', '')})\n"

        figcaption = figure_element.find('figcaption')
        if figcaption:
            caption_text = self.process_link_in_element(figcaption, outbound_links)
            if caption_text.strip():
                figure_text += f"*{caption_text}*\n"
        return figure_text

    def process_image(self, img_element):
        src = img_element.get('data-src') or img_element.get('src')
        if not src or (img_element.get('width') == '1' and img_element.get('height') == '1'):
            return {}
        return {"img_url": urljoin(self.BASE_URL, src), "alt_text": img_element.get('alt', 'image')}

    def process_link(self, a_element, outbound_links):
        link_text = a_element.get_text(separator=' ').strip()
        link_url = a_element.get('href', '').strip()
        if not link_url:
            return link_text, ""
        
        absolute_url = urljoin(self.BASE_URL, link_url)

        # Update all_links list for deduplication
        if absolute_url not in self.all_links:
            self.all_links.append(absolute_url)

        if not absolute_url.startswith(self.BASE_URL):
            # Check for duplicates before appending to outbound_links
            if absolute_url not in outbound_links:
                outbound_links.append(absolute_url)
        
        return link_text, absolute_url

    def parse_post(self, webpage_url):
        """Extract title, date, text, images, and outbound links from a Palo Alto Networks blog post"""
        html = self.fetch_page(webpage_url)
        if not html:
            return None

        soup = BeautifulSoup(html, 'html.parser')

        # Reset all_links for each new page
        self.all_links = []

        # Extract title
        title_element = soup.find('h1', class_='title')
        title = title_element.get_text(strip=True) if title_element else "No Title"

        # Extract and format publication date
        date_published = None
        date_element = soup.find('div', class_='published-date')
        if date_element:
            original_date_str = date_element.get_text(strip=True)
            try:
                dt_object = datetime.strptime(original_date_str, '%b %d, %Y')
                date_published = dt_object.strftime("%Y-%m-%d")
            except ValueError:
                date_published = original_date_str

        eastern = pytz.timezone('US/Eastern')
        date_pulled = datetime.now(eastern).date().isoformat()

        # Find the main article section
        article_section = soup.find('section', class_='article')

        # Process text content and get images from within that section
        text_content, img_urls, outbound_links = self.process_text_content(soup)
        
        # Fallback to catch images that might not be in a figure or paragraph
        if article_section:
            for img in article_section.find_all('img'):
                img_data = self.process_image(img)
                if img_data and not any(d['img_url'] == img_data['img_url'] for d in img_urls):
                    img_urls.append(img_data)

        post_data = {
            "company": self.DOMAIN,
            "title": title,
            "date_published": date_published,
            "webpage_url": webpage_url,
            "date_pulled": date_pulled,
            "text_content": text_content,
            "img_urls": img_urls,
            "outbound_links": outbound_links,
        }
        return post_data

    def scrape_all_posts(self):
        """Convenience method to get links and parse all posts"""
        post_urls = self.get_latest_post_links()
        posts_data = []
        for url in post_urls:
            logger.info(f"Parsing post: {url}")
            post_data = self.parse_post(url)
            if post_data:
                posts_data.append(post_data)
            time.sleep(self.DELAY_BETWEEN_REQUESTS) 
        return posts_data