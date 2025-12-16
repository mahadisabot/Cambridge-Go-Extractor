
import logging
import os
import shutil
from cambridge_api import CambridgeAPI

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def verify_answer_key():
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
        
    logger.info(f"Checking resources for: {target_book.get('title')}")
    
    # Manually check resources directly attached to book (which should include enrichments now)
    resources = target_book.get('resources', [])
    
    target_file = "asal_physics_wb_answers.zip"
    candidate = next((r for r in resources if target_file in r['name']), None)
    
    if candidate:
        logger.info(f"FOUND Candidate in Book Resources: {candidate}")
        logger.info(f"URL: {candidate['url']}")
        
        # Try Download
        output_dir = "verified_answer_key"
        if not os.path.exists(output_dir): os.makedirs(output_dir)
        
        filename = candidate['name']
        path = os.path.join(output_dir, filename)
        
        logger.info(f"Downloading to {path}...")
        try:
            with api.session.get(candidate['url'], stream=True, timeout=30) as r:
                if r.status_code == 200:
                   with open(path, 'wb') as f:
                       shutil.copyfileobj(r.raw, f)
                   
                   size = os.path.getsize(path)
                   logger.info(f"Download Complete. Size: {size} bytes")
                   
                   if size > 10000: # Broad check (>10KB)
                       logger.info("Valid Size! (Success)")
                   else:
                       logger.error("File possibly too small/corrupted.")
                       
                   # Check Zip Header
                   with open(path, 'rb') as f:
                       header = f.read(4)
                       if header.startswith(b'PK'):
                           logger.info("Valid ZIP Header detected!")
                       else:
                           logger.error(f"Invalid Header: {header}")
                else:
                    logger.error(f"HTTP Error: {r.status_code}")
        except Exception as e:
            logger.error(f"Download Exception: {e}")
            
    else:
        logger.error("Target answer key NOT found in resources list.")

if __name__ == "__main__":
    verify_answer_key()
