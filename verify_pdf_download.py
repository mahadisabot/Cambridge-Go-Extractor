
import logging
import os
import shutil
from cambridge_api import CambridgeAPI

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def verify_pdf_download():
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
    
    # Target Book: 1485 (Physics Workbook)
    target_id = "1485"
    target_book = next((b for b in books if b['id'] == target_id), None)
    
    if not target_book:
        logger.error(f"Book {target_id} not found.")
        return
        
    # We want to emulate the URL construction from _fetch_enrichments
    # Based on manifest entry:
    # "downloadUrl": "/file-widget-348600/exercise_answers_1_asal_physics_wb.pdf"
    
    src_url = target_book.get("src_url")
    package_doc_path = target_book.get("package_doc_path")
    
    doc_dir = os.path.dirname(package_doc_path).replace("\\", "/")
    if not src_url.endswith('/'):
        base = src_url
    else:
        base = src_url.rstrip('/')
        
    # Test specific PDF
    relative_url = "/file-widget-348600/exercise_answers_1_asal_physics_wb.pdf"
    
    # Current Logic Construction
    full_url = f"{base}{doc_dir}{relative_url}"
    
    logger.info(f"Target URL: {full_url}")
    
    # Check Headers
    logger.info("Checking Headers...")
    try:
        head = api.session.head(full_url, timeout=10)
        
        # Log all headers for deeper inspection
        logger.info(f"HEAD Status: {head.status_code}")
        for k, v in head.headers.items():
            logger.info(f"Header {k}: {v}")

        # Download Content
        output_file = "debug_exercise_answers.pdf"
        logger.info(f"Downloading to {output_file}...")
        
        resp = api.session.get(full_url)
        with open(output_file, 'wb') as f:
            f.write(resp.content)
            
        # Inspect Content
        if b'<!DOCTYPE html>' in resp.content[:100] or b'<html' in resp.content[:100]:
            logger.error("!!! CONTENT IS HTML (CORRUPTED) !!!")
            logger.info(f"First 500 bytes:\n{resp.content[:500].decode('utf-8', errors='ignore')}")
        elif resp.content.startswith(b'%PDF'):
             logger.info("!!! CONTENT IS VALID PDF !!!")
        else:
             logger.warning(f"Unknown Content Start: {resp.content[:20]}")
             
    except Exception as e:
        logger.error(f"Request failed: {e}")

if __name__ == "__main__":
    verify_pdf_download()
