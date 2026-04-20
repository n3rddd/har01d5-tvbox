# coding=utf-8
import base64
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
        self.name = "魔方APP"
        self.host = "http://www.613mf4k12.top"
        self.api_path = "/api.php/getappapi"
        self.user_agent = "okhttp/3.10.0"
        self.aes_key = "1234567887654321"
        self.aes_iv = "1234567887654321"

    def init(self, extend=""):
        self.init_api = "initV119"
        self.search_api = "searchList"
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
        cipher = AES.new(self.aes_key.encode("utf-8"), AES.MODE_CBC, self.aes_iv.encode("utf-8"))
        return base64.b64encode(cipher.encrypt(pad(str(text).encode("utf-8"), AES.block_size))).decode("utf-8")

    def _aes_decrypt(self, text):
        cipher = AES.new(self.aes_key.encode("utf-8"), AES.MODE_CBC, self.aes_iv.encode("utf-8"))
        return unpad(cipher.decrypt(base64.b64decode(str(text or ""))), AES.block_size).decode("utf-8")

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
