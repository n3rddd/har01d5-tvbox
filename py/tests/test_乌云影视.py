import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE = SourceFileLoader("wooyun_spider", str(ROOT / "乌云影视.py")).load_module()
Spider = MODULE.Spider


class TestWooyunSpider(unittest.TestCase):
    def setUp(self):
        Spider._instance = None
        self.spider = Spider()
        self.spider.init()

    def test_home_content_builds_classes_and_filters_from_menu(self):
        menu = [
            {"code": "movie", "name": "电影"},
            {"code": "tv_series", "name": "电视剧"},
            {"code": "animation", "name": "动画"},
            {"code": "variety", "name": "综艺"},
            {"code": "short_drama", "name": "短剧"},
            {
                "nameEn": "year",
                "children": [
                    {"code": "THIS_YEAR", "name": "今年"},
                    {"code": "LAST_YEAR", "name": "去年"},
                    {"code": "2024", "name": "2024"},
                ],
            },
            {
                "nameEn": "region",
                "children": [{"code": "CN", "name": "大陆"}],
            },
            {
                "nameEn": "genre",
                "children": [{"code": "COMEDY", "name": "喜剧"}],
            },
            {
                "nameEn": "language",
                "children": [{"code": "ZH", "name": "国语"}],
            },
        ]

        self.spider._request_json = lambda path, method="GET", data=None, headers=None: menu
        content = self.spider.homeContent(False)

        self.assertEqual(
            [item["type_id"] for item in content["class"]],
            ["movie", "tv_series", "animation", "variety", "short_drama", "THIS_YEAR", "LAST_YEAR"],
        )
        self.assertEqual(content["filters"]["movie"][0]["key"], "year")
        self.assertEqual(content["filters"]["movie"][1]["key"], "region")
        self.assertEqual(content["filters"]["movie"][2]["key"], "genre")
        self.assertEqual(content["filters"]["movie"][3]["key"], "lang")
        self.assertEqual(content["filters"]["movie"][4]["key"], "sort")

    def test_request_json_uses_post_for_json_payload(self):
        calls = {}

        class FakeResponse:
            def __init__(self):
                self.status_code = 200
                self.text = ""

            def json(self):
                return {"data": {"records": []}}

        def fake_post(
            url,
            json=None,
            headers=None,
            timeout=5,
            verify=True,
            stream=False,
            allow_redirects=True,
            params=None,
            data=None,
            cookies=None,
        ):
            calls["url"] = url
            calls["json"] = json
            calls["headers"] = headers
            return FakeResponse()

        self.spider.post = fake_post
        result = self.spider._request_json(
            "/movie/media/search",
            method="POST",
            data={"pageIndex": "1"},
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(calls["url"], "https://wooyun.tv/movie/media/search")
        self.assertEqual(calls["json"], {"pageIndex": "1"})
        self.assertEqual(calls["headers"]["Origin"], "https://wooyun.tv")
        self.assertEqual(result, {"records": []})

    def test_build_category_body_handles_year_shortcuts_and_filters(self):
        body = self.spider._build_category_body(
            "THIS_YEAR",
            "3",
            {"region": "CN", "year": "2025", "lang": "ZH", "sort": "hot"},
        )
        self.assertEqual(body["menuCodeList"], ["THIS_YEAR", "CN", "2025", "ZH"])
        self.assertEqual(body["pageIndex"], "3")
        self.assertEqual(body["sortCode"], "hot")
        self.assertEqual(body["topCode"], "movie")


if __name__ == "__main__":
    unittest.main()
