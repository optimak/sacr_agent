#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime
import pytz
import logging
import json

# Configure logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class OktaScraper:
    BASE_URL = "https://www.okta.com/blog/"
    DOMAIN = "Okta"
    NEWSROOM_URL_BASE = "https://www.okta.com/newsroom/articles/"

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

    def fetch_page(self, url):
        """Fetches page content and returns the final URL after redirects."""
        try:
            resp = self.session.get(url, timeout=self.REQUEST_TIMEOUT)
            resp.raise_for_status()
            return resp.text, resp.url
        except requests.RequestException as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return None, url

    def get_latest_post_links(self):
        """Scrape homepage for latest post URLs"""
        html, _ = self.fetch_page(self.BASE_URL)
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        links = []

        # Target blog and newsroom links
        selectors = [
            "h2.BlogTeaser__title a[href]",
            "a[href*='/blog/']",
            "a[href*='/newsroom/articles/']"
        ]

        for selector in selectors:
            for a_tag in soup.select(selector):
                href = a_tag.get("href")
                if href:
                    full_url = urljoin(self.BASE_URL, href)
                    if full_url not in links:
                        links.append(full_url)
                        if len(links) >= self.MAX_POSTS:
                            break
            if len(links) >= self.MAX_POSTS:
                break

        logger.info(f"Found {len(links)} latest posts")
        return links

    def _parse_newsroom_content(self, soup, webpage_url):
        """Helper to parse a newsroom article's content from a JSON-like data attribute."""
        text_content = []
        img_urls = []
        outbound_links = []

        content_div = soup.find("div", attrs={"data-cmp-data-layer": True, "class": "cmp-text"})
        if not content_div:
            return text_content, img_urls, outbound_links

        data_layer = content_div.get("data-cmp-data-layer")
        try:
            data = json.loads(data_layer)
            text_key = next((k for k in data.keys() if k.startswith("text-")), None)
            if not text_key:
                return text_content, img_urls, outbound_links
            
            html_text = data[text_key].get("xdm:text", "")
            content_soup = BeautifulSoup(html_text, "html.parser")

            all_elements = content_soup.find_all(['h3', 'p', 'ul', 'li', 'a', 'img', 'br'])
            current_section = ""
            for element in all_elements:
                if element.name in ['h3']:
                    if current_section.strip():
                        text_content.append(current_section.strip())
                    current_section = f"### {element.get_text(strip=True)}\n"
                elif element.name == 'p':
                    for a_tag in element.find_all('a', href=True):
                        href = a_tag.get('href')
                        if href and href.startswith('http') and 'okta.com' not in href:
                            if href not in outbound_links:
                                outbound_links.append(href)
                    current_section += element.get_text(strip=True, separator=' ') + " \n "
                elif element.name == 'ul':
                    list_items = []
                    for li in element.find_all('li'):
                        list_items.append(f"• {li.get_text(strip=True)}")
                    if list_items:
                        current_section += "\n".join(list_items) + "\n"
                elif element.name == 'img':
                    src = element.get('src')
                    alt = element.get('alt', '')
                    if src:
                        full_url = urljoin(webpage_url, src)
                        img_urls.append({"img_url": full_url, "alt_text": alt})
                        current_section += f"![{alt}]({full_url})\n"
                elif element.name == 'br':
                    current_section += "\n"
            if current_section.strip():
                text_content.append(current_section.strip())
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON content for newsroom article {webpage_url}: {e}")
        return text_content, img_urls, outbound_links

    def parse_newsroom_post(self, html, webpage_url):
        """Extracts data from a newsroom article's HTML."""
        soup = BeautifulSoup(html, "html.parser")
        title_tag = soup.find("h1", class_="cmp-hero__title")
        title = title_tag.get_text(strip=True) if title_tag else "No Title"
        date_published = None
        date_tag = soup.find("span", class_="cmp-hero__release-date__content")
        if date_tag:
            date_text = date_tag.get_text(strip=True)
            try:
                date_object = datetime.strptime(date_text, "%d %B %Y")
                date_published = date_object.date().isoformat()
            except Exception as e:
                logger.error(f"Could not parse newsroom date: {date_text}. Error: {e}")
                date_published = None
        
        text_content, img_urls, outbound_links = [], [], []

        article_content_div = soup.find("div", class_="container responsivegrid cmp-container--article-page-content")
        
        if article_content_div:
            content_div = article_content_div.find("div", attrs={"data-cmp-data-layer": True})
            
            if content_div:
                data_layer = content_div.get("data-cmp-data-layer")
                try:
                    data = json.loads(data_layer)
                    text_key = next((k for k in data.keys() if k.startswith("text-")), None)
                    if text_key:
                        html_text = data[text_key].get("xdm:text", "")
                        content_soup = BeautifulSoup(html_text, "html.parser")
                        
                        current_section = ""
                        elements = content_soup.find_all(['p', 'h3', 'ul', 'ol'])
                        
                        for element in elements:
                            processed_text = ""
                            # Check for a new section starting with h3
                            if element.name == 'h3':
                                if current_section.strip():
                                    text_content.append(current_section.strip())
                                current_section = f"### {element.get_text(strip=True)}\n\n"
                                continue  # Continue to the next element
                            
                            # Process links and images within the current element
                            for a_tag in element.find_all('a', href=True):
                                href = a_tag.get('href')
                                link_text = a_tag.get_text(strip=True)
                                if href:
                                    full_href = urljoin(webpage_url, href)
                                    a_tag.replace_with(f"[{link_text}]({full_href})")
                                    if 'okta.com' not in full_href and full_href.startswith('http'):
                                        if full_href not in outbound_links:
                                            outbound_links.append(full_href)

                            for img_tag in element.find_all('img'):
                                src = img_tag.get('src') or img_tag.get('data-src')
                                alt = img_tag.get('alt', '')
                                if src:
                                    full_url = urljoin(webpage_url, src)
                                    img_urls.append({"img_url": full_url, "alt_text": alt})
                                    img_tag.replace_with(f"![{alt}]({full_url})")

                            # Get the formatted text and append to current section
                            if element.name in ['ul', 'ol']:
                                list_items = [f"• {li.get_text(strip=True)}" for li in element.find_all('li')]
                                processed_text = "\n".join(list_items)
                            else: # p
                                processed_text = element.get_text(strip=True, separator=' ')

                            if processed_text:
                                current_section += processed_text.strip() + "\n\n"
                        
                        # Append the last section
                        if current_section.strip():
                            text_content.append(current_section.strip())
                            
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON content for newsroom article {webpage_url}: {e}")

        return self._create_post_data(title, date_published, webpage_url, text_content, img_urls, outbound_links)

    def parse_blog_post(self, html, webpage_url):
        """Extracts data from a blog post's HTML."""
        soup = BeautifulSoup(html, "html.parser")
        title_tag = soup.find("h1", class_="BlogFull__title")
        title = title_tag.get_text(strip=True) if title_tag else "No Title"
        date_published = None
        date_tag = soup.find("div", class_="Author__byline-right")
        if date_tag:
            date_text = date_tag.get_text(strip=True)
            try:
                date_object = datetime.strptime(date_text, "%B %d, %Y")
                date_published = date_object.date().isoformat()
            except Exception:
                date_published = None
        content_section = soup.find("div", class_="BlogFull__content")
        text_content, img_urls, outbound_links = [], [], []
        if content_section:
            current_section = ""
            elements = content_section.find_all(['h2', 'p', 'ul', 'ol', 'article'], recursive=True)
            for element in elements:
                if element.name == 'h2':
                    if current_section.strip():
                        text_content.append(current_section.strip())
                    heading_text = element.get_text(strip=True)
                    current_section = f"## {heading_text}\n"
                elif element.name in ['p', 'ul', 'ol']:
                    for a_tag in element.find_all('a', href=True):
                        href = a_tag.get('href')
                        if href.startswith('http') and 'okta.com' not in href:
                            if href not in outbound_links:
                                outbound_links.append(href)
                    element_copy = element.__copy__()
                    for img in element_copy.find_all('img'):
                        parent_article = img.find_parent('article')
                        if parent_article and 'media--type-image' in ' '.join(parent_article.get('class', [])):
                            src = img.get('src') or img.get('data-src')
                            alt = img.get('alt', '')
                            if src:
                                full_url = urljoin(webpage_url, src)
                                img_urls.append({"img_url": full_url, "alt_text": alt})
                                img.replace_with(f"![{alt} (image)]({full_url})")
                    for a_tag in element_copy.find_all('a', href=True):
                        href = a_tag.get('href')
                        link_text = a_tag.get_text(strip=True)
                        if href:
                            full_href = urljoin(webpage_url, href) if not href.startswith('http') else href
                            a_tag.replace_with(f"[{link_text}]({full_href})")
                    section_text = element_copy.get_text(separator=' ', strip=True)
                    if element.name in ['ul', 'ol']:
                        formatted_text = ""
                        for li in element.find_all('li'):
                            if li.get_text(strip=True):
                                formatted_text += f"• {li.get_text(strip=True)}\n"
                        section_text = formatted_text.strip()
                    if section_text:
                        current_section += section_text + " \n "
                elif element.name == 'article':
                    if 'media--type-image' in ' '.join(element.get('class', [])):
                        img_tag = element.find('img')
                        if img_tag:
                            src = img_tag.get('src') or img_tag.get('data-src')
                            alt = img_tag.get('alt', '')
                            if src:
                                full_url = urljoin(webpage_url, src)
                                img_urls.append({"img_url": full_url, "alt_text": alt})
                                current_section += f"![{alt} (image)]({full_url}) \n "
            if current_section.strip():
                text_content.append(current_section.strip())
            if not text_content and content_section.get_text(strip=True):
                text_content.append(content_section.get_text(strip=True, separator='\n'))
        return self._create_post_data(title, date_published, webpage_url, text_content, img_urls, outbound_links)

    def _create_post_data(self, title, date_published, webpage_url, text_content, img_urls, outbound_links):
        """Helper to create the final data dictionary."""
        eastern = pytz.timezone('US/Eastern')
        date_pulled = datetime.now(eastern).date().isoformat()
        return {
            "company": self.DOMAIN,
            "title": title,
            "date_published": date_published,
            "webpage_url": webpage_url,
            "date_pulled": date_pulled,
            "text_content": text_content,
            "img_urls": img_urls,
            "outbound_links": outbound_links,
        }

    def scrape_all_posts(self):
        """Convenience method to get links and parse all posts, handling redirects."""
        post_urls = self.get_latest_post_links()
        posts_data = []
        for url in post_urls:
            logger.info(f"Parsing post: {url}")
            html, final_url = self.fetch_page(url)
            if html:
                if self.NEWSROOM_URL_BASE in final_url:
                    post_data = self.parse_newsroom_post(html, final_url)
                else:
                    post_data = self.parse_blog_post(html, final_url)
                if post_data:
                    posts_data.append(post_data)
        return posts_data