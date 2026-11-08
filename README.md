# 🥊 One Punch Man Manga Downloader

<p align="center">
  <a href="https://github.com/MEhe132/one-punch-man-manga-downloader"><img src="https://img.shields.io/badge/Python-3.9%2B-blue?style=flat-square&logo=python" alt="Python 3.9+" /></a>
  <a href="https://github.com/MEhe132/one-punch-man-manga-downloader"><img src="https://img.shields.io/badge/Dependencies-Requests%20%7C%20BS4%20%7C%20tqdm-orange?style=flat-square" alt="Dependencies" /></a>
  <a href="https://github.com/MEhe132/one-punch-man-manga-downloader"><img src="https://img.shields.io/badge/License-MIT-green.svg?style=flat-square" alt="License: MIT" /></a>
  <a href="https://github.com/MEhe132/one-punch-man-manga-downloader"><img src="https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat-square" alt="PRs Welcome" /></a>
</p>

A fast, multithreaded Python web scraper and manga downloader designed to scrape and download One Punch Man chapters in organized, chapter-wise folders with interactive progress bars.

---

## 🚀 Key Features

- **⚡ Multithreaded Image Downloads**: Utilizes Python's `concurrent.futures.ThreadPoolExecutor` for concurrent page downloads, drastically cutting down total download time.
- **📊 Dual Interactive Progress Bars**: Real-time visual progress tracking powered by `tqdm` for both total chapter queue and individual page downloads.
- **🎯 Flexible Targeting & CLI Flags**:
  - Download a single chapter by number (`-c 5` or `--chapter 5`).
  - Download a chapter range (`-r 1-10` or `--range 5..15`).
  - Target a direct chapter URL (`--chapter-url <URL>`).
  - Adjust worker threads (`-w 8`) and output directory (`-o "Collection"`).
- **🛡️ Rate-Limit & HTTP 429 Handling**: Exponential backoff retry engine for rate limits and intermittent network drops.
- **🔄 Smart Resuming & Duplicate Check**: Automatically skips already downloaded, non-empty image files.
- **📁 Cross-Platform Path Sanitization**: Strips illegal file/folder characters (`:`, `?`, `*`, `|`, `"`) so it runs cleanly across Windows, Linux, and macOS.
- **📑 Chapter Catalog Export**: Generates an indexed offline HTML catalog (`chapters_list.html`) with direct links to all chapters.
- **🛑 Clean Cancellation**: Handles `Ctrl+C` (`KeyboardInterrupt`) gracefully without leaving corrupt or partial image files.

---

## 📁 Project Structure

```text
one-punch-man-manga-downloader/
├── downloader.py          # Core downloader engine, client & CLI parser
├── main.py                # Command-line entry point
├── requirements.txt       # Dependencies (requests, beautifulsoup4, tqdm)
├── LICENSE                # MIT License
├── .gitignore             # Git ignore rules for venv, cache, and downloaded media
└── README.md              # Project documentation
```

---

## 🛠️ Setup & Installation

### 1. Clone the Repository
```bash
git clone https://github.com/MEhe132/one-punch-man-manga-downloader.git
cd one-punch-man-manga-downloader
```

### 2. Create and Activate a Virtual Environment (`venv`)

**On Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**On Windows (Command Prompt):**
```cmd
python -m venv venv
.\venv\Scripts\activate.bat
```

**On macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

---

## 📖 Usage & CLI Examples

### Download a Single Chapter
```bash
python main.py -c 5
# or
python main.py --chapter 211
```

### Download a Range of Chapters
```bash
python main.py -r 1-10
# or with double-dot syntax:
python main.py --range 5..15
```

### Download All Chapters
```bash
python main.py
```

### Download with Custom Thread Count & Rate-Limit Delay
```bash
# 8 concurrent download threads, with 1 second delay between chapters
python main.py -r 1-5 -w 8 --delay 1.0
```

### Download a Specific Chapter Directly by URL
```bash
python main.py --chapter-url "https://readonepunch-man.com/one-punch-man-chapter-211/"
```

### Specify a Custom Output Directory
```bash
python main.py -r 1-5 -o "Manga Collection"
```

### View All CLI Options
```bash
python main.py --help
```

---

## ⚙️ CLI Reference Table

| Flag | Short | Default | Description |
| :--- | :---: | :---: | :--- |
| `--chapter` | `-c` | `None` | Download a single chapter by its number (e.g. `-c 15`) |
| `--range` | `-r` | `None` | Download a range of chapters (e.g. `-r 1-10` or `5..15`) |
| `--start` | | `None` | Start chapter index |
| `--end` | | `None` | End chapter index |
| `--workers` | `-w` | `5` | Concurrent download threads per chapter |
| `--output` | `-o` | `'Manga Images'` | Target directory for saving downloaded chapters |
| `--delay` | | `0.0` | Politeness delay (in seconds) between chapter queries |
| `--timeout` | | `25` | Network request timeout in seconds |
| `--chapter-url` | | `None` | Download directly from a specific chapter page URL |
| `--url` | | *Default catalog URL* | Base URL for chapters list |

---

## 📜 Dependencies

- [Requests](https://requests.readthedocs.io/) - HTTP connection pooling and session management.
- [Beautiful Soup 4](https://www.crummy.com/software/BeautifulSoup/bs4/doc/) - HTML DOM parsing and link extraction.
- [tqdm](https://tqdm.github.io/) - Real-time progress bars for chapter queues and page downloads.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE) - see the [LICENSE](LICENSE) file for details.

---

## ⚠️ Disclaimer

This project is created strictly for educational, personal archival, and research purposes. Please respect manga publishers, scanlation groups, and authors by supporting the official releases.
