import unittest
import base64
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
MODULE = SourceFileLoader("gimy_spider", str(ROOT / "剧迷.py")).load_module()
Spider = MODULE.Spider


class TestGimySpider(unittest.TestCase):
    def setUp(self):
        Spider._instance = None
        self.spider = Spider()
        self.spider.init()

    def test_home_content_exposes_expected_categories_and_filters(self):
        content = self.spider.homeContent(False)
        class_ids = [item["type_id"] for item in content["class"]]
        self.assertEqual(class_ids, ["1", "2", "4", "29", "34", "13"])
        self.assertEqual(content["filters"]["2"][0]["key"], "by")
        self.assertEqual(content["filters"]["2"][0]["init"], "time")

    def test_parse_cards_extracts_vod_id_title_cover_and_remarks(self):
        html = """
        <div class="module-item">
          <a href="/detail/123.html" title="鬥羅大陸" data-original="/cover.jpg"></a>
          <div class="module-item-note">更新至第3集</div>
        </div>
        """
        items = self.spider._extract_cards(html)
        self.assertEqual(
            items,
            [
                {
                    "vod_id": "123",
                    "vod_name": "斗罗大陆",
                    "vod_pic": "https://gimyai.tw/cover.jpg",
                    "vod_remarks": "更新至第3集",
                }
            ],
        )

    def test_build_category_url_uses_default_sort_for_page1(self):
        self.assertEqual(
            self.spider._build_category_url("2", "1", {}),
            "https://gimyai.tw/genre/2.html",
        )

    def test_build_category_url_appends_page_and_sort_when_needed(self):
        self.assertEqual(
            self.spider._build_category_url("2", "3", {"by": "hits"}),
            "https://gimyai.tw/genre/2.html?page=3&by=hits",
        )

    @patch.object(Spider, "_request_html")
    def test_home_video_content_limits_to_24_items(self, mock_request_html):
        cards = []
        for index in range(1, 27):
            cards.append(
                f'<div class="module-item"><a href="/detail/{index}.html" title="影片{index}" data-original="/{index}.jpg"></a></div>'
            )
        mock_request_html.return_value = "".join(cards)
        result = self.spider.homeVideoContent()
        self.assertEqual(len(result["list"]), 24)
        self.assertEqual(result["list"][0]["vod_id"], "1")

    @patch.object(Spider, "_request_html")
    def test_category_content_builds_page_result(self, mock_request_html):
        mock_request_html.return_value = """
        <div class="module-item">
          <a href="/detail/456.html" title="分类影片" data-original="/cate.jpg"></a>
          <div class="module-item-note">HD</div>
        </div>
        """
        result = self.spider.categoryContent("2", "2", False, {"by": "hits"})
        self.assertEqual(mock_request_html.call_args.args[0], "https://gimyai.tw/genre/2.html?page=2&by=hits")
        self.assertEqual(result["page"], 2)
        self.assertEqual(result["pagecount"], 2)
        self.assertEqual(result["list"][0]["vod_name"], "分类影片")

    def test_parse_detail_page_extracts_meta_and_playlists(self):
        html = """
        <meta property="og:image" content="/poster.jpg" />
        <h1 class="text-overflow">機動戰士鋼彈</h1>
        <ul>
          <li><span>狀態：</span>更新至第2集</li>
          <li><span>類別：</span>動畫</li>
          <li><span>年代：</span>2026</li>
          <li><span>國家/地區：</span>日本</li>
          <li><span>導演：</span><a>导演甲</a></li>
          <li><span>主演：</span><a>演员甲</a><a>演员乙</a></li>
        </ul>
        <div class="details-content">一段劇情簡介</div>
        <div id="playTab">
          <a href="#con_playlist_1">Gimy</a>
          <a href="#con_playlist_2">雲播</a>
        </div>
        <div id="con_playlist_1">
          <a href="/play/100-1-1.html">第1集</a>
          <a href="/play/100-1-2.html">第2集</a>
        </div>
        <div id="con_playlist_2">
          <a href="/play/100-2-1.html">第1集</a>
        </div>
        """
        result = self.spider._parse_detail_page(html, "100")
        vod = result["list"][0]
        self.assertEqual(vod["vod_id"], "100")
        self.assertEqual(vod["vod_name"], "机动战士钢弹")
        self.assertEqual(vod["vod_pic"], "https://gimyai.tw/poster.jpg")
        self.assertEqual(vod["vod_content"], "一段剧情简介")
        self.assertEqual(vod["vod_remarks"], "更新至第2集")
        self.assertEqual(vod["type_name"], "动画")
        self.assertEqual(vod["vod_year"], "2026")
        self.assertEqual(vod["vod_area"], "日本")
        self.assertEqual(vod["vod_actor"], "演员甲,演员乙")
        self.assertEqual(vod["vod_director"], "导演甲")
        self.assertEqual(vod["vod_play_from"], "Gimy$$$云播")
        self.assertEqual(vod["vod_play_url"], "第1集$100-1-1#第2集$100-1-2$$$第1集$100-2-1")

    @patch.object(Spider, "_request_html")
    def test_detail_content_accepts_numeric_id(self, mock_request_html):
        mock_request_html.return_value = """
        <h1 class="text-overflow">详情影片</h1>
        <div id="playTab"><a href="#con_playlist_1">Gimy</a></div>
        <div id="con_playlist_1"><a href="/play/300-1-1.html">正片</a></div>
        """
        result = self.spider.detailContent(["300"])
        self.assertEqual(mock_request_html.call_args.args[0], "https://gimyai.tw/detail/300.html")
        self.assertEqual(result["list"][0]["vod_id"], "300")

    def test_normalize_search_keyword_removes_noise_and_converts_traditional(self):
        self.assertEqual(self.spider._normalize_search_keyword("鬥羅大陸 線上看"), "斗罗大陆线上看")

    def test_refine_search_results_prefers_exact_match_after_simplification(self):
        result = self.spider._refine_search_results(
            [
                {"vod_name": "鬥羅大陸", "vod_id": "1"},
                {"vod_name": "斗罗大陆2绝世唐门", "vod_id": "2"},
                {"vod_name": "海贼王", "vod_id": "3"},
            ],
            "斗罗大陆",
        )
        self.assertEqual([item["vod_id"] for item in result], ["1", "2"])

    @patch.object(Spider, "_request_html")
    def test_search_content_filters_raw_results(self, mock_request_html):
        mock_request_html.return_value = """
        <div class="box-main-content">
          <div class="module-item">
            <a href="/detail/11.html" title="鬥羅大陸" data-original="/a.jpg"></a>
          </div>
          <div class="module-item">
            <a href="/detail/12.html" title="海賊王" data-original="/b.jpg"></a>
          </div>
        </div>
        """
        result = self.spider.searchContent("斗罗大陆", False, "1")
        self.assertEqual([item["vod_id"] for item in result["list"]], ["11"])
        self.assertEqual(result["page"], 1)
        self.assertEqual(result["pagecount"], 1)

    def test_extract_player_data_reads_json_block(self):
        html = '<script>var player_data = {"url":"https://video.example/direct.m3u8","encrypt":"0","from":"gimy"};</script>'
        data = self.spider._extract_player_data(html)
        self.assertEqual(data["url"], "https://video.example/direct.m3u8")

    def test_decode_play_url_supports_encrypt_0_1_2(self):
        self.assertEqual(
            self.spider._decode_play_url({"url": "https://video.example/raw.m3u8", "encrypt": "0"}),
            "https://video.example/raw.m3u8",
        )
        self.assertEqual(
            self.spider._decode_play_url({"url": "https%3A%2F%2Fvideo.example%2Fescape.m3u8", "encrypt": "1"}),
            "https://video.example/escape.m3u8",
        )
        encoded = base64.b64encode("https://video.example/base64.m3u8".encode("utf-8")).decode("utf-8")
        self.assertEqual(
            self.spider._decode_play_url({"url": encoded, "encrypt": "2"}),
            "https://video.example/base64.m3u8",
        )

    @patch.object(Spider, "_request_html")
    def test_player_content_returns_direct_media_url(self, mock_request_html):
        mock_request_html.return_value = """
        <script>var player_data = {"url":"https://video.example/final.m3u8","encrypt":"0","from":"gimy"};</script>
        """
        result = self.spider.playerContent("Gimy", "100-1-1", {})
        self.assertEqual(result["parse"], 0)
        self.assertEqual(result["url"], "https://video.example/final.m3u8")
        self.assertEqual(result["header"]["Referer"], "https://gimyai.tw/play/100-1-1.html")

    @patch.object(Spider, "_request_html")
    def test_player_content_uses_parse_php_when_available(self, mock_request_html):
        mock_request_html.side_effect = [
            '<script>var player_data = {"url":"https://middle.example/embed?id=1","encrypt":"0","from":"JD4K"};</script>',
            '{"url":"https://video.example/parsed.m3u8"}',
        ]
        result = self.spider.playerContent("Gimy", "100-1-1", {})
        self.assertEqual(result["parse"], 0)
        self.assertEqual(result["url"], "https://video.example/parsed.m3u8")
        self.assertEqual(result["header"]["Origin"], "https://play.gimyai.tw")

    @patch.object(Spider, "_request_html")
    def test_player_content_falls_back_to_raw_url_when_parse_php_returns_empty(self, mock_request_html):
        mock_request_html.side_effect = [
            '<script>var player_data = {"url":"https://middle.example/embed?id=1","encrypt":"0","from":"NSYS"};</script>',
            '{}',
        ]
        result = self.spider.playerContent("Gimy", "100-1-1", {})
        self.assertEqual(result["parse"], 1)
        self.assertEqual(result["jx"], 1)
        self.assertEqual(result["url"], "https://middle.example/embed?id=1")

    @patch.object(Spider, "_request_html")
    def test_player_content_falls_back_to_play_page_when_player_data_missing(self, mock_request_html):
        mock_request_html.return_value = "<html><body>empty</body></html>"
        result = self.spider.playerContent("Gimy", "100-1-1", {})
        self.assertEqual(result["parse"], 1)
        self.assertEqual(result["jx"], 1)
        self.assertEqual(result["url"], "https://gimyai.tw/play/100-1-1.html")


if __name__ == "__main__":
    unittest.main()
