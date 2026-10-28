# Ofrenda: Offline Remembrance Keeper (Project Brief for Antigravity CLI)

Challenge: Hacktoberfest Open-Source AI Challenge, "Ghost in the Machine" (Halloween / Dia de los Muertos).
Check the exact deadline on the challenge page before starting. Plan to publish at least 1 day before it.

## 1. One-line pitch
Ofrenda is a fully offline tool where you add stories, notes and transcripts about someone you miss, then ask questions and generate a remembrance page. The "ghost" only repeats what the family actually wrote. Every line links to its source sentence. Nothing leaves the laptop.

## 2. Why it fits the challenge
- Theme: honors the past in the spirit of Dia de los Muertos, with a gentle "ghost" voice.
- Open-source core: Gemma 3 4B via Ollama, nomic-embed-text, ChromaDB. No cloud.
- Open innovation story: family photos and stories stay private, works with the lights (and Wi-Fi) off, and is not locked inside a service that can disappear.
- Reuses SlothClerk: chunker, vector store, Ollama client, citation verification, FastAPI, single-page UI.

## 3. Hard rules (do not break)
1. Fully offline at runtime. No external API calls, no CDN fonts or scripts, telemetry off.
2. The model must not invent memories. If the stories do not say it, the answer is "The stories don't mention that."
3. Do not impersonate the deceased. The narrator is "the Keeper", who speaks ABOUT the person.
4. All sample data is synthetic and fictional (for example "Abuela Rosa"). No real family data in the repo.
5. No claims in README, UI or post that are not measured or tested. Say "citations checked against the source text", never "100% grounded".
6. Commit to git after every working step. Project lives on D:, not on OneDrive.
7. Do not add features beyond section 5 without asking me.

## 4. Stack
- Python 3.11+, FastAPI, uvicorn
- Ollama: gemma3:4b (generation), nomic-embed-text (embeddings)
- ChromaDB with anonymized_telemetry=False, always pass our own embeddings
- Single-page HTML/JS/CSS UI, no external assets
- pytest

## 5. Scope
### Must have (v1)
1. Add memories: paste text, or upload .txt / .md / .docx / .pdf. Each memory has a title and an optional "who told it" field.
2. Chunk on sentence/paragraph boundaries and embed locally.
3. "Ask the Keeper": RAG chat over the stories. Answers must quote the source sentence, and the quote is verified to exist in the source text. If no support is found, say so.
4. Remembrance page generator: a short, warm, plain-language tribute (3 to 5 paragraphs) where EVERY sentence cites a source memory. Drop sentences whose citation fails verification.
5. Ofrenda view: simple cards for favorite foods, songs, places and sayings, extracted by a deterministic scanner first (patterns like "loved", "favorite", "used to sing", "always made"), with the model only rewording. Each card links to its source.
6. Spooky-warm UI: candlelight and marigold colors, subtle flicker animation, "Offline: Ollama connected" badge, citation popover showing the source sentence highlighted.
7. Export remembrance page as a single HTML file (self-contained, no external assets).

### Nice to have (only if v1 is done and tested)
- Optional audio: transcribe a voice recording with open-source faster-whisper, running locally.
- Optional browser Web Speech read-aloud for the tribute (no cloud).

### Cut (do not build)
- Cloud hosting, ElevenLabs, accounts, image generation, OCR, multi-user.

## 6. Reuse from SlothClerk
Copy and adapt from D:\projects\slothclerk (or the GitHub repo): `config.py`, `chunker.py`, `vector_store.py`, `ollama_client.py`, quote verification and sentence-expansion logic, the sanitize and dedupe helpers, `offline_guard` test, UI shell and citation popover.
Replace the contract analyzer with a memory analyzer. Do not copy contract-specific prompts or filters.

## 7. Quality rules (lessons from SlothClerk)
- Rules find, the model words it. Use deterministic scanners to pick source sentences, and let Gemma only rewrite them in a gentle tone.
- A verified quote only proves the text exists, not that the claim is right. Add a check that each generated sentence shares real content words (names, foods, places, numbers) with its cited sentence, otherwise drop it.
- Never invent dates, names, places or relationships. Any name or date in the output must appear in the cited source.
- Temperature 0, fixed seed, num_predict capped, schema-constrained JSON output, strip trailing whitespace and stray quote artifacts, never cut mid-word.
- Log every dropped item with a reason, and show the drop counts in the metrics.
- The CLI and the web API must call the same function. Add a test that both return the same counts.
- Use at most 2 to 3 small LLM calls per request so latency stays under about 60 seconds.

## 8. Build order (STOP at each checkpoint and show me output)
1. Setup: venv on D:, requirements.txt, .gitignore (venv, chroma_db, uploads, .env), .env.example, git init. Checkpoint: pytest runs.
2. Port the shared modules (config, chunker, vector store, Ollama client, verification). Checkpoint: unit tests pass.
3. Create synthetic samples in `samples/`: 3 to 4 short fictional stories about "Abuela Rosa" (cooking, a song, a saying, a place). Include one fact that is deliberately NOT mentioned anywhere, to test refusal.
4. Memory analyzer + CLI: `python cli.py --ask "What did she love to cook?"` and `python cli.py --tribute`. Checkpoint: show full output with citations and drop counts.
5. Tests: refusal test ("What was her phone number?" must say not mentioned), every citation verified, no invented names or dates, CLI and API counts identical.
6. FastAPI endpoints: /health, /api/memories (add/list), /api/ask, /api/tribute, /api/ofrenda, /api/export.
7. UI: add memory, ask the Keeper, tribute view, ofrenda cards, citation popover, export button. Checkpoint: I will click through it.
8. README, MIT LICENSE, demo steps. No overclaims.

## 9. Offline check
- Ollama and Chroma only on localhost.
- Page must load with Wi-Fi off, with no external fonts or scripts.
- Include an offline guard test.

## 10. README must contain
- What it is and how to run it (Ollama pull commands, venv, uvicorn)
- Why open models (privacy, offline, no per-use cost, swap model in .env)
- How it works (rules find, model words, verify)
- Results table with real measured numbers only (time per request, citations verified, drops)
- "What didn't work" and Limits (English only, synthetic samples, 4B model wording, not a replacement for real remembrance)
- Demo link and MIT license

## 11. Blog post outline (for me to write in my own voice)
Use the Submission Template with tags #devchallenge and #hf26challenge.
1. Hook: why I built something to keep stories safe on my own machine
2. What I built and the demo (video recorded with Wi-Fi off, plus screenshots)
3. How I built it (Gemma, Ollama, Chroma, rules + verification)
4. Why open innovation matters (privacy, offline, no service to disappear, cost $0)
5. What went wrong (real failures only)
6. Limits
7. Prize categories: only Best Use of Gemma, plus others ONLY if actually used and shown
8. AI Disclosure: Antigravity and Gemma

## 12. First message to give Antigravity CLI
"Read ofrenda_plan.md fully. Follow section 8 step by step. Do steps 1 and 2 now, show me the test output, then stop and wait. Do not build anything outside section 5. Ask me before changing scope."
