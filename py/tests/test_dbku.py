import unittest
import base64
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
MODULE = SourceFileLoader("dbku_spider", str(ROOT / "独播库.py")).load_module()
Spider = MODULE.Spider


class TestDBKUSpider(unittest.TestCase):
    def setUp(self):
        self.spider = Spider()
        self.spider.init()

    def test_home_content_exposes_expected_categories(self):
        content = self.spider.homeContent(False)
        class_ids = [item["type_id"] for item in content["class"]]
        self.assertEqual(class_ids, ["index", "movie", "variety", "anime", "hk", "luju"])

    def test_parse_list_cards_extracts_detail_url_title_cover_and_description(self):
        html = """
        <div class="myui-vodlist__box">
          <a class="thumb" href="/voddetail/123.html" title="示例影片" data-original="https://img.example/dbku.jpg"></a>
          <span class="pic-text">更新至10集</span>
        </div>
        """
        cards = self.spider._parse_list_cards(html)
        self.assertEqual(
            cards,
            [
                {
                    "vod_id": "123",
                    "vod_name": "示例影片",
                    "vod_pic": "https://img.example/dbku.jpg",
                    "vod_remarks": "更新至10集",
                }
            ],
        )

    @patch.object(Spider, "fetch")
    def test_request_html_uses_dbku_headers(self, mock_fetch):
        class FakeResponse:
            def __init__(self, text):
                self.text = text
                self.status_code = 200
                self.encoding = "utf-8"

        mock_fetch.return_value = FakeResponse("<html><body>ok</body></html>")
        html = self.spider._request_html("/vodtype/1--------1---.html", expect_xpath="//body")
        self.assertIn("ok", html)
        called_headers = mock_fetch.call_args.kwargs["headers"]
        self.assertEqual(called_headers["Referer"], "https://www.dbku.tv")
        self.assertEqual(called_headers["Origin"], "https://www.dbku.tv")

    @patch.object(Spider, "_request_html")
    def test_category_content_builds_page_result(self, mock_request_html):
        mock_request_html.return_value = """
        <div class="myui-vodlist__box">
          <a href="/voddetail/456.html" title="分类影片" data-original="/cover.jpg"></a>
          <span class="pic-text">HD</span>
        </div>
        """
        result = self.spider.categoryContent("movie", "2", False, {})
        self.assertEqual(result["page"], 2)
        self.assertEqual(result["list"][0]["vod_name"], "分类影片")
        self.assertEqual(result["list"][0]["vod_pic"], "https://www.dbku.tv/cover.jpg")

    def test_parse_search_cards_prefers_search_list_container(self):
        html = """
        <div id="searchList">
          <div class="myui-vodlist__box">
            <a href="/voddetail/789.html" title="搜索命中" data-original="/search.jpg"></a>
          </div>
        </div>
        <div class="myui-vodlist__box">
          <a href="/voddetail/999.html" title="回退结果" data-original="/fallback.jpg"></a>
        </div>
        """
        results = self.spider._parse_search_cards(html)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["vod_name"], "搜索命中")

    @patch.object(Spider, "_request_html")
    def test_search_content_reuses_search_parser(self, mock_request_html):
        mock_request_html.return_value = """
        <div id="searchList">
          <div class="myui-vodlist__box">
            <a href="/voddetail/321.html" title="搜索影片" data-original="/search.jpg"></a>
          </div>
        </div>
        """
        result = self.spider.searchContent("繁花", False, "1")
        self.assertEqual(result["list"][0]["vod_id"], "321")
        self.assertEqual(result["list"][0]["vod_name"], "搜索影片")

    def test_parse_detail_page_extracts_meta_and_episodes(self):
        html = """
        <div class="myui-content__thumb">
          <img data-original="/poster.jpg" />
        </div>
        <div class="myui-content__detail">
          <h1 class="title">独播剧</h1>
          <p>年份：2025</p>
          <p>地区：大陆</p>
          <p>导演：张三</p>
          <p>主演：李四</p>
        </div>
        <span class="data">一段剧情简介</span>
        <a href="/vodplay/100-1-1.html">第1集</a>
        <a href="/vodplay/100-1-2.html">第2集</a>
        """
        result = self.spider._parse_detail_page(html, "100")
        vod = result["list"][0]
        self.assertEqual(vod["vod_id"], "100")
        self.assertEqual(vod["vod_name"], "独播剧")
        self.assertEqual(vod["vod_year"], "2025")
        self.assertEqual(vod["vod_play_from"], "独播库")
        self.assertIn("第1集$100-1-1", vod["vod_play_url"])

    def test_parse_detail_page_extracts_structured_fields_from_detail_block(self):
        html = """
        <div class="myui-content__thumb">
          <img data-original="/poster-ai.jpg" />
        </div>
        <div class="myui-content__detail">
          <h1 class="title">AI教我谈恋爱</h1>
          <div id="rating" class="score" data-mid="1" data-id="143508" data-score="3">
            <span class="branch">6</span>
          </div>
          <p class="data">
            <span class="text-muted">分类：</span><a href="/vodshow/21-----------.html">短剧</a>
            <span class="split-line"></span>
            <span class="text-muted hidden-xs">地区：</span><a href="/vodshow/21-大陆----------.html">大陆</a>
            <span class="split-line"></span>
            <span class="text-muted hidden-xs">年份：</span><a href="/vodshow/21-----------2026.html">2026</a>
          </p>
          <p class="data hidden-sm"><span class="text-muted">更新：</span><span class="text-red">2026-04-18 09:59:00</span></p>
          <p class="data">
            <span class="text-muted">主演：</span>
            <a href="/vodsearch/-%E7%AB%A0%E7%85%9C%E5%A5%87------------.html" target="_blank">章煜奇</a>&nbsp;
            <a href="/vodsearch/-%E8%A2%81%E4%BC%8A------------.html" target="_blank">袁伊</a>&nbsp;
            <a href="/vodsearch/-%E9%83%AD%E5%AD%90%E6%B8%9D------------.html" target="_blank">郭子渝</a>&nbsp;
            <a href="/vodsearch/-%E5%88%98%E5%B8%8C%E5%A9%A7------------.html" target="_blank">刘希婧</a>&nbsp;
          </p>
          <p class="data">
            <span class="text-muted">导演：</span>
            <a href="/vodsearch/-----%E5%BC%A0%E4%B8%96%E5%8D%9A--------.html" target="_blank">张世博</a>&nbsp;
            <a href="/vodsearch/-----%E6%BA%90%E8%AF%97%E5%98%89--------.html" target="_blank">源诗嘉</a>&nbsp;
          </p>
          <p class="data hidden-xs"><span class="text-muted">简介：</span>《AI教我谈恋爱》线上看，共26集，《AI教我谈恋爱》简介:漫画家袁七柚意外绑定...<a href="#desc">详情</a></p>
        </div>
        <a href="/vodplay/143508-1-1.html">第1集</a>
        """
        result = self.spider._parse_detail_page(html, "143508")
        vod = result["list"][0]
        self.assertEqual(vod["vod_id"], "143508")
        self.assertEqual(vod["path"], "https://www.dbku.tv/voddetail/143508.html")
        self.assertEqual(vod["vod_pic"], "https://www.dbku.tv/poster-ai.jpg")
        self.assertEqual(vod["type_name"], "短剧")
        self.assertEqual(vod["vod_area"], "大陆")
        self.assertEqual(vod["vod_year"], "2026")
        self.assertEqual(vod["vod_time"], "2026-04-18 09:59:00")
        self.assertEqual(vod["vod_actor"], "章煜奇,袁伊,郭子渝,刘希婧")
        self.assertEqual(vod["vod_director"], "张世博,源诗嘉")
        self.assertEqual(vod["vod_content"], "《AI教我谈恋爱》线上看，共26集，《AI教我谈恋爱》简介:漫画家袁七柚意外绑定...")
        self.assertEqual(vod["vod_play_url"], "第1集$143508-1-1")
        self.assertEqual(vod["vod_tag"], "")
        self.assertEqual(vod["vod_remarks"], "6")
        self.assertEqual(vod["vod_lang"], "")
        self.assertNotIn("dbid", vod)
        self.assertNotIn("type", vod)

    @patch.object(Spider, "_request_html")
    def test_detail_content_reads_from_vod_id_url(self, mock_request_html):
        mock_request_html.return_value = """
        <h1 class="title">详情影片</h1>
        <a href="/vodplay/200-1-1.html">第1集</a>
        """
        result = self.spider.detailContent(["200"])
        self.assertEqual(mock_request_html.call_args.args[0], "https://www.dbku.tv/voddetail/200.html")
        self.assertEqual(result["list"][0]["vod_id"], "200")
        self.assertEqual(result["list"][0]["vod_name"], "详情影片")

    def test_parse_player_data_reads_json_block(self):
        html = '<script>var player_data = {"url":"https://video.example/a.m3u8","encrypt":"0"};</script>'
        data = self.spider._parse_player_data(html)
        self.assertEqual(data["url"], "https://video.example/a.m3u8")

    def test_decode_play_url_by_encrypt_supports_modes_0_1_2_3(self):
        self.assertEqual(
            self.spider._decode_play_url_by_encrypt("https://video.example/raw.m3u8", 0),
            "https://video.example/raw.m3u8",
        )
        self.assertEqual(
            self.spider._decode_play_url_by_encrypt("https%3A//video.example/escape.m3u8", 1),
            "https://video.example/escape.m3u8",
        )
        mode2 = base64.b64encode("https://video.example/base64.m3u8".encode("utf-8")).decode("utf-8")
        self.assertEqual(
            self.spider._decode_play_url_by_encrypt(mode2, 2),
            "https://video.example/base64.m3u8",
        )
        mode3_raw = "ABCDEFGHhttps://video.example/trimmed.m3u8HGFEDCBA"
        mode3 = base64.b64encode(mode3_raw.encode("utf-8")).decode("utf-8")
        self.assertEqual(
            self.spider._decode_play_url_by_encrypt("12345678" + mode3, 3),
            "https://video.example/trimmed.m3u8",
        )

    @patch.object(Spider, "_request_html")
    def test_player_content_returns_decoded_direct_url(self, mock_request_html):
        mock_request_html.return_value = """
        <script>
        var player_data = {"url":"https://video.example/final.m3u8","encrypt":"0"};
        </script>
        """
        result = self.spider.playerContent("独播库", "100-1-1", {})
        self.assertEqual(result["parse"], 0)
        self.assertEqual(result["url"], "https://video.example/final.m3u8")
        self.assertEqual(result["header"]["Referer"], "https://www.dbku.tv/vodplay/100-1-1.html")

    @patch.object(Spider, "_request_html")
    def test_player_content_follows_internal_jump(self, mock_request_html):
        mock_request_html.side_effect = [
            '<script>var player_data = {"url":"/vodplay/100-1-2.html","encrypt":"0"};</script>',
            '<script>var player_data = {"url":"https://video.example/jump-final.m3u8","encrypt":"0"};</script>',
        ]
        result = self.spider.playerContent("独播库", "100-1-1", {})
        self.assertEqual(result["parse"], 0)
        self.assertEqual(result["url"], "https://video.example/jump-final.m3u8")


if __name__ == "__main__":
    unittest.main()
