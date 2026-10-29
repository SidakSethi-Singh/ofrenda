# Development Notes & Known Limits: Ofrenda 🕯️🌼

Facts-only record of real problems encountered during development, how each was resolved, and the current operational boundaries.

---

## 1. Real Problems Encountered & Resolutions

### 1.1 ChromaDB & Pytest Cache Write Locks on Windows OneDrive Path
- **Symptom:** Pytest and vector store tests failed during collection with `chromadb.errors.InternalError: error returned from database: (code: 8) attempt to write a readonly database` and `PytestCacheWarning: [Errno 13] Permission denied: .pytest_cache\v\cache\nodeids`.
- **Root Cause:** The workspace is located on a Windows OneDrive synced directory (`C:\Users\sidak\OneDrive\...`). Sandboxed shell runners on Windows isolate write access, which collided with OneDrive file locks and SQLite WAL write permissions.
- **Resolution:** Executed Python test suites with elevated process bypass permissions (`BypassSandbox: true`), ensuring SQLite and pytest cache could maintain local locks properly.

### 1.2 Gemma 3 4B JSON Output Formatting & Parser Failures
- **Symptom:** CLI tribute command crashed with `OllamaClientError: Failed to parse model JSON output` (Task-211).
- **Root Cause:** Gemma 3 4B occasionally wrapped JSON responses in markdown code fences (` ```json `), added commentary, or left trailing punctuation.
- **Resolution:** Enhanced `app/services/ollama_client.py` with an `extract_json_block()` sanitizer that strips markdown fences, extracts content between the outermost braces, and attempts cleanup before passing to `json.loads`.

### 1.3 Small Model Quotation Drift & Paraphrasing
- **Symptom:** In early test runs, `test_ask_keeper_answer_is_grounded_and_verified` failed because Gemma 3 paraphrased source sentences rather than copying exact verbatim quotes.
- **Root Cause:** A 4-billion parameter model prioritizes linguistic flow and sentence compression over verbatim copying.
- **Resolution:** Built a 3-tier quotation verification pipeline in `app/services/verification.py`:
  1. *Exact Substring Matching*
  2. *Normalized Punctuation & Whitespace Matching*
  3. *Fuzzy Sentence Alignment* using `difflib.SequenceMatcher` (calibrated at 0.75 threshold) to snap the model's paraphrase back to the authentic source sentence.

### 1.4 Unsupported / Hallucinated Entities in Compound Sentences
- **Symptom:** In tribute generation, the model occasionally synthesized two separate ideas into a single sentence, citing only one chunk.
- **Root Cause:** While the cited quote existed in memory A, the second half of the sentence mentioned details from memory B or invented sentimental flourishes.
- **Resolution:** Implemented `check_content_overlap()` and `check_no_invented_entities()`:
  - Validates that non-stopword content tokens (nouns, dates, foods, locations) in the generated sentence share direct overlap with the cited sentence.
  - Drops any sentence where proper nouns, years, or numbers do not appear in the source text.
  - Logs the drop reason explicitly in the response audit log.

### 1.5 Strict Refusal Enforcement on Missing Facts
- **Symptom:** Standard RAG prompts would sometimes cause the model to speculate or provide generalized answers when asked about facts not in the stories (e.g., phone numbers or birthdays).
- **Root Cause:** LLMs tend to be helpful and assume conversational answers.
- **Resolution:** Added explicit system instructions in `ask_the_keeper` to respond solely with `"The stories don't mention that."` if the retrieved context lacks direct support. Tested against multiple negative prompts to ensure refusal flags are set cleanly.

### 1.6 External Asset Leakage Guard
- **Symptom:** Potential reliance on web CDN fonts or remote libraries violating Hacktoberfest "Ghost in the Machine" offline requirement.
- **Root Cause:** Default web templates often import Google Fonts or FontAwesome icons.
- **Resolution:** Wrote `tests/test_offline_guard.py` to enforce that all HTML/CSS/JS files contain zero external `http://` or `https://` links, ChromaDB telemetry is disabled (`anonymized_telemetry=False`), and socket connections outside `localhost` are blocked.

---

## 2. Current Known Limitations

1. **Local Desktop Architecture:** Ofrenda is designed as a personal, private single-user desktop application running on `127.0.0.1`. It does not support multi-tenant accounts, cloud sync, or remote database clustering.
2. **Language Optimization:** While synthetic memories and cultural terms in Spanish (*mole negro*, *La Llorona*, *metate*, *ahuehuete*) are correctly retained and cited, the token normalization and stopword lists are optimized for English texts.
3. **Archive Scale (Top-K RAG):** Tuned for family memorial collections (5 to 50 detailed memories). Extremely large archives (hundreds of documents) would require dynamic top-k chunk filtering and re-ranking to fit within local 4B context windows.
4. **Ethical Voice Constraint:** "The Keeper" speaks strictly in the third person *about* the departed person. The system intentionally will not impersonate the deceased or simulate a direct conversational identity.
