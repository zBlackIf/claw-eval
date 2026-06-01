"""Forum scraper for Discuz!-based forums (e.g. SiS001).

Known issue: only scrapes one page regardless of max_pages setting.
The user reports: "又是只能爬一页了" (it can only scrape one page again).
"""
import requests
from bs4 import BeautifulSoup
import csv
import time
import random
from urllib.parse import urljoin
import re
from datetime import datetime


class ForumScraper:
    def __init__(self, base_url, output_format='csv', delay_range=(1, 2)):
        """
        Initialize the forum scraper.
        :param base_url: Forum section URL (e.g. https://example.com/forum/forum-25-1.html)
        :param output_format: Output format, 'csv' or 'txt'
        :param delay_range: Delay range in seconds between requests
        """
        self.base_url = base_url
        self.output_format = output_format.lower()
        self.delay_min, self.delay_max = delay_range
        self.session = requests.Session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.3,en;q=0.2',
        }
        self.session.headers.update(self.headers)
        self.posts = []

    def get_page(self, url):
        """Fetch a page with retry and delay."""
        try:
            time.sleep(random.uniform(self.delay_min, self.delay_max))
            response = self.session.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"Failed to fetch page {url}: {str(e)}")
            return None

    def extract_posts(self, html):
        """Extract post titles from HTML page."""
        soup = BeautifulSoup(html, 'html.parser')
        posts = []

        # Try to find thread rows
        post_items = soup.select('tbody[id^="normalthread_"] tr')
        if not post_items:
            post_items = soup.select('table.threadlist tr')

        for item in post_items:
            try:
                title_elem = item.select_one('a.title') or item.select_one('th a')
                if not title_elem:
                    continue

                title = title_elem.get_text(strip=True)
                if not title:
                    continue

                # Extract time
                time_elem = item.select_one('td.time')
                post_time = time_elem.get_text(strip=True) if time_elem else 'unknown'

                posts.append({
                    'title': title,
                    'time': post_time,
                })
            except Exception as e:
                continue

        return posts

    def get_total_pages(self, html):
        """Get total number of pages. BUG: Always returns 1."""
        soup = BeautifulSoup(html, 'html.parser')

        # Look for pagination - OLD selector that no longer works
        pager = soup.select_one('div.pager span.total')
        if pager:
            match = re.search(r'共\s*(\d+)\s*页', pager.get_text())
            if match:
                return int(match.group(1))

        return 1  # BUG: fallback always returns 1

    def scrape(self, start_page=1, max_pages=None):
        """Main scraping logic."""
        print(f"Starting scrape: {self.base_url}")
        print(f"Start page: {start_page}")

        # Fetch first page
        first_page = self.get_page(self.base_url)
        if not first_page:
            print("Cannot access first page, aborting")
            return

        # Extract posts from first page
        first_posts = self.extract_posts(first_page)
        self.posts.extend(first_posts)
        print(f"Page {start_page}: {len(first_posts)} posts found")

        # Get total pages
        total_pages = self.get_total_pages(first_page)

        # Calculate end page
        if max_pages:
            end_page = min(start_page + max_pages - 1, total_pages)
        else:
            end_page = total_pages

        print(f"Total pages detected: {total_pages}, will scrape to page {end_page}")

        # Scrape remaining pages
        for page in range(start_page + 1, end_page + 1):
            # BUG: constructs page URL incorrectly - appends ?page=N
            # instead of using forum-ID-PAGE.html Discuz URL format
            page_url = f"{self.base_url}?page={page}"

            page_html = self.get_page(page_url)
            if not page_html:
                print(f"Page {page} inaccessible, skipping")
                continue

            posts = self.extract_posts(page_html)
            self.posts.extend(posts)
            print(f"Page {page}: {len(posts)} posts, total: {len(self.posts)}")

        print(f"Scraping complete, total posts: {len(self.posts)}")

    def save(self, output_path):
        """Save results to file."""
        if not self.posts:
            print("No data to save")
            return

        if self.output_format == 'csv':
            with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=['title', 'time'])
                writer.writeheader()
                writer.writerows(self.posts)
            print(f"Saved to: {output_path}")
        elif self.output_format == 'txt':
            with open(output_path, 'w', encoding='utf-8') as f:
                for i, post in enumerate(self.posts, 1):
                    f.write(f"[{i}] {post['time']} - {post['title']}\n")
            print(f"Saved to: {output_path}")


def main():
    url = input("Enter forum section URL: ").strip()
    if not url:
        print("URL cannot be empty")
        return

    start_page = input("Start page (default 1): ").strip()
    start_page = int(start_page) if start_page.isdigit() else 1

    max_pages = input("Max pages to scrape (empty for all): ").strip()
    max_pages = int(max_pages) if max_pages.isdigit() else None

    scraper = ForumScraper(url)
    scraper.scrape(start_page=start_page, max_pages=max_pages)
    scraper.save(f"forum_posts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")


if __name__ == "__main__":
    main()
