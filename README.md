# 🥊 One Punch Man Manga Downloader

A fast, multithreaded Python web scraper and manga downloader designed to scrape and download One Punch Man chapters in organized, chapter-wise folders.

---

## 🚀 Features

- **⚡ Multithreaded Image Downloads**: Utilizes Python's `concurrent.futures.ThreadPoolExecutor` for concurrent page downloads, drastically cutting down total download time.
- **🔄 Smart Resuming & Duplicate Check**: Checks if image files already exist and are non-empty before downloading, avoiding redundant network requests.
- **🛡️ Cross-Platform Path Sanitization**: Automatically strips or replaces illegal file/folder characters (such as `:`, `?`, `*`, `|`) so it functions smoothly on both Windows and Linux.
- **🌐 Connection Reuse & Realistic Headers**: Uses `requests.Session` with custom browser User-Agent headers to ensure reliable connections and avoid simple bot blocks.
- **🎯 Flexible Chapter Range & Targeting**: Download all chapters, specify a range (e.g. chapters 1 to 10), or download a specific single chapter by URL.
- **📊 Interactive Progress Bars**: Real-time progress updates powered by `tqdm`.
- **📑 Chapter Catalog Export**: Automatically exports an indexed HTML list of chapters with clickable links.
- **🛑 Clean Cancellation**: Handles `KeyboardInterrupt` (`Ctrl+C`) gracefully without hanging threads or leaving corrupted image files.

---

## 📁 Project Structure

```text
2_One_punch_man_Manga_downloader/
├── downloader.py          # Core downloader engine and scraper
├── main.py                # Command-line entry point
├── requirements.txt       # Dependencies (requests, beautifulsoup4, tqdm)
├── .gitignore             # Git ignore rules for venv, cache, and media
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

## 📖 Usage

### Download All Chapters
```bash
python main.py
```

### Download a Range of Chapters (e.g., Chapters 1 to 10)
```bash
python main.py --start 1 --end 10
```

### Download with Custom Thread Count
```bash
python main.py --workers 8
```

### Download a Specific Chapter Directly
```bash
python main.py --chapter-url "https://readonepunch-man.com/one-punch-man-chapter-211/"
```

### Specify a Custom Output Directory
```bash
python main.py --output "My Manga Collection"
```

### View All CLI Options
```bash
python main.py --help
```

---

## 📜 Dependencies

- [Requests](https://requests.readthedocs.io/) - HTTP library for handling web requests and sessions.
- [Beautiful Soup 4](https://www.crummy.com/software/BeautifulSoup/bs4/doc/) - HTML parsing and web scraping.
- [tqdm](https://tqdm.github.io/) - Fast, extensible progress bars for loops and multithreading.

---

## ⚠️ Disclaimer

This project is created strictly for educational and personal archive purposes. Please respect manga publishers, scanlation groups, and authors by supporting the official releases.
