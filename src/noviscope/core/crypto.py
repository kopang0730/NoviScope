from base64 import urlsafe_b64encode
from hashlib import sha256

from cryptography.fernet import Fernet


class SecretBox:
    def __init__(self, secret_key: str) -> None:
        key = urlsafe_b64encode(sha256(secret_key.encode("utf-8")).digest())
        self._fernet = Fernet(key)

    def encrypt(self, value: str) -> str:
        return self._fernet.encrypt(value.encode("utf-8")).decode("utf-8")

    def decrypt(self, ciphertext: str) -> str:
        return self._fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
