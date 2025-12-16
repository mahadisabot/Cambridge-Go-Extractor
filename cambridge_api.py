import requests
import json
import logging
import os
import time
import re
import xml.etree.ElementTree as ET
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import unquote

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CambridgeAPI:
    """
    Client for interacting with the Cambridge/Elevate API.
    Implemented based on reverse-engineering of the official application.
    """
    
    BASE_URL = "https://elevate.cambridge.org/Openpageservices/BookService.svc"
    S3_BASE_URL = "https://elevate-s3.cambridge.org" # deduced from logs
    
    def __init__(self):
        self.session = requests.Session()
        # Header simulation (mimic Chrome/App)
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json',
            'Referer': 'https://elevate.cambridge.org/',
            'Origin': 'https://elevate.cambridge.org'
        })
        self.is_authenticated = False
        self.user_id = None
        self.access_token = None
        self.user_data = {}

    def login(self, username, password):
        """
        Authenticates with the Cambridge Elevate API.
        """
        logger.info(f"Attempting login for user: {username}")
        
        endpoint = f"{self.BASE_URL}/user/login/"
        payload = {
            "userName": username,
            "password": password,
            "deviceId": "web",
            "authenticationMode": "1"
        }

        try:
            response = self.session.post(endpoint, json=payload, timeout=15)
            
            if response.status_code == 200:
                try:
                    # Strip BOM if present
                    text = response.text.lstrip('\ufeff')
                    data = json.loads(text)
                    
                    self.user_id = data.get("id") or data.get("userId")
                    self.access_token = data.get("accessToken")
                    
                    if self.user_id and self.access_token:
                        self.is_authenticated = True
                        self.user_data = data
                        logger.info(f"Login Successful. UserID: {self.user_id}")
                        return True, "Login successful"
                    else:
                        return False, "Login succeeded but returned no tokens."
                except json.JSONDecodeError as e:
                    logger.error(f"Login JSON Parse Error: {e} | Text: {response.text[:100]}")
                    return False, "Login failed: Invalid JSON response."
            else:
                return False, f"Login failed: HTTP {response.status_code}"

        except requests.exceptions.RequestException as e:
            return False, f"Connection error: {e}"

    def get_books(self):
        """
        Fetches the list of books from the bookshelf endpoint.
        """
        if not self.is_authenticated or not self.user_id:
            logger.error("Cannot get books: Not authenticated.")
            return []

        endpoint = f"{self.BASE_URL}/user/{self.user_id}/bookshelf/"
        
        # Headers specifically required for this endpoint
        headers = self.session.headers.copy()
        headers.update({
            "accessToken": self.access_token,
            "userId": str(self.user_id)
        })
        
        payload = {"books": []}

        try:
            response = self.session.post(endpoint, json=payload, headers=headers, timeout=15)
            
            if response.status_code == 200:
                try:
                    text = response.text.lstrip('\ufeff')
                    data = json.loads(text)
                    
                    books = []
                    if isinstance(data, list):
                        books = data
                    elif isinstance(data, dict) and "books" in data:
                        books = data["books"]
                    
                    if books:
                        logger.info(f"Retrieved {len(books)} books. Scanning for resources...")
                        # Enhance books with resources
                        self._enhance_books_with_resources(books)
                        return books
                    
                    return []
                except json.JSONDecodeError:
                    logger.error("Failed to parse book list JSON.")
                    return []
            else:
                logger.error(f"Bookshelf fetch failed: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching books: {e}")
            return []

    def _enhance_books_with_resources(self, books):
        """
        Checks opcr_url for supplemental resources (Answer Keys, etc)
        """
        for book in books:
            opcr_url = book.get("opcr_url")
            if opcr_url:
                try:
                    # Scan TWO locations: 
                    # 1. The resources folder (opcr_url)
                    # 2. The parent folder (book root)
                    
                    urls_to_scan = [opcr_url]
                    # Generate parent URL
                    if opcr_url.endswith('/'):
                        # e.g. .../resources/ -> .../
                        parent = opcr_url.rstrip('/').rpartition('/')[0] + '/'
                    else:
                        parent = os.path.dirname(opcr_url) + '/'
                    urls_to_scan.append(parent)
                    
                    # 3. The src_url (extracted_books)
                    src_url = book.get("src_url")
                    if src_url:
                        if not src_url.endswith('/'): src_url += '/'
                        urls_to_scan.append(src_url)
                    
                    book_resources = []

                    # 0. Fetch Official Enrichment Manifest (High Priority)
                    enrichments = self._fetch_enrichments(book)
                    if enrichments:
                        book_resources.extend(enrichments)
                    
                    for scan_url in urls_to_scan:
                        logger.info(f"Scanning for resources at: {scan_url}")
                        
                        # Blind Probe - DISABLED to prevent false positives (ghost files / 3KB HTML)
                        # The enrichment manifest is the source of truth now.
                        # candidates = []
                        # isbn = book.get('isbn')
                        # if isbn:
                        #     candidates.append(f"{isbn}_Answer_Key.zip")
                        #     candidates.append(f"{isbn}_Answers.zip")
                        #     candidates.append(f"{isbn}_Resources.zip")
                        #     candidates.append(f"{isbn}_Teacher_Resources.zip")
                        
                        # # Specific fix for user report
                        # candidates.append("asal_physics_cb_answers.zip")
                        # candidates.append("asal_chemistry_cb_answers.zip")
                        # candidates.append("Answer_Key.zip")
                        # candidates.append("Answers.zip")

                        # for probe_file in candidates:
                        #     probe_url = scan_url.rstrip('/') + '/' + probe_file
                        #     try:
                        #         # Use HEAD to check if exists
                        #         ph = self.session.head(probe_url, timeout=5)
                        #         if ph.status_code == 200:
                        #             logger.info(f"[PROBE HIT] Found {probe_file}")
                        #             # Check if HTML/Fake
                        #             if 'html' not in ph.headers.get('Content-Type', '').lower():
                        #                  if not any(r['url'] == probe_url for r in book_resources):
                        #                      book_resources.append({'name': probe_file, 'url': probe_url})
                        #     except: pass

                        # 2. Try Standard Directory Listing (in case it works for some books)
                        resp = self.session.get(scan_url, timeout=5)
                        if resp.status_code == 200:
                            raw_html = resp.text
                            # Only parse if it looks like a directory listing
                            if "Server Error" not in raw_html:
                                links = re.findall(r'href=["\']([^"\']+)["\']', raw_html)
                                logger.info(f"Directory listing active. Links found: {len(links)}")
                                
                                for link in links:
                                    if link == "../" or link.endswith("/"): continue
                                    if link.startswith("?"): continue
                                    
                                    # Clean filename
                                    name = link
                                    url = scan_url.rstrip('/') + '/' + link
                                    
                                    # Filter
                                    if name.lower().endswith(('.zip', '.pdf', '.docx', '.pptx', '.xlsx')):
                                        if not any(r['url'] == url for r in book_resources):
                                            book_resources.append({'name': name, 'url': url})
                                            logger.info(f"-> ACCEPTED: {name}")
                        else:
                             logger.info(f"Scan failed {resp.status_code} for {scan_url}")

                    if book_resources:
                        book['resources'] = book_resources
                        logger.info(f"Found {len(book_resources)} total resources.")
                    else:
                        logger.info("No valid resource files found.")
                except Exception as e:
                    logger.warning(f"Failed to check resources for {book.get('title')}: {e}")

    def _fetch_enrichments(self, book):
        """
        Fetches enrichments.json from the book's source directory manifest.
        Reverse-engineered from catalog.min.js
        """
        src_url = book.get("src_url")
        package_doc_path = book.get("package_doc_path")
        
        if not src_url or not package_doc_path:
            return []
            
        try:
            # Construct URL: src_url + dirname(package_doc_path) + /enrichments.json
            # Note: src_url usually lacks trailing slash, package_doc_path usually has leading slash.
            # We want: src_url + /OEBPS + /enrichments.json
            
            doc_dir = os.path.dirname(package_doc_path).replace("\\", "/")
            if not src_url.endswith('/'):
                base = src_url
            else:
                base = src_url.rstrip('/')
                
            manifest_url = f"{base}{doc_dir}/enrichments.json"
            logger.info(f"Fetching enrichment manifest: {manifest_url}")
            
            response = self.session.get(manifest_url, timeout=10)
            if response.status_code == 200:
                text = response.text.lstrip('\ufeff')
                data = json.loads(text)
                
                resources = []
                if isinstance(data, list):
                    for item in data:
                        # We only care about items with a downloadUrl
                        download_url = item.get("downloadUrl")
                        title = item.get("title", "Unknown Resource")
                        
                        if download_url:
                            # Helper to clean/resolve URL
                            # downloadUrl often starts with / (e.g. /file-widget-349622/...)
                            # It is relative to the doc_dir base
                            if download_url.startswith('/'):
                                full_url = f"{base}{doc_dir}{download_url}"
                            else:
                                full_url = f"{base}{doc_dir}/{download_url}"
                                
                            # Convert common media types to zip if needed (bundle.js logic)
                            # For now, trust the manifest.
                            
                            # Sanitize filename
                            filename = re.sub(r'[<>:"/\\|?*]', '_', title)
                            # If filename doesn't have extension, infer from url
                            if not os.path.splitext(filename)[1]:
                                ext = os.path.splitext(download_url)[1]
                                if ext: filename += ext
                            
                            
                            # Ensure zip validation passes later
                            resource_entry = {
                                'name': filename,
                                'url': full_url,
                                'type': 'enrichment'
                            }
                            
                            # Create alternate URL candidate using opcr_url (books_data)
                            # Primary full_url was: src_url + doc_dir + downloadUrl
                            # PDF Probe confirmed working: opcr_url + file-widget-... (NO /OEBPS/)
                            # downloadUrl usually starts with `/file-widget...`
                            
                            opcr_url = book.get("opcr_url")
                            if opcr_url:
                                if not opcr_url.endswith('/'): opcr_url += '/'
                                # opcr_url already has _resources/ usually?
                                # Let's be careful. Probe success:
                                # OPCR: .../books_data/.../978..._resources/
                                # File: .../books_data/.../978..._resources/file-widget-.../file.pdf
                                
                                # downloadUrl: /file-widget-...
                                alt_url = f"{opcr_url}{download_url.lstrip('/')}"
                                resource_entry['alt_url'] = alt_url
                                
                            resources.append(resource_entry)
                            logger.info(f"Found Enrichment: {filename}")
                            
                return resources
            else:
                logger.info(f"No enrichment manifest found (HTTP {response.status_code})")
                return []
                
        except Exception as e:
            logger.warning(f"Error fetching enrichments: {e}")
            return []

    def download_book(self, book_metadata, output_dir, progress_callback=None):
        """
        Downloads a book using Direct EPUB URL (Preferred) or S3 Reconstruction (Fallback).
        Also downloads supplemental resources.
        """
        title = book_metadata.get('title', 'Unknown Book')
        safe_title = "".join([c for c in title if c.isalpha() or c.isdigit() or c==' ']).strip()
        epub_path = os.path.join(output_dir, f"{safe_title}.epub")
        
        logger.info(f"Starting download for: {title}")
        
        # 1. Use Reconstruction (Asset Mirroring)
        # Direct download_url provides an obfuscated blob (custom Cambridge format), not a valid EPUB.
        # We must reconstruct from unencrypted S3 assets.
        logger.info("Starting Download (Reconstructing from S3 assets)...")
        success = self._download_via_reconstruction(book_metadata, output_dir, progress_callback)
        if not success:
             return False

        # 3. Download Resources (Answer Keys)
        resources = book_metadata.get('resources', [])
        if resources:
            logger.info(f"Downloading {len(resources)} separate resources...")
            res_dir = os.path.join(output_dir, f"{safe_title}_Resources")
            if not os.path.exists(res_dir):
                os.makedirs(res_dir)
                
            for i, res in enumerate(resources):
                try:
                    r_path = os.path.join(res_dir, res['name'])
                    
                    # Logic: Try primary URL first. If fails, try alt_url.
                    urls_to_try = [res['url']]
                    if res.get('alt_url'):
                        urls_to_try.append(res.get('alt_url'))
                        
                    download_success = False
                    
                    for url_candidate in urls_to_try:
                        if download_success: break
                        
                        try:
                            # Use stream to check headers first
                            with self.session.get(url_candidate, stream=True, timeout=30) as r:
                                if r.status_code == 200:
                                    # VALIDATION: Check for "Fake" Zip/PDF (Redirect to Book EPUB or HTML Error)
                                    
                                    # Check 1: Content-Type header
                                    ctype = r.headers.get('Content-Type', '').lower()
                                    if 'html' in ctype:
                                         logger.warning(f"Skipping candidate {url_candidate}: Content-Type is html (likely error page)")
                                         continue
                                    if 'epub' in ctype:
                                         logger.warning(f"Skipping candidate {url_candidate}: Content-Type is epub (likely book redirect)")
                                         continue
                                    
                                    # Read first chunk to check headers/content
                                    chunk_iter = r.iter_content(chunk_size=1024)
                                    first_chunk = next(chunk_iter, None)
                                    
                                    if not first_chunk:
                                        logger.warning(f"Empty resource: {res['name']}")
                                        continue

                                    # Check 2: Content Sniffing
                                    if b'<!DOCTYPE html>' in first_chunk or b'<html' in first_chunk:
                                        logger.warning(f"Skipping candidate {url_candidate}: HTML content detected")
                                        continue
                                    if b'mimetypeapplication/epub+zip' in first_chunk:
                                        logger.warning(f"Skipping candidate {url_candidate}: EPUB signature detected")
                                        continue
                                        
                                    # If Valid, write chunk and continue
                                    with open(r_path, 'wb') as f:
                                        f.write(first_chunk)
                                        for chunk in chunk_iter:
                                            f.write(chunk)
                                            
                                    logger.info(f"Downloaded resource to: {r_path}")
                                    download_success = True
                                else:
                                    logger.warning(f"Resource request failed {r.status_code} for {url_candidate}")
                        except Exception as e:
                            logger.warning(f"Error downloading {url_candidate}: {e}")
                            
                    if not download_success:
                        logger.error(f"Failed to download resource {res['name']} after trying all candidates.")

                except Exception as e:
                    logger.error(f"Failed to download resource {res['name']}: {e}")
                    
        if progress_callback: progress_callback(100)
        return True

    def _download_via_reconstruction(self, book_metadata, output_dir, progress_callback=None):
        """Original logic for reconstructing from OPF/assets."""
        title = book_metadata.get('title', 'Unknown Book')
        safe_title = "".join([c for c in title if c.isalpha() or c.isdigit() or c==' ']).strip()
        epub_path = os.path.join(output_dir, f"{safe_title}.epub")
        
        src_base_url = book_metadata.get('src_url')
        opf_rel_path = book_metadata.get('package_doc_path')
        
        if not src_base_url or not opf_rel_path: return False

        temp_dir = os.path.join(output_dir, "temp_" + safe_title)
        if not os.path.exists(temp_dir): os.makedirs(temp_dir)

        try:
            # 1. OPF
            opf_url = src_base_url + opf_rel_path
            opf_resp = self.session.get(opf_url)
            if opf_resp.status_code != 200: return False
            
            local_opf_rel = opf_rel_path.lstrip('/')
            local_opf_path = os.path.join(temp_dir, local_opf_rel)
            os.makedirs(os.path.dirname(local_opf_path), exist_ok=True)
            with open(local_opf_path, "wb") as f: f.write(opf_resp.content)
            
            # 2. Parse
            root = ET.fromstring(opf_resp.content)
            manifest_items = []
            for elem in root.iter():
                if 'manifest' in elem.tag:
                    for item in elem:
                        if 'href' in item.attrib:
                            manifest_items.append(item.attrib['href'])
                    break
            
            total_items = len(manifest_items)
            opf_dir_url = src_base_url + "/" + os.path.dirname(local_opf_rel).replace("\\", "/")
            
            # 3. Download Assets
            def download_asset(href):
                try:
                    asset_url = f"{opf_dir_url}/{href}"
                    local_asset_path = os.path.join(temp_dir, os.path.dirname(local_opf_rel), href)
                    os.makedirs(os.path.dirname(local_asset_path), exist_ok=True)
                    if os.path.exists(local_asset_path): return True
                    r = self.session.get(asset_url, timeout=20)
                    if r.status_code == 200:
                        with open(local_asset_path, "wb") as f: f.write(r.content)
                        return True
                    return False
                except: return False

            completed = 0
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = {executor.submit(download_asset, item): item for item in manifest_items}
                for future in as_completed(futures):
                    completed += 1
                    if progress_callback: progress_callback((completed / total_items) * 90)

            # 3b. INJECT COVER IMAGE
            # Download the high-res cover from metadata and inject it into the EPUB
            cover_url = book_metadata.get('cover')
            if cover_url:
                try:
                    logger.info("Injecting Cover Image...")
                    cover_resp = self.session.get(cover_url, timeout=10)
                    if cover_resp.status_code == 200:
                        # Save to OEBPS/cover.jpg (or same dir as OPF)
                        opf_dir = os.path.dirname(local_opf_path)
                        cover_filename = "cover.jpg"
                        cover_path = os.path.join(opf_dir, cover_filename)
                        
                        with open(cover_path, "wb") as f:
                            f.write(cover_resp.content)
                            
                        # Update OPF XML
                        # 1. Add item to manifest
                        # 2. Add meta to metadata
                        ns = {'opf': 'http://www.idpf.org/2007/opf'}
                        ET.register_namespace('', ns['opf'])
                        
                        # We need to parse again or reuse 'root'
                        # Let's re-parse to be safe with namespaces
                        tree = ET.parse(local_opf_path)
                        root = tree.getroot()
                        
                        # Find Manifest
                        manifest = root.find('{http://www.idpf.org/2007/opf}manifest')
                        metadata = root.find('{http://www.idpf.org/2007/opf}metadata')
                        
                        if manifest is not None and metadata is not None:
                            # Check if item exists, if not add it
                            cover_id = "cover-image-injected"
                            
                            # Add item
                            item = ET.Element('{http://www.idpf.org/2007/opf}item', {
                                'id': cover_id,
                                'href': cover_filename,
                                'media-type': 'image/jpeg'
                            })
                            manifest.append(item)
                            
                            # Update/Add Meta
                            # Remove existing cover meta if any to avoid conflict?
                            # Or just add ours.
                            meta = ET.Element('{http://www.idpf.org/2007/opf}meta', {
                                'name': 'cover',
                                'content': cover_id
                            })
                            metadata.append(meta)
                            
                            tree.write(local_opf_path, encoding='UTF-8', xml_declaration=True)
                            logger.info("Cover injected into OPF.")
                except Exception as e:
                    logger.warning(f"Failed to inject cover: {e}")

            # 4. Valid EPUB Gen (Mimetype + Container)
            mimetype_path = os.path.join(temp_dir, "mimetype")
            with open(mimetype_path, "w", encoding="utf-8") as f: f.write("application/epub+zip")
                
            meta_inf_dir = os.path.join(temp_dir, "META-INF")
            os.makedirs(meta_inf_dir, exist_ok=True)
            container_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
    <rootfiles>
        <rootfile full-path="{local_opf_rel.replace(os.path.sep, '/')}" media-type="application/oebps-package+xml"/>
    </rootfiles>
</container>"""
            with open(os.path.join(meta_inf_dir, "container.xml"), "w", encoding="utf-8") as f: f.write(container_xml)

            # 5. Zip
            with zipfile.ZipFile(epub_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.write(mimetype_path, "mimetype", compress_type=zipfile.ZIP_STORED)
                for root_dir, _, files in os.walk(temp_dir):
                    for file in files:
                        if file == "mimetype": continue
                        full = os.path.join(root_dir, file)
                        zf.write(full, os.path.relpath(full, temp_dir))
            
            try:
                import shutil
                shutil.rmtree(temp_dir)
            except: pass
            
            return True
        except Exception as e:
            logger.error(f"Reconstruction failed: {e}")
            return False
