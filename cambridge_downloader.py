import os
import json
import logging
import requests
from PIL import Image
from io import BytesIO
from cambridge_api import CambridgeAPI
from cambridge_offline import CambridgeOffline

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CambridgeDownloader:
    """
    Manager class that integrates Online (API) and Offline (Blob Carving) methods.
    """
    
    def __init__(self, download_dir="downloads"):
        self.api = CambridgeAPI()
        self.offline = CambridgeOffline()
        self.download_dir = download_dir
        self.use_online = True
        self.books = []
        self.covers_dir = "covers"
        
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)
            
        if not os.path.exists(self.covers_dir):
            os.makedirs(self.covers_dir)

    def set_download_dir(self, path):
        """Updates the download directory."""
        if os.path.exists(path):
            self.download_dir = path
            logger.info(f"Download Directory set to: {self.download_dir}")

    def set_mode(self, online_mode):
        """Switches between Online and Offline modes."""
        self.use_online = online_mode
        logger.info(f"Mode set to: {'Online' if self.use_online else 'Offline'}")

    def login(self, username, password):
        """
        Attempts API login. 
        Returns (bool, message).
        """
        success, msg = self.api.login(username, password)
        if success:
            self.use_online = True
            return True, msg
        else:
            return False, msg

    def scan_library(self):
        """
        Scans for books.
        If Online: Fetches from API.
        If Offline: Scans local blobs.
        """
        raw_books = []
        
        # 1. Try Online
        if self.use_online:
            logger.info("Scanning Online Library...")
            api_books = self.api.get_books()
            if api_books:
                # Mark as online
                for b in api_books:
                    b['source'] = 'online'
                    b['status'] = 'Cloud'
                    # Try to cache cover
                    self._cache_cover(b)
                raw_books.extend(api_books)
                logger.info(f"Found {len(api_books)} books via API.")
            else:
                logger.warning("Online scan returned no books.")
        else:
            # 2. Try Offline ONLY if specifically in offline mode or if online failed
            logger.info("Scanning Local Storage...")
            offline_books = self.offline.get_books()
            
            for b in offline_books:
                b['source'] = 'offline'
                b['status'] = 'Cached Blob'
                raw_books.append(b)
        
        # Deduplicate based on ID or Title+ISBN
        unique_books = {}
        for b in raw_books:
            # Use ID if available, else Title
            key = str(b.get('id', b.get('title')))
            if key not in unique_books:
                unique_books[key] = b
            else:
                # If we have a duplicate, prefer the one with 'online' source
                if b.get('source') == 'online':
                    unique_books[key] = b
                    
        self.books = list(unique_books.values())
        return self.books

    def _cache_cover(self, book):
        """Downloads cover image to local cache if not exists."""
        cover_url = book.get('cover')
        if not cover_url: return
        
        # Unique filename
        book_id = str(book.get('id', 'unknown'))
        local_path = os.path.join(self.covers_dir, f"{book_id}.jpg")
        
        book['cover_local'] = local_path
        
        if os.path.exists(local_path):
            return # Already cached

        try:
            # Download using authenticated session
            resp = self.api.session.get(cover_url, timeout=5)
            if resp.status_code == 200:
                with open(local_path, "wb") as f:
                    f.write(resp.content)
        except Exception as e:
            logger.warning(f"Failed to cache cover for {book_id}: {e}")

    def download_book(self, book_id, progress_callback=None):
        """
        Downloads the book with the given ID.
        Routes to API or Offline extractor based on book source.
        """
        # Find book
        # Search by string ID to be safe
        book = next((b for b in self.books if str(b.get('id')) == str(book_id)), None)
        if not book:
            logger.error(f"Book ID {book_id} not found.")
            return False, "Book not found"
            
        logger.info(f"Starting download for {book.get('title')} ({book.get('source')})")
        
        # Determine Source
        source = book.get('source', 'offline')
        
        success = False
        if source == 'online':
            success = self.api.download_book(book, self.download_dir, progress_callback)
        else:
            success = self.offline.download_book(book, self.download_dir, progress_callback)
            
        if success:
            return True, "Download successful"
        else:
            return False, "Download failed"
