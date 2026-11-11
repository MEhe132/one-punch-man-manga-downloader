"""
One Punch Man Manga Downloader
==============================
A fast, multithreaded manga downloader that scrapes and downloads
One Punch Man chapters sequentially or concurrently.

Features:
- Multithreaded image downloads with ThreadPoolExecutor
- Dual tqdm progress bars (Chapters progress + Per-page download progress)
- Flexible CLI arguments: --chapter (-c), --range (-r), --start, --end, --workers (-w)
- Automated Comic Book Archive (.cbz) packaging via --cbz flag
- Resumable: skips already downloaded, valid non-empty images
- Robust retry with exponential backoff & HTTP 429 rate-limit handling
- Sanitized filenames for Windows/Linux path safety
- Custom User-Agent and connection pooling via requests.Session
- Chapter catalog export (HTML)
"""

import os
import re
import sys
import time
import zipfile
import argparse
from typing import List, Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm


# Default Configuration
DEFAULT_URL = "https://readonepunch-man.com/one-punch-man-chapters-list/"
DEFAULT_OUTPUT_DIR = "Manga Images"
DEFAULT_WORKERS = 5
DEFAULT_TIMEOUT = 25
DEFAULT_RETRIES = 3

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


def parse_range_string(range_str: str) -> Tuple[int, int]:
    """
    Parse range strings like '1-10', '5..15', or '20:30' into (start, end).
    """
    m = re.match(r"^(\d+)\s*[-:.]{1,2}\s*(\d+)$", range_str.strip())
    if not m:
        raise argparse.ArgumentTypeError(
            f"Invalid range format '{range_str}'. Use format like '1-10' or '5..15'."
        )
    start, end = int(m.group(1)), int(m.group(2))
    if start > end:
        start, end = end, start
    return start, end


def create_cbz(chapter_folder: str) -> Optional[str]:
    """
    Compress downloaded chapter images into a Comic Book Zip (.cbz) file.
    .cbz is a standard format recognized by Tachiyomi, Mihon, CDisplayEx,
    and digital comic e-readers.
    """
    if not os.path.isdir(chapter_folder):
        return None

    cbz_path = f"{chapter_folder}.cbz"
    images = sorted([
        f for f in os.listdir(chapter_folder)
        if f.lower().endswith((".webp", ".jpg", ".jpeg", ".png"))
    ])
    if not images:
        return None

    with zipfile.ZipFile(cbz_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for img in images:
            img_path = os.path.join(chapter_folder, img)
            zf.write(img_path, arcname=img)

    return cbz_path


class MangaClient:
    """Handles HTTP requests with sessions, retries, exponential backoff, and headers."""

    def __init__(
        self,
        session: Optional[requests.Session] = None,
        timeout: int = DEFAULT_TIMEOUT,
        retries: int = DEFAULT_RETRIES,
    ):
        self.session = session or requests.Session()
        self.session.headers.update(HEADERS)
        self.timeout = timeout
        self.retries = retries

    def get_soup(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch URL and return a BeautifulSoup parsed object with retry backoff."""
        for attempt in range(1, self.retries + 1):
            try:
                response = self.session.get(url, timeout=self.timeout)
                if response.status_code == 200:
                    return BeautifulSoup(response.content, "html.parser")
                elif response.status_code == 429:
                    wait_time = attempt * 3
                    tqdm.write(f"  [!] Rate limited (429) on {url}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    tqdm.write(f"  [!] Failed to fetch {url} (Status: {response.status_code})")
                    break
            except requests.RequestException as exc:
                if attempt == self.retries:
                    tqdm.write(f"  [!] Network error fetching {url}: {exc}")
                time.sleep(attempt * 1.5)
        return None

    def download_image(self, img_url: str, save_path: str) -> bool:
        """Download and write an image to disk with atomic write and duplicate check."""
        # Skip if file already exists and is non-empty
        if os.path.isfile(save_path) and os.path.getsize(save_path) > 0:
            return True

        for attempt in range(1, self.retries + 1):
            try:
                resp = self.session.get(img_url, timeout=self.timeout)
                if resp.status_code == 200 and resp.content:
                    # Write to temporary file first to prevent partial corrupt files
                    temp_path = f"{save_path}.tmp"
                    with open(temp_path, "wb") as f:
                        f.write(resp.content)
                    os.replace(temp_path, save_path)
                    return True
                elif resp.status_code == 429:
                    time.sleep(attempt * 2)
            except requests.RequestException:
                time.sleep(attempt * 1.0)

        return False


class OnePunchManDownloader:
    """Manages chapter retrieval, folder structure, multithreaded downloads, and CBZ archives."""

    def __init__(
        self,
        base_url: str = DEFAULT_URL,
        output_dir: str = DEFAULT_OUTPUT_DIR,
        max_workers: int = DEFAULT_WORKERS,
        timeout: int = DEFAULT_TIMEOUT,
        delay_between_chapters: float = 0.0,
        export_cbz: bool = False,
    ):
        self.base_url = base_url
        self.output_dir = output_dir
        self.max_workers = max_workers
        self.delay_between_chapters = delay_between_chapters
        self.export_cbz = export_cbz
        self.client = MangaClient(timeout=timeout)

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
        """Save discovered chapters and links into an HTML file for reference."""
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
        and downloads all pages concurrently with an interactive progress bar.
        """
        os.makedirs(target_dir, exist_ok=True)
        soup = self.client.get_soup(chapter_url)
        if not soup:
            return 0

        # Locate image figures (standard WordPress manga pattern)
        figures = soup.find_all("figure", class_="wp-block-image size-full")
        if not figures:
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
            tqdm.write(f"  [!] No images found on {chapter_url}")
            return 0

        downloaded = 0
        total_pages = len(img_urls)

        # Download pages concurrently with dedicated progress bar
        with tqdm(total=total_pages, desc="    Pages", unit="pg", leave=False) as pbar:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_url = {}
                for idx, img_url in enumerate(img_urls, start=1):
                    ext = os.path.splitext(img_url.split("?")[0])[1] or ".webp"
                    file_name = f"page_{idx:03d}{ext}"
                    save_path = os.path.join(target_dir, file_name)

                    future = executor.submit(self.client.download_image, img_url, save_path)
                    future_to_url[future] = save_path

                for future in as_completed(future_to_url):
                    if future.result():
                        downloaded += 1
                    pbar.update(1)

        return downloaded

    def run(self, start_idx: Optional[int] = None, end_idx: Optional[int] = None):
        """Run the full download process across chapters."""
        chapters = self.get_chapters()
        if not chapters:
            print("[!] No chapters available to download.")
            return

        self.export_catalog(chapters)

        # Slice chapters if requested
        start = (start_idx - 1) if (start_idx and start_idx > 0) else 0
        end = end_idx if (end_idx and end_idx <= len(chapters)) else len(chapters)
        selected_chapters = chapters[start:end]

        print(f"[*] Downloading {len(selected_chapters)} chapters (from #{start+1} to #{end})...\n")

        for idx, ch in enumerate(tqdm(selected_chapters, desc="Chapters Progress", unit="ch"), start=start+1):
            chapter_name = sanitize_filename(ch["name"])
            chapter_folder = os.path.join(self.output_dir, f"{idx:03d}_{chapter_name}")

            try:
                tqdm.write(f"[+] Processing Chapter {idx}: {ch['name']}")
                count = self.download_chapter_images(ch["url"], chapter_folder)
                tqdm.write(f"    [+] Saved {count} pages into {chapter_folder}")

                if self.export_cbz:
                    cbz_path = create_cbz(chapter_folder)
                    if cbz_path:
                        tqdm.write(f"    [+] Created CBZ archive: {os.path.basename(cbz_path)}")

                tqdm.write("")

                if self.delay_between_chapters > 0:
                    time.sleep(self.delay_between_chapters)

            except KeyboardInterrupt:
                print("\n[!] Download interrupted by user. Exiting cleanly...")
                sys.exit(0)
            except Exception as e:
                tqdm.write(f"    [!] Error processing {ch['name']}: {e}\n")

        print("[+] All requested chapters processed successfully!")


def main():
    parser = argparse.ArgumentParser(
        description="One Punch Man Manga Downloader - fast, concurrent chapter downloads.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_URL,
        help="Main chapter list URL (default: One Punch Man chapters list)",
    )
    parser.add_argument(
        "--output", "-o",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory to save images (default: '{DEFAULT_OUTPUT_DIR}')",
    )
    parser.add_argument(
        "--workers", "-w",
        type=int,
        default=DEFAULT_WORKERS,
        help="Number of concurrent download threads per chapter (default: 5)",
    )
    parser.add_argument(
        "--chapter", "-c",
        type=int,
        default=None,
        help="Download a single chapter by its number (e.g., -c 5)",
    )
    parser.add_argument(
        "--range", "-r",
        type=str,
        default=None,
        help="Download a range of chapters (e.g., -r 1-10 or --range 5..15)",
    )
    parser.add_argument(
        "--start",
        type=int,
        default=None,
        help="Start chapter number (e.g., --start 1)",
    )
    parser.add_argument(
        "--end",
        type=int,
        default=None,
        help="End chapter number (e.g., --end 10)",
    )
    parser.add_argument(
        "--chapter-url",
        type=str,
        default=None,
        help="Download a single chapter directly by its full URL",
    )
    parser.add_argument(
        "--cbz",
        action="store_true",
        help="Automatically pack each downloaded chapter into a .cbz (Comic Book Zip) file for comic readers",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.0,
        help="Delay in seconds between chapter requests (default: 0.0)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"Network request timeout in seconds (default: {DEFAULT_TIMEOUT})",
    )

    args = parser.parse_args()

    # Determine start and end index
    start_idx = args.start
    end_idx = args.end

    if args.chapter is not None:
        start_idx = args.chapter
        end_idx = args.chapter
    elif args.range:
        start_idx, end_idx = parse_range_string(args.range)

    downloader = OnePunchManDownloader(
        base_url=args.url,
        output_dir=args.output,
        max_workers=args.workers,
        timeout=args.timeout,
        delay_between_chapters=args.delay,
        export_cbz=args.cbz,
    )

    if args.chapter_url:
        folder_name = sanitize_filename(args.chapter_url.rstrip("/").split("/")[-1])
        target_dir = os.path.join(args.output, folder_name)
        print(f"[*] Downloading single chapter from {args.chapter_url} to {target_dir}")
        count = downloader.download_chapter_images(args.chapter_url, target_dir)
        print(f"[+] Downloaded/verified {count} images in '{target_dir}'.")
        if args.cbz:
            cbz_path = create_cbz(target_dir)
            if cbz_path:
                print(f"[+] Created CBZ archive: {cbz_path}")
    else:
        downloader.run(start_idx=start_idx, end_idx=end_idx)


if __name__ == "__main__":
    main()
