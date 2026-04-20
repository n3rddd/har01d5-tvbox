import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
MODULE = SourceFileLoader("zxzj_spider", str(ROOT / "在线之家.py")).load_module()
Spider = MODULE.Spider


class TestZXZJSpider(unittest.TestCase):
    def setUp(self):
        Spider._instance = None
        self.spider = Spider()
        self.spider.init()

    def test_home_content_exposes_expected_classes_and_filter_keys(self):
        content = self.spider.homeContent(False)
        self.assertEqual(
            [item["type_id"] for item in content["class"]],
            ["1", "2", "3", "4", "5", "6"],
        )
        self.assertEqual(
            [item["key"] for item in content["filters"]["1"]],
            ["class", "area", "year", "by"],
        )

    def test_home_video_content_returns_empty_list(self):
        self.assertEqual(self.spider.homeVideoContent(), {"list": []})

    def test_build_category_url_applies_default_and_selected_filters(self):
        url = self.spider._build_category_url("1", "2", {"area": "欧美", "by": "hits", "year": "2025"})
        self.assertEqual(url, "https://www.zxzjhd.com/vodshow/1-欧美-hits------2---2025.html")

    def test_build_category_url_for_first_page_keeps_page_1_segment(self):
        url = self.spider._build_category_url("2", "1", {})
        self.assertEqual(url, "https://www.zxzjhd.com/vodshow/2--------1---.html")

    def test_fix_json_wrapped_html_unwraps_html_string(self):
        wrapped = "\"<html><body>ok</body></html>\""
        self.assertEqual(self.spider._fix_json_wrapped_html(wrapped), "<html><body>ok</body></html>")

    def test_parse_cards_extracts_short_vod_id_title_cover_and_remarks(self):
        html = """
        <ul class="stui-vodlist clearfix">
          <li>
            <a href="/voddetail/12345.html" title="示例影片" data-original="/cover.jpg"></a>
            <span class="pic-text">更新至10集</span>
          </li>
        </ul>
        """
        cards = self.spider._parse_cards(html)
        self.assertEqual(
            cards,
            [
                {
                    "vod_id": "voddetail/12345.html",
                    "vod_name": "示例影片",
                    "vod_pic": "https://www.zxzjhd.com/cover.jpg",
                    "vod_remarks": "更新至10集",
                }
            ],
        )

    @patch.object(Spider, "_request_html")
    def test_category_content_uses_built_url_and_returns_page_result(self, mock_request_html):
        mock_request_html.return_value = """
        <ul class="stui-vodlist clearfix">
          <li>
            <a href="/voddetail/23456.html" title="分类影片" data-original="/cate.jpg"></a>
            <span class="pic-text">HD</span>
          </li>
        </ul>
        """
        result = self.spider.categoryContent("1", "2", False, {"area": "欧美"})
        self.assertEqual(mock_request_html.call_args.args[0], "https://www.zxzjhd.com/vodshow/1-欧美-------2---.html")
        self.assertEqual(result["page"], 2)
        self.assertEqual(result["limit"], 24)
        self.assertEqual(result["list"][0]["vod_id"], "voddetail/23456.html")
        self.assertNotIn("pagecount", result)

    @patch.object(Spider, "_request_html")
    def test_search_content_parses_search_cards(self, mock_request_html):
        mock_request_html.return_value = """
        <ul class="stui-vodlist clearfix">
          <li>
            <a href="/voddetail/34567.html" title="搜索命中" data-original="/search.jpg"></a>
            <span class="pic-text">抢先版</span>
          </li>
        </ul>
        """
        result = self.spider.searchContent("繁花", False, "1")
        self.assertEqual(
            mock_request_html.call_args.args[0],
            "https://www.zxzjhd.com/vodsearch/%E7%B9%81%E8%8A%B1-------------.html",
        )
        self.assertEqual(result["list"][0]["vod_name"], "搜索命中")
        self.assertNotIn("pagecount", result)

    def test_detect_pan_type_prefers_share_domain(self):
        self.assertEqual(self.spider._detect_pan_type("百度网盘", "https://pan.quark.cn/s/demo"), "quark")
        self.assertEqual(self.spider._detect_pan_type("资源链接", "https://drive.uc.cn/s/demo"), "uc")
        self.assertEqual(self.spider._detect_pan_type("阿里网盘", "https://www.alipan.com/s/demo"), "aliyun")

    @patch.object(Spider, "_request_html")
    def test_detail_content_merges_zxzj_and_netdisk_groups(self, mock_request_html):
        mock_request_html.side_effect = [
            """
            <div class="stui-content__thumb"><img data-original="/poster.jpg" /></div>
            <div class="stui-content__detail">
              <h1 class="title">示例剧 2025 日本 剧情</h1>
              <p><span class="text-muted">导演：</span><a>导演甲</a></p>
              <p><span class="text-muted">主演：</span><a>演员甲</a><a>演员乙</a></p>
            </div>
            <div class="detail">一段剧情简介</div>
            <div class="stui-vodlist__head"><h3>在线播放</h3></div>
            <ul class="stui-content__playlist clearfix">
              <li><a href="/vodplay/999-1-1.html">第1集</a></li>
              <li><a href="/vodplay/999-1-2.html">第2集</a></li>
            </ul>
            <div class="stui-vodlist__head"><h3>夸克网盘</h3></div>
            <ul class="stui-content__playlist clearfix">
              <li><a href="/vodplay/999-pan-1.html">夸克一</a></li>
              <li><a href="/vodplay/999-pan-2.html">夸克二</a></li>
            </ul>
            <div class="stui-vodlist__head"><h3>百度云</h3></div>
            <ul class="stui-content__playlist clearfix">
              <li><a href="/vodplay/999-pan-bd.html">百度合集</a></li>
            </ul>
            """,
            '<script>var player_aaaa={"url":"https://pan.quark.cn/s/q-demo"};</script>',
            '<script>var player_aaaa={"url":"https://pan.quark.cn/s/q-demo"};</script>',
            '<script>var player_aaaa={"url":"https://pan.baidu.com/s/b-demo"};</script>',
        ]
        result = self.spider.detailContent(["voddetail/999.html"])
        vod = result["list"][0]
        self.assertEqual(vod["vod_id"], "voddetail/999.html")
        self.assertEqual(vod["vod_name"], "示例剧")
        self.assertEqual(vod["vod_pic"], "https://www.zxzjhd.com/poster.jpg")
        self.assertEqual(vod["vod_year"], "2025")
        self.assertEqual(vod["vod_area"], "日本")
        self.assertEqual(vod["vod_class"], "剧情")
        self.assertEqual(vod["vod_director"], "导演甲")
        self.assertEqual(vod["vod_actor"], "演员甲,演员乙")
        self.assertEqual(vod["vod_content"], "一段剧情简介")
        self.assertEqual(vod["vod_play_from"], "zxzj$$$quark$$$baidu")
        self.assertEqual(
            vod["vod_play_url"],
            "第1集$vodplay/999-1-1.html#第2集$vodplay/999-1-2.html$$$夸克一$https://pan.quark.cn/s/q-demo$$$百度合集$https://pan.baidu.com/s/b-demo",
        )

    @patch.object(Spider, "_request_html")
    def test_extract_pan_groups_skips_invalid_or_unknown_links(self, mock_request_html):
        mock_request_html.side_effect = [
            '<script>var player_aaaa={"url":"https://example.com/not-pan"};</script>',
            '<html><body>empty</body></html>',
        ]
        groups = self.spider._extract_pan_groups(
            [
                {"name": "无效一", "url": "https://www.zxzjhd.com/vodplay/x-1.html", "tab_name": "网盘资源"},
                {"name": "无效二", "url": "https://www.zxzjhd.com/vodplay/x-2.html", "tab_name": "网盘资源"},
            ]
        )
        self.assertEqual(groups, [])

    def test_decrypt_url_round_trip_with_fixture(self):
        self.assertEqual(
            self.spider._decrypt_url("d6f636e256c607d6168756e2f67464544434241456469667f2f2a33707474786"),
            "https://video.example.com",
        )

    def test_extract_iframe_url_reads_jx_target(self):
        html = '<script>var player_data = {"url":"https://jx.zxzj.example/player?id=1"};</script>'
        self.assertEqual(
            self.spider._extract_iframe_url(html),
            "https://jx.zxzj.example/player?id=1",
        )

    @patch.object(Spider, "_request_html")
    def test_player_content_returns_decoded_direct_url_for_zxzj(self, mock_request_html):
        mock_request_html.side_effect = [
            '<script>var player_data = {"url":"https://jx.zxzj.example/player?id=1"};</script>',
            '<script>var result_v2 = {"data":"d6f636e256c607d6168756e2f67464544434241456469667f2f2a33707474786"};</script>',
        ]
        result = self.spider.playerContent("zxzj", "vodplay/999-1-1.html", {})
        self.assertEqual(result["parse"], 0)
        self.assertEqual(result["jx"], 0)
        self.assertEqual(result["url"], "https://video.example.com")
        self.assertEqual(result["header"]["Referer"], "https://jx.zxzj.example/player?id=1")

    @patch.object(Spider, "_request_html")
    def test_player_content_falls_back_to_play_page_when_decrypt_fails(self, mock_request_html):
        mock_request_html.side_effect = [
            '<script>var player_data = {"url":"https://jx.zxzj.example/player?id=1"};</script>',
            '<script>var result_v2 = {"data":"broken"};</script>',
        ]
        result = self.spider.playerContent("zxzj", "vodplay/999-1-1.html", {})
        self.assertEqual(result["parse"], 1)
        self.assertEqual(result["jx"], 1)
        self.assertEqual(result["url"], "https://www.zxzjhd.com/vodplay/999-1-1.html")

    def test_player_content_returns_direct_netdisk_link(self):
        result = self.spider.playerContent("quark", "https://pan.quark.cn/s/demo", {})
        self.assertEqual(
            result,
            {"parse": 0, "jx": 0, "playUrl": "", "url": "https://pan.quark.cn/s/demo", "header": {}},
        )

    def test_home_content_keeps_reference_filter_values_for_movie_and_anime(self):
        filters = self.spider.homeContent(False)["filters"]
        movie_filters = filters["1"]
        anime_filters = filters["6"]
        self.assertIn({"n": "喜剧", "v": "喜剧"}, movie_filters[0]["value"])
        self.assertIn({"n": "欧美", "v": "欧美"}, movie_filters[1]["value"])
        self.assertIn({"n": "2025", "v": "2025"}, movie_filters[2]["value"])
        self.assertEqual(movie_filters[3]["value"][1], {"n": "人气", "v": "hits"})
        self.assertIn({"n": "国产", "v": "国产"}, anime_filters[1]["value"])
        self.assertIn({"n": "热血", "v": "热血"}, anime_filters[0]["value"])


if __name__ == "__main__":
    unittest.main()
