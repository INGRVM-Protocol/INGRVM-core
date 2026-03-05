import os
import hashlib
import shutil
from typing import Optional, Tuple

class CIDStorage:
    """
    Phase 6: Content-Addressed Storage (Simulated IPFS).
    Files are stored by their SHA-256 hash (CID) to ensure integrity
    and prevent duplicate weights in the mesh.
    """
    def __init__(self, root_dir: str = "neuromorphic_env/ipfs_blob"):
        self.root_dir = root_dir
        if not os.path.exists(self.root_dir):
            os.makedirs(self.root_dir, exist_ok=True)

    def _calculate_cid(self, file_path: str) -> str:
        """ Generates a 'CID' based on the file's SHA-256 hash. """
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return f"bafy{sha256_hash.hexdigest()}" # Mock IPFS V1 CID prefix

    def add_file(self, source_path: str) -> Tuple[str, str]:
        """
        Calculates CID, moves file to storage, and returns (cid, path).
        """
        if not os.path.exists(source_path):
            raise FileNotFoundError(f"Source file {source_path} not found.")

        cid = self._calculate_cid(source_path)
        dest_path = os.path.join(self.root_dir, cid)
        
        # If CID exists, we don't need to copy (deduplication)
        if not os.path.exists(dest_path):
            shutil.copy2(source_path, dest_path)
            print(f"[IPFS-MOCK] Added new blob: {cid}")
        else:
            print(f"[IPFS-MOCK] Deduplicated blob: {cid}")
            
        return cid, dest_path

    def get_file_path(self, cid: str) -> Optional[str]:
        """ Returns the path to a blob if it exists. """
        path = os.path.join(self.root_dir, cid)
        return path if os.path.exists(path) else None

    def remove_blob(self, cid: str):
        """ Deletes a blob from local storage. """
        path = os.path.join(self.root_dir, cid)
        if os.path.exists(path):
            os.remove(path)
            print(f"[IPFS-MOCK] Removed blob: {cid}")

if __name__ == "__main__":
    # Test
    storage = CIDStorage()
    # Create a dummy weight file
    test_file = "test_weights.pt"
    with open(test_file, "w") as f:
        f.write("MOCK_WEIGHT_DATA_12345")
    
    cid, path = storage.add_file(test_file)
    print(f"File CID: {cid}")
    
    # Cleanup test
    os.remove(test_file)
    if storage.get_file_path(cid):
        print("SUCCESS: CID Storage verified.")
