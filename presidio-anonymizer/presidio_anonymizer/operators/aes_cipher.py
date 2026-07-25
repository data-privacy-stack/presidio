import base64
import os

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


class AESCipher:
    """Advanced Encryption Standard (aka Rijndael) en/decryption in CBC mode."""

    @staticmethod
    def encrypt(key: bytes, text: str) -> str:
        """
        Encrypts a text using AES cypher in CBC mode.

        Uses padding and random IV.
        :param key: AES encryption key in bytes.
        :param text: The text for encryption.
        :returns: The encrypted text.
        """
        encoded_text = text.encode("utf-8")
        padder = padding.PKCS7(algorithms.AES.block_size).padder()
        padded_text = padder.update(encoded_text) + padder.finalize()
        iv = os.urandom(16)
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
        encryptor = cipher.encryptor()
        encrypted_text = base64.urlsafe_b64encode(
            iv + encryptor.update(padded_text) + encryptor.finalize()
        )
        return encrypted_text.decode()

    @staticmethod
    def decrypt(key: bytes, text: str) -> str:
        """
        Decrypts a previously AES-CBC encrypted text.

        :param key: AES encryption key in bytes.
        :param text: The text for decryption.
        :returns: The decrypted text.
        """
        decoded_text = base64.urlsafe_b64decode(text)
        iv = decoded_text[:16]
        ct = decoded_text[16:]
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
        decryptor = cipher.decryptor()
        unpadder = padding.PKCS7(128).unpadder()
        decrypted_text = decryptor.update(ct) + decryptor.finalize()
        return (unpadder.update(decrypted_text) + unpadder.finalize()).decode("utf-8")
    @staticmethod
    def is_valid_key_size(key: bytes) -> bool:
        """
        Validate key size for AES.

        :param key: AES encryption key in bytes.
        :returns: True if the key is of valid size, False otherwise.
        """
        return len(key) * 8 in algorithms.AES.key_sizes
