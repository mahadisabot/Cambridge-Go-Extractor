import logging
import json
from cambridge_api import CambridgeAPI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def probe_details():
    api = CambridgeAPI()
    
    # Login
    username = "8284jade@comfythings.com"
    password = "Xd6G'GM,Q\"4g)h'"
    
    success, msg = api.login(username, password)
    if not success:
        logger.error(f"Login failed: {msg}")
        return

    logger.info("Login successful. Probing Book Details Service...")
    
    # Target Book (Physics Workbook)
    book_id = "1485" 
    
    # Endpoint: /user/{userId}/book/{bookId}/details/
    endpoint = f"{api.BASE_URL}/user/{api.user_id}/book/{book_id}/details/"
    
    headers = api.session.headers.copy()
    headers.update({
        "accessToken": api.access_token,
        "userId": str(api.user_id)
    })
    
    try:
        # Details service likely implies GET? Or POST?
        # webServices.min.js just sets the URL strings.
        # But usually details fetch is GET. Let's try GET first.
        
        logger.info(f"Attempting GET {endpoint}")
        response = api.session.get(endpoint, headers=headers, timeout=15)
        
        if response.status_code == 200:
            text = response.text.lstrip('\ufeff')
            try:
                data = json.loads(text)
                
                # Save
                filename = f"details_dump_{book_id}.json"
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
                logger.info(f"Saved response to {filename}")
                
                # Check for enrichments
                if "enrichments" in data:
                    logger.info(f"!!! FOUND ENRICHMENTS: {len(data['enrichments'])} items !!!")
                elif "resources" in data:
                    logger.info(f"!!! FOUND RESOURCES: {len(data['resources'])} items !!!")
                else:
                    logger.warning("No 'enrichments' or 'resources' key found.")
                    logger.info(f"Keys: {list(data.keys())}")
                    
            except json.JSONDecodeError:
                logger.error("Failed to parse JSON")
        else:
            logger.warning(f"GET failed: {response.status_code}. Trying POST...")
            
            # Try POST with empty body
            response = api.session.post(endpoint, json={}, headers=headers, timeout=15)
            if response.status_code == 200:
                text = response.text.lstrip('\ufeff')
                try:
                    data = json.loads(text)
                    filename = f"details_dump_{book_id}_post.json"
                    with open(filename, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=4)
                    logger.info(f"Saved POST response to {filename}")
                     # Check for enrichments
                    if "enrichments" in data:
                        logger.info(f"!!! FOUND ENRICHMENTS (POST): {len(data['enrichments'])} items !!!")
                except:
                    logger.error("Failed to parse POST JSON")
            else:
                 logger.error(f"POST failed: {response.status_code}")

    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    probe_details()
