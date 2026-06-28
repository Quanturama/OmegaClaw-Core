# PHEME Agentverse Bridge

The **PHEME market-intelligence uAgent** — wraps PHEME's FastMCP server as a uAgent
registered on Agentverse, so any agent (including OmegaClaw) can call PHEME's crypto
market intelligence over the Fetch.ai network.

## Live agent

- **Address:** `agent1q0nwgquytzxrrhsplpq4zt5f25avuk385027vdzvjsyupprgmcrrg6vj8q6`
- **Network:** testnet
- **Inspector / live test:**
  https://agentverse.ai/agents/details/agent1q0nwgquytzxrrhsplpq4zt5f25avuk385027vdzvjsyupprgmcrrg6vj8q6/testing

## How the bridge works

```
OmegaClaw  (MeTTa skill: pheme-query)
   │  CallTool(tool="pheme_market_brief")
   ▼
uAgent send_sync_message  ──►  Agentverse mailbox  ──►  PHEME uAgent (this code)
                                                            │
                                                            ▼
                                              FastMCP → pheme_market_brief tool
                                                            │
                                              live regime / prices / sentiment / signals
```

The OmegaClaw side lives in [`src/agentverse.py`](../src/agentverse.py) (`pheme_query`)
and [`src/skills.metta`](../src/skills.metta) (`(pheme-query $arg)`).

## Run

```bash
docker build -t pheme-agentverse .
docker run -d --name pheme-agentverse \
  -v /path/to/shared:/shared:ro \
  -e SHARED_SIGNALS_PATH=/shared \
  -e AGENTVERSE_API_KEY=... \
  -e ASI1_API_KEY=... \
  -e PHEME_AGENT_SEED=... \
  pheme-agentverse
```

## PHEME tools exposed

| Tool | Returns |
|------|---------|
| `pheme_market_brief` | Full brief — prices, regime, sentiment, top signals |
| `pheme_regime` | Regime, intensity, direction, Polymarket confidence |
| `pheme_macro_analysis` | Cross-layer synthesis + verdict |
| `pheme_macro_context` | Traditional-market trends + BTC correlations |
| `pheme_crypto_positioning` | Market cap, dominance, stablecoin velocity |

PHEME is a standalone crypto news-intelligence system (news ingestion → Claude regime
classification → Polymarket overlay → traditional-market correlation) by Quanturama.
