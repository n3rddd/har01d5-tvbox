# coding=utf-8
import json
import re
import sys
from urllib.parse import parse_qsl, quote, urljoin, urlsplit

from lxml import html as lxml_html

from base.spider import Spider as BaseSpider

sys.path.append("..")


class Spider(BaseSpider):
    def __init__(self):
        self.name = "4KVM"
        self.host = "https://www.4kvm.org"
        self.page_limit = 30
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/134.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": self.host + "/",
            "Cache-Control": "no-cache",
        }
        self.play_extensions = (".m3u8", ".mp4", ".flv", ".avi", ".mkv", ".ts")

    def init(self, extend=""):
        return None

    def getName(self):
        return self.name

    def _build_url(self, path):
        return urljoin(self.host + "/", str(path or "").strip())

    def _normalize_url(self, value):
        raw = str(value or "").strip()
        if not raw:
            return ""
        if raw.startswith("//"):
            return "https:" + raw
        if raw.startswith(("http://", "https://")):
            return raw
        return self._build_url(raw.lstrip("/"))

    def _encode_site_path(self, value):
        raw = str(value or "").strip()
        if not raw:
            return ""
        if raw.startswith("//"):
            raw = "https:" + raw

        if raw.startswith(("http://", "https://")):
            parsed = urlsplit(raw)
            path = parsed.path.lstrip("/")
            query = parsed.query
        else:
            parsed = urlsplit(raw)
            path = parsed.path.lstrip("/")
            query = parsed.query

        if not path and not query:
            return ""
        return path + ("?" + query if query else "")

    def _decode_site_path(self, value):
        raw = str(value or "").strip()
        if not raw:
            return ""
        if raw.startswith(("http://", "https://")):
            return raw
        return self._build_url(raw.lstrip("/"))

    def _request_html(self, url):
        response = self.fetch(url, headers=self.headers, timeout=10, verify=False)
        if response.status_code != 200:
            return ""
        return response.text or ""

    def _parse_html(self, html_text):
        text = str(html_text or "").strip()
        if not text:
            return None
        return lxml_html.fromstring(text)

    def _clean_text(self, value):
        return re.sub(r"\s+", " ", str(value or "").replace("\xa0", " ")).strip()

    def _first_non_empty(self, values):
        for value in values:
            clean = self._clean_text(value)
            if clean:
                return clean
        return ""

    def _node_text(self, node):
        if node is None:
            return ""
        return self._clean_text("".join(node.xpath(".//text()")))

    def _first_xpath_text(self, node, expressions):
        for expr in expressions:
            values = node.xpath(expr)
            if not values:
                continue
            if isinstance(values[0], str):
                text = self._first_non_empty(values)
            else:
                text = self._first_non_empty([self._node_text(item) for item in values])
            if text:
                return text
        return ""

    def _first_xpath_attr(self, node, expressions):
        for expr in expressions:
            values = node.xpath(expr)
            if values:
                value = self._clean_text(values[0])
                if value:
                    return value
        return ""

    def _is_allowed_class_link(self, href):
        path = "/" + self._encode_site_path(href).split("?", 1)[0].lstrip("/")
        return bool(re.match(r"^/(movie|tv|anime|filter)(/.*)?$", path))

    def _default_classes(self):
        return [
            {"type_id": "movie", "type_name": "电影"},
            {"type_id": "tv", "type_name": "电视剧"},
            {"type_id": "anime", "type_name": "动漫"},
            {"type_id": "filter", "type_name": "筛选"},
        ]

    def _extract_video_basic(self, node):
        href = self._first_xpath_attr(
            node,
            [
                ".//a[contains(@href,'/play/')]/@href",
                ".//a[1]/@href",
                ".//h3//a[1]/@href",
            ],
        )
        vod_id = self._encode_site_path(href)
        if not vod_id:
            return None

        title = self._first_xpath_text(
            node,
            [
                ".//h3[1]//text()",
                ".//*[contains(@class,'data')]//h3[1]//text()",
                ".//img[1]/@alt",
                ".//a[1]/@title",
            ],
        ) or "未知标题"
        pic = self._encode_site_path(
            self._first_xpath_attr(node, [".//img[1]/@data-src", ".//img[1]/@src"])
        )
        remarks = self._first_xpath_text(
            node,
            [
                ".//*[contains(@class,'absolute') and contains(@class,'bottom-0')]//span[last()]//text()",
                ".//*[contains(@class,'text-xs') and contains(@class,'text-gray-400')][last()]//text()",
                ".//*[contains(@class,'rating') or contains(@class,'imdb') or contains(@class,'vote')]//text()",
                ".//*[contains(@class,'type') or contains(@class,'genre') or contains(@class,'tag')]//text()",
                ".//span[last()]//text()",
            ],
        )

        return {
            "vod_id": vod_id,
            "vod_name": title,
            "vod_pic": self._decode_site_path(pic) if pic else "",
            "vod_remarks": remarks,
        }

    def _card_nodes(self, root):
        if root is None:
            return []
        return root.xpath(
            "//*[contains(@class,'movie-card')]"
            "|//article"
            "|//*[contains(@class,'items')]//article"
            "|//*[contains(@class,'content')]//article"
        )

    def _parse_video_list(self, html_text):
        root = self._parse_html(html_text)
        seen = set()
        videos = []
        for node in self._card_nodes(root):
            item = self._extract_video_basic(node)
            if not item or item["vod_id"] in seen:
                continue
            seen.add(item["vod_id"])
            videos.append(item)
        return videos

    def _parse_search_video_list(self, html_text):
        root = self._parse_html(html_text)
        if root is None:
            return []

        videos = []
        seen = set()
        for node in root.xpath("//a[starts-with(@href,'/play/')]"):
            vod_id = self._encode_site_path(node.get("href"))
            if not vod_id or vod_id in seen:
                continue

            title = self._first_non_empty(
                [
                    self._first_xpath_text(node, [".//h3[1]//text()"]),
                    node.xpath(".//img[1]/@alt")[0] if node.xpath(".//img[1]/@alt") else "",
                    node.get("title", ""),
                ]
            )
            if not title:
                continue

            pic = self._first_xpath_attr(node, [".//img[1]/@data-src", ".//img[1]/@src"])
            remarks = self._first_xpath_text(
                node,
                [
                    ".//*[contains(@class,'absolute') and contains(@class,'top-2') and contains(@class,'right-2')]//text()",
                    ".//*[contains(@class,'absolute') and contains(@class,'bottom-0')]//p//text()",
                ],
            )

            seen.add(vod_id)
            videos.append(
                {
                    "vod_id": vod_id,
                    "vod_name": title,
                    "vod_pic": self._decode_site_path(self._encode_site_path(pic)) if pic else "",
                    "vod_remarks": remarks,
                }
            )
        return videos

    def _page_result(self, items, pg):
        page = int(pg)
        return {
            "list": items,
            "page": page,
            "limit": self.page_limit,
            "total": (max(page, 1) - 1) * self.page_limit + len(items),
        }

    def homeContent(self, filter):
        html_text = self._request_html(self.host)
        root = self._parse_html(html_text)
        classes = []
        seen = set()
        if root is not None:
            for node in root.xpath("//nav//a[contains(@class,'nav-item')]"):
                name = self._node_text(node)
                href = node.get("href", "")
                type_id = self._encode_site_path(href)
                if (
                    not name
                    or not type_id
                    or name in ["首页", "影片下载", "片单"]
                    or not self._is_allowed_class_link(href)
                    or type_id in seen
                ):
                    continue
                seen.add(type_id)
                classes.append({"type_id": type_id, "type_name": name})
        return {"class": classes or self._default_classes()}

    def homeVideoContent(self):
        html_text = self._request_html(self.host)
        return {"list": self._parse_video_list(html_text)}

    def _build_category_url(self, tid, pg):
        encoded = self._encode_site_path(tid)
        if not encoded:
            return self.host
        url = self._decode_site_path(encoded)
        page = int(pg)
        if page <= 1:
            return url
        return url + ("&" if "?" in url else "?") + f"page={page}"

    def categoryContent(self, tid, pg, filter, extend):
        html_text = self._request_html(self._build_category_url(tid, pg))
        return self._page_result(self._parse_video_list(html_text), pg)

    def filterSearchResults(self, results, search_key):
        if not results or not search_key:
            return results

        query = self._clean_text(search_key).lower()
        words = [item for item in query.split(" ") if item]
        scored = []
        for item in results:
            title = self._clean_text(item.get("vod_name", "")).lower()
            score = 0
            if query == title:
                score = 100
            elif title.startswith(query):
                score = 80
            elif query in title:
                score = 70
            elif words and all(word in title for word in words):
                score = 60
            else:
                matches = len([word for word in words if word in title])
                if matches == 0:
                    continue
                score = 30 + matches * 10

            if "剧" in query and ("tvshows" in item.get("vod_id", "") or "/tv/" in item.get("vod_id", "")):
                score += 5
            if "电影" in query and ("movies" in item.get("vod_id", "") or "/movie/" in item.get("vod_id", "")):
                score += 5
            scored.append({"score": score, "result": item})

        scored.sort(key=lambda item: item["score"], reverse=True)
        min_score = 30 if len(words) > 1 else 40
        filtered = [item["result"] for item in scored if item["score"] >= min_score]
        if len(filtered) < 3 and len(scored) > 3:
            return [item["result"] for item in scored[:10]]
        return filtered

    def searchContent(self, key, quick, pg="1"):
        page = int(pg)
        url = f"{self.host}/search?q={quote(str(key or ''))}"
        if page > 1:
            url += f"&page={page}"
        html_text = self._request_html(url)
        items = self.filterSearchResults(self._parse_search_video_list(html_text), key)
        return self._page_result(items, pg)

    def _extract_detail_map(self, root):
        detail_map = {}
        if root is None:
            return detail_map
        for node in root.xpath("//*[contains(@class,'grid')]//*[contains(@class,'text-gray-500')]"):
            key = self._node_text(node)
            value_node = node.getnext()
            value = self._node_text(value_node)
            if key and value:
                detail_map[key] = value
        return detail_map

    def _extract_play_options(self, root, detail_id):
        if root is None:
            return []
        play_links = []
        nodes = root.xpath(
            "//*[@id='playeroptions']//li"
            "|//*[contains(concat(' ', normalize-space(@class), ' '), ' dooplay_player_option ')]"
        )
        for node in nodes:
            title = self._first_xpath_text(node, [".//*[contains(@class,'title')]//text()", ".//span[contains(@class,'title')]//text()"]) or "播放"
            server = self._first_xpath_text(node, [".//*[contains(@class,'server')]//text()", ".//span[contains(@class,'server')]//text()"])
            if server:
                title = f"{title}-{server}"

            data_post = self._clean_text(node.get("data-post", ""))
            data_nume = self._clean_text(node.get("data-nume", ""))
            data_type = self._clean_text(node.get("data-type", "")) or "movie"
            if not data_post or not data_nume:
                continue
            play_links.append(
                {
                    "name": title,
                    "url": f"{detail_id}?post={data_post}&nume={data_nume}&type={data_type}",
                }
            )
        return play_links

    def _extract_episode_sources(self, root, detail_id):
        if root is None:
            return []
        source_map = {}
        order_keys = []
        for node in root.xpath("//*[contains(concat(' ', normalize-space(@class), ' '), ' episode-link ')][@data-line][@data-episode]"):
            href = self._encode_site_path(node.get("href", ""))
            if not href:
                continue
            line = self._clean_text(node.get("data-line", "")) or "1"
            source_name = f"线路{line}"
            raw_name = self._first_xpath_text(node, [".//span[last()]//text()"]) or self._clean_text(node.get("data-episode", "")) or "播放"
            episode_number = self._clean_text(node.get("data-episode", ""))
            if raw_name.isdigit():
                episode_name = f"第{raw_name}集"
            elif episode_number.isdigit():
                episode_name = f"第{episode_number}集"
            else:
                episode_name = raw_name

            if source_name not in source_map:
                source_map[source_name] = []
                order_keys.append(source_name)

            try:
                order = int(episode_number)
            except Exception:
                order = len(source_map[source_name]) + 1

            source_map[source_name].append({"name": episode_name, "url": href, "order": order})

        sources = []
        for name in order_keys:
            episodes = source_map[name]
            episodes.sort(key=lambda item: item["order"])
            sources.append({"name": name, "episodes": [{"name": item["name"], "url": item["url"]} for item in episodes]})

        if sources:
            return sources

        play_links = self._extract_play_options(root, detail_id)
        if play_links:
            return [{"name": "4KVM", "episodes": play_links}]
        return []

    def _serialize_play_sources(self, sources):
        valid = [item for item in sources if item.get("episodes")]
        return {
            "vod_play_from": "$$$".join([item.get("name", "") for item in valid]) or "4KVM",
            "vod_play_url": "$$$".join(
                ["#".join([f"{ep.get('name', '')}${ep.get('url', '')}" for ep in item.get("episodes", [])]) for item in valid]
            ),
        }

    def detailContent(self, ids):
        detail_id = self._encode_site_path(ids[0] if ids else "")
        html_text = self._request_html(self._decode_site_path(detail_id))
        root = self._parse_html(html_text)
        detail_map = self._extract_detail_map(root)

        meta_desc = self._first_xpath_attr(root, ["//meta[@name='description']/@content"]) if root is not None else ""
        meta_pic = self._first_xpath_attr(root, ["//meta[@property='og:image']/@content"]) if root is not None else ""
        meta_title = self._first_xpath_attr(root, ["//meta[@property='og:title']/@content"]) if root is not None else ""
        meta_keywords = self._first_xpath_attr(root, ["//meta[@name='keywords']/@content"]) if root is not None else ""

        vod = {
            "vod_id": detail_id,
            "vod_name": self._first_xpath_text(root, ["//h1[contains(@class,'text-xl')][1]//text()", "//h1[1]//text()"])
            or re.sub(r"\s*-\s*第\d+集.*$", "", meta_title)
            or "未知标题",
            "vod_pic": self._decode_site_path(
                self._encode_site_path(
                    self._first_xpath_attr(root, ["//*[contains(@class,'video-player')][1]/@data-poster", "//*[contains(@class,'video-player')]//img[1]/@src"])
                    or meta_pic
                )
            ),
            "vod_content": self._first_xpath_text(
                root,
                ["//*[contains(@class,'bg-dark-800')]//p[contains(@class,'text-xs') and contains(@class,'text-gray-300')][1]//text()"],
            )
            or self._clean_text(meta_desc),
            "vod_year": detail_map.get("年份", ""),
            "vod_area": detail_map.get("地区", "") or detail_map.get("国家/地区", ""),
            "vod_remarks": detail_map.get("状态", ""),
            "vod_actor": detail_map.get("主演", ""),
            "vod_director": detail_map.get("导演", ""),
        }

        genres = []
        if detail_map.get("类型"):
            genres.extend([self._clean_text(item) for item in detail_map["类型"].split("/") if self._clean_text(item)])
        elif meta_keywords:
            keywords = [self._clean_text(item) for item in meta_keywords.split(",") if self._clean_text(item)]
            genres.extend([item for item in keywords if item not in [vod["vod_name"], vod["vod_director"]]][:1])
        if genres:
            vod["type_name"] = ", ".join(genres)

        sources = self._extract_episode_sources(root, detail_id)
        if not sources:
            sources = [{"name": "4KVM", "episodes": [{"name": "播放", "url": detail_id}]}]
        play_data = self._serialize_play_sources(sources)
        vod["vod_play_from"] = play_data["vod_play_from"]
        vod["vod_play_url"] = play_data["vod_play_url"]
        return {"list": [vod]}

    def _is_direct_play_url(self, url):
        lower_url = str(url or "").lower()
        return any(ext in lower_url for ext in self.play_extensions)

    def _parse_json(self, text):
        try:
            return json.loads(text or "{}")
        except Exception:
            return {}

    def playerContent(self, flag, id, vipFlags):
        encoded = self._encode_site_path(id)
        parsed = urlsplit(self._decode_site_path(encoded))
        base_id = parsed.path.lstrip("/")
        page_url = self._decode_site_path(base_id)
        params = dict(parse_qsl(parsed.query, keep_blank_values=True))
        data_post = self._clean_text(params.get("post", ""))
        data_nume = self._clean_text(params.get("nume", ""))
        data_type = self._clean_text(params.get("type", "")) or "movie"

        if data_post and data_nume:
            api_url = f"{self.host}/wp-json/dooplayer/v1/post/{data_post}"
            response = self.fetch(
                api_url,
                params={"type": data_type, "source": data_nume},
                headers=self.headers,
                timeout=10,
                verify=False,
            )
            if response.status_code == 200:
                embed_url = self._clean_text(self._parse_json(response.text).get("embed_url", ""))
                if embed_url:
                    return {
                        "parse": 0 if self._is_direct_play_url(embed_url) else 1,
                        "url": self._normalize_url(embed_url),
                        "header": self.headers,
                    }

        html_text = self._request_html(page_url)
        root = self._parse_html(html_text)
        iframe = self._first_xpath_attr(
            root,
            [
                "(//iframe[contains(@class,'metaframe')]/@src)",
                "(//*[contains(@class,'dooplay_player')]//iframe/@src)",
                "(//*[contains(@class,'player')]//iframe/@src)",
                "(//iframe/@src)",
            ],
        )
        if iframe:
            iframe_url = self._normalize_url(iframe)
            return {
                "parse": 0 if self._is_direct_play_url(iframe_url) else 1,
                "url": iframe_url,
                "header": self.headers,
            }

        video_url = self._first_xpath_attr(root, ["(//video/source/@src)", "(//video/@src)"])
        if video_url:
            full_video_url = self._normalize_url(video_url)
            return {"parse": 0, "url": full_video_url, "header": self.headers}

        return {"parse": 1, "url": page_url or self._decode_site_path(encoded), "header": self.headers}
