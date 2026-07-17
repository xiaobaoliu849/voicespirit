from __future__ import annotations

import asyncio
import unittest
from unittest.mock import patch
from httpx import Response, Request

from services.audio_research_service import (
    AudioResearchService,
    DuckDuckGoResultParser,
    HtmlContentExtractor,
    ResearchDocument,
    _is_safe_public_url,
    _resolve_public_host,
)
from services.audio_retrieval_service import AudioRetrievalService
from services.audio_script_writer import AudioScriptWriter


class FakeResearchService:
    def __init__(self) -> None:
        self.search_calls: list[str] = []
        self.fetch_calls: list[str] = []

    async def search(self, query: str, *, limit: int = 5) -> list[dict[str, str]]:
        self.search_calls.append(query)
        return [
            {
                "title": "Search result",
                "url": "https://example.com/search-result",
                "snippet": "Search snippet",
            }
        ][:limit]

    async def fetch_document(
        self,
        url: str,
        *,
        title_hint: str = "",
        snippet_hint: str = "",
        source_type: str = "web_page",
        score: float = 0.7,
    ) -> ResearchDocument:
        self.fetch_calls.append(url)
        return ResearchDocument(
            title=title_hint or "Fetched page",
            url=url,
            snippet=snippet_hint or "Fetched snippet",
            content=f"Fetched content for {url}",
            score=score,
            source_type=source_type,
            meta={"fetch_status": "ok"},
        )


class FakeMemoryService:
    def should_skip_memory(self, topic: str) -> bool:
        _ = topic
        return False

    async def search_memories(
        self,
        *,
        query: str,
        user_id: str,
        min_score: float,
    ) -> list[dict[str, object]]:
        _ = (query, user_id, min_score)
        return [
            {"content": "First memory preference", "score": 0.92, "type": "preference"},
            {"content": "Second memory task context", "score": 0.88, "type": "task_context"},
        ]


class FakeAsyncClient:
    calls: list[str] = []
    responses: list[Response] = []
    errors: list[Exception] = []

    def __init__(self, *args, **kwargs) -> None:
        _ = (args, kwargs)

    async def __aenter__(self) -> "FakeAsyncClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        _ = (exc_type, exc, tb)

    async def get(self, url: str) -> Response:
        self.calls.append(url)
        if self.errors:
            raise self.errors.pop(0)
        response = self.responses.pop(0)
        response.request = Request("GET", url)
        return response


def fake_request_public_url_once(url: str, ip_address: str) -> Response:
    _ = ip_address
    FakeAsyncClient.calls.append(url)
    if FakeAsyncClient.errors:
        raise FakeAsyncClient.errors.pop(0)
    response = FakeAsyncClient.responses.pop(0)
    response.request = Request("GET", url)
    return response


async def fake_resolve_public_host(hostname: str, port: int | None) -> list[str]:
    _ = (hostname, port)
    return ["93.184.216.34"]


class AudioResearchServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        FakeAsyncClient.calls = []
        FakeAsyncClient.responses = []
        FakeAsyncClient.errors = []

    def test_safe_public_url_rejects_local_and_private_targets(self) -> None:
        self.assertFalse(_is_safe_public_url("file:///etc/passwd"))
        self.assertFalse(_is_safe_public_url("http://localhost:8000"))
        self.assertFalse(_is_safe_public_url("http://localhost.:8000"))
        self.assertFalse(_is_safe_public_url("http://127.0.0.1:8000"))
        self.assertFalse(_is_safe_public_url("http://127.1:8000"))
        self.assertFalse(_is_safe_public_url("http://2130706433:8000"))
        self.assertFalse(_is_safe_public_url("http://0x7f000001:8000"))
        self.assertFalse(_is_safe_public_url("http://0177.0.0.1:8000"))
        self.assertFalse(_is_safe_public_url("http://0x7f.0.0.1:8000"))
        self.assertFalse(_is_safe_public_url("http://127.000.000.001:8000"))
        self.assertFalse(_is_safe_public_url("http://10.0.0.8/page"))
        self.assertFalse(_is_safe_public_url("http://192.168.1.5/page"))
        self.assertFalse(_is_safe_public_url("http://[::1]:8000"))
        self.assertTrue(_is_safe_public_url("https://example.com/page"))
        self.assertTrue(_is_safe_public_url("https://93.184.216.34/page"))

    def test_resolve_public_host_rejects_private_dns_answers(self) -> None:
        def fake_getaddrinfo(*args, **kwargs):
            _ = (args, kwargs)
            return [
                (
                    2,
                    1,
                    6,
                    "",
                    ("192.168.1.20", 443),
                )
            ]

        with patch("services.audio_research_service.socket.getaddrinfo", fake_getaddrinfo):
            with self.assertRaises(ValueError):
                asyncio.run(_resolve_public_host("example.com", 443))

    def test_html_extractor_removes_noise_and_keeps_title_and_body(self) -> None:
        parser = HtmlContentExtractor()
        parser.feed(
            """
            <html><head><title> Research Title </title><style>.x{}</style></head>
            <body><nav>Navigation should disappear</nav>
            <main><p>This paragraph contains enough meaningful words to survive extraction.</p></main>
            <script>console.log('drop')</script></body></html>
            """
        )
        self.assertEqual(parser.title, "Research Title")
        self.assertIn("meaningful words", parser.text)
        self.assertNotIn("Navigation should disappear", parser.text)
        self.assertNotIn("console.log", parser.text)

    def test_duckduckgo_parser_extracts_redirected_result_urls(self) -> None:
        parser = DuckDuckGoResultParser()
        parser.feed(
            """
            <a class="result__a" href="/l/?uddg=https%3A%2F%2Fexample.com%2Fa">Example A</a>
            <a class="result__snippet">Useful snippet</a>
            """
        )
        self.assertEqual(parser.results[0]["title"], "Example A")
        self.assertEqual(parser.results[0]["url"], "https://example.com/a")
        self.assertEqual(parser.results[0]["snippet"], "Useful snippet")

    def test_fetch_document_rejects_unsafe_url_without_network(self) -> None:
        document = asyncio.run(AudioResearchService().fetch_document("http://127.0.0.1:8000/private"))
        self.assertEqual(document.meta["fetch_status"], "skipped")
        self.assertEqual(document.source_type, "web_page")
        self.assertEqual(document.content, "")

    def test_fetch_document_rejects_redirect_to_unsafe_url(self) -> None:
        FakeAsyncClient.responses = [
            Response(302, headers={"location": "http://127.0.0.1:8000/private"})
        ]
        with (
            patch(
                "services.audio_research_service.AudioResearchService._request_public_url_once",
                staticmethod(fake_request_public_url_once),
            ),
            patch("services.audio_research_service._resolve_public_host", fake_resolve_public_host),
        ):
            document = asyncio.run(AudioResearchService().fetch_document("https://example.com/redirect"))
        self.assertEqual(document.meta["fetch_status"], "failed")
        self.assertEqual(document.content, "")
        self.assertEqual(FakeAsyncClient.calls, ["https://example.com/redirect"])

    def test_fetch_document_extracts_html_with_final_url(self) -> None:
        FakeAsyncClient.responses = [
            Response(
                200,
                headers={"content-type": "text/html; charset=utf-8"},
                text="<html><title>Fetched Title</title><p>This article body is long enough to be extracted as research content.</p></html>",
            )
        ]
        with (
            patch(
                "services.audio_research_service.AudioResearchService._request_public_url_once",
                staticmethod(fake_request_public_url_once),
            ),
            patch("services.audio_research_service._resolve_public_host", fake_resolve_public_host),
        ):
            document = asyncio.run(AudioResearchService().fetch_document("https://example.com/article"))
        self.assertEqual(document.title, "Fetched Title")
        self.assertEqual(document.meta["fetch_status"], "ok")
        self.assertIn("article body", document.content)

    def test_fetch_document_connects_to_prevalidated_ip_address(self) -> None:
        captured: dict[str, str] = {}

        async def resolve_to_public_ip(hostname: str, port: int | None) -> list[str]:
            _ = (hostname, port)
            return ["93.184.216.34"]

        def capture_request(url: str, ip_address: str) -> Response:
            captured["url"] = url
            captured["ip_address"] = ip_address
            response = Response(
                200,
                headers={"content-type": "text/plain"},
                text="resolved IP was used for this request",
            )
            response.request = Request("GET", url)
            return response

        with (
            patch(
                "services.audio_research_service.AudioResearchService._request_public_url_once",
                staticmethod(capture_request),
            ),
            patch("services.audio_research_service._resolve_public_host", resolve_to_public_ip),
        ):
            document = asyncio.run(AudioResearchService().fetch_document("https://example.com/article"))
        self.assertEqual(captured["url"], "https://example.com/article")
        self.assertEqual(captured["ip_address"], "93.184.216.34")
        self.assertEqual(document.meta["fetch_status"], "ok")

    def test_fetch_document_handles_http_failure_as_nonfatal_source(self) -> None:
        FakeAsyncClient.responses = [Response(503, text="unavailable")]
        with (
            patch(
                "services.audio_research_service.AudioResearchService._request_public_url_once",
                staticmethod(fake_request_public_url_once),
            ),
            patch("services.audio_research_service._resolve_public_host", fake_resolve_public_host),
        ):
            document = asyncio.run(AudioResearchService().fetch_document("https://example.com/down"))
        self.assertEqual(document.meta["fetch_status"], "failed")
        self.assertEqual(document.content, "")
        self.assertGreater(document.score, 0)

    def test_fetch_document_handles_socket_failure_as_nonfatal_source(self) -> None:
        FakeAsyncClient.errors = [OSError("connection refused")]
        with (
            patch(
                "services.audio_research_service.AudioResearchService._request_public_url_once",
                staticmethod(fake_request_public_url_once),
            ),
            patch("services.audio_research_service._resolve_public_host", fake_resolve_public_host),
        ):
            document = asyncio.run(AudioResearchService().fetch_document("https://example.com/down"))
        self.assertEqual(document.meta["fetch_status"], "failed")
        self.assertEqual(document.content, "")
        self.assertIn("connection refused", document.meta["error"])

    def test_fetch_document_keeps_plain_text_with_length_limit(self) -> None:
        FakeAsyncClient.responses = [
            Response(
                200,
                headers={"content-type": "text/plain"},
                text="plain text research " * 1000,
            )
        ]
        with (
            patch(
                "services.audio_research_service.AudioResearchService._request_public_url_once",
                staticmethod(fake_request_public_url_once),
            ),
            patch("services.audio_research_service._resolve_public_host", fake_resolve_public_host),
        ):
            document = asyncio.run(AudioResearchService().fetch_document("https://example.com/plain.txt"))
        self.assertIn("plain text research", document.content)
        self.assertLessEqual(len(document.content), 5000)

    def test_search_filters_duplicates_and_respects_limit(self) -> None:
        FakeAsyncClient.responses = [
            Response(
                200,
                text="""
                <a class="result__a" href="/l/?uddg=https%3A%2F%2Fexample.com%2Fa">A</a>
                <a class="result__snippet">Snippet A</a>
                <a class="result__a" href="/l/?uddg=https%3A%2F%2Fexample.com%2Fa">A duplicate</a>
                <a class="result__a" href="/l/?uddg=http%3A%2F%2F127.0.0.1%2Fprivate">Local</a>
                <a class="result__a" href="/l/?uddg=https%3A%2F%2Fexample.com%2Fb">B</a>
                """,
            )
        ]
        with (
            patch(
                "services.audio_research_service.AudioResearchService._request_public_url_once",
                staticmethod(fake_request_public_url_once),
            ),
            patch("services.audio_research_service._resolve_public_host", fake_resolve_public_host),
        ):
            results = asyncio.run(AudioResearchService().search("topic", limit=2))
        self.assertEqual([item["url"] for item in results], ["https://example.com/a", "https://example.com/b"])

    def test_search_handles_socket_failure_as_empty_results(self) -> None:
        FakeAsyncClient.errors = [OSError("network unavailable"), OSError("network unavailable")]
        with (
            patch(
                "services.audio_research_service.AudioResearchService._request_public_url_once",
                staticmethod(fake_request_public_url_once),
            ),
            patch("services.audio_research_service._resolve_public_host", fake_resolve_public_host),
        ):
            results = asyncio.run(AudioResearchService().search("topic", limit=2))
        self.assertEqual(results, [])

    def test_search_fallback_to_bing_on_duckduckgo_failure(self) -> None:
        FakeAsyncClient.errors = [OSError("network unavailable")]
        FakeAsyncClient.responses = [
            Response(
                200,
                text="""
                <li class="b_algo">
                  <h2><a href="https://example.com/bing-a">Bing Title A</a></h2>
                  <div class="b_caption">
                    <p>Snippet Bing A</p>
                  </div>
                </li>
                <li class="b_algo">
                  <h2><a href="https://example.com/bing-b">Bing Title B</a></h2>
                  <p>Snippet Bing B</p>
                </li>
                """,
            )
        ]
        with (
            patch(
                "services.audio_research_service.AudioResearchService._request_public_url_once",
                staticmethod(fake_request_public_url_once),
            ),
            patch("services.audio_research_service._resolve_public_host", fake_resolve_public_host),
        ):
            results = asyncio.run(AudioResearchService().search("topic", limit=2))
        self.assertEqual([item["url"] for item in results], ["https://example.com/bing-a", "https://example.com/bing-b"])
        self.assertEqual([item["title"] for item in results], ["Bing Title A", "Bing Title B"])
        self.assertEqual([item["snippet"] for item in results], ["Snippet Bing A", "Snippet Bing B"])


class AudioRetrievalServiceTests(unittest.TestCase):
    def test_collect_sources_fetches_manual_urls_and_auto_searches_when_sparse(self) -> None:
        fake = FakeResearchService()
        service = AudioRetrievalService(research_service=fake)  # type: ignore[arg-type]
        sources = asyncio.run(
            service.collect_sources(
                topic="AI podcast research",
                use_memory=False,
                source_urls=["https://example.com/manual"],
                source_text=None,
            )
        )
        self.assertEqual(fake.fetch_calls[0], "https://example.com/manual")
        self.assertEqual(fake.search_calls, ["AI podcast research"])
        self.assertEqual([item["source_type"] for item in sources], ["manual_url", "web_search"])
        self.assertLessEqual(len(sources[0]["content"]), 5000)

    def test_collect_sources_uses_manual_text_without_auto_search(self) -> None:
        fake = FakeResearchService()
        service = AudioRetrievalService(research_service=fake)  # type: ignore[arg-type]
        sources = asyncio.run(
            service.collect_sources(
                topic="AI podcast research",
                use_memory=False,
                source_urls=[],
                source_text="Manual context " * 500,
            )
        )
        self.assertEqual(fake.search_calls, [])
        self.assertEqual(sources[0]["source_type"], "manual_text")
        self.assertLessEqual(len(sources[0]["content"]), 4000)

    def test_collect_sources_dedupes_and_caps_research_sources(self) -> None:
        fake = FakeResearchService()
        service = AudioRetrievalService(research_service=fake)  # type: ignore[arg-type]
        urls = [f"https://example.com/{idx}" for idx in range(12)]
        sources = asyncio.run(
            service.collect_sources(
                topic="AI podcast research",
                use_memory=False,
                source_urls=urls,
                source_text=None,
            )
        )
        self.assertLessEqual(len(sources), 8)
        self.assertEqual(len({item["uri"] for item in sources}), len(sources))

    def test_collect_sources_keeps_memory_before_auto_search(self) -> None:
        fake = FakeResearchService()
        service = AudioRetrievalService(research_service=fake, max_sources=2)  # type: ignore[arg-type]
        with patch(
            "services.audio_retrieval_service.EverMemConfig.get_service",
            return_value=FakeMemoryService(),
        ):
            sources = asyncio.run(
                service.collect_sources(
                    topic="AI podcast research",
                    use_memory=True,
                    source_urls=[],
                    source_text=None,
                )
            )
        self.assertEqual([item["source_type"] for item in sources], ["evermem", "evermem"])
        self.assertEqual(fake.search_calls, [])


class AudioScriptWriterResearchBriefTests(unittest.TestCase):
    def test_research_brief_and_evidence_summary_include_citations(self) -> None:
        sources = [
            {
                "source_type": "web_search",
                "title": "Source A",
                "uri": "https://example.com/a",
                "snippet": "Important detail",
                "content": "",
                "score": 0.9,
                "meta": {},
            }
        ]
        brief = AudioScriptWriter._build_research_brief(sources)
        evidence = AudioScriptWriter._build_evidence_summary(sources)
        self.assertIn("Source mix: web_search=1", brief)
        self.assertIn("https://example.com/a", brief)
        self.assertIn("[https://example.com/a]", evidence)


if __name__ == "__main__":
    unittest.main()
