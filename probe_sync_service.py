import logging
import json
from cambridge_api import CambridgeAPI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def probe_sync_service():
    api = CambridgeAPI()
    
    # Login
    username = "8284jade@comfythings.com"
    password = "Xd6G'GM,Q\"4g)h'"
    
    success, msg = api.login(username, password)
    if not success:
        logger.error(f"Login failed: {msg}")
        return

    logger.info("Login successful. Probing Sync Service...")
    
    # Target Book (from previous logs)
    # Physics Workbook: id=1485, isbn=9781108796606
    # Physics Coursebook: id=1484, isbn=9781108796521
    
    target_books = [
        {"id": "1485", "title": "Physics Workbook"},
        {"id": "1484", "title": "Physics Coursebook"}
    ]
    
    for book in target_books:
        book_id = book['id']
        logger.info(f"--- Probing {book['title']} (ID: {book_id}) ---")
        
        # Endpoint: /user/{userId}/book/{bookId}/sync/
        endpoint = f"{api.BASE_URL}/user/{api.user_id}/book/{book_id}/sync/"
        
        headers = api.session.headers.copy()
        headers.update({
            "accessToken": api.access_token,
            "userId": str(api.user_id)
        })
        
        try:
            # Try multiple payload variations based on bundle.js analysis
            # bundle.js logic: JSON.parse(t.syncData).lastSyncTime
            
            # Exact payload from reader.min.js line 564
            inner_json = json.dumps({
                "lastSyncTime": "0",
                "syncFilter": ["settings", "annotations", "bookmarks", "enrichments"]
            })
            
            payloads = [
                # Candidate 1: Wrapped in syncData (doubly encoded JSON string)
                {"syncData": inner_json},
                
                # Candidate 2: Direct JSON
                {
                    "lastSyncTime": "0",
                    "syncFilter": ["settings", "annotations", "bookmarks", "enrichments"]
                }
            ]
            
            for i, payload in enumerate(payloads):
                logger.info(f"Attempting Payload #{i}: {payload}")
                try:
                    response = api.session.post(endpoint, json=payload, headers=headers, timeout=15)
                    
                    if response.status_code == 200:
                        text = response.text.lstrip('\ufeff')
                        if not text:
                            logger.error("Empty response body")
                            continue
                            
                        # Try parsing
                        try:
                            data = json.loads(text)
                            logger.info("SUCCESS: Valid JSON received!")
                            
                            filename = f"sync_dump_{book_id}_p{i}.json"
                            with open(filename, "w", encoding="utf-8") as f:
                                json.dump(data, f, indent=4)
                            logger.info(f"Saved to {filename}")
                            
                            # Inspect
                            if "enrichments" in data:
                                logger.info(f"Found 'enrichments': {len(data['enrichments'])}")
                            
                            # If we got a valid response with data, break
                            if data: break
                            
                        except json.JSONDecodeError:
                            logger.error(f"Failed to parse JSON for payload {i}")
                            logger.error(f"Raw text: {text[:200]}")
                    else:
                        logger.error(f"Status {response.status_code}")
                except Exception as e:
                    logger.error(f"Request failed: {e}")
                
        except Exception as e:
            logger.error(f"Error: {e}")

if __name__ == "__main__":
    probe_sync_service()
