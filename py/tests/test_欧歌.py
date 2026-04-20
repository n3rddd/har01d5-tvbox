import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
MODULE = SourceFileLoader("ouge_spider", str(ROOT / "欧歌.py")).load_module()
Spider = MODULE.Spider


class TestOuGeSpider(unittest.TestCase):
    def setUp(self):
        Spider._instance = None
        self.spider = Spider()
        self.spider.init()

    def test_home_content_exposes_reference_categories(self):
        content = self.spider.homeContent(False)
        self.assertEqual(
            [(item["type_id"], item["type_name"]) for item in content["class"]],
            [
                ("1", "欧歌电影"),
                ("2", "欧哥剧集"),
                ("3", "欧歌动漫"),
                ("4", "欧歌综艺"),
                ("5", "欧歌短剧"),
                ("21", "欧歌综合"),
            ],
        )

    def test_home_video_content_returns_empty_list(self):
        self.assertEqual(self.spider.homeVideoContent(), {"list": []})

    def test_build_url_joins_relative_paths_against_host(self):
        self.assertEqual(
            self.spider._build_url("/index.php/vod/detail/id/1.html"),
            "https://woog.nxog.eu.org/index.php/vod/detail/id/1.html",
        )
        self.assertEqual(
            self.spider._build_url("https://cdn.example.com/poster.jpg"),
            "https://cdn.example.com/poster.jpg",
        )

    def test_detect_pan_type_returns_expected_type_and_label(self):
        self.assertEqual(
            self.spider._detect_pan_type("https://pan.baidu.com/s/demo"),
            ("baidu", "百度资源"),
        )
        self.assertEqual(
            self.spider._detect_pan_type("https://pan.quark.cn/s/demo"),
            ("quark", "夸克资源"),
        )
        self.assertEqual(
            self.spider._detect_pan_type("https://example.com/video"),
            ("", ""),
        )

    def test_parse_cards_extracts_short_path_id_and_cover(self):
        html = """
        <div id="main">
          <div class="module-item">
            <div class="module-item-pic">
              <a href="/index.php/vod/detail/id/123.html"></a>
              <img data-src="/poster.jpg" alt="示例影片" />
            </div>
            <div class="module-item-text">HD</div>
          </div>
        </div>
        """
        self.assertEqual(
            self.spider._parse_cards(html),
            [
                {
                    "vod_id": "/index.php/vod/detail/id/123.html",
                    "vod_name": "示例影片",
                    "vod_pic": "https://woog.nxog.eu.org/poster.jpg",
                    "vod_remarks": "HD",
                }
            ],
        )

    @patch.object(Spider, "_request_html")
    def test_category_content_builds_reference_url_and_returns_page_payload(self, mock_request_html):
        mock_request_html.return_value = """
        <div id="main">
          <div class="module-item">
            <div class="module-item-pic">
              <a href="/index.php/vod/detail/id/456.html"></a>
              <img data-src="/cate.jpg" alt="分类影片" />
            </div>
            <div class="module-item-text">更新至10集</div>
          </div>
        </div>
        """
        result = self.spider.categoryContent("2", "3", False, {})
        self.assertEqual(
            mock_request_html.call_args.args[0],
            "https://woog.nxog.eu.org/index.php/vod/show/id/2/page/3.html",
        )
        self.assertEqual(result["page"], 3)
        self.assertEqual(result["limit"], 1)
        self.assertEqual(result["list"][0]["vod_name"], "分类影片")
        self.assertNotIn("pagecount", result)

    @patch.object(Spider, "_request_html")
    def test_search_content_builds_reference_url_and_parses_results(self, mock_request_html):
        mock_request_html.return_value = """
        <div class="module-search-item">
          <a class="video-serial" href="/index.php/vod/detail/id/789.html" title="搜索影片">抢先版</a>
          <div class="module-item-pic">
            <img data-src="/search.jpg" alt="搜索影片" />
          </div>
        </div>
        """
        result = self.spider.searchContent("繁花", False, "2")
        self.assertEqual(
            mock_request_html.call_args.args[0],
            "https://woog.nxog.eu.org/index.php/vod/search/page/2/wd/%E7%B9%81%E8%8A%B1.html",
        )
        self.assertEqual(
            result["list"][0],
            {
                "vod_id": "/index.php/vod/detail/id/789.html",
                "vod_name": "搜索影片",
                "vod_pic": "https://woog.nxog.eu.org/search.jpg",
                "vod_remarks": "抢先版",
            },
        )
        self.assertNotIn("pagecount", result)

    @patch.object(Spider, "_request_html")
    def test_search_content_short_circuits_blank_keyword(self, mock_request_html):
        result = self.spider.searchContent("", False, "1")
        self.assertEqual(result, {"page": 1, "total": 0, "list": []})
        mock_request_html.assert_not_called()


if __name__ == "__main__":
    unittest.main()
