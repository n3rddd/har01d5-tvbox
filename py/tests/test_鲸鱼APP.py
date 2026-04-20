import json
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE = SourceFileLoader("jingyu_spider", str(ROOT / "鲸鱼APP.py")).load_module()
Spider = MODULE.Spider


class TestJingyuSpider(unittest.TestCase):
    def setUp(self):
        Spider._instance = None
        self.spider = Spider()

    def test_aes_encrypt_decrypt_roundtrip(self):
        plaintext = '{"key":"value"}'
        encrypted = self.spider._aes_encrypt(plaintext)
        decrypted = self.spider._aes_decrypt(encrypted)
        self.assertEqual(decrypted, plaintext)

    def test_aes_encrypt_produces_base64(self):
        import re
        encrypted = self.spider._aes_encrypt("hello")
        self.assertTrue(re.match(r'^[A-Za-z0-9+/=]+$', encrypted))

    def test_api_post_decrypts_response(self):
        payload = {"result": "ok"}
        encrypted = self.spider._aes_encrypt(json.dumps(payload))

        class FakeResponse:
            status_code = 200
            encoding = "utf-8"
            def json(self):
                return {"data": encrypted}

        self.spider.post = lambda url, **kwargs: FakeResponse()
        self.spider.host = "http://test.com"
        result = self.spider._api_post("someEndpoint")
        self.assertEqual(result, payload)

    def test_init_fetches_host_from_site_url(self):
        init_encrypted = self.spider._aes_encrypt(json.dumps({"type_list": []}))

        class FakeInitResponse:
            status_code = 200
            encoding = "utf-8"
            text = "http://example.com"
            def json(self):
                return {"data": init_encrypted}

        self.spider.fetch = lambda url, **kwargs: FakeInitResponse()
        self.spider.post = lambda url, **kwargs: FakeInitResponse()
        self.spider.init()
        self.assertEqual(self.spider.host, "http://example.com")

    def test_process_classes_blocks_and_sorts(self):
        type_list = [
            {"type_id": "0", "type_name": "全部"},
            {"type_id": "1", "type_name": "电影"},
            {"type_id": "3", "type_name": "综艺"},
            {"type_id": "2", "type_name": "电视剧"},
            {"type_id": "4", "type_name": "动漫"},
        ]
        classes = self.spider._process_classes(type_list)
        names = [c["type_name"] for c in classes]
        self.assertNotIn("全部", names)
        self.assertEqual(names, ["电影", "电视剧", "综艺", "动漫"])

    def test_process_area_filter_merges_mainland_areas(self):
        areas = ["全部", "中国大陆", "大陆", "内地", "美国", "日本"]
        result = self.spider._process_area_filter(areas)
        self.assertIn("大陆", result)
        self.assertNotIn("中国大陆", result)
        self.assertNotIn("内地", result)
        self.assertIn("美国", result)

    def test_convert_filters_adds_current_year(self):
        import datetime
        type_list = [{
            "type_id": "1",
            "filter_type_list": [
                {"name": "year", "list": ["全部", "2024"]},
                {"name": "area", "list": ["全部", "中国大陆"]},
            ]
        }]
        current = str(datetime.datetime.now().year)
        filters = self.spider._convert_filters(type_list)
        year_values = [v["v"] for v in filters["1"][0]["value"]]
        self.assertIn(current, year_values)
        area_values = [v["v"] for v in filters["1"][1]["value"]]
        self.assertIn("大陆", area_values)
        self.assertNotIn("中国大陆", area_values)

    def test_category_content_posts_filter_payload(self):
        encrypted_empty = self.spider._aes_encrypt(json.dumps({"recommend_list": []}))

        class FakeRsp:
            status_code = 200
            encoding = "utf-8"
            def json(self):
                return {"data": encrypted_empty}

        self.spider.post = lambda url, **kwargs: FakeRsp()
        self.spider.host = "http://test.com"
        self.spider.init_data = {}
        result = self.spider.categoryContent("1", "2", False, {"area": "美国", "year": "2025"})
        self.assertEqual(result["page"], 2)
        self.assertNotIn("pagecount", result)
        self.assertEqual(result["list"], [])

    def test_category_content_merges_area_when_mainland_selected(self):
        items_a = [{"vod_id": "1", "vod_name": "A", "vod_pic": "", "vod_remarks": ""}]
        items_b = [{"vod_id": "2", "vod_name": "B", "vod_pic": "", "vod_remarks": ""},
                    {"vod_id": "1", "vod_name": "A", "vod_pic": "", "vod_remarks": ""}]

        call_idx = {"n": 0}

        def fake_api_post(endpoint, payload=None):
            call_idx["n"] += 1
            if call_idx["n"] == 1:
                return {"recommend_list": items_a}
            return {"recommend_list": items_b}

        self.spider._api_post = fake_api_post
        self.spider.host = "http://test.com"
        self.spider.init_data = {}
        result = self.spider.categoryContent("1", "1", False, {"area": "大陆"})
        ids = [v["vod_id"] for v in result["list"]]
        self.assertEqual(len(ids), 2)
        self.assertIn("1", ids)
        self.assertIn("2", ids)
