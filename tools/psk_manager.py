import os
import hashlib
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

class PSKManager:
    """
    Security Engine: Implements Pre-Shared Key (PSK) support.
    Allows private sub-meshes to encrypt their spikes.
    """
    def __init__(self, secret_key: str):
        # Derive a 32-byte key from the secret string
        self.key = hashlib.sha256(secret_key.encode()).digest()

    def encrypt_payload(self, data: bytes) -> bytes:
        """ Encrypts mesh traffic using AES-GCM. """
        nonce = os.urandom(12)
        cipher = Cipher(algorithms.AES(self.key), modes.GCM(nonce), backend=default_backend())
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(data) + encryptor.finalize()
        return nonce + encryptor.tag + ciphertext

    def decrypt_payload(self, encrypted_data: bytes) -> bytes:
        """ Decrypts mesh traffic. Returns None if key is wrong. """
        try:
            nonce = encrypted_data[:12]
            tag = encrypted_data[12:28]
            ciphertext = encrypted_data[28:]
            cipher = Cipher(algorithms.AES(self.key), modes.GCM(nonce, tag), backend=default_backend())
            decryptor = cipher.decryptor()
            return decryptor.update(ciphertext) + decryptor.finalize()
        except Exception:
            return None

# --- Verification Test ---
if __name__ == "__main__":
    psk = PSKManager("Austin_Genesis_2026")
    
    original_msg = b"Sensitive Neural Spike Data"
    encrypted = psk.encrypt_payload(original_msg)
    
    # Correct key test
    decrypted = psk.decrypt_payload(encrypted)
    print(f"Decrypted: {decrypted.decode()}")
    
    # Wrong key test
    attacker_psk = PSKManager("Wrong_Key")
    failed_decryption = attacker_psk.decrypt_payload(encrypted)
    
    if decrypted == original_msg and failed_decryption is None:
        print("\nSUCCESS: PSK Security correctly isolates private sub-meshes.")
