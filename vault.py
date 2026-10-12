import json
import os
import base64
import tempfile
import uuid
from crypto_utils import derive_key, encrypt_data, decrypt_data

class Vault:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.key = None
        self.entries = {}

    def is_initialized(self) -> bool:
        return os.path.exists(self.filepath)

    def initialize(self, password: str):
        """Creates a new empty vault."""
        self.entries = {}
        salt = os.urandom(16)
        self.key = derive_key(password, salt)
        self._save(salt)

    def unlock(self, password: str):
        """Decrypts and loads the vault."""
        with open(self.filepath, 'r') as f:
            envelope = json.load(f)
        
        salt = base64.b64decode(envelope['salt'])
        nonce = base64.b64decode(envelope['nonce'])
        ciphertext = base64.b64decode(envelope['ciphertext'])

        self.key = derive_key(password, salt)
        
        plaintext = decrypt_data(self.key, nonce, ciphertext)
        self.entries = json.loads(plaintext.decode('utf-8'))

    def lock(self):
        """Clears memory secrets. Python garbage collection handles the rest."""
        self.entries = {}
        if self.key:
            # Overwrite key in memory as a best-effort cleanup
            self.key = b'\x00' * len(self.key)
            self.key = None

    def change_password(self, new_password: str):
        """Re-encrypts the vault with a new key and new salt."""
        new_salt = os.urandom(16)
        self.key = derive_key(new_password, new_salt)
        self._save(new_salt)

    def _save(self, salt: bytes = None):
        """Serializes, encrypts, and atomically writes the vault to disk."""
        if not self.key:
            raise RuntimeError("Vault is locked.")
        
        if salt is None:
            # If re-saving an existing vault, reuse the old salt but generate a new nonce
            with open(self.filepath, 'r') as f:
                salt = base64.b64decode(json.load(f)['salt'])

        plaintext = json.dumps(self.entries).encode('utf-8')
        nonce, ciphertext = encrypt_data(self.key, plaintext)

        envelope = {
            'salt': base64.b64encode(salt).decode('utf-8'),
            'nonce': base64.b64encode(nonce).decode('utf-8'),
            'ciphertext': base64.b64encode(ciphertext).decode('utf-8')
        }

        # Atomic write: Write to temp file, fsync to hardware, then replace original
        dir_name = os.path.dirname(self.filepath) or '.'
        fd, temp_path = tempfile.mkstemp(dir=dir_name, text=True)
        try:
            with os.fdopen(fd, 'w') as f:
                json.dump(envelope, f)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_path, self.filepath)
        except Exception as e:
            os.remove(temp_path)
            raise e

    def add_entry(self, site, username, password, notes):
        entry_id = str(uuid.uuid4())
        self.entries[entry_id] = {
            "site": site,
            "username": username,
            "password": password,
            "notes": notes
        }
        self._save()
        return entry_id

    def delete_entry(self, entry_id):
        if entry_id in self.entries:
            del self.entries[entry_id]
            self._save()