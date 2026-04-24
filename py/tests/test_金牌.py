import hashlib
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
MODULE = SourceFileLoader("jinpai_spider", str(ROOT / "金牌.py")).load_module()
Spider = MODULE.Spider


class TestJinPaiSpider(unittest.TestCase):
    def setUp(self):
        Spider._instance = None
        self.spider = Spider()
        self.spider.init()

    @patch("jinpai_spider.time.time", return_value=1713952212.345)
    def test_signed_headers_generates_expected_hashes(self, _mock_time):
        headers = self.spider._signed_headers({"pageNum": "1", "type1": "2"})
        expected_t = "1713952212345"
        expected_obj = "pageNum=1&type1=2&key=cb808529bae6b6be45ecfab29a4889bc&t=1713952212345"
        expected_sign = hashlib.sha1(
            hashlib.md5(expected_obj.encode("utf-8")).hexdigest().encode("utf-8")
        ).hexdigest()
        self.assertEqual(headers["t"], expected_t)
        self.assertEqual(headers["sign"], expected_sign)
        self.assertEqual(headers["Referer"], "https://m.jiabaide.cn/")

    @patch.object(Spider, "_fetch_json")
    def test_home_content_returns_class_filters_and_hot_list(self, mock_fetch_json):
        mock_fetch_json.side_effect = [
            {"data": [{"typeId": 1, "typeName": "电影"}, {"typeId": 2, "typeName": "剧集"}]},
            {
                "data": {
                    "1": {
                        "typeList": [{"itemText": "动作", "itemValue": "dongzuo"}],
                        "plotList": [{"itemText": "剧情"}],
                        "districtList": [{"itemText": "中国香港"}],
                        "languageList": [{"itemText": "粤语"}],
                        "yearList": [{"itemText": "2026"}],
                    }
                }
            },
            {
                "data": [
                    {
                        "vodId": 9,
                        "vodName": "热播片",
                        "vodPic": "https://img/9.jpg",
                        "vodRemarks": "更新至10集",
                        "vodDoubanScore": "8.6",
                        "vodPubdate": "2026-01-01",
                        "typeId": 1,
                        "typeName": "电影",
                    }
                ]
            },
        ]
        result = self.spider.homeContent(False)
        self.assertEqual(
            result["class"],
            [{"type_id": "1", "type_name": "电影"}, {"type_id": "2", "type_name": "剧集"}],
        )
        self.assertEqual(result["filters"]["1"][0]["key"], "type")
        self.assertEqual(result["filters"]["1"][0]["value"][0], {"n": "全部", "v": ""})
        self.assertEqual(result["filters"]["1"][0]["value"][1], {"n": "动作", "v": "dongzuo"})
        self.assertEqual(result["filters"]["1"][-1]["key"], "by")
        self.assertEqual(result["list"][0]["vod_remarks"], "更新至10集_8.6")
        self.assertEqual(result["list"][0]["vod_year"], "2026")

    def test_home_video_content_returns_empty_list(self):
        self.assertEqual(self.spider.homeVideoContent(), {"list": []})

    @patch.object(Spider, "_fetch_json")
    def test_category_content_maps_filters_to_api_payload(self, mock_fetch_json):
        mock_fetch_json.return_value = {
            "data": {
                "list": [
                    {
                        "vodId": 11,
                        "vodName": "分类片",
                        "vodPic": "https://img/11.jpg",
                        "vodRemarks": "完结",
                        "vodDoubanScore": "7.1",
                        "vodPubdate": "2025-09-09",
                        "typeId": 1,
                        "typeName": "电影",
                    }
                ]
            }
        }
        result = self.spider.categoryContent(
            "1",
            "2",
            False,
            {"area": "中国香港", "lang": "粤语", "year": "2025", "by": "4", "type": "dongzuo", "class": "剧情"},
        )
        self.assertEqual(
            mock_fetch_json.call_args.args,
            (
                "/api/mw-movie/anonymous/video/list",
                {
                    "area": "中国香港",
                    "lang": "粤语",
                    "pageNum": "2",
                    "pageSize": "30",
                    "sort": "4",
                    "sortBy": "1",
                    "type": "dongzuo",
                    "type1": "1",
                    "v_class": "剧情",
                    "year": "2025",
                },
            ),
        )
        self.assertEqual(result["page"], 2)
        self.assertEqual(result["limit"], 30)
        self.assertEqual(result["list"][0]["vod_id"], "11")
        self.assertNotIn("pagecount", result)

    def test_search_content_returns_empty_for_blank_keyword(self):
        self.assertEqual(self.spider.searchContent("", False, "1"), {"page": 1, "limit": 30, "total": 0, "list": []})

    @patch.object(Spider, "_fetch_json")
    def test_search_content_maps_keyword_and_page(self, mock_fetch_json):
        mock_fetch_json.return_value = {
            "data": {
                "list": [
                    {
                        "vodId": 21,
                        "vodName": "搜索片",
                        "vodPic": "https://img/21.jpg",
                        "vodRemarks": "更新",
                        "vodDoubanScore": "8.0",
                        "vodPubdate": "2024-01-01",
                        "typeId": 2,
                        "typeName": "剧集",
                    }
                ]
            }
        }
        result = self.spider.searchContent("繁花", False, "3")
        self.assertEqual(
            mock_fetch_json.call_args.args,
            (
                "/api/mw-movie/anonymous/video/searchByWordPageable",
                {"keyword": "繁花", "pageNum": "3", "pageSize": "30"},
            ),
        )
        self.assertEqual(result["page"], 3)
        self.assertEqual(result["list"][0]["vod_name"], "搜索片")
        self.assertEqual(result["list"][0]["vod_year"], "2024")

    @patch.object(Spider, "_fetch_json")
    def test_detail_content_maps_metadata_and_episode_ids(self, mock_fetch_json):
        mock_fetch_json.return_value = {
            "data": {
                "vodId": 88,
                "vodName": "详情片",
                "vodPic": "https://img/88.jpg",
                "vodClass": "动作",
                "vodRemarks": "更新至12集",
                "vodYear": "2026",
                "vodArea": "中国香港",
                "vodLang": "粤语",
                "vodDirector": "导演甲",
                "vodActor": "演员甲/演员乙",
                "vodContent": "一段简介",
                "episodeList": [{"name": "第1集", "nid": 9001}, {"name": "第2集", "nid": 9002}],
            }
        }
        result = self.spider.detailContent(["88"])
        vod = result["list"][0]
        self.assertEqual(mock_fetch_json.call_args.args, ("/api/mw-movie/anonymous/video/detail", {"id": "88"}))
        self.assertEqual(vod["vod_id"], "88")
        self.assertEqual(vod["vod_name"], "详情片")
        self.assertEqual(vod["vod_play_from"], "金牌线路")
        self.assertEqual(vod["vod_play_url"], "第1集$88@9001#第2集$88@9002")

    def test_detail_content_returns_empty_for_blank_id(self):
        self.assertEqual(self.spider.detailContent([""]), {"list": []})

    @patch.object(Spider, "_fetch_json")
    def test_player_content_returns_first_episode_url_with_headers(self, mock_fetch_json):
        mock_fetch_json.return_value = {
            "data": {
                "list": [
                    {"name": "1080P", "url": "https://cdn.example/1080.m3u8"},
                    {"name": "720P", "url": "https://cdn.example/720.m3u8"},
                ]
            }
        }
        result = self.spider.playerContent("金牌线路", "88@9001", {})
        self.assertEqual(
            mock_fetch_json.call_args.args,
            ("/api/mw-movie/anonymous/v2/video/episode/url", {"clientType": "3", "id": "88", "nid": "9001"}),
        )
        self.assertEqual(
            result,
            {
                "parse": 0,
                "playUrl": "",
                "url": "https://cdn.example/1080.m3u8",
                "header": {"User-Agent": self.spider.mobile_ua},
            },
        )

    def test_player_content_rejects_broken_play_id(self):
        self.assertEqual(
            self.spider.playerContent("金牌线路", "broken", {}),
            {"parse": 0, "playUrl": "", "url": "", "header": {}},
        )
