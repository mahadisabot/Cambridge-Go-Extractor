import requests
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
BASE_URL = "https://elevate.cambridge.org/Openpageservices/BookService.svc"
USER_ID = "2542840"
ACCESS_TOKEN = "235a94ef-dc2c-4544-a8ff-1e25e2eff3d0"

def verify_bookshelf():
    # Construct URL
    # Format: /user/{userId}/bookshelf/
    bookshelf_url = f"{BASE_URL}/user/{USER_ID}/bookshelf/"
    
    logger.info(f"Targeting Bookshelf: {bookshelf_url}")
    
    # Hypothesized Headers based on CORS and standard practice
    headers = {
        "accessToken": ACCESS_TOKEN,
        "userId": USER_ID,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36",
        "Accept": "application/json"
    }
    
    try:
        # Use POST as confirmed by code analysis (Const.SERVICE_TYPE: "POST")
        # Payload: {"books": []} found in ws_lib_namespace.min.js
        payload = {"books": []}
        
        logger.info(f"Sending POST to {bookshelf_url} with payload {payload}")
        
        resp = requests.post(bookshelf_url, json=payload, headers=headers, timeout=10)
        
        logger.info(f"Status Code: {resp.status_code}")
        
        if resp.status_code == 200:
            logger.info("SUCCESS: Bookshelf Accessed!")
            try:
                data = resp.json()
                # Determine if it's a list or a wrapper
                if isinstance(data, list):
                    logger.info(f"Found {len(data)} books.")
                    if len(data) > 0:
                        first_book = data[0]
                        logger.info("DUMPING FIRST BOOK JSON:")
                        logger.info(json.dumps(first_book, indent=2))
                else:
                    logger.info("Response is not a list, dumping keys:")
                    logger.info(data.keys())
            except Exception as e:
                logger.warning(f"Response 200 but parse error: {e}")
                logger.info(resp.text[:500])
        else:
            logger.error("Failed to access bookshelf.")
            logger.info(resp.text[:500])
            
    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    verify_bookshelf()
