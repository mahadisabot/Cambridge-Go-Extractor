import requests
from cambridge_api import CambridgeAPI

def probe_and_verify():
    api = CambridgeAPI()
    if not api.login("8284jade@comfythings.com", "Xd6G'GM,Q\"4g)h'"):
        print("Login failed")
        return

    # Physics Book ISBN from previous logs
    isbn = "9781108796606"
    
    # Construct base URLs
    # Base 1: OPCR URL logic
    # Base 2: SRC URL logic
    
    # From previous logs: src_url = https://elevate-s3.cambridge.org/books_data/9781108796606-54.1.1/
    # And opcr_url was .../resources/ (deduced)
    
    base_src = "https://elevate-s3.cambridge.org/books_data/9781108796606-54.1.1/"
    base_res = f"https://elevate-s3.cambridge.org/books_data/{isbn}-54.1.1/resources/" # guessed
    
    # Files to probe
    candidates = [
        "asal_physics_cb_answers.zip",
        "ASAL_Physics_CB_Answers.zip",
        "9781108796606_Answer_Key.zip",
        "9781108796606_Answers.zip",
        f"{isbn}_Answer_Key.zip",
        f"{isbn}_Answers.zip"
    ]
    
    bases = [
        base_src,
        base_src + "resources/",
        base_src + f"{isbn}_resources/",
        base_res
    ]
    
    print("--- STARTING PROBE ---")
    
    found = []
    
    for base in bases:
        for f in candidates:
            url = base + f
            try:
                # HEAD request
                h = api.session.head(url, timeout=5)
                if h.status_code == 200:
                    clen = h.headers.get('Content-Length', '0')
                    ctype = h.headers.get('Content-Type', 'unknown')
                    print(f"[HIT] {f}")
                    print(f"  URL: {url}")
                    print(f"  Size: {clen} bytes")
                    print(f"  Type: {ctype}")
                    
                    if int(clen) > 10000: # > 10KB
                         print("  --> VALID CANDIDATE (Size > 4KB)")
                         found.append(url)
                    else:
                         print("  --> INVALID (Too small, likely fake)")
            except Exception as e:
                pass
                
    if found:
        print("\n--- FOUND VALID RESOURCES ---")
        for x in found: print(x)
    else:
        print("\n--- NO VALID RESOURCES FOUND ---")

if __name__ == "__main__":
    probe_and_verify()
