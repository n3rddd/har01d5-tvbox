import json
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
MODULE = SourceFileLoader("siwan_spider", str(ROOT / "四万影视.py")).load_module()
Spider = MODULE.Spider


class TestSiWanSpider(unittest.TestCase):
    def setUp(self):
        Spider._instance = None
        self.spider = Spider()
        self.spider.init()

    def _response(self, status_code=200, payload=None, text=None):
        body = text if text is not None else json.dumps(payload or {}, ensure_ascii=False)
        return SimpleNamespace(status_code=status_code, text=body)

    def test_home_content_exposes_expected_classes_and_filters(self):
        content = self.spider.homeContent(False)
        self.assertEqual(
            [item["type_id"] for item in content["class"]],
            ["20", "30", "39", "45", "32"],
        )
        self.assertEqual(
            [item["key"] for item in content["filters"]["20"]],
            ["subType", "year", "sort"],
        )
        self.assertEqual(content["filters"]["20"][0]["init"], "20")
        self.assertEqual(content["filters"]["20"][1]["value"][0], {"n": "全部", "v": ""})
        self.assertEqual(content["filters"]["20"][2]["value"][0], {"n": "时间", "v": "time"})

    def test_home_video_content_returns_empty_list(self):
        self.assertEqual(self.spider.homeVideoContent(), {"list": []})

    @patch.object(Spider, "fetch")
    def test_api_get_requests_maccms_endpoint_with_browser_headers(self, mock_fetch):
        mock_fetch.return_value = self._response(payload={"list": []})
        data = self.spider._api_get({"ac": "detail", "pg": 1})
        self.assertEqual(data, {"list": []})
        self.assertEqual(mock_fetch.call_args.args[0], "https://40000.me/api/maccms")
        self.assertEqual(mock_fetch.call_args.kwargs["params"], {"ac": "detail", "pg": 1})
        self.assertEqual(mock_fetch.call_args.kwargs["headers"]["Referer"], "https://40000.me/")

    @patch.object(Spider, "fetch")
    def test_api_get_rejects_non_200_and_non_object_body(self, mock_fetch):
        mock_fetch.return_value = self._response(status_code=500, payload={"msg": "bad"})
        with self.assertRaises(ValueError):
            self.spider._api_get({"ac": "detail"})

        mock_fetch.return_value = self._response(text="[]")
        with self.assertRaises(ValueError):
            self.spider._api_get({"ac": "detail"})

    def test_normalize_vod_applies_type_name_actor_cleanup_and_fallback_cover(self):
        self.assertEqual(
            self.spider._normalize_vod(
                {
                    "vod_id": 7,
                    "vod_name": "示例影片",
                    "vod_pic": "",
                    "type_id": "20",
                    "vod_remarks": "HD",
                    "vod_year": "2025",
                    "vod_actor": "O&amp;#039;Brien , 张三",
                }
            ),
            {
                "vod_id": "7",
                "vod_name": "示例影片",
                "vod_pic": "https://40000.me/public/favicon.png",
                "vod_remarks": "HD",
                "vod_year": "2025",
                "type_name": "电影",
                "vod_actor": "O'Brien, 张三",
            },
        )

    @patch.object(Spider, "_api_get")
    def test_category_content_maps_subtype_year_sort_and_page(self, mock_api_get):
        mock_api_get.return_value = {
            "page": 2,
            "total": 55,
            "list": [
                {"vod_id": 100, "vod_name": "分类影片", "vod_pic": "/p.jpg", "type_id": "21", "vod_remarks": "更新中"}
            ],
        }
        result = self.spider.categoryContent("20", "2", False, {"subType": "21", "year": "2025", "sort": "hits"})
        self.assertEqual(
            mock_api_get.call_args.args[0],
            {"ac": "detail", "t": "21", "pg": 2, "h": "2025", "by": "hits"},
        )
        self.assertEqual(result["page"], 2)
        self.assertEqual(result["total"], 55)
        self.assertEqual(result["limit"], 1)
        self.assertEqual(result["list"][0]["vod_id"], "100")
        self.assertNotIn("pagecount", result)

    @patch.object(Spider, "_api_get")
    def test_search_content_maps_keyword_and_page(self, mock_api_get):
        mock_api_get.return_value = {
            "page": 3,
            "total": 10,
            "list": [
                {"vod_id": 200, "vod_name": "搜索结果", "vod_pic": "", "type_id": "30", "vod_remarks": "完结"}
            ],
        }
        result = self.spider.searchContent("繁花", False, "3")
        self.assertEqual(mock_api_get.call_args.args[0], {"ac": "detail", "wd": "繁花", "pg": 3})
        self.assertEqual(result["page"], 3)
        self.assertEqual(result["list"][0]["type_name"], "电视剧")

    def test_search_content_returns_empty_list_for_blank_keyword(self):
        self.assertEqual(self.spider.searchContent("", False, "1"), {"page": 1, "limit": 0, "total": 0, "list": []})

    def test_parse_play_groups_builds_repo_style_play_fields(self):
        self.assertEqual(
            self.spider._parse_play_groups(
                {
                    "vod_play_from": "量子$$$",
                    "vod_play_url": "第1集$https://cdn.example/1.m3u8#第2集$abc$$$solo",
                }
            ),
            {
                "vod_play_from": "量子$$$线路2",
                "vod_play_url": "第1集$https://cdn.example/1.m3u8#第2集$abc$$$第1集$solo",
            },
        )

    @patch.object(Spider, "_api_get")
    def test_detail_content_builds_detail_and_play_fields(self, mock_api_get):
        mock_api_get.return_value = {
            "list": [
                {
                    "vod_id": 300,
                    "vod_name": "详情影片",
                    "vod_pic": "/poster.jpg",
                    "type_id": "30",
                    "type_name": "",
                    "vod_year": "2024",
                    "vod_area": "大陆",
                    "vod_director": "导演甲",
                    "vod_actor": "A&amp;#039;B , 演员乙",
                    "vod_blurb": "一段简介",
                    "vod_remarks": "更新至2集",
                    "vod_play_from": "量子$$$非凡",
                    "vod_play_url": "第1集$https://cdn.example/1.m3u8#第2集$play-2$$$正片$play-3",
                }
            ]
        }
        result = self.spider.detailContent(["300"])
        vod = result["list"][0]
        self.assertEqual(vod["vod_id"], "300")
        self.assertEqual(vod["type_name"], "电视剧")
        self.assertEqual(vod["vod_actor"], "A'B, 演员乙")
        self.assertEqual(vod["vod_play_from"], "量子$$$非凡")
        self.assertEqual(
            vod["vod_play_url"],
            "第1集$https://cdn.example/1.m3u8#第2集$play-2$$$正片$play-3",
        )

    @patch.object(Spider, "_api_get")
    def test_category_content_returns_empty_payload_on_api_error(self, mock_api_get):
        mock_api_get.side_effect = ValueError("boom")
        self.assertEqual(
            self.spider.categoryContent("20", "1", False, {}),
            {"page": 1, "limit": 0, "total": 0, "list": []},
        )

    @patch.object(Spider, "_api_get")
    def test_detail_content_returns_empty_list_on_api_error(self, mock_api_get):
        mock_api_get.side_effect = ValueError("boom")
        self.assertEqual(self.spider.detailContent(["9"]), {"list": []})

    def test_player_content_returns_direct_url_for_http_play_id(self):
        result = self.spider.playerContent("量子", "https://cdn.example/test.m3u8", {})
        self.assertEqual(result["parse"], 0)
        self.assertEqual(result["jx"], 0)
        self.assertEqual(result["url"], "https://cdn.example/test.m3u8")
        self.assertEqual(result["header"]["Referer"], "https://40000.me/")

    def test_player_content_marks_non_http_play_id_for_parse(self):
        result = self.spider.playerContent("量子", "play-2", {})
        self.assertEqual(result["parse"], 1)
        self.assertEqual(result["jx"], 1)
        self.assertEqual(result["url"], "play-2")

    def test_player_content_returns_empty_parse_payload_for_blank_id(self):
        self.assertEqual(
            self.spider.playerContent("量子", "", {}),
            {
                "parse": 1,
                "jx": 1,
                "url": "",
                "header": {
                    "User-Agent": self.spider.headers["User-Agent"],
                    "Referer": "https://40000.me/",
                },
            },
        )
