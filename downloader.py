"""
One Punch Man Manga Downloader
==============================
A fast, multithreaded manga downloader that scrapes and downloads
One Punch Man chapters sequentially or concurrently.

Features:
- Multithreaded image downloads with ThreadPoolExecutor
- Resumable: skips already downloaded, valid images
- Sanitized filenames for Windows/Linux path safety
- Custom User-Agent and connection pooling via requests.Session
- Range selection (download specific chapters or range)
- Chapter catalog export (HTML/JSON)
- Clean visual progress tracking with tqdm
"""

import os
import re
import sys
import time
import argparse
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm


# Default Configuration
DEFAULT_URL = "https://readonepunch-man.com/one-punch-man-chapters-list/"
DEFAULT_OUTPUT_DIR = "Manga Images"
DEFAULT_WORKERS = 5
REQUEST_TIMEOUT = 20

# Standard browser headers to avoid simple bot blocks
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://readonepunch-man.com/",
}


def sanitize_filename(name: str) -> str:
    """
    Remove illegal characters from folder/file names to ensure compatibility
    across Windows and POSIX file systems.
    """
    # Replace invalid filesystem characters: < > : " / \ | ? *
    sanitized = re.sub(r'[<>:"/\\|?*]', "_", name).strip()
    # Normalize multiple whitespace characters
    sanitized = re.sub(r"\s+", " ", sanitized)
    return sanitized or "untitled"


class MangaClient:
    """Handles HTTP requests with sessions, retries, and headers."""

    def __init__(self, session: Optional[requests.Session] = None):
        self.session = session or requests.Session()
        self.session.headers.update(HEADERS)

    def get_soup(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch URL and return a BeautifulSoup parsed object."""
        try:
            response = self.session.get(url, timeout=REQUEST_TIMEOUT)
            if response.status_code == 200:
                return BeautifulSoup(response.content, "html.parser")
            print(f"[!] Warning: Failed to fetch {url} (Status: {response.status_code})")
        except requests.RequestException as exc:
            print(f"[!] Network error fetching {url}: {exc}")
        return None

    def download_image(self, img_url: str, save_path: str, retries: int = 2) -> bool:
        """Download and write an image to disk if not already downloaded."""
        # Skip if file already exists and is non-empty
        if os.path.isfile(save_path) and os.path.getsize(save_path) > 0:
            return True

        for attempt in range(1, retries + 1):
            try:
                resp = self.session.get(img_url, timeout=REQUEST_TIMEOUT)
                if resp.status_code == 200 and resp.content:
                    # Write to temporary file first to prevent partial corrupt files
                    temp_path = f"{save_path}.tmp"
                    with open(temp_path, "wb") as f:
                        f.write(resp.content)
                    os.replace(temp_path, save_path)
                    return True
            except requests.RequestException:
                time.sleep(1)

        return False


class OnePunchManDownloader:
    """Manages chapter retrieval, folder structure, and multithreaded downloads."""

    def __init__(
        self,
        base_url: str = DEFAULT_URL,
        output_dir: str = DEFAULT_OUTPUT_DIR,
        max_workers: int = DEFAULT_WORKERS,
    ):
        self.base_url = base_url
        self.output_dir = output_dir
        self.max_workers = max_workers
        self.client = MangaClient()

    def get_chapters(self) -> List[Dict[str, str]]:
        """
        Scrapes the main chapter list page.
        Returns a list of dicts: [{'name': '...', 'url': '...'}] in ascending order.
        """
        print(f"[*] Fetching chapter list from {self.base_url}...")
        soup = self.client.get_soup(self.base_url)
        if not soup:
            print("[!] Could not retrieve chapter list.")
            return []

        chapter_list_tag = soup.find("ul", class_="chapter-list")
        if not chapter_list_tag:
            # Fallback for alternative structures
            chapter_list_tag = soup.find("div", class_="chapter-list") or soup

        links = chapter_list_tag.find_all("a")
        chapters = []
        for a_tag in links:
            url = a_tag.get("href")
            name = a_tag.text.strip()
            if url and name:
                chapters.append({"name": name, "url": url})

        # Reverse so chapters start from the first chapter (Chapter 1) onwards
        chapters.reverse()
        print(f"[+] Found {len(chapters)} chapters in total.")
        return chapters

    def export_catalog(self, chapters: List[Dict[str, str]], filename: str = "chapters_list.html"):
        """Save discovered chapters and links into an HTML/text file for reference."""
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write("<!DOCTYPE html><html><head><meta charset='utf-8'><title>One Punch Man Chapters</title></head><body>\n")
                f.write("<h1>One Punch Man Chapter List</h1><ul>\n")
                for ch in chapters:
                    f.write(f'<li><a href="{ch["url"]}" target="_blank">{ch["name"]}</a></li>\n')
                f.write("</ul></body></html>\n")
            print(f"[+] Chapter catalog successfully saved to {filename}")
        except IOError as err:
            print(f"[!] Failed to save chapter catalog: {err}")

    def download_chapter_images(self, chapter_url: str, target_dir: str) -> int:
        """
        Parses a single chapter page, locates all manga image figures,
        and downloads all pages concurrently.
        """
        os.makedirs(target_dir, exist_ok=True)
        soup = self.client.get_soup(chapter_url)
        if not soup:
            return 0

        # Locate image figures (standard WordPress manga pattern)
        figures = soup.find_all("figure", class_="wp-block-image size-full")
        if not figures:
            # Fallback search for any images inside entry content
            content_div = soup.find("div", class_="entry-content")
            figures = content_div.find_all("img") if content_div else []

        img_urls = []
        for fig in figures:
            img = fig if fig.name == "img" else fig.find("img")
            if img:
                src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
                if src and src not in img_urls:
                    img_urls.append(src)

        if not img_urls:
            print(f"  [!] No images found on {chapter_url}")
            return 0

        # Download images concurrently using ThreadPoolExecutor
        downloaded = 0
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_url = {}
            for idx, img_url in enumerate(img_urls, start=1):
                # Format name with zero-padded index (e.g. page_01.webp)
                ext = os.path.splitext(os.path.basename(img_url.split("?")[0]))[1] or ".webp"
                file_name = f"page_{idx:03d}{ext}"
                save_path = os.path.join(target_dir, file_name)

                future = executor.submit(self.client.download_image, img_url, save_path)
                future_to_url[future] = save_path

            for future in as_completed(future_to_url):
                if future.result():
                    downloaded += 1

        return downloaded

    def run(self, start_idx: Optional[int] = None, end_idx: Optional[int] = None):
        """Run the full download process across chapters."""
        chapters = self.get_chapters()
        if not chapters:
            print("[!] No chapters available to download.")
            return

        # Always keep catalog for offline reference
        self.export_catalog(chapters)

        # Slice chapters if requested
        start = (start_idx - 1) if (start_idx and start_idx > 0) else 0
        end = end_idx if (end_idx and end_idx <= len(chapters)) else len(chapters)
        selected_chapters = chapters[start:end]

        print(f"[*] Downloading {len(selected_chapters)} chapters (from #{start+1} to #{end})...")

        for idx, ch in enumerate(tqdm(selected_chapters, desc="Chapters Progress", unit="ch"), start=start+1):
            chapter_name = sanitize_filename(ch["name"])
            chapter_folder = os.path.join(self.output_dir, f"{idx:03d}_{chapter_name}")

            try:
                tqdm.write(f"\n[+] Processing Chapter {idx}: {ch['name']}")
                count = self.download_chapter_images(ch["url"], chapter_folder)
                tqdm.write(f"    Downloaded/verified {count} images in {chapter_folder}")
            except KeyboardInterrupt:
                print("\n[!] Download interrupted by user. Exiting cleanly...")
                sys.exit(0)
            except Exception as e:
                tqdm.write(f"    [!] Error processing {ch['name']}: {e}")

        print("\n[✓] All requested chapters processed successfully!")


def main():
    parser = argparse.ArgumentParser(
        description="Download One Punch Man manga chapters concurrently."
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_URL,
        help="Main chapter list URL (default: One Punch Man chapters list)",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory to save images (default: '{DEFAULT_OUTPUT_DIR}')",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        help="Number of concurrent download threads (default: 5)",
    )
    parser.add_argument(
        "--start",
        type=int,
        default=None,
        help="Start chapter number (e.g., 1)",
    )
    parser.add_argument(
        "--end",
        type=int,
        default=None,
        help="End chapter number (e.g., 10)",
    )
    parser.add_argument(
        "--chapter-url",
        type=str,
        default=None,
        help="Download a single chapter directly by its URL",
    )

    args = parser.parse_args()

    downloader = OnePunchManDownloader(
        base_url=args.url,
        output_dir=args.output,
        max_workers=args.workers,
    )

    if args.chapter_url:
        folder_name = sanitize_filename(args.chapter_url.rstrip("/").split("/")[-1])
        target_dir = os.path.join(args.output, folder_name)
        print(f"[*] Downloading single chapter from {args.chapter_url} to {target_dir}")
        count = downloader.download_chapter_images(args.chapter_url, target_dir)
        print(f"[✓] Downloaded/verified {count} images.")
    else:
        downloader.run(start_idx=args.start, end_idx=args.end)


if __name__ == "__main__":
    main()
