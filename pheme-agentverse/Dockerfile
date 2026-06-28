FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir \
    "uagents>=0.25.2" \
    "uagents-adapter>=0.6.2" \
    "mcp[cli]>=1.0.0" \
    "pydantic>=2.0.0" \
    "httpx>=0.27.0" \
    "yfinance>=0.2.0" \
    "requests>=2.31.0"

# Copy quanturama-mcp (the FastMCP server with all PHEME tools)
COPY quanturama-mcp/ /app/quanturama-mcp/

# Copy the agent
COPY pheme-agentverse/agent.py /app/pheme-agentverse/agent.py

# Shared signals will be mounted at /shared
ENV SHARED_SIGNALS_PATH=/shared
ENV PHEME_MCP_PATH=/app/quanturama-mcp

WORKDIR /app
CMD ["python3", "pheme-agentverse/agent.py"]
