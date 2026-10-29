# Ofrenda: 90-Second Wi-Fi-Off Demo Script 🕯️🌼

**Target Duration:** Exactly 90 Seconds  
**Environment:** Laptop running completely offline (Wi-Fi turned OFF in OS control center)  
**Prerequisites:** Local Ollama daemon running with `gemma3:4b` and `nomic-embed-text`. Local server active on `http://127.0.0.1:8000`.

---

## Preparation (Before Recording)
1. Turn off Wi-Fi on your laptop (show the disconnected network icon in your taskbar).
2. Start the local server:
   ```bash
   uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```
3. Open browser to `http://127.0.0.1:8000`. Notice the header badge: **`[● Offline: Ollama Connected]`**.

---

## Demo Timeline & Steps

### 00:00 – 00:15 | Step 1: Show Offline Mode & Add a Story
- **Action:**
  1. Point cursor at the top status badge showing **"Offline: Ollama Connected"** and the system network tray showing Wi-Fi disabled.
  2. Scroll down to the **"Add a Memory"** form.
  3. Enter:
     - **Title:** `Afternoons at Chapultepec Park`
     - **Told by:** `Carlos (Brother)`
     - **Story Text:** Paste text from `samples/04_chapultepec_park.md` (or drag and drop the markdown file).
  4. Click **"Save Memory"**.
- **Voiceover / Caption:**
  > *"Welcome to Ofrenda, a 100% local, offline remembrance keeper. Notice Wi-Fi is completely disabled. We start by adding a family memory about Abuela Rosa visiting Chapultepec Park. The story is chunked and embedded locally using nomic-embed-text."*

---

### 00:15 – 00:30 | Step 2: Ask a Grounded Question
- **Action:**
  1. Navigate to the **"Ask the Keeper"** tab.
  2. In the query box, type:
     ```text
     What did she love to cook?
     ```
  3. Click **"Ask"**.
  4. Watch the candle glow animation while Gemma 3 4B processes locally (~5 seconds).
  5. View the response:
     > *"Abuela Rosa always cooked her signature mole negro in a round earthenware clay pot that her mother had given her in 1968."*
- **Voiceover / Caption:**
  > *"Now we ask the Keeper: 'What did she love to cook?' Within seconds, Gemma 3 4B retrieves the family recipe story and quotes the exact 1968 clay pot memory."*

---

### 00:30 – 00:45 | Step 3: Ask a Refusal Question (Missing Fact)
- **Action:**
  1. In the query input, replace the question with an unmentioned detail:
     ```text
     What was her phone number?
     ```
  2. Click **"Ask"**.
  3. Observe immediate clean refusal:
     > *"The stories don't mention that."*
  4. Note the refusal badge: `[Refusal Confirmed: Fact Not Found in Memories]`.
- **Voiceover / Caption:**
  > *"Crucially, the model will not invent memories. When asked for something never recorded—like a phone number or car—it refuses cleanly: 'The stories don't mention that.' Zero hallucinations."*

---

### 00:45 – 00:60 | Step 4: Hover and Inspect a Citation
- **Action:**
  1. Return to the answer for the cooking question.
  2. Hover your mouse over the citation badge `[Citation #1: Sunday Mole and the Clay Pot]`.
  3. The interactive popover appears, displaying:
     - Verified quote excerpt
     - Memory origin (`Sunday Mole and the Clay Pot`)
     - Contributor (`Mateo (Grandson)`)
     - Chunk ID: `sample_01_sunday_mole_c1`
- **Voiceover / Caption:**
  > *"Every claim links directly to its source. Hovering over a citation reveals the exact verified sentence in the family archive, proving the fact was genuinely written by her grandson Mateo."*

---

### 00:60 – 00:75 | Step 5: Generate the Remembrance Tribute
- **Action:**
  1. Click the **"Remembrance Tribute"** tab.
  2. Click the button: **"Generate Tribute"**.
  3. Watch the multi-tier pipeline run:
     - Gemma 3 4B composes warm memorial paragraphs.
     - The verification engine checks every sentence against source chunks.
  4. Point to the **Citation Verification Summary**:
     - *Verified Sentences:* `7`
     - *Dropped Sentences:* `0` (or audit log showing rejected unsupported claims)
- **Voiceover / Caption:**
  > *"Next, we generate a tribute page. Our verification engine checks each generated sentence word-for-word against the source memories. Any ungrounded sentence or invented date is automatically filtered out."*

---

### 00:75 – 00:90 | Step 6: Export the Page
- **Action:**
  1. Click the **"Export Remembrance Page"** button in the top right.
  2. The browser immediately downloads a single file: `ofrenda_abuela_rosa.html`.
  3. Double-click the exported HTML file to open it in a separate browser window.
  4. Show that the page renders beautifully with all marigold styling, citations, and memories intact—with no external fonts, CSS, or scripts.
- **Voiceover / Caption:**
  > *"Finally, export the completed remembrance page as a self-contained HTML document. It contains no external fonts or CDN dependencies, meaning it can be archived on a USB stick or shared with family to keep forever. Private, grounded, and forever offline."*
