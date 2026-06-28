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
# Two-path design:
#   Primary:  uAgent bridge via Agentverse (BGI demo path — correct architecture)
#   Fallback: Direct HTTPS to mcp.quanturama.com (if relay times out)

import urllib.request
import threading

PHEME_AGENT_ADDRESS = os.environ.get(
    "PHEME_AGENT_ADDRESS",
    "agent1q0nwgquytzxrrhsplpq4zt5f25avuk385027vdzvjsyupprgmcrrg6vj8q6",
)
PHEME_MCP_URL = os.environ.get(
    "PHEME_MCP_URL",
    "https://mcp.quanturama.com/mcp",
)


class PhemeBlockedError(Exception):
    pass


def _call_pheme_direct(skill_name: str, parameters: dict, timeout: int = 15) -> str:
    """Fallback: call PHEME MCP tool directly via HTTPS JSON-RPC."""
    payload = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": skill_name, "arguments": parameters},
    }).encode()
    req = urllib.request.Request(
        PHEME_MCP_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        result = json.loads(resp.read().decode())
    content = result.get("result", {}).get("content", [])
    text = " ".join(c.get("text", "") for c in content if c.get("type") == "text").strip()
    if not text:
        text = json.dumps(result)
    if "blocked" in text.lower():
        try:
            parsed = json.loads(text)
            if parsed.get("status") == "blocked":
                raise PhemeBlockedError(parsed.get("reason", "signal blocked"))
        except (json.JSONDecodeError, AttributeError):
            pass
    return text


def _call_pheme_agent(skill_name: str, parameters: dict, timeout: int = 45) -> str:
    """Primary: call PHEME via uAgent bridge (BGI Agentverse path).
    Runs asyncio.run() in a dedicated thread to avoid event-loop conflicts
    with OmegaClaw's MeTTa py-call runtime.
    """
    from uagents_adapter.mcp import CallTool, CallToolResponse

    result_holder = [None]
    error_holder = [None]

    def _run():
        try:
            request = CallTool(tool=skill_name, args=parameters)
            raw = asyncio.run(_ask_agent(PHEME_AGENT_ADDRESS, request, timeout))
            try:
                resp = CallToolResponse.model_validate_json(raw)
                result_holder[0] = resp.result or ""
            except Exception:
                result_holder[0] = str(raw)
        except Exception as e:
            error_holder[0] = e

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    t.join(timeout + 5)

    if error_holder[0]:
        raise error_holder[0]
    if result_holder[0] is None:
        raise TimeoutError("uAgent bridge timed out")

    text = result_holder[0]
    if "blocked" in text.lower():
        try:
            parsed = json.loads(text)
            if parsed.get("status") == "blocked":
                raise PhemeBlockedError(parsed.get("reason", "signal blocked"))
        except (json.JSONDecodeError, AttributeError):
            pass
    return text


def pheme_query(arg: str, format: str = "telegram") -> str:
    """Get a full PHEME crypto market brief.
    Tries uAgent bridge first (BGI demo path), falls back to direct HTTPS.
    """
    # Primary: uAgent → Agentverse → PHEME agent
    try:
        return _call_pheme_agent("pheme_market_brief", {"format": "text"})
    except PhemeBlockedError:
        pass
    except Exception:
        pass

    # Fallback: direct HTTPS to mcp.quanturama.com
    try:
        return _call_pheme_direct("pheme_market_brief", {"format": "text"})
    except PhemeBlockedError:
        pass
    except Exception:
        pass

    try:
        return _call_pheme_direct("pheme_macro_analysis", {"format": "text"})
    except Exception as e:
        return f"PHEME unavailable: {e}"
