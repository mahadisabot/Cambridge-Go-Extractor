import sys

def check_consistency(filepath):
    with open(filepath, 'rb') as f:
        data = bytearray(f.read(100))
    
    # Define constraints
    # Key indices: 0..19.
    # We check consistency where we have multiple known plaintexts for the SAME key index.
    
    # Plaintext map: {offset: byte_val}
    vals = {}
    
    # PK Header
    vals[0]=0x50; vals[1]=0x4B; vals[2]=0x03; vals[3]=0x04
    
    # Compression (Stored)
    vals[8]=0x00; vals[9]=0x00
    
    # NameLen (8)
    vals[26]=0x08; vals[27]=0x00
    
    # ExtraLen (0)
    vals[28]=0x00; vals[29]=0x00
    
    # mimetype
    mm = b"mimetype" # len 8
    # offsets 30-37
    for i in range(8): vals[30+i] = mm[i]
        
    # content
    cc = b"application/epub+zip" # len 20
    # offsets 38-57
    for i in range(20): vals[38+i] = cc[i]
    
    # Check consistency
    for k in range(20):
        # Gather all derivations for this key index
        derivations = []
        for off, pval in vals.items():
            if off % 20 == k:
                d = data[off] ^ pval
                derivations.append((off, d))
        
        if len(derivations) > 1:
            # Check if all d are same
            first = derivations[0][1]
            match = all(x[1] == first for x in derivations)
            status = "MATCH" if match else "MISMATCH"
            print(f"Key[{k:2d}]: {status} {derivations}")
        elif len(derivations) == 1:
             print(f"Key[{k:2d}]: SINGLE {derivations}")
        else:
             print(f"Key[{k:2d}]: UNKNOWN")

check_consistency(sys.argv[1])
