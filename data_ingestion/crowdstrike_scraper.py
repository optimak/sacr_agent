"""
CrowdStrike Web Scraper

This script provides a web scraper for the CrowdStrike blog, designed to
extract metadata, text content, image URLs, and outbound links from a
series of recent blog posts.
"""

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

class CrowdStrikeScraper:
    BASE_URL = "https://www.crowdstrike.com"
    BLOG_URL = "https://www.crowdstrike.com/en-us/blog/recent-articles/"
    MAX_POSTS = 5
    DOMAIN = "CrowdStrike"

    def __init__(self, config=None):
        self.session = requests.Session()
        if config:
            self.MAX_POSTS = config.get('max_posts', 5)
            self.REQUEST_TIMEOUT = config.get('request_timeout', 10)
            self.DELAY_BETWEEN_REQUESTS = config.get('delay_between_requests', 1)
        else:
            self.MAX_POSTS = 5
            self.REQUEST_TIMEOUT = 10
            self.DELAY_BETWEEN_REQUESTS = 1
        self.session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})

    def fetch_page(self, url):
        """Fetches the HTML content of a given URL."""
        try:
            resp = self.session.get(url, timeout=self.REQUEST_TIMEOUT)
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return None

    def get_latest_post_links(self):
        """Scrapes the blog homepage for the latest 5 post URLs."""
        html = self.fetch_page(self.BLOG_URL)
        if not html:
            return []

        soup = BeautifulSoup(html, 'html.parser')
        blog_links = []

        blog_section = soup.find('div', id='blogAutoGenerationDiv')
        if blog_section:
            articles = blog_section.find_all('div', class_='col-12 col-lg-4 post_image')
            for article in articles[:self.MAX_POSTS]:
                link_tag = article.find('a', href=True)
                if link_tag and link_tag.get('href'):
                    href = urljoin(self.BASE_URL, link_tag['href'])
                    blog_links.append(href)
                    logger.info(f"Found recent post: {href}")

        logger.info(f"Found {len(blog_links)} latest posts")
        return blog_links

    def process_text_content(self, soup):
        """
        Processes the main content, returning a list of strings. Each string
        represents a section of the article, delimited by <h2> headings.

        Args:
            soup (BeautifulSoup): The BeautifulSoup object to process.

        Returns:
            tuple: A tuple containing a list of text sections (list),
                  a list of all image URLs (list), and a list of all outbound links (list).
        """
        text_sections = []
        img_urls = []
        outbound_links = []
        current_section = ""

        # Find the main content container
        content_div = soup.find('div', class_='container-wp aem-GridColumn aem-GridColumn--default--12')
        if not content_div:
            return [], [], []

        # Find all relevant elements in the correct order
        relevant_elements = content_div.find_all(['h2', 'p', 'ul', 'ol', 'img', 'figure', 'pre', 'table'])

        for element in relevant_elements:
            if element.name == 'h2':
                # Start a new section with a heading
                if current_section:
                    text_sections.append(current_section.strip())
                current_section = f"## {element.get_text(strip=True)}\n\n"
            elif element.name == 'p':
                # Append a new paragraph to the current section
                current_section += self.process_paragraph(element, img_urls, outbound_links) + "\n\n"
            elif element.name in ['ul', 'ol']:
                # Append a list to the current section
                current_section += self.process_list(element, outbound_links) + "\n"
            elif element.name == 'img':
                # Process an image and add its Markdown to the current section
                img_data = self.process_image(element)
                if img_data:
                    # Add to master list if not already present
                    if not any(d['img_url'] == img_data['img_url'] for d in img_urls):
                        img_urls.append(img_data)
                    current_section += f"![{img_data.get('alt_text', '')}]({img_data.get('img_url', '')})\n"
            elif element.name == 'figure':
                # Process a figure which may contain an image and a caption
                current_section += self.process_figure(element, img_urls, outbound_links)
            elif element.name == 'pre':
                # Process a code block
                current_section += self.process_code_block(element) + "\n"
            elif element.name == 'table':
                # Process a table
                current_section += self.process_table(element, outbound_links)

        # Add the last section
        if current_section:
            text_sections.append(current_section.strip())

        return text_sections, img_urls, outbound_links

    def process_paragraph(self, p_element, img_urls, outbound_links):
        """Processes a paragraph element, including nested links and images."""
        text = ""
        for element in p_element.children:
            if hasattr(element, 'name'):
                if element.name == 'a':
                    link_text, link_url = self.process_link(element, outbound_links)
                    text += f"[{link_text}]({link_url})"
                elif element.name == 'img':
                    img_data = self.process_image(element)
                    if img_data:
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
        """Processes an ordered or unordered list."""
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
        """Processes a preformatted code block."""
        code_element = pre_element.find('code')
        code_text = code_element.get_text() if code_element else pre_element.get_text()
        return f"```\n{code_text}\n```"

    def process_table(self, table_element, outbound_links):
        """Processes an HTML table and converts it to Markdown."""
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
        """Processes a link within a parent element."""
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
        """Processes a figure element containing an image and a caption."""
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
        """Extracts image URL and alt text."""
        src = img_element.get('data-src') or img_element.get('src')
        if not src or (img_element.get('width') == '1' and img_element.get('height') == '1'):
            return {}
        return {"img_url": urljoin(self.BASE_URL, src), "alt_text": img_element.get('alt', 'image')}

    def process_link(self, a_element, outbound_links):
        """Extracts link text and URL, handling absolute and relative paths."""
        link_text = a_element.get_text(separator=' ').strip()
        link_url = a_element.get('href', '').strip()
        if not link_url:
            return link_text, ""

        absolute_url = urljoin(self.BASE_URL, link_url)

        if not absolute_url.startswith(self.BASE_URL):
            if absolute_url not in outbound_links:
                outbound_links.append(absolute_url)

        return link_text, absolute_url

    def parse_post(self, webpage_url):
        """Extracts title, date, text, images, and outbound links from a single blog post."""
        html = self.fetch_page(webpage_url)
        if not html:
            return None

        soup = BeautifulSoup(html, 'html.parser')

        # Extract title from the specified div
        title_element = soup.find('div', class_='headline aem-GridColumn aem-GridColumn--default--12')
        title = title_element.find('h1').get_text(strip=True) if title_element and title_element.find('h1') else "No Title"

        # Extract date from the specified div
        date_published = None
        date_element = soup.find('div', class_='publish_info')
        if date_element and date_element.find('p'):
            original_date_str = date_element.find('p').get_text(strip=True)
            try:
                dt_object = datetime.strptime(original_date_str, '%B %d, %Y')
                date_published = dt_object.strftime("%Y-%m-%d")
            except ValueError:
                date_published = original_date_str

        eastern = pytz.timezone('US/Eastern')
        date_pulled = datetime.now(eastern).date().isoformat()

        # Process the main content div
        text_content, img_urls, outbound_links = self.process_text_content(soup)

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
        """Convenience method to get links and parse all posts."""
        post_urls = self.get_latest_post_links()
        posts_data = []
        for url in post_urls:
            logger.info(f"Parsing post: {url}")
            post_data = self.parse_post(url)
            if post_data:
                posts_data.append(post_data)
            time.sleep(self.DELAY_BETWEEN_REQUESTS)
        return posts_data