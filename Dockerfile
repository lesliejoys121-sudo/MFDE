FROM python:3.12-slim

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# HuggingFace Spaces requires UID 1000
RUN useradd -m -u 1000 appuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chown -R appuser:appuser /app

USER appuser

# Env vars (override at runtime or in HF Space secrets)
ENV ANTHROPIC_API_KEY=""
ENV GMAIL_MCP_URL="https://gmail.mcp.claude.com/mcp"
ENV API_BASE_URL="http://localhost:7860"

# Hugging Face requires port 7860
EXPOSE 7860

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
