# coding=utf-8
import base64
import sys

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7

from base.spider import Spider as BaseSpider

sys.path.append("..")


class Spider(BaseSpider):
    def __init__(self):
        self.name = "黑猫APP"
        self.host = "http://app1-0-0.87333.cc"
        self.api_path = "/api.php/getappapi"
        self.user_agent = "okhttp/3.10.0"
        self.aes_key = "VwsHxkCViDXEExWa"
        self.aes_iv = "VwsHxkCViDXEExWa"

    def init(self, extend=""):
        self.search_api = "searchList"
        self.init_api = "initV119"
        self.search_verify = False
        return None

    def getName(self):
        return self.name

    def homeVideoContent(self):
        return {"list": []}

    def _build_api_url(self, endpoint):
        path = str(endpoint or "").lstrip("/")
        return f"{self.host}{self.api_path}.index/{path}"

    def _aes_encrypt(self, text):
        padder = PKCS7(128).padder()
        data = padder.update(str(text).encode("utf-8")) + padder.finalize()
        cipher = Cipher(algorithms.AES(self.aes_key.encode("utf-8")), modes.CBC(self.aes_iv.encode("utf-8")))
        encryptor = cipher.encryptor()
        return base64.b64encode(encryptor.update(data) + encryptor.finalize()).decode("utf-8")

    def _aes_decrypt(self, text):
        data = base64.b64decode(str(text or ""))
        cipher = Cipher(algorithms.AES(self.aes_key.encode("utf-8")), modes.CBC(self.aes_iv.encode("utf-8")))
        decryptor = cipher.decryptor()
        padded = decryptor.update(data) + decryptor.finalize()
        unpadder = PKCS7(128).unpadder()
        return (unpadder.update(padded) + unpadder.finalize()).decode("utf-8")

    def _replace_code(self, text):
        replacements = {
            "y": "9",
            "口": "0",
            "q": "0",
            "u": "0",
            "o": "0",
            ">": "1",
            "d": "0",
            "b": "8",
            "已": "2",
            "D": "0",
            "五": "5",
        }
        return "".join(replacements.get(char, char) for char in str(text or ""))
