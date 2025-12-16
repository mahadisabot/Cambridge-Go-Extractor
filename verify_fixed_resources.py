
import logging
import os
import shutil
from cambridge_api import CambridgeAPI

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def verify_fixed_resources():
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
        
    logger.info(f"Target Book: {target_book.get('title')}")
    
    resources = target_book.get('resources', [])
    if not resources:
        logger.error("No resources found (did automatic enrichment fetch fail?)")
        return
        
    logger.info(f"Found {len(resources)} resources.")
    
    # 1. Verify Ghost Check (Chemistry)
    ghost_found = any('chemistry' in r['name'].lower() for r in resources)
    if ghost_found:
        logger.error("FAIL: Ghost Chemistry files still present!")
    else:
        logger.info("PASS: No Ghost Chemistry files found.")
        
    # 2. Verify PDF Download
    target_pdf_name = "exercise_answers_1_asal_physics_wb.pdf"
    pdf_resource = next((r for r in resources if target_pdf_name in r['name']), None)
    
    if pdf_resource:
        logger.info(f"Found Target PDF: {pdf_resource['name']}")
        logger.info(f"Primary URL: {pdf_resource['url']}")
        logger.info(f"Alt URL: {pdf_resource.get('alt_url', 'None')}")
        
        # Determine output path
        output_dir = "verified_final"
        if not os.path.exists(output_dir): os.makedirs(output_dir)
        output_path = os.path.join(output_dir, target_pdf_name)
        
        # Simulate the download loop logic
        # We want to see if it successfully downloads a valid PDF
        
        download_success = False
        urls_to_try = [pdf_resource['url']]
        if pdf_resource.get('alt_url'):
            urls_to_try.append(pdf_resource.get('alt_url'))
            
        for url in urls_to_try:
            logger.info(f"Attempting download from: {url}")
            try:
                with api.session.get(url, stream=True, timeout=30) as r:
                    logger.info(f"Status: {r.status_code}")
                    ctype = r.headers.get('Content-Type', '').lower()
                    logger.info(f"Content-Type: {ctype}")
                    
                    if r.status_code == 200 and 'html' not in ctype and 'epub' not in ctype:
                        # Check header bytes
                        chunk = next(r.iter_content(100))
                        if b'%PDF' in chunk:
                            logger.info("PASS: Valid PDF Header detected!")
                            download_success = True
                            with open(output_path, 'wb') as f:
                                f.write(chunk)
                                shutil.copyfileobj(r.raw, f)
                            break
                        else:
                            logger.warning(f"Invalid header: {chunk[:20]}")
                    else:
                        logger.warning("Invalid content type or status.")
            except Exception as e:
                logger.error(f"Error: {e}")
                
        if download_success:
            logger.info("[SUCCESS] PDF downloaded and verified.")
        else:
            logger.error("[FAIL] PDF download failed for all candidates.")
            
    else:
        logger.error("Target PDF not found in resource list.")

if __name__ == "__main__":
    verify_fixed_resources()
