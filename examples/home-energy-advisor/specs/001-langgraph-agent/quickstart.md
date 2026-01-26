# Quickstart: Home Energy Advisor

Get the Home Energy Advisor agent running in 10 minutes.

## Prerequisites

- Python 3.10+
- [Ollama](https://ollama.ai/) installed and running
- 8GB+ RAM (for llama3.1:8b model)

## 1. Install Ollama Models

```bash
# Install the LLM model
ollama pull llama3.1:8b

# Install the embedding model
ollama pull nomic-embed-text
```

Verify Ollama is running:
```bash
curl http://localhost:11434/api/tags
```

## 2. Clone and Install

```bash
# Clone the repository
git clone https://github.com/reelfy/context-forge
cd context-forge/examples/home-energy-advisor

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## 3. Configure API Keys (Optional)

For real weather and solar data, create a `.env` file:

```bash
cp .env.example .env
```

Edit `.env` with your API keys:
```env
# Free tier APIs
OPENWEATHERMAP_API_KEY=your_key_here  # Get at: https://openweathermap.org/api
NREL_API_KEY=your_key_here            # Get at: https://developer.nrel.gov/signup/

# Optional: Use mock data instead (no API keys needed)
USE_MOCK_TOOLS=false
```

**No API keys?** Set `USE_MOCK_TOOLS=true` to use realistic mock data.

## 4. Initialize Knowledge Base

Run the ingestion pipeline to load energy documents into Milvus:

```bash
python scripts/ingest_knowledge_base.py
```

Expected output:
```
Loading documents from knowledge_base/...
Found 5 documents
Generating embeddings with nomic-embed-text...
Inserting into Milvus Lite (data/milvus.db)...
Done! 127 chunks indexed.
```

## 5. Run the Agent

### Interactive Mode

```bash
python main.py
```

```
Home Energy Advisor v1.0.0
Using Ollama (llama3.1:8b) | Profile: home_123

You: When should I charge my EV?

Advisor: Based on your PG&E EV-TOU-5 rate schedule, I recommend charging overnight
between 9 PM and 6 AM when rates are lowest ($0.18/kWh vs $0.45/kWh during peak).

With your 6kW solar system and tomorrow's forecast showing 6.5 solar hours,
you could also charge midday to maximize self-consumption.

Shall I factor in your work schedule for more specific timing?

You: I work from home now, actually

Advisor: Good to know! I've updated your profile. Since you work from home,
your car is available to charge during peak solar hours (10 AM - 2 PM).

Updated recommendation:
- Primary: Charge 10 AM - 2 PM (free solar power)
- Backup: Charge 9 PM - 6 AM (off-peak rates if solar insufficient)

This could save you $15-20/month compared to evening charging!
```

### Single Query Mode

```bash
python main.py --query "When should I charge my EV?"
```

### With Instrumentation (for evaluation)

```bash
python main.py --trace --output ./traces/
```

This saves a trace file: `./traces/trace-{run_id}.json`

## 6. Evaluate Traces

Run ContextForge graders on a trace:

```bash
python evaluate.py traces/ev-charging-stale-memory.json
```

Expected output:
```
TRAJECTORY EVALUATION: FAIL

BudgetGrader: PASS
  tokens_used: 3003 / 5000 (60%)
  tool_calls: 2 / 10 (20%)

LoopGrader: PASS
  no repeated steps detected

MemoryHygieneGrader: FAIL
  Evidence:
    - step_id: step-2 (memory_read)
    - field: household.work_schedule
    - last_updated: 2025-06-15 (220 days ago)
    - threshold: 90 days
    - recommendation: Memory refresh required

RetrievalRelevanceGrader: WARN
  Evidence:
    - documents_retrieved: 5
    - documents_used: 1
    - usage_ratio: 0.2 (threshold: 0.5)
```

## 7. Explore Sample Traces

Pre-recorded traces demonstrating different scenarios:

```bash
# Good trajectory (all graders pass)
python evaluate.py traces/ev-charging-good.json

# Stale memory (MemoryHygieneGrader fails)
python evaluate.py traces/ev-charging-stale-memory.json

# Tool loop (LoopGrader fails)
python evaluate.py traces/ev-charging-loop.json

# Retrieval waste (RetrievalRelevanceGrader warns)
python evaluate.py traces/ev-charging-retrieval-waste.json
```

---

## Configuration Options

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `LLM_MODEL` | `llama3.1:8b` | Ollama model for chat |
| `EMBEDDING_MODEL` | `nomic-embed-text` | Ollama model for embeddings |
| `USE_MOCK_TOOLS` | `false` | Use mock data instead of real APIs |
| `OPENWEATHERMAP_API_KEY` | - | OpenWeatherMap API key |
| `NREL_API_KEY` | - | NREL API key |
| `DATA_DIR` | `./data` | Directory for profiles and Milvus DB |

### Custom Model

To use a different Ollama model:

```bash
# Pull the model
ollama pull mistral:7b

# Run with custom model
LLM_MODEL=mistral:7b python main.py
```

---

## Troubleshooting

### "Connection refused" to Ollama

```bash
# Check if Ollama is running
ollama list

# Start Ollama if needed
ollama serve
```

### "Model not found"

```bash
# Pull the required models
ollama pull llama3.1:8b
ollama pull nomic-embed-text
```

### "API rate limit exceeded"

Set `USE_MOCK_TOOLS=true` in your `.env` file to use mock data.

### "Out of memory"

The llama3.1:8b model requires ~8GB RAM. Try a smaller model:

```bash
ollama pull llama3.2:3b
LLM_MODEL=llama3.2:3b python main.py
```

---

## Next Steps

1. **Modify the demo profile**: Edit `data/profiles/home_123.json` to test different scenarios
2. **Add your own documents**: Put markdown files in `knowledge_base/` and re-run ingestion
3. **Create custom graders**: See ContextForge docs for domain-specific evaluation
4. **Read the article series**: [Forging Better Agents](#) on Towards AI