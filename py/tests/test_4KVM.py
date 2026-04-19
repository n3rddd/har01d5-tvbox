import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
MODULE = SourceFileLoader("k4vm_spider", str(ROOT / "4KVM.py")).load_module()
Spider = MODULE.Spider


class FakeResponse:
    def __init__(self, text="", status_code=200, headers=None):
        self.text = text
        self.status_code = status_code
        self.headers = headers or {}
        self.encoding = "utf-8"


class Test4KVMSpider(unittest.TestCase):
    def setUp(self):
        Spider._instance = None
        self.spider = Spider()
        self.spider.init()

    def test_encode_site_path_keeps_short_ids(self):
        self.assertEqual(self.spider._encode_site_path("/play/test-slug"), "play/test-slug")
        self.assertEqual(self.spider._encode_site_path("https://www.4kvm.org/tv?page=2"), "tv?page=2")
        self.assertEqual(self.spider._decode_site_path("play/test-slug"), "https://www.4kvm.org/play/test-slug")

    @patch.object(Spider, "fetch")
    def test_home_content_and_home_video_content_parse_nav_and_cards(self, mock_fetch):
        mock_fetch.return_value = FakeResponse(
            """
            <html>
              <nav>
                <a class="nav-item" href="/">首页</a>
                <a class="nav-item" href="/movie">电影</a>
                <a class="nav-item" href="/tv">电视剧</a>
                <a class="nav-item" href="/anime">动漫</a>
                <a class="nav-item" href="/download">影片下载</a>
              </nav>
              <article class="movie-card">
                <a href="/play/home-film">
                  <img src="/poster.jpg" alt="首页推荐" />
                </a>
                <h3>首页推荐</h3>
                <div class="absolute bottom-0"><span>HD中字</span></div>
              </article>
            </html>
            """
        )

        home = self.spider.homeContent(False)
        videos = self.spider.homeVideoContent()

        self.assertEqual(
            home["class"],
            [
                {"type_id": "movie", "type_name": "电影"},
                {"type_id": "tv", "type_name": "电视剧"},
                {"type_id": "anime", "type_name": "动漫"},
            ],
        )
        self.assertEqual(
            videos["list"],
            [
                {
                    "vod_id": "play/home-film",
                    "vod_name": "首页推荐",
                    "vod_pic": "https://www.4kvm.org/poster.jpg",
                    "vod_remarks": "HD中字",
                }
            ],
        )

    @patch.object(Spider, "fetch")
    def test_category_content_builds_page_url_and_returns_items_without_pagecount(self, mock_fetch):
        mock_fetch.return_value = FakeResponse(
            """
            <html>
              <article>
                <a href="/play/cate-film"><img src="/cate.jpg" alt="分类片" /></a>
                <h3>分类片</h3>
                <span class="text-xs text-gray-400">更新至10集</span>
              </article>
            </html>
            """
        )

        result = self.spider.categoryContent("tv", "2", False, {})

        self.assertEqual(result["page"], 2)
        self.assertNotIn("pagecount", result)
        self.assertEqual(result["list"][0]["vod_id"], "play/cate-film")
        self.assertEqual(result["list"][0]["vod_remarks"], "更新至10集")
        self.assertEqual(mock_fetch.call_args.args[0], "https://www.4kvm.org/tv?page=2")

    @patch.object(Spider, "fetch")
    def test_search_content_filters_and_ranks_results(self, mock_fetch):
        mock_fetch.return_value = FakeResponse(
            """
            <html>
              <a href="/play/exact-hit">
                <img src="/exact.jpg" alt="繁花" />
                <h3>繁花</h3>
                <div class="absolute top-2 right-2">完结</div>
              </a>
              <a href="/play/partial-hit">
                <img src="/partial.jpg" alt="繁花前传" />
                <h3>繁花前传</h3>
              </a>
              <a href="/play/other">
                <img src="/other.jpg" alt="风起云涌" />
                <h3>风起云涌</h3>
              </a>
            </html>
            """
        )

        result = self.spider.searchContent("繁花", False, "3")

        self.assertEqual(result["page"], 3)
        self.assertNotIn("pagecount", result)
        self.assertEqual([item["vod_id"] for item in result["list"]], ["play/exact-hit", "play/partial-hit"])
        self.assertIn("/search?q=%E7%B9%81%E8%8A%B1&page=3", mock_fetch.call_args.args[0])

    @patch.object(Spider, "fetch")
    def test_detail_content_maps_meta_and_episode_sources(self, mock_fetch):
        mock_fetch.return_value = FakeResponse(
            """
            <html>
              <head>
                <meta name="description" content="站点简介" />
                <meta property="og:image" content="/meta.jpg" />
                <meta name="keywords" content="详情片,剧情,导演甲" />
              </head>
              <body>
                <h1 class="text-xl">详情片</h1>
                <div class="video-player" data-poster="/poster.jpg"></div>
                <div class="grid">
                  <div class="text-gray-500">年份</div><div>2025</div>
                  <div class="text-gray-500">地区</div><div>大陆</div>
                  <div class="text-gray-500">状态</div><div>更新至2集</div>
                  <div class="text-gray-500">主演</div><div>主演甲/主演乙</div>
                  <div class="text-gray-500">导演</div><div>导演甲</div>
                  <div class="text-gray-500">类型</div><div>剧情/动作</div>
                </div>
                <div class="bg-dark-800">
                  <p class="text-xs text-gray-300 leading-relaxed">正文简介</p>
                </div>
                <a class="episode-link" data-line="2" data-episode="1" href="/play/detail-slug?ep=1"><span>1</span></a>
                <a class="episode-link" data-line="1" data-episode="2" href="/play/detail-slug?ep=2"><span>2</span></a>
                <a class="episode-link" data-line="1" data-episode="1" href="/play/detail-slug?ep=1"><span>1</span></a>
              </body>
            </html>
            """
        )

        result = self.spider.detailContent(["play/detail-slug"])
        vod = result["list"][0]

        self.assertEqual(vod["vod_id"], "play/detail-slug")
        self.assertEqual(vod["vod_name"], "详情片")
        self.assertEqual(vod["vod_pic"], "https://www.4kvm.org/poster.jpg")
        self.assertEqual(vod["vod_content"], "正文简介")
        self.assertEqual(vod["vod_year"], "2025")
        self.assertEqual(vod["vod_area"], "大陆")
        self.assertEqual(vod["vod_remarks"], "更新至2集")
        self.assertEqual(vod["vod_actor"], "主演甲/主演乙")
        self.assertEqual(vod["vod_director"], "导演甲")
        self.assertEqual(vod["type_name"], "剧情, 动作")
        self.assertEqual(vod["vod_play_from"], "线路2$$$线路1")
        self.assertEqual(
            vod["vod_play_url"],
            "第1集$play/detail-slug?ep=1$$$第1集$play/detail-slug?ep=1#第2集$play/detail-slug?ep=2",
        )

    @patch.object(Spider, "fetch")
    def test_detail_content_falls_back_to_dooplay_options(self, mock_fetch):
        mock_fetch.return_value = FakeResponse(
            """
            <html>
              <body>
                <h1>选集片</h1>
                <li class="dooplay_player_option" data-post="7788" data-nume="2" data-type="movie">
                  <span class="title">正片</span>
                  <span class="server">海外</span>
                </li>
              </body>
            </html>
            """
        )

        result = self.spider.detailContent(["play/option-slug"])
        vod = result["list"][0]

        self.assertEqual(vod["vod_play_from"], "4KVM")
        self.assertEqual(vod["vod_play_url"], "正片-海外$play/option-slug?post=7788&nume=2&type=movie")

    @patch.object(Spider, "fetch")
    def test_player_content_prefers_api_embed_url(self, mock_fetch):
        def fake_fetch(url, params=None, headers=None, timeout=5, verify=True, stream=False, allow_redirects=True):
            self.assertEqual(url, "https://www.4kvm.org/wp-json/dooplayer/v1/post/7788")
            self.assertEqual(params, {"type": "movie", "source": "2"})
            return FakeResponse('{"embed_url":"https://cdn.example.com/master.m3u8"}')

        mock_fetch.side_effect = fake_fetch

        result = self.spider.playerContent("", "play/option-slug?post=7788&nume=2&type=movie", [])

        self.assertEqual(result["parse"], 0)
        self.assertEqual(result["url"], "https://cdn.example.com/master.m3u8")

    @patch.object(Spider, "fetch")
    def test_player_content_falls_back_to_iframe_then_video(self, mock_fetch):
        responses = [
            FakeResponse("{}", status_code=500),
            FakeResponse('<html><iframe class="metaframe" src="//player.example.com/embed/42"></iframe></html>'),
            FakeResponse('<html><video><source src="/stream.m3u8" /></video></html>'),
        ]
        mock_fetch.side_effect = responses

        iframe_result = self.spider.playerContent("", "play/fallback?post=11&nume=1&type=tv", [])
        video_result = self.spider.playerContent("", "play/video-only", [])

        self.assertEqual(iframe_result["parse"], 1)
        self.assertEqual(iframe_result["url"], "https://player.example.com/embed/42")
        self.assertEqual(video_result["parse"], 0)
        self.assertEqual(video_result["url"], "https://www.4kvm.org/stream.m3u8")


if __name__ == "__main__":
    unittest.main()
