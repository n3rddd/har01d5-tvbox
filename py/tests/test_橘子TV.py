import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
MODULE = SourceFileLoader("juzi_spider", str(ROOT / "橘子TV.py")).load_module()
Spider = MODULE.Spider


class TestJuZiTVSpider(unittest.TestCase):
    def setUp(self):
        Spider._instance = None
        self.spider = Spider()

    @patch.object(Spider, "fetch")
    def test_init_loads_api_host_from_json_config(self, mock_fetch):
        class FakeResponse:
            def __init__(self, text):
                self.text = text
                self.status_code = 200
                self.encoding = "utf-8"

        mock_fetch.return_value = FakeResponse('["https://api1.example.com","https://api2.example.com"]')
        self.spider.init()
        self.assertEqual(self.spider.api_host, "https://api1.example.com")

    @patch.object(Spider, "fetch")
    def test_init_loads_api_host_from_plain_text_config(self, mock_fetch):
        class FakeResponse:
            def __init__(self, text):
                self.text = text
                self.status_code = 200
                self.encoding = "utf-8"

        mock_fetch.return_value = FakeResponse("https://api3.example.com,\nhttps://api4.example.com")
        self.spider.init()
        self.assertEqual(self.spider.api_host, "https://api3.example.com")

    @patch.object(Spider, "fetch")
    def test_build_payload_adds_sign_and_common_fields(self, mock_fetch):
        class FakeResponse:
            def __init__(self, text):
                self.text = text
                self.status_code = 200
                self.encoding = "utf-8"

        mock_fetch.return_value = FakeResponse('["https://api1.example.com"]')
        self.spider.init()
        payload = self.spider._build_payload({"vodId": "123"})
        self.assertEqual(payload["appId"], "fea23e11fc1241409682880e15fb2851")
        self.assertEqual(payload["bundlerId"], "com.voraguzzee.ts")
        self.assertEqual(payload["vodId"], "123")
        self.assertIn("requestId", payload)
        self.assertIn("sign", payload)
        self.assertEqual(len(payload["sign"]), 32)

    @patch.object(Spider, "_post_api")
    @patch.object(Spider, "fetch")
    def test_home_content_maps_channel_list(self, mock_fetch, mock_post_api):
        class FakeResponse:
            def __init__(self, text):
                self.text = text
                self.status_code = 200
                self.encoding = "utf-8"

        mock_fetch.return_value = FakeResponse('["https://api1.example.com"]')
        mock_post_api.return_value = {
            "data": {
                "channeList": [
                    {"channelId": 1, "channelName": "电影"},
                    {"channelId": 2, "channelName": "剧集"},
                ]
            }
        }
        self.spider.init()
        result = self.spider.homeContent(False)
        self.assertEqual(
            result,
            {
                "class": [
                    {"type_id": "1", "type_name": "电影"},
                    {"type_id": "2", "type_name": "剧集"},
                ]
            },
        )

    @patch.object(Spider, "_post_api")
    @patch.object(Spider, "fetch")
    def test_home_video_content_flattens_topic_vod_list(self, mock_fetch, mock_post_api):
        class FakeResponse:
            def __init__(self, text):
                self.text = text
                self.status_code = 200
                self.encoding = "utf-8"

        mock_fetch.return_value = FakeResponse('["https://api1.example.com"]')
        mock_post_api.return_value = {
            "data": {
                "vodTopicList": [
                    {
                        "vodList": [
                            {
                                "vodId": 11,
                                "vodName": "推荐影片",
                                "coverImg": "https://img.example.com/a.jpg",
                                "remark": "更新至1集",
                                "flags": "2026 / 大陆",
                            }
                        ]
                    }
                ]
            }
        }
        self.spider.init()
        result = self.spider.homeVideoContent()
        self.assertEqual(result["list"][0]["vod_id"], "11")
        self.assertEqual(result["list"][0]["vod_name"], "推荐影片")
        self.assertEqual(result["list"][0]["vod_year"], "2026")

    @patch.object(Spider, "_post_api")
    @patch.object(Spider, "fetch")
    def test_category_content_maps_items_and_page_fields(self, mock_fetch, mock_post_api):
        class FakeResponse:
            def __init__(self, text):
                self.text = text
                self.status_code = 200
                self.encoding = "utf-8"

        mock_fetch.return_value = FakeResponse('["https://api1.example.com"]')
        mock_post_api.return_value = {
            "data": {
                "hasNext": 1,
                "nextVal": "token-2",
                "items": [
                    {
                        "vodId": 21,
                        "vodName": "分类影片",
                        "coverImg": "https://img.example.com/cate.jpg",
                        "remark": "完结",
                        "flags": "2025 / 美国",
                        "intro": "分类简介",
                    }
                ],
            }
        }
        self.spider.init()
        result = self.spider.categoryContent("7", "2", False, {})
        self.assertEqual(result["page"], 2)
        self.assertEqual(result["pagecount"], 3)
        self.assertEqual(result["list"][0]["vod_id"], "21")
        self.assertEqual(result["list"][0]["vod_content"], "分类简介")
        payload = mock_post_api.call_args.args[1]
        self.assertEqual(payload["nextCount"], 18)
        self.assertEqual(payload["nextVal"], "")
        self.assertEqual(payload["sortType"], "")
        self.assertEqual(payload["queryValueJson"], '[{"filerName":"channelId","filerValue":"7"}]')

    @patch.object(Spider, "_post_api")
    @patch.object(Spider, "fetch")
    def test_search_content_maps_items_without_next_page(self, mock_fetch, mock_post_api):
        class FakeResponse:
            def __init__(self, text):
                self.text = text
                self.status_code = 200
                self.encoding = "utf-8"

        mock_fetch.return_value = FakeResponse('["https://api1.example.com"]')
        mock_post_api.return_value = {
            "data": {
                "hasNext": 0,
                "items": [
                    {
                        "vodId": 31,
                        "vodName": "搜索影片",
                        "coverImg": "https://img.example.com/search.jpg",
                        "remark": "",
                        "score": "8.5",
                        "flags": "2024 / 日本",
                        "intro": "搜索简介",
                    }
                ],
            }
        }
        self.spider.init()
        result = self.spider.searchContent("繁花", False, "1")
        self.assertEqual(result["page"], 1)
        self.assertEqual(result["pagecount"], 1)
        self.assertEqual(result["list"][0]["vod_id"], "31")
        self.assertEqual(result["list"][0]["vod_remarks"], "评分：8.5")
        payload = mock_post_api.call_args.args[1]
        self.assertEqual(payload["keyword"], "繁花")
        self.assertEqual(payload["nextVal"], "")

    def test_parse_people_joins_worker_names(self):
        self.assertEqual(
            self.spider._parse_people(
                [
                    {"vodWorkerId": 1, "vodWorkerName": "张三"},
                    {"vodWorkerId": 2, "vodWorkerName": "李四"},
                ]
            ),
            "张三,李四",
        )

    @patch.object(Spider, "_post_api")
    @patch.object(Spider, "fetch")
    def test_detail_content_maps_meta_and_multi_line_playlists(self, mock_fetch, mock_post_api):
        class FakeResponse:
            def __init__(self, text):
                self.text = text
                self.status_code = 200
                self.encoding = "utf-8"

        mock_fetch.return_value = FakeResponse('["https://api1.example.com"]')
        mock_post_api.return_value = {
            "data": {
                "vodId": 41,
                "vodName": "详情影片",
                "coverImg": "https://img.example.com/detail.jpg",
                "updateRemark": "更新至3集",
                "year": "2026",
                "areaName": "大陆",
                "intro": "详情简介",
                "actorList": [{"vodWorkerName": "主演甲"}, {"vodWorkerName": "主演乙"}],
                "directorList": [{"vodWorkerName": "导演甲"}],
                "playerList": [
                    {
                        "playerName": "线路A",
                        "epList": [{"epName": "第1集", "epId": "ep-a-1"}, {"epName": "第2集", "epId": "ep-a-2"}],
                    },
                    {
                        "playerName": "线路B",
                        "epList": [{"epName": "正片", "epId": "ep-b-1"}],
                    },
                ],
            }
        }
        self.spider.init()
        result = self.spider.detailContent(["41"])
        vod = result["list"][0]
        self.assertEqual(vod["vod_id"], "41")
        self.assertEqual(vod["vod_name"], "详情影片")
        self.assertEqual(vod["vod_remarks"], "更新至3集")
        self.assertEqual(vod["vod_year"], "2026")
        self.assertEqual(vod["vod_area"], "大陆")
        self.assertEqual(vod["vod_actor"], "主演甲,主演乙")
        self.assertEqual(vod["vod_director"], "导演甲")
        self.assertEqual(vod["vod_content"], "详情简介")
        self.assertEqual(vod["vod_play_from"], "线路A$$$线路B")
        self.assertEqual(vod["vod_play_url"], "第1集$ep-a-1#第2集$ep-a-2$$$正片$ep-b-1")

    @patch.object(Spider, "_post_api")
    @patch.object(Spider, "fetch")
    def test_player_content_collects_resolution_urls(self, mock_fetch, mock_post_api):
        class FakeResponse:
            def __init__(self, text):
                self.text = text
                self.status_code = 200
                self.encoding = "utf-8"

        mock_fetch.return_value = FakeResponse('["https://api1.example.com"]')
        mock_post_api.side_effect = [
            {
                "data": [
                    {"showName": "高清", "vodResolution": "1080p"},
                    {"showName": "标清", "vodResolution": "720p"},
                ]
            },
            {"data": {"playUrl": "https://cdn.example.com/1080.m3u8"}},
            {"data": {"playUrl": "https://cdn.example.com/720.m3u8"}},
        ]
        self.spider.init()
        result = self.spider.playerContent("线路A", "ep-a-1", {})
        self.assertEqual(result["parse"], 0)
        self.assertEqual(
            result["url"],
            ["高清", "https://cdn.example.com/1080.m3u8", "标清", "https://cdn.example.com/720.m3u8"],
        )
        self.assertEqual(result["header"]["User-Agent"], "ExoPlayer")


if __name__ == "__main__":
    unittest.main()
