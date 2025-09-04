import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime
import pytz
import logging

# Configure logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class MandiantScraper:
    BASE_URL = "https://www.mandiant.com"
    BLOG_URL = "https://www.mandiant.com/resources/blog"
    DOMAIN = "Google"

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
        try:
            resp = self.session.get(url, timeout=self.REQUEST_TIMEOUT)
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return None

    def get_latest_post_links(self):
        """Scrape homepage for latest post URLs"""
        html = self.fetch_page(self.BLOG_URL)
        if not html:
            return []

        soup = BeautifulSoup(html, 'html.parser')
        blog_links = []

        # Get featured article link
        featured_div = soup.find('div', class_='PcC8Zd nRhiJb-kR0ZEf-OWXEXe-GV1x9e-II5mzb nRhiJb-kR0ZEf-OWXEXe-GV1x9e-wNfPc-V2iZpe nRhiJb-snVHke-ibL1re-X66g3b nRhiJb-snVHke-R6PoUb-V2iZpe nRhiJb-kR0ZEf-OWXEXe-fW01td-AipIyc')
        if featured_div:
            featured_link = featured_div.find('a', href=True)
            if featured_link:
                blog_links.append(featured_link['href'])
                logger.info(f"Found featured article: {featured_link['href']}")

        # Get regular article links from the specified div
        regular_articles_div = soup.find('div', class_='MvKdV nRhiJb-DbgRPb-II5mzb-cGMI2b')
        if regular_articles_div:
            article_links = regular_articles_div.find_all('a', href=True, limit=4)
            for link in article_links:
                if len(blog_links) < self.MAX_POSTS:
                    blog_links.append(link['href'])
                    logger.info(f"Found regular article: {link['href']}")

        logger.info(f"Found {len(blog_links)} latest posts")
        return blog_links

    def process_text_content(self, soup):
        """Process text content from the article, organizing by H3 sections"""
        text_sections = []
        img_urls = []
        outbound_links = []
        processed_content = set()  # Track processed content for deduplication

        # Find the main content container
        main_content = soup.find('div', class_='OYL9D nRhiJb-kR0ZEf-OWXEXe-GV1x9e-OiUrBf')
        if not main_content:
            # Fallback to finding content sections directly
            all_sections = soup.find_all(['section'])
        else:
            # Get all direct child sections from main content container
            all_sections = main_content.find_all(['section'], recursive=False)

        # Let's specifically look for QzPuud sections anywhere in the document
        qzpuud_sections = soup.find_all('section', class_='QzPuud')

        # Filter to content sections (skip author section which is typically first)
        content_sections = []
        for section in all_sections:
            # Look for sections that contain substantial content
            has_content = section.find(['h2', 'h3', 'h4', 'p', 'figure', 'table', 'ul', 'ol'])
            section_classes = section.get('class', [])

            if (has_content and
                (not section_classes or
                 any(cls in section_classes for cls in ['Wy08Ac', 'QzPuud']) or
                 'QzPuud' in str(section_classes))):
                content_sections.append(section)

        # Skip the first section if it looks like an author section
        if content_sections and content_sections[0].find('p') and 'written by' in content_sections[0].get_text().lower()[:100]:
            content_sections = content_sections[1:]

        # TEMPORARY FIX: If we found QzPuud sections but they're not in content_sections, add them
        if qzpuud_sections and not any('QzPuud' in str(s.get('class', [])) for s in content_sections):
            content_sections.extend(qzpuud_sections)

        section_text = ""

        for section in content_sections:
            section_copy = section.__copy__()

            # Process all content elements in document order
            elements = section_copy.find_all(['h2', 'h3', 'h4', 'p', 'ul', 'ol', 'pre', 'code', 'table', 'figure'], recursive=True)

            for element in elements:
                # Skip if this element is inside a figure that we'll process separately
                if element.find_parent('figure') and element.name != 'figure':
                    continue

                if element.name in ['h2', 'h3']:
                    # If we have accumulated text, save the current section
                    if section_text.strip():
                        text_sections.append(section_text.strip())

                    # Start new section with heading
                    heading_text = element.get_text(separator=' ').strip()
                    if heading_text not in processed_content:
                        processed_content.add(heading_text)
                        section_text = f"## {heading_text}\n"
                    else:
                        section_text = ""

                elif element.name == 'h4':
                    heading_text = element.get_text(separator=' ').strip()
                    if heading_text not in processed_content:
                        processed_content.add(heading_text)
                        section_text += f"**{heading_text}**\n"

                elif element.name == 'p':
                    paragraph_text = self.process_paragraph(element, img_urls, outbound_links)
                    if paragraph_text.strip() and paragraph_text not in processed_content:
                        processed_content.add(paragraph_text.strip())
                        section_text += f"{paragraph_text}\n"

                elif element.name in ['ul', 'ol']:
                    list_text = self.process_list(element, outbound_links)
                    if list_text.strip() and list_text not in processed_content:
                        processed_content.add(list_text.strip())
                        section_text += f"{list_text}\n"

                elif element.name == 'pre':
                    code_text = self.process_code_block(element)
                    if code_text.strip() and code_text not in processed_content:
                        processed_content.add(code_text.strip())
                        section_text += f"{code_text}\n"

                elif element.name == 'code' and element.parent.name != 'pre':
                    # Handle inline code
                    code_text = element.get_text(separator=' ').strip()
                    if code_text and f"`{code_text}`" not in processed_content:
                        processed_content.add(f"`{code_text}`")
                        section_text += f"`{code_text}`"

                elif element.name == 'table':
                    table_text = self.process_table(element, outbound_links)
                    if table_text.strip() and table_text not in processed_content:
                        processed_content.add(table_text.strip())
                        section_text += f"{table_text}\n"

                elif element.name == 'figure':
                    figure_text = self.process_figure(element, img_urls, outbound_links)
                    if figure_text.strip() and figure_text not in processed_content:
                        processed_content.add(figure_text.strip())
                        section_text += f"{figure_text}\n"

        # Add the final section if it has content
        if section_text.strip():
            text_sections.append(section_text.strip())

        return text_sections, img_urls, outbound_links

    def process_paragraph(self, p_element, img_urls, outbound_links):
        """Process a paragraph element, handling inline images and links"""
        text = ""

        for element in p_element.children:
            if hasattr(element, 'name'):
                if element.name == 'img':
                    # Process image
                    img_url = self.process_image(element)
                    if img_url:
                        img_urls.append({"img_url": img_url, "alt_text": element.get('alt', 'image')})
                        alt_text = element.get('alt', 'image')
                        text += f"![{alt_text}]({img_url})"

                elif element.name == 'a':
                    # Process link
                    link_text, link_url = self.process_link(element, outbound_links)
                    text += f"[{link_text}]({link_url})"

                elif element.name == 'strong':
                    text += f"**{element.get_text(separator=' ')}**"

                elif element.name == 'code':
                    text += f"`{element.get_text(separator=' ')}`"

                else:
                    text += element.get_text(separator=' ')
            else:
                # Text node
                text += str(element)

        return text.strip()

    def process_list(self, list_element, outbound_links):
        """Process ul/ol elements into bullet points"""
        list_text = ""

        for li in list_element.find_all('li', recursive=False):
            li_text = ""

            for element in li.children:
                if hasattr(element, 'name'):
                    if element.name == 'a':
                        link_text, link_url = self.process_link(element, outbound_links)
                        li_text += f"[{link_text}]({link_url})"
                    elif element.name == 'code':
                        li_text += f"`{element.get_text(separator=' ')}`"
                    elif element.name == 'strong':
                        li_text += f"**{element.get_text(separator=' ')}**"
                    else:
                        li_text += element.get_text(separator=' ')
                else:
                    li_text += str(element)

            if li_text.strip():
                list_text += f"• {li_text.strip()}\n"

        return list_text

    def process_code_block(self, pre_element):
        """Process pre/code blocks into markdown code blocks"""
        code_element = pre_element.find('code')
        if code_element:
            code_text = code_element.get_text()
        else:
            code_text = pre_element.get_text()

        return f"```\n{code_text}\n```"

    def process_table(self, table_element, outbound_links):
        """Process HTML table into markdown table format"""
        table_text = ""
        rows = table_element.find_all('tr')

        if not rows:
            return ""

        # Process header row
        header_row = rows[0]
        headers = []
        for th in header_row.find_all(['th', 'td']):
            header_text = ""
            for element in th.children:
                if hasattr(element, 'name'):
                    if element.name == 'a':
                        link_text, link_url = self.process_link(element, outbound_links)
                        header_text += f"[{link_text}]({link_url})"
                    else:
                        header_text += element.get_text(separator=' ')
                else:
                    header_text += str(element)
            headers.append(header_text.strip())

        if headers:
            table_text += "| " + " | ".join(headers) + " |\n"
            table_text += "|" + "|".join(["-" * (len(h) + 2) for h in headers]) + "|\n"

        # Process data rows
        for row in rows[1:]:
            cells = []
            for td in row.find_all(['td', 'th']):
                cell_text = ""
                for element in td.children:
                    if hasattr(element, 'name'):
                        if element.name == 'a':
                            link_text, link_url = self.process_link(element, outbound_links)
                            cell_text += f"[{link_text}]({link_url})"
                        elif element.name == 'code':
                            cell_text += f"`{element.get_text(separator=' ')}`"
                        else:
                            cell_text += element.get_text(separator=' ')
                    else:
                        cell_text += str(element)
                cells.append(cell_text.strip())

            if cells:
                table_text += "| " + " | ".join(cells) + " |\n"

        return table_text

    def process_figure(self, figure_element, img_urls, outbound_links):
        """Process figure elements containing images and captions"""
        figure_text = ""

        # Find images in the figure (avoid duplicates by checking the first one)
        img_tags = figure_element.find_all('img', class_=lambda x: x and 'JcsBte' in x)

        if img_tags:
            # Use only the first image to avoid duplicates from modal
            img = img_tags[0]
            img_url = self.process_image(img)
            if img_url and not any(item["img_url"] == img_url for item in img_urls):
                alt_text = img.get('alt', 'image')
                img_urls.append({"img_url": img_url, "alt_text": alt_text})
                figure_text += f"![{alt_text}]({img_url})\n"

        # Find caption
        caption_p = figure_element.find('p')
        if caption_p:
            caption_text = self.process_paragraph(caption_p, [], outbound_links)
            if caption_text.strip():
                figure_text += f"*{caption_text}*\n"

        return figure_text

    def process_image(self, img_element):
        """Process image element and return absolute URL"""
        img_src = img_element.get('src') or img_element.get('data-src')
        if img_src:
            return urljoin(self.BASE_URL, img_src)
        return None

    def process_link(self, a_element, outbound_links):
        """Process link element and categorize it"""
        link_text = a_element.get_text(separator=' ').strip()
        link_url = a_element.get('href', '')

        if link_url:
            # Convert to absolute URL
            absolute_url = urljoin(self.BASE_URL, link_url)

            # Check if it's an outbound link
            if not absolute_url.startswith('https://cloud.google.com'):
                outbound_links.append(absolute_url)

            return link_text, absolute_url

        return link_text, link_url

    def parse_post(self, webpage_url):
        """Extract title, date, text, images, and outbound links from a Mandiant blog post"""

        html = self.fetch_page(webpage_url)
        if not html:
            return None

        soup = BeautifulSoup(html, 'html.parser')

        # Extract title
        title_tag = soup.find('div', class_='Qwf2Db-MnozTc Qwf2Db-MnozTc-OWXEXe-MnozTc-ibL1re')
        title = "No Title"
        if title_tag:
            title_span = title_tag.find('span', class_='FewWi')
            if title_span and title_span.next_sibling:
                title = title_span.next_sibling.strip()
            else:
                title = title_tag.get_text(separator=' ').strip()

        # Extract date published
        date_published = None
        date_tag = soup.find('div', class_='nRhiJb-fmcmS-oXtfBe dEogG')
        if date_tag:
            date_text = date_tag.get_text(separator=' ').strip()
            try:
                # Convert "August 26, 2025" format to "2025-08-26"
                dt_object = datetime.strptime(date_text, "%B %d, %Y")
                date_published = dt_object.strftime("%Y-%m-%d")
            except ValueError:
                date_published = None

        # Get current date in Eastern timezone
        eastern = pytz.timezone('US/Eastern')
        date_pulled = datetime.now(eastern).date().isoformat()

        # Process text content
        text_content, img_urls, outbound_links = self.process_text_content(soup)

        # Extract images from specific class (fallback)
        img_divs = soup.find_all('div', class_='JcsBte mZzdH ZOnyjc')
        for img_div in img_divs:
            img_tags = img_div.find_all('img')
            for img in img_tags:
                img_url = self.process_image(img)
                if img_url and not any(item["img_url"] == img_url for item in img_urls):
                    alt_text = img.get('alt', 'image')
                    img_urls.append({"img_url": img_url, "alt_text": alt_text})

        post_data = {
            "company": self.DOMAIN,
            "title": title,
            "date_published": date_published,
            "webpage_url": webpage_url,
            "date_pulled": date_pulled,
            "text_content": text_content,
            "img_urls": img_urls,
            "outbound_links": outbound_links
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

        return posts_data