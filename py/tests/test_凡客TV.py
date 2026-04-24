import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path


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


if __name__ == "__main__":
    unittest.main()
