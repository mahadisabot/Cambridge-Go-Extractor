import logging
import os
from cambridge_downloader import CambridgeDownloader

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

USERNAME = "8284jade@comfythings.com"
PASSWORD = "Xd6G'GM,Q\"4g)h'"

def verify_full_stack():
    logger.info("Initializing Manager...")
    manager = CambridgeDownloader(download_dir="verified_downloads")
    
    # 1. Test Login
    logger.info("Testing Login...")
    success, msg = manager.login(USERNAME, PASSWORD)
    if success:
        logger.info("LOGIN SUCCESS")
    else:
        logger.error(f"LOGIN FAILED: {msg}")
        return

    # 2. Test Scan
    logger.info("Testing Library Scan...")
    books = manager.scan_library()
    logger.info(f"Found {len(books)} books.")
    
    if not books:
        logger.error("No books found. Aborting.")
        return

    # 3. Test Download (First Online Book)
    online_books = [b for b in books if b.get('source') == 'online']
    if online_books:
        target = online_books[0]
        logger.info(f"Attempting to download: {target['title']}")
        
        def mock_progress(p):
            if int(p) % 20 == 0:
                logger.info(f"Progress: {p}%")
                
        success, msg = manager.download_book(target['id'], progress_callback=mock_progress)
        
        if success:
            logger.info("DOWNLOAD SUCCESS")
        else:
            logger.error(f"DOWNLOAD FAILED: {msg}")
    else:
        logger.warning("No online books to test download.")

    # 4. Test Offline Scan explicitly
    manager.set_mode(False) # Switch to offline
    offline_books = manager.scan_library()
    logger.info(f"Offline Mode found {len(offline_books)} items.")

if __name__ == "__main__":
    verify_full_stack()
