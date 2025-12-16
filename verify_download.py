import requests
import xml.etree.ElementTree as ET
import logging
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Data from previous step
SRC_URL = "https://elevate-s3.cambridge.org/rkdjwhqowc/extracted_books/9781108796606-54.1.1"
OPF_PATH = "/OEBPS/content.opf"

def verify_download():
    full_opf_url = SRC_URL + OPF_PATH
    logger.info(f"Targeting OPF: {full_opf_url}")
    
    # Updated Headers to bypass Cloudflare/S3 restrictions
    headers = {
        "Referer": "https://elevate.cambridge.org/",
        "Origin": "https://elevate.cambridge.org",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36",
        # Add Cloudflare cookies if available (hardcoded from previous login log for testing)
        "Cookie": "AWSALB=qKS81jstg8JG4ocvi3zwKvzTv87XNqJz+N7XzeIyqDvmDrw5f6dnRujxrvPYf9jWUEFCax5zyK7pb18EJZxMMyuvnK/hGiQm99Iqak8QPdHi/HV5rdZs5jCzuS7r; __cf_bm=vjMBiy_jiMuALaRyxnTPqKk4eKlmkTxcRb5H5p4wzyA-1765873468-1.0.1.1-9c1ctRqEnB2D50wZ73Riy_p2HzS6PNeubXBFxlUtCpiO73yZPhyWccvvKWoWPv4OEQ7DL7ze.H_kOCZGxU8tCCn_fmzVI4N_Yw3k0xiaxyI"
    }

    try:
        # Try simple GET first
        resp = requests.get(full_opf_url, headers=headers, timeout=10)
        
        logger.info(f"Status Code: {resp.status_code}")
        
        if resp.status_code == 200:
            logger.info("SUCCESS: OPF Accessible!")
            content = resp.text
            logger.info(f"OPF Content Length: {len(content)}")
            
            # Save OPF for inspection
            with open("test_content.opf", "w", encoding="utf-8") as f:
                f.write(content)
                
            # Parse OPF to find first item
            try:
                # Remove namespaces for simple parsing
                # (Simple hack: replace xmlns with internal_ns to avoid verbosity in find)
                root = ET.fromstring(content)
                ns = {'opf': 'http://www.idpf.org/2007/opf'}
                
                # Try to find manifest
                manifest = root.findall('.//{http://www.idpf.org/2007/opf}manifest')
                if not manifest:
                     # Try without namespace if that failed (sometimes xml parsing is tricky)
                     manifest = root.findall('manifest')
                
                # Use a more robust search if strict namespacing fails
                items = []
                for elem in root.iter():
                    if 'manifest' in elem.tag:
                         items = list(elem)
                         break
                
                logger.info(f"Found {len(items)} items in manifest.")
                    
                if items:
                        first_item = items[2] # Pick the 3rd item to avoid ncx or similar
                        href = first_item.attrib.get('href')
                        logger.info(f"Attempting to download item: {href}")
                        
                        # Construct URL (href is relative to OPF usually, or OEBPS root)
                        # OPF is in /OEBPS/, so hrefs are usually relative to that.
                        # SRC_URL ends in .../9781108796606-54.1.1
                        # OPF is at .../OEBPS/content.opf
                        # If href is "css/style.css", full url is .../OEBPS/css/style.css
                        
                        item_url = SRC_URL + "/OEBPS/" + href
                        logger.info(f"Item URL: {item_url}")
                        
                        item_resp = requests.get(item_url, headers=headers)
                        if item_resp.status_code == 200:
                            logger.info(f"SUCCESS: Downloaded item {href}")
                        else:
                            logger.error(f"Failed to download item: {item_resp.status_code}")
                else:
                    logger.warning("No manifest found (check namespaces?)")

            except Exception as parse_e:
                logger.error(f"OPF Parse Error: {parse_e}")
                
        else:
            logger.error("Failed to download OPF.")
            logger.info("Headers might be needed?")
            logger.info(resp.text[:500])

    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    verify_download()
