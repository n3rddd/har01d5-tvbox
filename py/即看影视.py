# coding=utf-8
import base64
import hashlib
import sys

try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad, unpad
except ModuleNotFoundError:
    from Cryptodome.Cipher import AES
    from Cryptodome.Util.Padding import pad, unpad

from base.spider import Spider as BaseSpider

sys.path.append("..")


class Spider(BaseSpider):
    def __init__(self):
        self.name = "即看影视"
        self.host_config_url = "https://skyappdata-1321528676.cos.accelerate.myqcloud.com/4kapp/appipr.txt"
        self.aes_key = "ygcnbckhcuvygdyb"
        self.aes_iv = "4023892775143708"
        self.ck_key = "ygcnbcrvaervztmw"
        self.ck_iv = "1212164105143708"
        self.user_agent = "Dart/2.10 (dart:io)"
        self.headers = {
            "User-Agent": self.user_agent,
            "Accept-Encoding": "gzip",
        }
        self.api_host = ""
        self.auth_token = ""
        self.config_data = {}
        self.is_ready = False

    def init(self, extend=""):
        return None

    def getName(self):
        return self.name

    def _resolve_api_host(self):
        response = self.fetch(self.host_config_url, headers=self.headers, timeout=10, verify=False)
        return str(getattr(response, "text", "")).strip().rstrip("/")

    def _md5(self, text):
        return hashlib.md5(str(text).encode("utf-8")).hexdigest()

    def _sk_decrypt(self, text):
        value = str(text or "")
        prefix = "FROMSKZZJM"
        if not value.startswith(prefix):
            return value
        encrypted_hex = value[len(prefix):]
        cipher = AES.new(self.aes_key.encode("utf-8"), AES.MODE_CBC, self.aes_iv.encode("utf-8"))
        return unpad(cipher.decrypt(bytes.fromhex(encrypted_hex)), AES.block_size).decode("utf-8")

    def _ck_encrypt(self, text):
        first = base64.b64encode(str(text).encode("utf-8"))
        second = base64.b64encode(first)
        cipher = AES.new(self.ck_key.encode("utf-8"), AES.MODE_CBC, self.ck_iv.encode("utf-8"))
        encrypted = cipher.encrypt(pad(second, AES.block_size)).hex()
        return base64.b64encode(encrypted.encode("utf-8")).decode("utf-8")
