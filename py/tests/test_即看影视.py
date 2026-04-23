import base64
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad
except ModuleNotFoundError:
    from Cryptodome.Cipher import AES
    from Cryptodome.Util.Padding import pad


ROOT = Path(__file__).resolve().parents[1]
MODULE = SourceFileLoader("jikanyingshi_spider", str(ROOT / "即看影视.py")).load_module()
Spider = MODULE.Spider


def build_sk_payload(value, key, iv):
    cipher = AES.new(key.encode("utf-8"), AES.MODE_CBC, iv.encode("utf-8"))
    encrypted = cipher.encrypt(pad(value.encode("utf-8"), AES.block_size)).hex()
    return "FROMSKZZJM" + encrypted


class TestJiKanYingShiSpider(unittest.TestCase):
    def setUp(self):
        Spider._instance = None
        self.spider = Spider()
        self.spider.init()

    @patch.object(Spider, "fetch")
    def test_resolve_api_host_reads_appipr_txt(self, mock_fetch):
        mock_fetch.return_value = SimpleNamespace(text="https://appsky2025999.ideasz.net\n")
        self.assertEqual(self.spider._resolve_api_host(), "https://appsky2025999.ideasz.net")

    def test_sk_decrypt_returns_plain_text_without_prefix(self):
        self.assertEqual(self.spider._sk_decrypt("plain-text"), "plain-text")

    def test_sk_decrypt_decodes_prefixed_ciphertext(self):
        encrypted = build_sk_payload('{"msg":"ok"}', self.spider.aes_key, self.spider.aes_iv)
        self.assertEqual(self.spider._sk_decrypt(encrypted), '{"msg":"ok"}')

    def test_ck_encrypt_returns_base64_ascii(self):
        result = self.spider._ck_encrypt("https://host##5483##1700000000000##ckzmbc")
        decoded = base64.b64decode(result.encode("utf-8")).decode("utf-8")
        self.assertTrue(decoded)


if __name__ == "__main__":
    unittest.main()
