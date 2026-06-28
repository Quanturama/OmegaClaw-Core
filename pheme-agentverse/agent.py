"""PHEME Agentverse bridge — wraps PHEME FastMCP as a uAgent on Agentverse.

Run:
    cd /Users/s0101/Documents/Pheme
    source .env
    python3.11 pheme-agentverse/agent.py

Requires env vars:
    AGENTVERSE_API_KEY  — Agentverse account key (free, from agentverse.ai)
    ASI1_API_KEY        — ASI:One LLM key (Fetch.ai)
    PHEME_AGENT_SEED    — fixed hex seed, determines permanent agent1q... address

Once running, prints:
    Agent address: agent1q...
    Agent wallet:  fetch1...
All PHEME skills are discoverable and callable via Agentverse manifest.
"""
import os
import sys

# Load .env from the Pheme repo root (parent of this directory)
_env_file = os.path.join(os.path.dirname(__file__), "..", ".env")
if os.path.exists(_env_file):
    with open(_env_file) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _, _v = _line.partition("=")
                os.environ.setdefault(_k.strip(), _v.strip())

# Import quanturama-mcp/main.py by absolute path to avoid shadowing by Pheme's own main.py.
# sys.path.insert alone is insufficient when CWD contains a different main.py.
_MCP_PATH = os.path.abspath(
    os.environ.get(
        "PHEME_MCP_PATH",
        os.path.join(os.path.dirname(__file__), "..", "..", "quanturama-mcp"),
    )
)
import importlib.util as _ilu
_spec = _ilu.spec_from_file_location("quanturama_mcp", os.path.join(_MCP_PATH, "main.py"))
_mod  = _ilu.module_from_spec(_spec)
sys.modules["quanturama_mcp"] = _mod
sys.path.insert(0, _MCP_PATH)  # needed for relative imports inside main.py
_spec.loader.exec_module(_mod)
mcp = _mod.mcp  # FastMCP instance — all PHEME tools already registered

from uagents import Agent
from uagents_adapter import MCPServerAdapter

ASI1_API_KEY   = os.environ["ASI1_API_KEY"]
AGENTVERSE_KEY = os.environ["AGENTVERSE_API_KEY"]
AGENT_SEED     = os.environ["PHEME_AGENT_SEED"]

mcp_adapter = MCPServerAdapter(
    mcp_server=mcp,
    asi1_api_key=ASI1_API_KEY,
    model="asi1-mini",  # fastest model — market brief needs no LLM reasoning
)

agent = Agent(
    name="pheme-market-intelligence",
    seed=AGENT_SEED,
    port=8001,  # 8000 is reserved for pheme-mcp Docker container
    network="testnet",
    agentverse={
        "api_key": AGENTVERSE_KEY,
        "url": "https://agentverse.ai",
    },
    mailbox=True,
)

for protocol in mcp_adapter.protocols:
    agent.include(protocol, publish_manifest=True)

if __name__ == "__main__":
    print(f"Agent address: {agent.address}")
    print(f"Agent wallet:  {agent.wallet.address()}")
    agent.run()
