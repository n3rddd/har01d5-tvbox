import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
MODULE = SourceFileLoader("lumman_spider", str(ROOT / "路漫漫.py")).load_module()
Spider = MODULE.Spider

SAMPLE_LIST_HTML = """
<html><body>
<div class="video-img-box">
  <a href="/vod/detail/1001.html">
    <img class="lazyload" data-src="/upload/1001.jpg" />
    <h6 class="title">海贼王</h6>
    <div class="label">更新至1123集</div>
  </a>
</div>
<div class="video-img-box">
  <a href="/vod/detail/1002.html">
    <img class="lazyload" src="https://img.example.com/1002.jpg" />
    <h6 class="title">你的名字</h6>
    <div class="label">全集</div>
  </a>
</div>
</body></html>
"""


class TestLuManManSpider(unittest.TestCase):
    def setUp(self):
        Spider._instance = None
        self.spider = Spider()
        self.spider.init()

    def test_home_content_returns_only_animation_classes(self):
        result = self.spider.homeContent(False)
        self.assertEqual(
            result["class"],
            [
                {"type_id": "6", "type_name": "日本动漫"},
                {"type_id": "7", "type_name": "国产动漫"},
                {"type_id": "8", "type_name": "欧美动漫"},
                {"type_id": "3", "type_name": "日本动画电影"},
                {"type_id": "4", "type_name": "国产动画电影"},
                {"type_id": "5", "type_name": "欧美动画电影"},
            ],
        )

    @patch.object(Spider, "_get_html")
    def test_home_video_content_parses_cards(self, mock_html):
        mock_html.return_value = SAMPLE_LIST_HTML
        result = self.spider.homeVideoContent()
        self.assertEqual(len(result["list"]), 2)
        self.assertEqual(result["list"][0]["vod_id"], "vod/detail/1001.html")
        self.assertEqual(result["list"][0]["vod_pic"], "https://www.lmm85.com/upload/1001.jpg")
        self.assertEqual(result["list"][1]["vod_pic"], "https://img.example.com/1002.jpg")

    @patch.object(Spider, "_get_html")
    def test_category_content_builds_filtered_url(self, mock_html):
        mock_html.return_value = SAMPLE_LIST_HTML
        result = self.spider.categoryContent("6", "2", False, {"年代": "/year/2024", "排序": "/by/time"})
        self.assertEqual(result["page"], 2)
        self.assertEqual(len(result["list"]), 2)
        mock_html.assert_called_with("https://www.lmm85.com/vod/show/id/6/year/2024/by/time/page/2.html")

    @patch.object(Spider, "_get_html")
    def test_search_content_uses_search_path(self, mock_html):
        mock_html.return_value = SAMPLE_LIST_HTML
        result = self.spider.searchContent("海贼", False, "3")
        self.assertEqual(result["page"], 3)
        self.assertEqual(result["list"][0]["vod_name"], "海贼王")
        mock_html.assert_called_with("https://www.lmm85.com/vod/search/page/3/wd/%E6%B5%B7%E8%B4%BC.html")


if __name__ == "__main__":
    unittest.main()
