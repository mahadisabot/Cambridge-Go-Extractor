import re
import os
import glob
import struct

def verify_sibling_link():
    paths_dir = os.path.expandvars(r"%LOCALAPPDATA%\Cambridge Reader\User Data\Default\File System\000\p\Paths")
    logs = glob.glob(os.path.join(paths_dir, "*"))
    
    print(f"Scanning logs for sibling relationships...")
    
    # We want to find:
    # 1. A parent P that contains an EPUB (e.g. 1487)
    # 2. The SAME parent P that contains a small file (e.g. 1, 2, ... 16)
    
    parent_map = {} # ParentID -> [List of Children IDs]
    
    for log in logs:
        try:
            with open(log, 'rb') as f:
                data = f.read()
                
            # Regex: CHILD_OF:(ParentID):(ChildID)
            # Catch decimal IDs
            matches = re.finditer(rb'CHILD_OF:(\d+):(\d+)', data)
            for m in matches:
                pid = m.group(1).decode()
                cid = int(m.group(2))
                
                if pid not in parent_map: parent_map[pid] = set()
                parent_map[pid].add(cid)
                
        except: pass
        
    print(f"Found {len(parent_map)} parents having children.")
    
    # Analyze Parents
    for pid, children in parent_map.items():
        # Check if this parent has both a "Big ID" (EPUB) and a "Small ID" (Cover)
        # Small IDs are < 100 (based on my Orphan scan showing 1-16)
        # Big IDs are > 1000 (usually)
        
        small_children = sorted([c for c in children if c < 50])
        big_children = sorted([c for c in children if c > 50])
        
        if small_children and big_children:
            print(f"\n[PARENT {pid}]")
            print(f"  Covers? (Small IDs): {small_children}")
            print(f"  Books?  (Big IDs):   {big_children}")
            
            # If we find this pattern, it PROVES the link.
            # Parent 56 seems to be the "Bookshelf" directory?
            
if __name__ == "__main__":
    verify_sibling_link()
