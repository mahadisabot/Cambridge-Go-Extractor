![Cambridge Downloader Banner](images/banner.png)

# Cambridge Downloader (Python Version)

A powerful, standalone utility to authenticate with Cambridge Go/Elevate, verify your library, and download digital textbooks as standard, offline-accessible EPUB files. 

> **Release Version:** 2.0 (Stable Python Release)
> **Note:** This is the Python implementation. A high-performance Rust rewrite is currently in development.

## Features

*   **🔒 Secure Authentication:** Logs in directly to Cambridge Elevate/Go securely.
*   **📚 Library Sync:** Automatically fetches your entire book list.
*   **💾 Offline Access:** Downloads verified EPUB files that work on any e-reader (Apple Books, Calibre, eInk devices).
*   **🧩 Resource Extraction:** 
    *   Automatically repairs broken EPUB structures.
    *   **[NEW]** Intelligent "Enrichment" extraction (Answer Keys, Worksheets, Audio).
    *   **[NEW]** Fixes "Ghost" resources and "Corrupted PDF" issues using multi-source resolution.
*   **🖼️ Cover Injection:** Automatically fetches and embeds high-resolution cover art into the EPUB files.

## Installation

1.  Ensure you have **Python 3.10+** installed.
2.  Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

### Graphical Interface (Recommended)

Run the modern GUI for an easy point-and-click experience:

```bash
python cambridge_downloader_gui.py
```

1.  Enter your Email and Password.
2.  Click **Login**.
3.  Wait for your library to load.
4.  Click **Download** on any book card.
    *   The progress bar will show the status of asset fetching and EPUB reconstruction.
    *   Resources (Answer keys etc.) are downloaded to a `your_book_title_resources/` folder next to the EPUB.

### Building a Standalone Executable (.exe)

You can build a portable `.exe` file that requires no Python installation:

```bash
python build_exe.py
```

The output file will be in the `dist/` folder.

## Technical Details

This tool uses a sophisticated reverse-engineered API client (`CambridgeAPI`) to mirror the behavior of the official web reader.

*   **Logic:** It fetches the `content.opf` manifest directly from Cambridge's S3 buckets and reconstructs the EPUB file-by-file locally.
*   **Protection:** It handles session cookies (`AWSALB`, `__cf_bm`) to bypass Cloudflare protection legally as an authenticated user.
*   **Validation:** It validates headers of every file to ensure no corrupted (4KB HTML error pages) files are saved.

### Structure

*   `cambridge_api.py`: The core logic for Auth, Library, and Download.
*   `cambridge_downloader_gui.py`: The CustomTkinter-based frontend.
*   `user_config.json`: (Generated) Stores encrypted local session data for convenience.

---

*For educational and archival purposes only.*
