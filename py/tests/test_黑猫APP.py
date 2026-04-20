import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE = SourceFileLoader("heimao_spider", str(ROOT / "黑猫APP.py")).load_module()
Spider = MODULE.Spider


class TestHeiMaoAppSpider(unittest.TestCase):
    def setUp(self):
        Spider._instance = None
        self.spider = Spider()
        self.spider.init()

    def test_home_video_content_returns_empty_list(self):
        self.assertEqual(self.spider.homeVideoContent(), {"list": []})

    def test_build_api_url_uses_default_getappapi_path(self):
        self.assertEqual(
            self.spider._build_api_url("initV119"),
            "http://app1-0-0.87333.cc/api.php/getappapi.index/initV119",
        )

    def test_aes_encrypt_and_decrypt_round_trip(self):
        encrypted = self.spider._aes_encrypt('{"msg":"ok"}')
        self.assertNotEqual(encrypted, '{"msg":"ok"}')
        self.assertEqual(self.spider._aes_decrypt(encrypted), '{"msg":"ok"}')

    def test_replace_code_normalizes_common_ocr_misreads(self):
        self.assertEqual(self.spider._replace_code("5y6口"), "5960")


if __name__ == "__main__":
    unittest.main()
