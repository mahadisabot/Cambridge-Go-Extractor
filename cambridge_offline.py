import os
import json
import shutil
import logging
import struct
import zlib
import zipfile

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CambridgeOffline:
    """
    Offline extractor for Cambridge Reader.
    Scans local file system for cached blobs and carves EPUBs from them.
    """
    def __init__(self):
        # Default path for Cambridge Reader data
        self.base_path = "c:/Users/Breeze/AppData/Local/Cambridge Reader/User Data/Default/File System"
        
    def get_books(self):
        """
        Scans the local filesystem for books (blobs) using size heuristic.
        Returns a list of book dictionaries compatible with CambridgeAPI.
        """
        books = []
        blob_path = os.path.join(self.base_path, "000", "p", "00")
        
        if not os.path.exists(blob_path):
            logger.warning(f"Blob path not found: {blob_path}")
            return books
        
        logger.info(f"Scanning {blob_path} for large blobs...")
        
        try:
            for root, dirs, files in os.walk(blob_path):
                for file in files:
                    fpath = os.path.join(root, file)
                    try:
                        size = os.path.getsize(fpath)
                        
                        # Heuristic: Books are likely > 500KB (strict filter to avoid noise)
                        if size > 500 * 1024: 
                            books.append({
                                "id": file,
                                "title": f"Local Cache: {file}", # Placeholder until extracted
                                "path": fpath,
                                "src_url": None, # Offline only
                                "offline": True,
                                "size": size
                            })
                    except OSError:
                        pass
        except Exception as e:
            logger.error(f"Error scanning local library: {e}")
                    
        logger.info(f"Found {len(books)} potential book blobs.")
        return books

    def download_book(self, book_metadata, output_dir, progress_callback=None):
        """
        Carves the EPUB from the blob.
        """
        source_path = book_metadata.get('path')
        if not source_path or not os.path.exists(source_path):
            logger.error("Source file not found")
            return False

        # Use book ID or Title for filename
        filename = f"{book_metadata.get('id', 'unknown')}.epub"
        output_path = os.path.join(output_dir, filename)
        
        logger.info(f"Carving {source_path} to {output_path}...")
        
        try:
            with open(source_path, 'rb') as f:
                data = f.read()

            if progress_callback: progress_callback(10)

            # Dictionary to store carved files: {filename: content_bytes}
            carved_files = {}
            
            # Carving Pattern: Version(2.0) + Flags(0x08)
            pattern = b'\x14\x00\x08\x00'
            next_off = 0
            count = 0
            total_len = len(data)
            
            while True:
                idx = data.find(pattern, next_off)
                if idx == -1: break
                
                if progress_callback and count % 50 == 0:
                    prog = 10 + (idx / total_len * 70)
                    progress_callback(prog)

                next_off = idx + 1
                start = idx - 4
                if start < 0: continue
                
                try:
                    # Parse Local File Header
                    method = struct.unpack('<H', data[start+8:start+10])[0]
                    name_len = struct.unpack('<H', data[start+26:start+28])[0]
                    extra_len = struct.unpack('<H', data[start+28:start+30])[0]
                    
                    if name_len > 1024 or extra_len > 4096: continue
                    
                    filename_entry = data[start+30 : start+30+name_len].decode('utf-8', 'ignore')
                    data_start = start + 30 + name_len + extra_len
                    
                    # Find Data Descriptor (PK\x07\x08)
                    dd_sig = b'\x50\x4B\x07\x08'
                    dd_idx = data.find(dd_sig, data_start)
                    if dd_idx == -1: continue
                    
                    file_data = data[data_start : dd_idx]
                    
                    content = None
                    if method == 0: 
                        content = file_data
                    elif method == 8:
                        try: content = zlib.decompress(file_data, -15)
                        except: 
                            try: content = zlib.decompress(file_data)
                            except: pass
                    
                    if content is not None:
                        carved_files[filename_entry] = content
                        count += 1
                        
                    next_off = dd_idx + 16 
                    
                except Exception:
                    pass

            if count > 0:
                logger.info(f"Carved {len(carved_files)} files. Repacking...")
                if progress_callback: progress_callback(85)
                
                with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as epub:
                    # 1. Write mimetype first (STORED)
                    if "mimetype" in carved_files:
                        epub.writestr("mimetype", carved_files["mimetype"], compress_type=zipfile.ZIP_STORED)
                    else:
                        epub.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
                        
                    # 2. Write everything else
                    for name, content in carved_files.items():
                        if name == "mimetype": continue
                        epub.writestr(name, content)
                
                if progress_callback: progress_callback(100)
                return True
            else:
                logger.error("No ZIP entries found in blob.")
                return False
                    
        except Exception as e:
            logger.error(f"Carve failed: {e}")
            return False
