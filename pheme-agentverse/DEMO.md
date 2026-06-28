# PHEME × OmegaClaw — BGI Demo

**Quanturama · Agents & Goals Initiative (BGI)**
Live integration: **OmegaClaw calls the PHEME crypto-intelligence agent over the Fetch.ai Agentverse network.**

---

## What this is

**PHEME** is a standalone crypto **market-intelligence system** — it ingests news, classifies
market regime with an LLM, overlays Polymarket prediction-market probability and traditional-market
correlations, and emits a structured signal. We wrapped PHEME's MCP server (10 tools) as a
**uAgent on Agentverse**, so any agent on the network — including **OmegaClaw** — can request a
live market brief.

This turns PHEME into a reusable, discoverable BGI agent: one agent's intelligence becomes another
agent's tool.

---

## Architecture

```
 ┌────────────┐   "(pheme-query \"crypto market brief\")"
 │  OmegaClaw │  ── MeTTa skill ──►  src/agentverse.py : pheme_query()
 └────────────┘
        │  CallTool(tool="pheme_market_brief")
        ▼
 ┌────────────────────┐   send_sync_message    ┌──────────────────────┐
 │  Agentverse mailbox │ ─────────────────────► │  PHEME uAgent        │
 │  (Fetch.ai network) │                        │  agent1q0nwgquytz... │
 └────────────────────┘                         └──────────┬───────────┘
                                                            │ FastMCP
                                                            ▼
                                              pheme_market_brief tool
                                                            │
                                  live regime · prices · sentiment · signals
```

- **OmegaClaw side:** [`src/agentverse.py`](../src/agentverse.py) (`pheme_query`) + [`src/skills.metta`](../src/skills.metta) (`(pheme-query $arg)`)
- **PHEME agent side:** [`pheme-agentverse/agent.py`](./agent.py) — `MCPServerAdapter` wrapping PHEME's FastMCP

---

## Live agent

| | |
|---|---|
| **Address** | `agent1q0nwgquytzxrrhsplpq4zt5f25avuk385027vdzvjsyupprgmcrrg6vj8q6` |
| **Network** | Fetch.ai testnet |
| **Protocols** | `MCPProtocol`, `AgentChatProtocol` |
| **Live test (Agentverse)** | https://agentverse.ai/agents/details/agent1q0nwgquytzxrrhsplpq4zt5f25avuk385027vdzvjsyupprgmcrrg6vj8q6/testing |

---

## Demo 1 — PHEME agent on Agentverse

Calling `pheme_market_brief` on the live agent via the Agentverse testing console returns:

```
pheme-market-intelligence

Here is the latest crypto market brief from PHEME (June 28, 2026):

Market Overview:
  BTC: $60,131 (▼0.4% 24h | ▼6.0% 7d)
  ETH: ▼9.0% 7d
  SOL: ▼2.5% 7d
  Total Market Cap: $2.07T
  24h Volume: $42B
  BTC Dominance: 58.2%

Regime & Sentiment:
  Event Regime:   BAN (low intensity, 0.27) | Polymarket: 55%
  Market Regime:  NEUTRAL
  Sentiment:      Extreme Fear (18/100)
  Funding Rates:  Neutral
  Traditional Markets: All neutral
  Verdict:        Bearish Confluence (3/8 layers bearish)

Signals:
  BTC: Neutral (Medium confidence)
  ETH: Neutral (Low confidence)

Data provided by PHEME / Quanturama, updated every 15 minutes.
```

> The agent receives the `CallTool` envelope over Agentverse, routes it to PHEME's FastMCP,
> and returns the live signal — confirming the uAgent bridge end-to-end.

---

## Demo 2 — OmegaClaw → PHEME (Telegram)

OmegaClaw (running in Docker, Telegram channel) discovers the `pheme-query` skill and calls
the PHEME agent over Agentverse:

```
User  ▸ auth quanturama2026
Bot   ▸ Authentication successful for @Quanturama.

User  ▸ (pheme-query "crypto market brief")
Bot   ▸ PHEME Crypto Market Brief — Jun 28, 2026
        BTC $60,131 (▼6.0% 7d) | ETH ▼9.0% 7d | SOL ▼2.5% 7d
        Market cap $2.07T | BTC dominance 58.2%
        Event Regime: BAN (0.27) | Market Regime: NEUTRAL
        Sentiment: Extreme Fear (18/100)
        Verdict: BEARISH CONFLUENCE (3/8 layers bearish)
        — Signal by PHEME / Quanturama
```

The OmegaClaw MeTTa skill `(pheme-query $arg)` → `pheme_query()` →
`send_sync_message` to the PHEME agent → live brief returned to the user.

---

## Raw tool output (verbatim, captured live)

`pheme_market_brief` returns exactly:

```
PHEME MARKET BRIEF — Jun 28, 2026

BTC $60,131 ▼0.4% 24h ▼6.0% 7d | ETH ▼9.0% 7d | SOL ▼2.5% 7d
Market cap $2.07T | Vol $42B | BTC dom 58.2%

EVENT REGIME: BAN — low intensity (0.27) | Polymarket: 55%
MARKET REGIME: NEUTRAL
SENTIMENT: Extreme Fear (18/100) | Funding: neutral
TRADITIONAL MARKETS: all neutral
VERDICT: BEARISH CONFLUENCE (3/8 layers bearish)

SIGNALS (3):
• [BTC] Neutral · Medium
• [ETH] Neutral · Low
• [ETH] Neutral · Low

Signal by PHEME / Quanturama — updated every 15 min.
```

---

## PHEME tools exposed via the agent

| Tool | Returns |
|------|---------|
| `pheme_market_brief` | Full brief — prices, regime, sentiment, top signals |
| `pheme_regime` | Regime, intensity, direction, Polymarket confidence |
| `pheme_macro_analysis` | Cross-layer synthesis + verdict |
| `pheme_macro_context` | Traditional-market trends + BTC correlations |
| `pheme_crypto_positioning` | Market cap, dominance, stablecoin velocity |
| `pheme_top_influencers` | Social-signal influencer ranking |

---

## Run it

```bash
# PHEME agent (this folder)
docker build -t pheme-agentverse .
docker run -d --name pheme-agentverse \
  -v /path/to/shared:/shared:ro \
  -e SHARED_SIGNALS_PATH=/shared \
  -e AGENTVERSE_API_KEY=... \
  -e ASI1_API_KEY=... \
  -e PHEME_AGENT_SEED=... \
  pheme-agentverse

# OmegaClaw with the PHEME skill (repo root)
./scripts/omegaclaw start -t telegram -p Anthropic -d omegaclaw-pheme -s <secret>
```

---

## Tech stack

- **Fetch.ai uAgents** + `uagents-adapter` (`MCPServerAdapter`)
- **MCP** (FastMCP, streamable-HTTP) — 10 PHEME tools
- **OmegaClaw** (SingularityNET) — MeTTa agentic harness
- **Agentverse** — agent registration, discovery, mailbox routing
- **PHEME / Quanturama** — crypto news-intelligence pipeline (LLM regime classification + Polymarket + traditional-market overlay)
