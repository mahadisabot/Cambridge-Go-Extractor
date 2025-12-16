
import logging
import os
import shutil
import json
from cambridge_api import CambridgeAPI

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def probe_opcr_data():
    api = CambridgeAPI()
    
    # Login
    username = "8284jade@comfythings.com"
    password = "Xd6G'GM,Q\"4g)h'"
    
    logger.info("Logging in...")
    success, msg = api.login(username, password)
    if not success:
        logger.error(f"Login failed: {msg}")
        return
        
    logger.info("Getting books...")
    books = api.get_books()
    
    target_id = "1485"
    target_book = next((b for b in books if b['id'] == target_id), None)
    
    if not target_book:
        logger.error(f"Book {target_id} not found.")
        return
        
    # Get opcr_url (points to books_data)
    # e.g. https://elevate-s3.cambridge.org/rkdjwhqowc/books_data/9781108796606-54.1.1/9781108796606_resources/
    opcr_url = target_book.get("opcr_url")
    logger.info(f"OPCR URL: {opcr_url}")
    
    if not opcr_url:
        logger.error("No OPCR URL found.")
        return
        
    if not opcr_url.endswith('/'): opcr_url += '/'
    
    # Try multiple constructions based on opcr_url
    
    widget_id = "348600"
    pdf_filename = "exercise_answers_1_asal_physics_wb.pdf"
    
    # 1. Direct relative from opcr_url
    # opcr_url has '..._resources/' on the end.
    # Manifest downloadUrl is '/file-widget-.../file.pdf'
    
    path_1 = f"{opcr_url}file-widget-{widget_id}/{pdf_filename}"
    
    # 2. opcr_url WITHOUT the trailing resources folder?
    # e.g. .../books_data/ISBN-ver/
    if '_resources/' in opcr_url:
        base_books_data = opcr_url.split('_resources/')[0]
        # This gives .../books_data/ISBN-ver/ (Wait, verify split)
        # 9781108796606-54.1.1/9781108796606_resources/
        # base would be .../9781108796606-54.1.1/
    else:
        base_books_data = os.path.dirname(opcr_url.rstrip('/')) + '/'
        
    path_2 = f"{base_books_data}file-widget-{widget_id}/{pdf_filename}"
    path_3 = f"{base_books_data}resources/file-widget-{widget_id}/{pdf_filename}"
    path_4 = f"{base_books_data}OEBPS/resources/file-widget-{widget_id}/{pdf_filename}"
    
    paths_to_test = [path_1, path_2, path_3, path_4]
    
    logger.info("--- Probing OPCR / books_data ---")
    
    for url in paths_to_test:
        try:
             logger.info(f"Probing: {url}")
             r = api.session.head(url, timeout=5)
             status_msg = f"{r.status_code}"
             ctype = r.headers.get('Content-Type', '').lower()
             
             if r.status_code == 200 and 'html' in ctype:
                 status_msg += " (HTML Error)"
             elif r.status_code == 200:
                 status_msg += " (POSSIBLE HIT)"
             
             logger.info(f"  -> {status_msg}")
             
             if "POSSIBLE HIT" in status_msg:
                 logger.info("  [!!!] DOWNLOADING SAMPLE [!!!]")
                 r2 = api.session.get(url, stream=True)
                 chunk = next(r2.iter_content(64))
                 logger.info(f"  Header: {chunk}")
                 if b'%PDF' in chunk:
                     logger.info("  [SUCCESS] VALID PDF FOUND")
                     return
        except Exception as e:
            logger.error(f"Error: {e}")

if __name__ == "__main__":
    probe_opcr_data()
