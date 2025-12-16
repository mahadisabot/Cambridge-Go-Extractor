import logging
import json
from cambridge_api import CambridgeAPI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def probe_metadata_file():
    api = CambridgeAPI()
    
    # Login
    username = "8284jade@comfythings.com"
    password = "Xd6G'GM,Q\"4g)h'"
    
    success, msg = api.login(username, password)
    if not success:
        logger.error(f"Login failed: {msg}")
        return

    logger.info("Login successful. Probing Metadata Files...")
    
    # Target Book (Physics Workbook)
    # opcr_url: https://elevate-s3.cambridge.org/rkdjwhqowc/books_data/9781108796606-54.1.1/9781108796606_resources/
    
    base_url = "https://elevate-s3.cambridge.org/rkdjwhqowc/books_data/9781108796606-54.1.1/9781108796606_resources/"
    
    candidates = [
        "enrichments.json",
        "enrichment.json",
        "resources.json",
        "manifest.json",
        "toc.json",
        "content.json",
        "assets.json"
    ]
    
    headers = api.session.headers.copy()
    headers.update({
        "Referer": "https://elevate.cambridge.org/",
        "Origin": "https://elevate.cambridge.org"
    })
    
    # 4. Probe src_url derived path (Correct logic from catalog.min.js)
    # src_url: https://elevate-s3.cambridge.org/rkdjwhqowc/extracted_books/9781108796606-54.1.1
    # package_doc_path: /OEBPS/content.opf
    # derived: src_url + /OEBPS/enrichments.json
    
    src_url = "https://elevate-s3.cambridge.org/rkdjwhqowc/extracted_books/9781108796606-54.1.1"
    package_doc_path = "/OEBPS/content.opf"
    
    # Logic: src_url + dirname(package_doc_path) + / + enrichment.json
    # Note: src_url has no trailing slash. package_doc_path has leading slash.
    
    import os
    doc_dir = os.path.dirname(package_doc_path).replace("\\", "/") # /OEBPS
    
    candidates = [
        "enrichments.json",
        "enrichment.json",
        "resources.json",
        "quizs.json", # Also saw this in grep
        "TOCData.json" # Also saw this
    ]
    
    for filename in candidates:
        # Construct content URL
        # src_url + doc_dir + / + filename
        url = f"{src_url}{doc_dir}/{filename}"
        logger.info(f"Probing src_url: {url}")
        
        try:
             response = api.session.get(url, headers=headers, timeout=10)
             if response.status_code == 200:
                text = response.text.lstrip('\ufeff') # Strip BOM
                
                if "<html" in text.lower():
                     logger.info(f"Failed (HTML) for {url}")
                else:
                     logger.info(f"SUCCESS: Found {filename} at src_url!")
                     try:
                        data = json.loads(text)
                        logger.info(f"JSON Parsed. Keys: {list(data.keys())}")
                         # Dump it
                        dump_name = f"found_src_{filename}"
                        with open(dump_name, "w", encoding="utf-8") as f:
                            json.dump(data, f, indent=4)
                        
                        if isinstance(data, list) and len(data) > 0:
                             logger.info(f"Item 0: {data[0]}")
                             # Check for answer key URL
                             for item in data:
                                 if "answer" in str(item).lower():
                                     logger.info(f"!!! FOUND ANSWER KEY CANDIDATE: {item}")
                     except Exception as e:
                        logger.error(f"Failed to parse JSON: {e}")
                        # Save raw text anyway for inspection
                        dump_name = f"found_src_{filename}_raw.txt"
                        with open(dump_name, "w", encoding="utf-8") as f:
                            f.write(text)
                        logger.info(f"Saved raw text to {dump_name}")

             else:
                logger.info(f"Failed: {response.status_code}")
        except Exception as e:
            logger.error(f"Error: {e}")

if __name__ == "__main__":
    probe_metadata_file()
