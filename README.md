# Ofrenda: Offline Remembrance Keeper 🕯️🌼

> **Hacktoberfest Open-Source AI Challenge: "Ghost in the Machine" (Dia de los Muertos / Halloween)**  
> *A local, privacy-first remembrance keeper where every sentence is checked against source family stories. Nothing leaves your laptop.*

---

## 1. Overview

**Ofrenda** is an offline memory archive and remembrance keeper. You add stories, letters, recipes, or audio transcripts about a departed loved one, ask questions, and generate a gentle remembrance page.

Unlike ungrounded RAG or conversational biographers that can invent dates, relationships, or details:
- **Strict Grounding:** The narrator is "the Keeper", who speaks *about* the person in the third person.
- **Verification Engine:** Every generated sentence must quote and share key content words with a verified sentence in the source text.
- **Refusal Behavior:** If a fact is not in the stories (e.g. *"What was her phone number?"*), Ofrenda returns: *"The stories don't mention that."*
- **Offline Runtime (citations checked against the source text):** Runs locally on your laptop using open-source models (**Gemma 3 4B** and **nomic-embed-text**) via **Ollama**, local **ChromaDB**, and **FastAPI**. No external CDNs, no telemetry, no cloud APIs.

---

## 2. Why Open Models & Local AI?

1. **Absolute Family Privacy:** Personal memories, grief, and family stories are kept local on your machine and not uploaded to cloud AI providers, sold for training, or retained on remote servers.
2. **Works With the Wi-Fi Off:** In the spirit of Dia de los Muertos candlelight vigils, Ofrenda works even during power or internet outages.
3. **No Per-Query Costs:** No subscription or token bills.
4. **Model Swappability:** Switch between models (e.g., `gemma3:4b`, `llama3.2:3b`, `mistral`) simply by modifying `.env`.

---

## 3. How It Works: The 3-Tier Grounding Architecture

```
┌────────────────────────────────────────────────────────┐
│ 1. Deterministic Extraction (Rules Find)               │
│    - Regex pattern matching for foods, songs, places   │
│    - Sentence & paragraph boundary chunking            │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│ 2. Gentle Rewording (Gemma 3 4B Words It)             │
│    - Temperature 0.0, fixed seed 42, strict JSON schema│
│    - Preserves tone without inventing facts             │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│ 3. Multi-Stage Verification Pipeline                   │
│    ✓ Exact / Normalized / Fuzzy Substring Verification │
│    ✓ Content Word Overlap (Names, foods, dates, places)│
│    ✓ Strict Entity & Date Consistency Checker          │
│    ✗ Drop invalid sentences and log reasons            │
└────────────────────────────────────────────────────────┘
```

1. **Rules Find:** High-signal patterns (e.g. *"favorite"*, *"loved"*, *"used to sing"*, *"always made"*) extract candidate sentences.
2. **Model Words:** Local Gemma 3 4B formats them into a warm, respectful tribute.
3. **Pipeline Verifies:**
   - The cited quote is expanded and verified to exist verbatim or near-verbatim in source text chunks.
   - The generated sentence is tested for content overlap with the cited sentence.
   - Any proper nouns, years, or numbers in the sentence that do not appear in the source text cause the sentence to be dropped.

---

## 4. Measured Results (Real Benchmarks)

Measured directly on Windows with Ollama running locally (`gemma3:4b` and `nomic-embed-text`):

| Task / Query | Model | Latency | Verified Citations | Dropped Items / Reasons | Status | Measured Source |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Ask Known Fact** (*"What did she love to cook?"*) | Gemma 3 4B | 5.1s | 1 verified quote | 0 dropped | **Answered & Verified** | `cli.py --ask` (task-122) |
| **Ask Known Fact** (*"What song did she sing?"*) | Gemma 3 4B | 5.4s | 1 verified quote | 0 dropped | **Answered & Verified** | `cli.py --ask` (task-127) |
| **Refusal Test** (*"What was her phone number?"*) | Gemma 3 4B | 4.0s | 0 (refusal) | 0 dropped | **Refused cleanly** | `cli.py --ask` (task-132) |
| **Refusal Test** (*"When was her birthday?"*) | Gemma 3 4B | 4.6s | 0 (refusal) | 0 dropped | **Refused cleanly** | `cli.py --ask` (task-134) |
| **Refusal Test** (*"What was her favorite color?"*) | Gemma 3 4B | 4.0s | 0 (refusal) | 0 dropped | **Refused cleanly** | `cli.py --ask` (task-140) |
| **Ofrenda Altar** (Foods, Songs, Places, Sayings) | Gemma 3 4B | 17.1s | 4 verified quotes | 0 dropped | **All 4 Cards Verified** | `cli.py --ofrenda` (task-142) |
| **Remembrance Tribute** (Run 2 & 3) | Gemma 3 4B | 15.3s | 7 verified sentences | 0 dropped | **Audited & Filtered** | `cli.py --tribute` (task-110, task-115) |
| **Remembrance Tribute** (Run 1) | Gemma 3 4B | 23.5s | 5 verified sentences | 2 dropped (content overlap) | **Audited & Filtered** | `cli.py --tribute` (task-101) |

*Citations are checked against the source text. All drop counts and reasons are visible directly in the UI audit log and CLI output.*

---

## 5. Quickstart Guide

### Prerequisites
1. **Ollama** installed on your system ([ollama.ai](https://ollama.ai))
2. Pull required open models:
   ```bash
   ollama pull gemma3:4b
   ollama pull nomic-embed-text
   ```
3. Python 3.11 or 3.12

### Installation
```bash
# Clone the repository
git clone https://github.com/SidakSethi-Singh/ofrenda.git
cd ofrenda

# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\activate   # Windows
# source venv/bin/activate # Linux/macOS

# Install dependencies
pip install -r requirements.txt

# Create .env config
copy .env.example .env
```

### Running the CLI
```bash
# Initialize synthetic sample memories (Abuela Rosa)
python cli.py --init-samples

# List registered memories
python cli.py --list-memories

# Ask the Keeper a question
python cli.py --ask "What did she love to cook?"

# Test refusal on an unmentioned fact
python cli.py --ask "What was her phone number?"

# Generate a remembrance tribute with citation audit
python cli.py --tribute

# Generate Ofrenda altar cards
python cli.py --ofrenda
```

### Running the Web UI & API
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
Open your browser to: **`http://127.0.0.1:8000`**

### Running the Test Suite
```bash
pytest -v
```

---

## 6. Synthetic Sample Data

All samples in `samples/` are completely synthetic and fictional, centered on the persona **"Abuela Rosa"**:
- `01_sunday_mole.md` — Family cooking traditions, clay pot, mole negro.
- `02_oaxaca_guitar.md` — Twilight songs, guitar, *La Llorona*.
- `03_kitchen_sayings.md` — Kitchen wisdom and calm proverbs.
- `04_chapultepec_park.md` — Weekend walks in Mexico City.

*A phone number, modern vehicle, and foreign travels were deliberately excluded from all samples to verify model refusal behavior.*

---

## 7. What Didn't Work & Limitations

- **Small Model Quote Drift:** A 4B parameter model frequently tries to paraphrase quotes rather than copying verbatim. Our multi-stage sentence expansion and token normalizer were required to anchor quotes back to exact source sentences.
- **Multi-Sentence Quotes:** The model sometimes bundles two consecutive sentences into one quote block; we introduced recursive sentence-boundary decomposition to extract the exact grounded sentence.
- **English-First Verification:** While sample texts include Spanish cultural terms and sayings, the stopword filters and entity extractors are currently tuned for English.
- **Not a Replacement for Real Mourning:** Ofrenda is a software archive and tribute generator; it does not impersonate the deceased or simulate consciousness.

---

## 8. License

This project is licensed under the [MIT License](LICENSE).
