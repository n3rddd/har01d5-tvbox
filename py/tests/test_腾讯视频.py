import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
MODULE = SourceFileLoader("tengxun_spider", str(ROOT / "腾讯视频.py")).load_module()
Spider = MODULE.Spider


HOME_HTML = """
<div class="list_item">
  <a data-float="/x/cover/mzc00200abc1111.html"><img alt="海底小纵队" src="https://img.test/a.jpg"></a>
  <a>更新至10集</a>
</div>
<div class="list_item">
  <a data-float="/x/cover/mzc00200abc2222.html"><img alt="熊出没" src="https://img.test/b.jpg"></a>
  <a>全52集</a>
</div>
"""

CATEGORY_HTML = """
<div class="list_item">
  <a data-float="/x/cover/cid001/vid001.html"><img alt="三体" src="https://img.test/c.jpg"></a>
  <a>更新至30集</a>
</div>
"""


class TestTencentSpider(unittest.TestCase):
    def setUp(self):
        Spider._instance = None
        self.spider = Spider()
        self.spider.init()

    def test_parse_list_items_extracts_cards(self):
        cards = self.spider._parse_list_items(HOME_HTML, with_channel=False)
        self.assertEqual(
            cards,
            [
                {
                    "vod_id": "/x/cover/mzc00200abc1111.html",
                    "vod_name": "海底小纵队",
                    "vod_pic": "https://img.test/a.jpg",
                    "vod_remarks": "更新至10集",
                },
                {
                    "vod_id": "/x/cover/mzc00200abc2222.html",
                    "vod_name": "熊出没",
                    "vod_pic": "https://img.test/b.jpg",
                    "vod_remarks": "全52集",
                },
            ],
        )

    @patch.object(Spider, "fetch")
    def test_home_content_returns_fixed_classes_and_top_20_cards(self, mock_fetch):
        mock_fetch.return_value = SimpleNamespace(text=HOME_HTML)
        result = self.spider.homeContent(False)
        self.assertEqual(
            [item["type_id"] for item in result["class"]],
            ["choice", "movie", "tv", "variety", "cartoon", "child", "doco"],
        )
        self.assertEqual(result["list"][0]["vod_name"], "海底小纵队")
        self.assertNotIn("filters", result)

    def test_player_content_passthroughs_raw_url(self):
        result = self.spider.playerContent("腾讯视频", "https://v.qq.com/x/cover/demo.html", {})
        self.assertEqual(
            result,
            {
                "parse": 1,
                "jx": 1,
                "url": "https://v.qq.com/x/cover/demo.html",
                "header": {"User-Agent": "PC_UA"},
            },
        )

    @patch.object(Spider, "fetch")
    def test_category_content_maps_filters_and_prefixes_channel(self, mock_fetch):
        mock_fetch.return_value = SimpleNamespace(text=CATEGORY_HTML)
        result = self.spider.categoryContent(
            "tv",
            "2",
            False,
            {
                "sort": "18",
                "iyear": "2024",
                "year": "2024",
                "type": "17",
                "feature": "4",
                "area": "2",
                "itrailer": "1",
                "sex": "1",
            },
        )
        request_url = mock_fetch.call_args.args[0]
        self.assertIn("channel=tv", request_url)
        self.assertIn("offset=21", request_url)
        self.assertIn("sort=18", request_url)
        self.assertIn("iyear=2024", request_url)
        self.assertIn("year=2024", request_url)
        self.assertIn("itype=17", request_url)
        self.assertIn("ifeature=4", request_url)
        self.assertIn("iarea=2", request_url)
        self.assertIn("itrailer=1", request_url)
        self.assertIn("gender=1", request_url)
        self.assertEqual(result["list"][0]["vod_id"], "tv$/x/cover/cid001/vid001.html")
        self.assertEqual(result["page"], 2)
        self.assertEqual(result["limit"], 21)
        self.assertEqual(result["pagecount"], 9999)

    @patch.object(Spider, "fetch")
    def test_get_batch_video_info_parses_qzoutputjson_payload(self, mock_fetch):
        mock_fetch.return_value = SimpleNamespace(
            text='QZOutputJson={"results":[{"fields":{"vid":"vid001","title":"第1集","category_map":["0","正片"]}}]};'
        )
        result = self.spider._get_batch_video_info(["vid001"])
        self.assertEqual(result, [{"vid": "vid001", "title": "第1集", "type": "正片"}])

    @patch.object(Spider, "_get_batch_video_info")
    @patch.object(Spider, "fetch")
    def test_detail_content_merges_main_and_trailer_into_single_line(self, mock_fetch, mock_get_batch_video_info):
        mock_fetch.return_value = SimpleNamespace(
            json=lambda: {
                "c": {
                    "title": "斗罗大陆",
                    "year": "2024",
                    "description": "热血冒险",
                    "pic": "/cover.jpg",
                    "video_ids": ["vid001", "vid002"],
                },
                "typ": ["热血", "冒险"],
                "nam": ["配音甲", "配音乙"],
                "rec": "更新中",
            }
        )
        mock_get_batch_video_info.return_value = [
            {"vid": "vid001", "title": "1", "type": "正片"},
            {"vid": "vid002", "title": "终极预告", "type": "预告"},
        ]

        result = self.spider.detailContent(["tv$cid001"])
        vod = result["list"][0]

        self.assertEqual(vod["vod_id"], "tv$cid001")
        self.assertEqual(vod["vod_name"], "斗罗大陆")
        self.assertEqual(vod["type_name"], "热血,冒险")
        self.assertEqual(vod["vod_actor"], "配音甲,配音乙")
        self.assertEqual(vod["vod_pic"], "https://v.qq.com/cover.jpg")
        self.assertEqual(vod["vod_play_from"], "腾讯视频")
        self.assertEqual(
            vod["vod_play_url"],
            "第1集$https://v.qq.com/x/cover/cid001/vid001.html#终极预告$https://v.qq.com/x/cover/cid001/vid002.html",
        )


if __name__ == "__main__":
    unittest.main()
