import unittest
from datetime import datetime
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest.mock import patch


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

    @patch.object(Spider, "_api_post")
    def test_home_content_filters_categories_merges_area_and_inserts_current_year(self, mock_api_post):
        mock_api_post.return_value = {
            "type_list": [
                {
                    "type_id": "6",
                    "type_name": "伦理",
                    "recommend_list": [],
                    "filter_type_list": [],
                },
                {
                    "type_id": "3",
                    "type_name": "综艺",
                    "recommend_list": [{"vod_id": "z1"}],
                    "filter_type_list": [
                        {"name": "area", "list": ["全部", "中国大陆", "香港"]},
                        {"name": "year", "list": ["全部", "2025", "2024"]},
                        {"name": "sort", "list": ["最新", "最热"]},
                    ],
                },
                {
                    "type_id": "1",
                    "type_name": "电影",
                    "recommend_list": [{"vod_id": "m1"}],
                    "filter_type_list": [],
                },
            ],
            "config": {},
        }
        content = self.spider.homeContent(False)
        self.assertEqual([item["type_name"] for item in content["class"]], ["电影", "综艺"])
        self.assertEqual(content["list"], [{"vod_id": "z1"}, {"vod_id": "m1"}])
        area_values = content["filters"]["3"][0]["value"]
        year_values = content["filters"]["3"][1]["value"]
        self.assertEqual(area_values[1], {"n": "大陆", "v": "大陆"})
        self.assertIn({"n": str(datetime.now().year), "v": str(datetime.now().year)}, year_values)
        self.assertEqual(content["filters"]["3"][2]["key"], "by")

    @patch.object(Spider, "_api_post")
    def test_category_content_maps_by_to_sort_and_omits_pagecount(self, mock_api_post):
        mock_api_post.return_value = {
            "recommend_list": [{"vod_id": "movie-1", "vod_name": "分类片"}]
        }
        result = self.spider.categoryContent(
            "1",
            "2",
            False,
            {"area": "香港", "year": "2025", "by": "最热", "lang": "粤语", "class": "动作"},
        )
        self.assertEqual(
            mock_api_post.call_args.args,
            (
                "typeFilterVodList",
                {
                    "type_id": "1",
                    "page": "2",
                    "area": "香港",
                    "year": "2025",
                    "sort": "最热",
                    "lang": "粤语",
                    "class": "动作",
                },
            ),
        )
        self.assertEqual(result["page"], 2)
        self.assertEqual(result["list"][0]["vod_id"], "movie-1")
        self.assertNotIn("pagecount", result)

    @patch.object(Spider, "_api_post")
    def test_category_content_merges_mainland_results_and_deduplicates(self, mock_api_post):
        mock_api_post.side_effect = [
            {"recommend_list": [{"vod_id": "a"}, {"vod_id": "b"}]},
            {"recommend_list": [{"vod_id": "b"}, {"vod_id": "c"}]},
            {"recommend_list": [{"vod_id": "c"}, {"vod_id": "d"}]},
        ]
        result = self.spider.categoryContent("1", "1", False, {"area": "大陆"})
        self.assertEqual([item["vod_id"] for item in result["list"]], ["a", "b", "c", "d"])
        self.assertEqual(
            [call.args[1]["area"] for call in mock_api_post.call_args_list],
            ["中国大陆", "大陆", "内地"],
        )

    @patch.object(Spider, "_api_post")
    def test_search_content_filters_ethics_and_non_matching_items(self, mock_api_post):
        mock_api_post.return_value = {
            "search_list": [
                {"vod_id": "1", "vod_name": "繁花", "vod_pic": "p1", "vod_year": "2024", "vod_class": "剧情"},
                {"vod_id": "2", "vod_name": "别的片", "vod_pic": "p2", "vod_year": "2024", "vod_class": "伦理"},
                {"vod_id": "3", "vod_name": "完全无关", "vod_pic": "p3", "vod_year": "2023", "vod_class": "动作"},
            ]
        }
        result = self.spider.searchContent("繁花", False, "1")
        self.assertEqual(
            result["list"],
            [{"vod_id": "1", "vod_name": "繁花", "vod_pic": "p1", "vod_remarks": "2024 剧情"}],
        )
        self.assertNotIn("pagecount", result)


if __name__ == "__main__":
    unittest.main()
