import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest.mock import patch


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

    def test_extract_home_list_deduplicates_media_resources(self):
        home_blocks = {
            "records": [
                {
                    "mediaResources": [
                        {"id": 1, "title": "影片A", "posterUrl": "/a.jpg"},
                        {"id": 1, "title": "影片A", "posterUrl": "/a.jpg"},
                    ]
                },
                {
                    "mediaResources": [
                        {"id": 2, "title": "影片B", "posterUrlS3": "https://img.example/b.jpg"},
                    ]
                },
            ]
        }
        items = self.spider._extract_home_list(home_blocks)
        self.assertEqual([item["id"] for item in items], ["1", "2"])

    def test_map_vod_picks_expected_fields(self):
        item = {
            "id": 7,
            "title": "示例片",
            "posterUrl": "/poster.jpg",
            "mediaType": {"code": "movie", "name": "电影"},
            "episodeStatus": "更新至4集",
            "releaseYear": "2026",
            "rating": "8.8",
            "actors": ["甲", "乙"],
            "directors": ["丙"],
        }
        vod = self.spider._map_vod(item)
        self.assertEqual(vod["vod_id"], "7")
        self.assertEqual(vod["vod_pic"], "/poster.jpg")
        self.assertEqual(vod["vod_actor"], "甲/乙")
        self.assertEqual(vod["vod_director"], "丙")

    @patch.object(Spider, "_request_json")
    def test_home_video_content_reads_home_blocks(self, mock_request_json):
        mock_request_json.return_value = {
            "records": [
                {"mediaResources": [{"id": 1, "title": "首页片", "posterUrl": "/a.jpg"}]}
            ]
        }
        result = self.spider.homeVideoContent()
        self.assertEqual(result["list"][0]["vod_id"], "1")
        self.assertEqual(result["list"][0]["vod_name"], "首页片")

    @patch.object(Spider, "_request_json")
    def test_category_content_posts_search_body_and_returns_page_data(self, mock_request_json):
        mock_request_json.return_value = {
            "records": [{"id": 9, "title": "分类片", "posterUrl": "/cate.jpg"}],
            "total": 30,
            "pages": 2,
        }
        result = self.spider.categoryContent("movie", "2", False, {"sort": "latest"})
        kwargs = mock_request_json.call_args.kwargs
        self.assertEqual(kwargs["method"], "POST")
        self.assertEqual(kwargs["data"]["pageIndex"], "2")
        self.assertEqual(kwargs["data"]["sortCode"], "latest")
        self.assertEqual(result["page"], 2)
        self.assertEqual(result["pagecount"], 2)
        self.assertEqual(result["limit"], 24)
        self.assertEqual(result["total"], 30)

    @patch.object(Spider, "_request_json")
    def test_search_content_returns_empty_result_for_blank_keyword(self, mock_request_json):
        result = self.spider.searchContent("", False, "1")
        self.assertEqual(result, {"page": 1, "pagecount": 0, "total": 0, "list": []})
        mock_request_json.assert_not_called()

    @patch.object(Spider, "_request_json")
    def test_search_content_posts_keyword_body(self, mock_request_json):
        mock_request_json.return_value = {
            "records": [{"id": 15, "title": "搜索片", "posterUrl": "/search.jpg"}],
            "total": 1,
            "pages": 1,
        }
        result = self.spider.searchContent("繁花", False, "1")
        body = mock_request_json.call_args.kwargs["data"]
        self.assertEqual(body["searchKey"], "繁花")
        self.assertEqual(body["topCode"], "")
        self.assertEqual(result["list"][0]["vod_id"], "15")

    def test_build_play_sources_encodes_multiple_seasons(self):
        seasons = [
            {
                "seasonNo": 1,
                "videoList": [
                    {"id": 101, "epNo": 1, "remark": "", "playUrl": "/play-1.m3u8"},
                    {"id": 102, "epNo": 2, "remark": "加更", "playUrl": "/play-2.m3u8"},
                ],
            },
            {
                "seasonNo": 2,
                "videoList": [
                    {"id": 201, "epNo": 1, "remark": "", "playUrl": "/play-3.m3u8"},
                ],
            },
        ]
        payload = self.spider._build_play_sources(seasons, "99")
        self.assertEqual(payload["vod_play_from"], "第1季$$$第2季")
        self.assertIn("第1集$", payload["vod_play_url"])
        self.assertIn("第2集 加更$", payload["vod_play_url"])

    def test_decode_play_id_round_trips_base64url_payload(self):
        encoded = self.spider._encode_play_payload(
            {
                "mediaId": "88",
                "seasonNo": 1,
                "epNo": 3,
                "videoId": 12,
                "playUrl": "/video.m3u8",
                "name": "第3集",
            }
        )
        decoded = self.spider._decode_play_id(encoded)
        self.assertEqual(decoded["mediaId"], "88")
        self.assertEqual(decoded["seasonNo"], 1)
        self.assertEqual(decoded["epNo"], 3)
        self.assertEqual(decoded["playUrl"], "/video.m3u8")

    @patch.object(Spider, "_request_json")
    def test_detail_content_merges_detail_apis_and_videos(self, mock_request_json):
        mock_request_json.side_effect = [
            {"id": 300, "title": "基础标题", "posterUrl": "/base.jpg"},
            {
                "id": 300,
                "title": "完整标题",
                "posterUrlS3": "https://img.example/detail.jpg",
                "mediaType": {"code": "tv_series", "name": "电视剧"},
                "episodeStatus": "更新至2集",
                "releaseYear": "2026",
                "region": "大陆",
                "actors": ["张三", "李四"],
                "directors": ["王五"],
                "overview": "一段简介",
                "rating": "9.1",
            },
            [
                {
                    "seasonNo": 1,
                    "videoList": [
                        {"id": 901, "epNo": 1, "remark": "", "playUrl": "/ep1.m3u8"},
                        {"id": 902, "epNo": 2, "remark": "超前", "playUrl": "/ep2.m3u8"},
                    ],
                }
            ],
        ]
        result = self.spider.detailContent(["300"])
        vod = result["list"][0]
        self.assertEqual(vod["vod_id"], "300")
        self.assertEqual(vod["vod_name"], "完整标题")
        self.assertEqual(vod["vod_pic"], "https://img.example/detail.jpg")
        self.assertEqual(vod["type_name"], "电视剧")
        self.assertEqual(vod["vod_area"], "大陆")
        self.assertEqual(vod["vod_actor"], "张三/李四")
        self.assertEqual(vod["vod_director"], "王五")
        self.assertEqual(vod["vod_content"], "一段简介")
        self.assertEqual(vod["vod_douban_score"], "9.1")
        self.assertEqual(vod["vod_play_from"], "乌云影视")
        self.assertIn("第2集 超前$", vod["vod_play_url"])


if __name__ == "__main__":
    unittest.main()
