import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
MODULE = SourceFileLoader("fktv_spider", str(ROOT / "凡客TV.py")).load_module()
Spider = MODULE.Spider


class TestFKTVSpider(unittest.TestCase):
    def setUp(self):
        Spider._instance = None
        self.spider = Spider()
        self.spider.init()

    def test_home_content_returns_expected_classes(self):
        result = self.spider.homeContent(False)
        self.assertEqual(
            result["class"],
            [
                {"type_id": "1", "type_name": "电影"},
                {"type_id": "2", "type_name": "剧集"},
                {"type_id": "4", "type_name": "动漫"},
                {"type_id": "3", "type_name": "综艺"},
                {"type_id": "8", "type_name": "短剧"},
                {"type_id": "6", "type_name": "纪录片"},
                {"type_id": "7", "type_name": "解说"},
                {"type_id": "5", "type_name": "音乐"},
            ],
        )

    def test_encode_and_decode_play_id_round_trip(self):
        encoded = self.spider._encode_play_id(
            {
                "movie_id": "9001",
                "link_id": "ep-1",
                "line_id": "line-a",
                "line_name": "线路A",
                "episode_name": "第1集",
                "type": "switch",
                "page": "https://fktv.me/movie/detail/9001",
            }
        )
        payload = self.spider._decode_play_id(encoded)
        self.assertEqual(payload["movie_id"], "9001")
        self.assertEqual(payload["link_id"], "ep-1")
        self.assertEqual(payload["line_id"], "line-a")
        self.assertEqual(payload["episode_name"], "第1集")
        self.assertEqual(payload["page"], "https://fktv.me/movie/detail/9001")

    @patch.object(Spider, "_request_html")
    def test_category_content_builds_url_and_parses_cards(self, mock_request_html):
        mock_request_html.return_value = """
        <div class="card-wrap">
          <div class="meta-wrap">
            <a class="normal-title" href="/movie/detail/abc123" title="示例电影">示例电影</a>
            <img class="lazy-load" data-src="/poster.jpg" />
            <span class="tag">电影</span>
            <span class="tag">更新中</span>
          </div>
        </div>
        """
        result = self.spider.categoryContent("1", "2", False, {})
        self.assertEqual(
            mock_request_html.call_args.args[0],
            "https://fktv.me/channel?page=2&cat_id=1&page_size=32&order=new",
        )
        self.assertEqual(
            result["list"],
            [
                {
                    "vod_id": "abc123",
                    "vod_name": "示例电影",
                    "vod_pic": "https://fktv.me/poster.jpg",
                    "vod_remarks": "电影 | 更新中",
                    "type_name": "电影",
                }
            ],
        )
        self.assertNotIn("pagecount", result)

    @patch.object(Spider, "_request_html")
    def test_search_content_builds_url_and_handles_blank_keyword(self, mock_request_html):
        blank = self.spider.searchContent("", False, "1")
        self.assertEqual(blank, {"page": 1, "limit": 0, "total": 0, "list": []})
        mock_request_html.assert_not_called()

        mock_request_html.return_value = """
        <div class="hover-wrap">
          <a class="hover-title" href="/movie/detail/xyz789" title="搜索影片">搜索影片</a>
          <img class="lazy-load" data-src="https://img.example/search.jpg" />
          <span class="tag">剧集</span>
        </div>
        """
        result = self.spider.searchContent("繁花", False, "3")
        self.assertEqual(
            mock_request_html.call_args.args[0],
            "https://fktv.me/search?keyword=%E7%B9%81%E8%8A%B1",
        )
        self.assertEqual(result["page"], 3)
        self.assertEqual(result["list"][0]["vod_id"], "xyz789")


if __name__ == "__main__":
    unittest.main()
