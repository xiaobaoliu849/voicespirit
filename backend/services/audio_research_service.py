from __future__ import annotations

import asyncio
import html
import ipaddress
import re
import socket
import ssl
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any
from urllib.parse import parse_qs, quote_plus, unquote, urljoin, urlparse

import httpx


USER_AGENT = (
    "VoiceSpiritResearchAgent/1.0 "
    "(local podcast research; contact: voicespirit.local)"
)
MAX_SOURCE_CONTENT_CHARS = 5000
MAX_SEARCH_RESULTS = 5
REQUEST_TIMEOUT_SECONDS = 10.0
MAX_REDIRECTS = 5
MAX_RESPONSE_BYTES = 600_000
_IPV4_NUMBER_LABEL_PATTERN = re.compile(r"^(?:0x[0-9a-f]+|\d+)$", re.IGNORECASE)


@dataclass(frozen=True)
class ResearchDocument:
    title: str
    url: str
    snippet: str
    content: str
    score: float
    source_type: str
    meta: dict[str, Any]

    def to_source(self) -> dict[str, Any]:
        return {
            "source_type": self.source_type,
            "title": self.title,
            "uri": self.url,
            "snippet": self.snippet,
            "content": self.content,
            "score": self.score,
            "meta": self.meta,
        }


class HtmlContentExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self._in_title = False
        self._skip_depth = 0
        self._chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag_name = tag.lower()
        if tag_name == "title":
            self._in_title = True
            return
        if tag_name in {"script", "style", "noscript", "svg", "canvas", "form", "nav", "footer", "header"}:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        tag_name = tag.lower()
        if tag_name == "title":
            self._in_title = False
            return
        if tag_name in {"script", "style", "noscript", "svg", "canvas", "form", "nav", "footer", "header"}:
            self._skip_depth = max(0, self._skip_depth - 1)

    def handle_data(self, data: str) -> None:
        text = _normalize_whitespace(data)
        if not text:
            return
        if self._in_title:
            self.title = _normalize_whitespace(f"{self.title} {text}")[:240]
            return
        if self._skip_depth:
            return
        if len(text) >= 24:
            self._chunks.append(text)

    @property
    def text(self) -> str:
        return _normalize_whitespace("\n".join(self._chunks))


class DuckDuckGoResultParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.results: list[dict[str, str]] = []
        self._capture_link = False
        self._capture_snippet = False
        self._current_href = ""
        self._current_title_parts: list[str] = []
        self._current_snippet_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {name: value or "" for name, value in attrs}
        class_name = attrs_dict.get("class", "")
        if tag.lower() == "a" and "result__a" in class_name:
            self._capture_link = True
            self._current_href = attrs_dict.get("href", "")
            self._current_title_parts = []
            return
        if "result__snippet" in class_name:
            self._capture_snippet = True
            self._current_snippet_parts = []

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._capture_link:
            title = _normalize_whitespace(" ".join(self._current_title_parts))
            resolved_url = _normalize_duckduckgo_url(self._current_href)
            if title and resolved_url:
                self.results.append({"title": title[:240], "url": resolved_url, "snippet": ""})
            self._capture_link = False
            self._current_href = ""
            self._current_title_parts = []
            return
        if self._capture_snippet and tag.lower() in {"a", "div"}:
            snippet = _normalize_whitespace(" ".join(self._current_snippet_parts))[:500]
            if snippet and self.results:
                self.results[-1]["snippet"] = snippet
            self._capture_snippet = False
            self._current_snippet_parts = []

    def handle_data(self, data: str) -> None:
        if self._capture_link:
            self._current_title_parts.append(data)
        elif self._capture_snippet:
            self._current_snippet_parts.append(data)


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(str(value or ""))).strip()


def _normalize_duckduckgo_url(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    parsed = urlparse(raw)
    if parsed.path.startswith("/l/"):
        params = parse_qs(parsed.query)
        uddg = params.get("uddg", [""])[0]
        return unquote(uddg)
    if parsed.scheme in {"http", "https"}:
        return raw
    return urljoin("https://duckduckgo.com", raw)


def _looks_like_nonstandard_ipv4(hostname: str) -> bool:
    labels = hostname.split(".")
    return 1 <= len(labels) <= 4 and all(
        bool(_IPV4_NUMBER_LABEL_PATTERN.fullmatch(label)) for label in labels
    )


def _is_safe_public_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
    except Exception:
        return False
    if parsed.scheme not in {"http", "https"}:
        return False
    hostname = (parsed.hostname or "").strip().lower().rstrip(".")
    if not hostname or hostname in {"localhost", "127.0.0.1", "::1"}:
        return False
    if hostname.endswith(".local") or hostname.endswith(".localhost"):
        return False
    try:
        ip = ipaddress.ip_address(hostname)
    except ValueError:
        return not _looks_like_nonstandard_ipv4(hostname)
    if str(ip) != hostname.strip("[]"):
        return False
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


async def _resolve_public_host(hostname: str, port: int | None) -> list[str]:
    normalized = hostname.strip().lower().rstrip(".")
    try:
        addresses = await asyncio.to_thread(
            socket.getaddrinfo,
            normalized,
            port,
            type=socket.SOCK_STREAM,
        )
    except socket.gaierror as exc:
        raise ValueError(f"Could not resolve host: {normalized}") from exc

    resolved: list[str] = []
    for family, _socktype, _proto, _canonname, sockaddr in addresses:
        if family not in {socket.AF_INET, socket.AF_INET6}:
            continue
        ip_text = str(sockaddr[0])
        try:
            ip = ipaddress.ip_address(ip_text)
        except ValueError as exc:
            raise ValueError(f"Resolved host to invalid address: {ip_text}") from exc
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            raise ValueError(f"Resolved host to non-public address: {ip_text}")
        resolved.append(ip_text)
    if not resolved:
        raise ValueError(f"Host did not resolve to a public address: {normalized}")
    return resolved


class AudioResearchService:
    async def _validate_public_target(self, url: str) -> list[str]:
        if not _is_safe_public_url(url):
            raise ValueError("URL is not a public HTTP(S) source")
        parsed = urlparse(url)
        hostname = (parsed.hostname or "").strip()
        if not hostname:
            raise ValueError("URL host is empty")
        return await _resolve_public_host(hostname, parsed.port)

    @staticmethod
    def _request_public_url_once(url: str, ip_address: str) -> httpx.Response:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("URL is not a public HTTP(S) source")

        default_port = 443 if parsed.scheme == "https" else 80
        port = parsed.port or default_port
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"
        host_header = parsed.hostname
        if parsed.port and parsed.port != default_port:
            host_header = f"{host_header}:{parsed.port}"

        raw_socket = socket.create_connection(
            (ip_address, port),
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        try:
            if parsed.scheme == "https":
                context = ssl.create_default_context()
                stream = context.wrap_socket(raw_socket, server_hostname=parsed.hostname)
            else:
                stream = raw_socket
            try:
                request = (
                    f"GET {path} HTTP/1.1\r\n"
                    f"Host: {host_header}\r\n"
                    f"User-Agent: {USER_AGENT}\r\n"
                    "Accept: text/html,text/plain;q=0.9,*/*;q=0.1\r\n"
                    "Accept-Encoding: identity\r\n"
                    "Connection: close\r\n"
                    "\r\n"
                ).encode("ascii", errors="ignore")
                stream.sendall(request)
                chunks: list[bytes] = []
                total = 0
                while total < MAX_RESPONSE_BYTES:
                    chunk = stream.recv(min(65536, MAX_RESPONSE_BYTES - total))
                    if not chunk:
                        break
                    chunks.append(chunk)
                    total += len(chunk)
            finally:
                stream.close()
        except Exception:
            raw_socket.close()
            raise

        raw_response = b"".join(chunks)
        header_bytes, separator, body = raw_response.partition(b"\r\n\r\n")
        if not separator:
            raise httpx.ProtocolError("Response did not include HTTP headers")
        header_lines = header_bytes.decode("iso-8859-1", errors="replace").split("\r\n")
        status_parts = header_lines[0].split(" ", 2)
        if len(status_parts) < 2 or not status_parts[1].isdigit():
            raise httpx.ProtocolError("Response status line is invalid")
        headers: list[tuple[bytes, bytes]] = []
        for line in header_lines[1:]:
            if ":" not in line:
                continue
            name, value = line.split(":", 1)
            headers.append((name.strip().encode("ascii", errors="ignore"), value.strip().encode("iso-8859-1", errors="ignore")))
        request_obj = httpx.Request("GET", url)
        return httpx.Response(
            int(status_parts[1]),
            headers=headers,
            content=body,
            request=request_obj,
        )

    async def _get_public_response(self, url: str) -> httpx.Response:
        current_url = url
        response: httpx.Response | None = None
        for _ in range(MAX_REDIRECTS + 1):
            resolved_addresses = await self._validate_public_target(current_url)
            try:
                response = await asyncio.to_thread(
                    self._request_public_url_once,
                    current_url,
                    resolved_addresses[0],
                )
            except (OSError, TimeoutError, ssl.SSLError) as exc:
                raise httpx.TransportError(
                    f"Network error while fetching source: {exc}",
                    request=httpx.Request("GET", current_url),
                ) from exc
            if not response.is_redirect:
                response.raise_for_status()
                return response
            location = response.headers.get("location", "")
            if not location:
                response.raise_for_status()
            current_url = urljoin(str(response.url), location)
        request = response.request if response is not None else httpx.Request("GET", url)
        raise httpx.TooManyRedirects(
            f"Exceeded {MAX_REDIRECTS} redirects while fetching source",
            request=request,
        )

    async def search(self, query: str, *, limit: int = MAX_SEARCH_RESULTS) -> list[dict[str, str]]:
        cleaned = _normalize_whitespace(query)
        if not cleaned:
            return []
        search_url = f"https://duckduckgo.com/html/?q={quote_plus(cleaned)}"
        try:
            response = await self._get_public_response(search_url)
            response.raise_for_status()
        except (httpx.HTTPError, ValueError):
            return []

        parser = DuckDuckGoResultParser()
        parser.feed(response.text[:300_000])
        results: list[dict[str, str]] = []
        seen: set[str] = set()
        for item in parser.results:
            url = item.get("url", "")
            if not _is_safe_public_url(url) or url in seen:
                continue
            seen.add(url)
            results.append(item)
            if len(results) >= max(1, min(limit, MAX_SEARCH_RESULTS)):
                break
        return results

    async def fetch_document(
        self,
        url: str,
        *,
        title_hint: str = "",
        snippet_hint: str = "",
        source_type: str = "web_page",
        score: float = 0.7,
    ) -> ResearchDocument:
        clean_url = str(url or "").strip()
        title = _normalize_whitespace(title_hint) or clean_url[:160]
        snippet = _normalize_whitespace(snippet_hint)
        if not _is_safe_public_url(clean_url):
            return ResearchDocument(
                title=title,
                url=clean_url[:1000],
                snippet=snippet or "URL was skipped because it is not a public HTTP(S) source.",
                content="",
                score=0.0,
                source_type=source_type,
                meta={"fetch_status": "skipped", "reason": "unsafe_or_unsupported_url"},
            )

        try:
            response = await self._get_public_response(clean_url)
        except (httpx.HTTPError, ValueError) as exc:
            return ResearchDocument(
                title=title,
                url=clean_url[:1000],
                snippet=snippet or f"Failed to fetch source: {exc}",
                content="",
                score=max(0.1, score - 0.4),
                source_type=source_type,
                meta={"fetch_status": "failed", "error": str(exc)[:300]},
            )

        content_type = response.headers.get("content-type", "")
        text = response.text[:500_000]
        extractor = HtmlContentExtractor()
        if "html" in content_type.lower() or "<html" in text[:1000].lower():
            extractor.feed(text)
            extracted = extractor.text[:MAX_SOURCE_CONTENT_CHARS]
            title = extractor.title or title
        else:
            extracted = _normalize_whitespace(text)[:MAX_SOURCE_CONTENT_CHARS]

        if not snippet:
            snippet = extracted[:500]
        return ResearchDocument(
            title=title,
            url=str(response.url)[:1000],
            snippet=snippet[:500],
            content=extracted,
            score=score if extracted else max(0.1, score - 0.3),
            source_type=source_type,
            meta={
                "fetch_status": "ok" if extracted else "empty",
                "content_type": content_type[:120],
                "content_length": len(extracted),
            },
        )
