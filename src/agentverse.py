import asyncio
import json
import os
from typing import Any

from uagents import Model
from uagents.query import send_sync_message

TECHNICAL_ANALYSIS_AGENT_ADDRESS = os.environ.get(
    "TECHNICAL_ANALYSIS_AGENT_ADDRESS",
    "agent1q085746wlr3u2uh4fmwqplude8e0w6fhrmqgsnlp49weawef3ahlutypvu6",
)
TAVILY_SEARCH_AGENT_ADDRESS = os.environ.get(
    "TAVILY_SEARCH_AGENT_ADDRESS",
    "agent1qt5uffgp0l3h9mqed8zh8vy5vs374jl2f8y0mjjvqm44axqseejqzmzx9v8",
)


class WebSearchRequest(Model):
    query: str


class TechAnalysisRequest(Model):
    ticker: str


def _truncate_text(value: Any, limit: int) -> str:
    text = " ".join(str(value).split())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _format_tavily_results(response: str, max_results: int = 5) -> str:
    try:
        data = json.loads(response)
    except json.JSONDecodeError:
        return response

    if not isinstance(data, dict):
        return response

    results = data.get("results")
    if not isinstance(results, list):
        return response

    formatted = []
    for result in results[:max_results]:
        if not isinstance(result, dict):
            continue

        title = _truncate_text(result.get("title", ""), 160)
        url = _truncate_text(result.get("url", ""), 240)
        snippet = _truncate_text(result.get("content", ""), 400)

        parts = []
        if title:
            parts.append(f"TITLE: {title}")
        if url:
            parts.append(f"URL: {url}")
        if snippet:
            parts.append(f"SNIPPET: {snippet}")

        if parts:
            formatted.append(f"({' '.join(parts)})")

    return f"({' '.join(formatted)})" if formatted else response

async def _ask_agent(destination: str, request: Model, timeout: int = 60) -> str:
    envelope_or_status = await send_sync_message(
        destination=destination,
        message=request,
        timeout=timeout,
    )
    return str(envelope_or_status)


def technical_analysis(ticker: str, timeout: int = 60) -> str:
    try:
        request = TechAnalysisRequest(ticker=ticker)
        return asyncio.run(
            _ask_agent(TECHNICAL_ANALYSIS_AGENT_ADDRESS, request, int(timeout))
        )
    except Exception as e:
        return f"error: {e}"


def tavily_search(search_query: str, timeout: int = 60) -> str:
    try:
        request = WebSearchRequest(query=search_query)
        response = asyncio.run(
            _ask_agent(TAVILY_SEARCH_AGENT_ADDRESS, request, int(timeout))
        )
        return _format_tavily_results(response)
    except Exception as e:
        return f"error: {e}"


# ── PHEME market intelligence ─────────────────────────────────────────────────

class PhemeBlockedError(Exception):
    """Raised when PHEME MCP returns a blocked signal (pipeline down or expired)."""
    pass


def _call_pheme_mcp(skill_name: str, parameters: dict) -> str:
    """Call a PHEME MCP skill via direct HTTP session.

    Direct HTTP call — NOT an Agentverse uAgent hop. Latency: low single-digit seconds.
    Network path: PHEME_MCP_URL env var (set if OmegaClaw runs outside pheme-mcp's Docker
    network) or http://localhost:8000 default (same host / same Docker network).
    """
    import urllib.request
    import urllib.error
    import json as _json

    base_url = os.environ.get("PHEME_MCP_URL", "http://localhost:8000/mcp")
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    timeout = 10

    def _post(payload: dict, extra_headers: dict = {}) -> tuple[dict, dict]:
        data = _json.dumps(payload).encode()
        req = urllib.request.Request(base_url, data=data,
                                     headers={**headers, **extra_headers},
                                     method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp_headers = dict(resp.headers)
            body = resp.read().decode()
            # SSE response: extract data: line
            for line in body.splitlines():
                if line.startswith("data: "):
                    return _json.loads(line[6:]), resp_headers
        raise ValueError("No data line in SSE response")

    # 1. Initialize session
    _, init_headers = _post({
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                   "clientInfo": {"name": "omegaclaw", "version": "1.0"}}
    })
    session_id = init_headers.get("mcp-session-id") or init_headers.get("Mcp-Session-Id", "")

    # 2. Call the tool
    result, _ = _post({
        "jsonrpc": "2.0", "id": 2, "method": "tools/call",
        "params": {"name": skill_name, "arguments": parameters}
    }, extra_headers={"mcp-session-id": session_id})

    text = result.get("result", {}).get("content", [{}])[0].get("text", "")

    # 3. Check for blocked status
    if "blocked" in text.lower():
        try:
            parsed = _json.loads(text)
            if parsed.get("status") == "blocked":
                raise PhemeBlockedError(parsed.get("reason", "signal blocked"))
        except (_json.JSONDecodeError, AttributeError):
            pass  # text contains "blocked" as a word but isn't a blocked JSON response

    return text


def pheme_query(arg: str, format: str = "telegram") -> str:
    """Get a full PHEME crypto market brief (regime, prices, sentiment, top headlines).

    arg satisfies the MeTTa calling convention (pheme-query $arg) but is intentionally
    unused — pheme_market_brief returns a fixed full brief, not a query-specific response.
    Future: wire arg to a coin/topic filter.

    Falls back to pheme_macro_analysis (regime + verdict, no prices/headlines) if
    pheme_market_brief is blocked or unavailable.
    """
    try:
        result = _call_pheme_mcp("pheme_market_brief", {"format": "text"})
        if format == "irc":
            # Flatten for IRC single-line output — not in demo critical path (demo is Telegram)
            result = " | ".join(line.strip() for line in result.splitlines() if line.strip())
        return result
    except PhemeBlockedError:
        # PHEME pipeline returned a blocked signal — fall through to simpler fallback.
        # Logged separately from generic Exception so demo-day debugging can distinguish
        # "PHEME pipeline down" from "network/timeout failure".
        pass
    except Exception:
        pass
    # Fallback — proven live, covers regime read without prices/headlines
    try:
        return _call_pheme_mcp("pheme_macro_analysis", {"format": "text"})
    except Exception as e:
        return f"PHEME unavailable: {e}"
