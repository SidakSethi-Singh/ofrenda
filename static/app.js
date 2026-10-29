// Ofrenda: Offline Remembrance Keeper UI Client
document.addEventListener("DOMContentLoaded", () => {
    // State
    let currentTribute = null;
    let currentOfrenda = null;

    // Elements
    const statusBadge = document.getElementById("status-badge");
    const statusText = document.getElementById("status-text");
    const memoryCountNum = document.getElementById("memory-count-num");

    const tabButtons = document.querySelectorAll(".tab-btn");
    const tabContents = document.querySelectorAll(".tab-content");

    // Tribute Elements
    const btnGenerateTribute = document.getElementById("btn-generate-tribute");
    const btnExportHtml = document.getElementById("btn-export-html");
    const tributeLoading = document.getElementById("tribute-loading");
    const tributeDisplay = document.getElementById("tribute-display");
    const tributeAudit = document.getElementById("tribute-audit");
    const statVerifiedCount = document.getElementById("stat-verified-count");
    const statDroppedCount = document.getElementById("stat-dropped-count");
    const statTributeLatency = document.getElementById("stat-tribute-latency");
    const auditDropLog = document.getElementById("audit-drop-log");

    // Ofrenda Elements
    const btnLoadOfrenda = document.getElementById("btn-load-ofrenda");
    const ofrendaLoading = document.getElementById("ofrenda-loading");
    const ofrendaContainer = document.getElementById("ofrenda-grid-container");

    // Ask Elements
    const formAsk = document.getElementById("form-ask");
    const inputQuestion = document.getElementById("input-question");
    const btnAskSubmit = document.getElementById("btn-ask-submit");
    const askLoading = document.getElementById("ask-loading");
    const askResult = document.getElementById("ask-result");
    const promptChips = document.querySelectorAll(".chip-btn");

    // Memories Elements
    const archiveCount = document.getElementById("archive-count");
    const memoriesList = document.getElementById("memories-list");
    const formPasteMemory = document.getElementById("form-paste-memory");
    const formUploadMemory = document.getElementById("form-upload-memory");
    const subtabButtons = document.querySelectorAll(".subtab-btn");
    const memoryForms = document.querySelectorAll(".memory-form");

    // Global Popover
    const globalPopover = document.getElementById("global-popover");
    const popoverQuoteText = document.getElementById("popover-quote-text");
    const popoverSourceMeta = document.getElementById("popover-source-meta");

    // -----------------------------------------------------------------------
    // Initialization & Health Check
    // -----------------------------------------------------------------------
    async function checkHealth() {
        try {
            const res = await fetch("/health");
            if (!res.ok) throw new Error("Health endpoint error");
            const data = await res.json();

            if (data.ollama_connected) {
                statusBadge.className = "status-badge status-connected";
                const model = data.models_available.find(m => m.includes("gemma")) || "gemma3:4b";
                statusText.textContent = `Offline: Ollama Connected (${model})`;
            } else {
                statusBadge.className = "status-badge status-disconnected";
                statusText.textContent = "Offline: Ollama Disconnected";
            }
            memoryCountNum.textContent = data.memory_count;
        } catch (err) {
            statusBadge.className = "status-badge status-disconnected";
            statusText.textContent = "Cannot reach local server";
        }
    }

    // -----------------------------------------------------------------------
    // Navigation Tabs
    // -----------------------------------------------------------------------
    tabButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            const targetTab = btn.getAttribute("data-tab");
            tabButtons.forEach(b => {
                b.classList.toggle("active", b === btn);
                b.setAttribute("aria-selected", b === btn);
            });
            tabContents.forEach(c => {
                c.classList.toggle("active", c.id === `tab-${targetTab}`);
            });

            if (targetTab === "memories") {
                loadMemories();
            } else if (targetTab === "ofrenda" && !currentOfrenda) {
                loadOfrenda();
            }
        });
    });

    // Subtabs in Memories panel
    subtabButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            const target = btn.getAttribute("data-subtab");
            subtabButtons.forEach(b => b.classList.toggle("active", b === btn));
            memoryForms.forEach(f => {
                f.classList.toggle("active", f.id === `form-${target}-memory`);
            });
        });
    });

    // -----------------------------------------------------------------------
    // Remembrance Tribute
    // -----------------------------------------------------------------------
    btnGenerateTribute.addEventListener("click", async () => {
        btnGenerateTribute.disabled = true;
        btnExportHtml.disabled = true;
        tributeLoading.classList.remove("hidden");
        tributeAudit.classList.add("hidden");

        try {
            const res = await fetch("/api/tribute");
            if (!res.ok) throw new Error("Failed to generate tribute");
            const data = await res.json();
            currentTribute = data;

            renderTribute(data);
            btnExportHtml.disabled = false;
        } catch (err) {
            tributeDisplay.innerHTML = `<div class="tribute-placeholder" style="color: #f87171;">Error generating tribute: ${escapeHtml(err.message)}</div>`;
        } finally {
            tributeLoading.classList.add("hidden");
            btnGenerateTribute.disabled = false;
        }
    });

    function renderTribute(tribute) {
        let html = `<h2 class="tribute-subject-title">In Remembrance of ${escapeHtml(tribute.subject_name)}</h2>`;
        html += `<div class="tribute-text-body">`;

        // Map sentences with citations
        const sentenceMap = {};
        (tribute.sentences || []).forEach(s => {
            if (s.citation) {
                sentenceMap[s.sentence.trim()] = s;
            }
        });

        (tribute.paragraphs || []).forEach(p => {
            let renderedP = escapeHtml(p.trim());
            Object.keys(sentenceMap).forEach(sentText => {
                const escapedSent = escapeHtml(sentText);
                if (renderedP.includes(escapedSent)) {
                    const cit = sentenceMap[sentText].citation;
                    const citDataAttr = encodeURIComponent(JSON.stringify(cit));
                    const interactiveSpan = `
                        <span class="grounded-phrase" data-citation="${citDataAttr}">
                            ${escapedSent}
                            <span class="cite-tag">[source]</span>
                        </span>
                    `;
                    renderedP = renderedP.replace(escapedSent, interactiveSpan);
                }
            });
            html += `<p>${renderedP}</p>`;
        });

        html += `</div>`;
        tributeDisplay.innerHTML = html;

        // Attach popover events to grounded phrases
        attachCitationEvents();

        // Render audit stats
        statVerifiedCount.textContent = (tribute.sentences || []).length;
        statDroppedCount.textContent = tribute.dropped_count || 0;
        statTributeLatency.textContent = `${Math.round(tribute.latency_ms || 0)}ms`;

        if (tribute.drop_reasons && tribute.drop_reasons.length > 0) {
            auditDropLog.innerHTML = tribute.drop_reasons.map(r => `<div class="drop-log-item">&#9888; ${escapeHtml(r)}</div>`).join("");
        } else {
            auditDropLog.innerHTML = `<div style="color: #34d399;">&#10003; All generated sentences passed grounded quote verification.</div>`;
        }
        tributeAudit.classList.remove("hidden");
    }

    // Export HTML button
    btnExportHtml.addEventListener("click", async () => {
        try {
            btnExportHtml.disabled = true;
            btnExportHtml.textContent = "Exporting...";
            const res = await fetch("/api/export", { method: "POST" });
            if (!res.ok) throw new Error("Export failed");
            const data = await res.json();

            // Download file
            const blob = new Blob([data.html], { type: "text/html;charset=utf-8" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = data.filename || "ofrenda_remembrance.html";
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        } catch (err) {
            alert(`Could not export remembrance page: ${err.message}`);
        } finally {
            btnExportHtml.disabled = false;
            btnExportHtml.innerHTML = `<span class="btn-icon">&#128190;</span> Export HTML`;
        }
    });

    // -----------------------------------------------------------------------
    // Ofrenda Altar Cards
    // -----------------------------------------------------------------------
    btnLoadOfrenda.addEventListener("click", loadOfrenda);

    async function loadOfrenda() {
        btnLoadOfrenda.disabled = true;
        ofrendaLoading.classList.remove("hidden");

        try {
            const res = await fetch("/api/ofrenda");
            if (!res.ok) throw new Error("Failed to load altar cards");
            const data = await res.json();
            currentOfrenda = data;
            renderOfrenda(data);
        } catch (err) {
            ofrendaContainer.innerHTML = `<div class="tribute-placeholder" style="color: #f87171;">Error loading cards: ${escapeHtml(err.message)}</div>`;
        } finally {
            ofrendaLoading.classList.add("hidden");
            btnLoadOfrenda.disabled = false;
        }
    }

    function renderOfrenda(ofrenda) {
        const categories = [
            { title: "Favorite Foods & Offerings", icon: "🥣", cards: ofrenda.foods },
            { title: "Songs & Melodies", icon: "🎶", cards: ofrenda.songs },
            { title: "Cherished Places & Walks", icon: "🌿", cards: ofrenda.places },
            { title: "Sayings & Wisdom", icon: "📜", cards: ofrenda.sayings }
        ];

        let html = "";
        categories.forEach(cat => {
            if (!cat.cards || cat.cards.length === 0) return;

            const cardsHtml = cat.cards.map(c => `
                <div class="card-item">
                    <h4 class="card-item-title">${escapeHtml(c.title)}</h4>
                    <p class="card-item-detail">${escapeHtml(c.detail)}</p>
                    <div class="card-item-cite">
                        <span class="cite-quote">"${escapeHtml(c.citation.quote)}"</span>
                        <span class="cite-source">&mdash; ${escapeHtml(c.citation.source_title || 'Memory')} (${escapeHtml(c.citation.chunk_id)})</span>
                    </div>
                </div>
            `).join("");

            html += `
                <div class="ofrenda-cat-block">
                    <h3 class="cat-header"><span class="cat-icon">${cat.icon}</span> ${cat.title} (${cat.cards.length})</h3>
                    <div class="cards-grid">
                        ${cardsHtml}
                    </div>
                </div>
            `;
        });

        ofrendaContainer.innerHTML = html || `<div class="tribute-placeholder">No altar offerings found in memories.</div>`;
    }

    // -----------------------------------------------------------------------
    // Ask the Keeper
    // -----------------------------------------------------------------------
    promptChips.forEach(chip => {
        chip.addEventListener("click", () => {
            const q = chip.getAttribute("data-q");
            inputQuestion.value = q;
            submitQuestion(q);
        });
    });

    formAsk.addEventListener("submit", (e) => {
        e.preventDefault();
        const q = inputQuestion.value.trim();
        if (q) submitQuestion(q);
    });

    async function submitQuestion(question) {
        btnAskSubmit.disabled = true;
        askLoading.classList.remove("hidden");
        askResult.classList.add("hidden");

        try {
            const res = await fetch("/api/ask", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ question })
            });
            if (!res.ok) throw new Error("Failed to consult the Keeper");
            const data = await res.json();
            renderAskResult(data);
        } catch (err) {
            askResult.innerHTML = `<div style="color: #f87171;">Error: ${escapeHtml(err.message)}</div>`;
            askResult.classList.remove("hidden");
        } finally {
            askLoading.classList.add("hidden");
            btnAskSubmit.disabled = false;
        }
    }

    function renderAskResult(resp) {
        let html = "";
        if (resp.not_mentioned) {
            html += `
                <div class="refusal-badge">&#128683; Refusal Confirmed (Not in Memories)</div>
                <div class="keeper-badge">&#128330;&#65039; The Keeper</div>
                <p class="keeper-answer-text"><em>"${escapeHtml(resp.answer)}"</em></p>
                <p style="font-size: 0.85rem; color: var(--text-dim);">Strict grounding rule: The Keeper will never invent facts that do not exist in family records.</p>
            `;
        } else {
            html += `
                <div class="keeper-badge">&#128330;&#65039; The Keeper</div>
                <p class="keeper-answer-text">${escapeHtml(resp.answer)}</p>
            `;

            if (resp.citations && resp.citations.length > 0) {
                html += `
                    <div class="ask-citations-box">
                        <div class="ask-citations-title">&#10003; Verified Citations (${resp.citations.length}):</div>
                `;
                resp.citations.forEach(cit => {
                    html += `
                        <div class="citation-bubble">
                            <span class="cite-quote">"${escapeHtml(cit.quote)}"</span>
                            <span class="cite-source">&mdash; ${escapeHtml(cit.source_title || 'Memory')} [${escapeHtml(cit.chunk_id)}]</span>
                        </div>
                    `;
                });
                html += `</div>`;
            }
        }

        html += `
            <div style="margin-top: 1rem; font-size: 0.75rem; color: var(--text-dim);">
                Latency: ${Math.round(resp.latency_ms)}ms | Model: ${escapeHtml(resp.model)}
            </div>
        `;

        askResult.innerHTML = html;
        askResult.classList.remove("hidden");
    }

    // -----------------------------------------------------------------------
    // Memories Archive
    // -----------------------------------------------------------------------
    async function loadMemories() {
        try {
            const res = await fetch("/api/memories");
            if (!res.ok) throw new Error("Failed to load memories");
            const memories = await res.json();

            archiveCount.textContent = memories.length;
            memoryCountNum.textContent = memories.length;

            if (memories.length === 0) {
                memoriesList.innerHTML = `<div class="tribute-placeholder">No stories yet. Add one above!</div>`;
                return;
            }

            memoriesList.innerHTML = memories.map(m => `
                <div class="mem-item">
                    <h4 class="mem-item-title">${escapeHtml(m.title)}</h4>
                    <div class="mem-item-meta">Told by: ${escapeHtml(m.author || 'Family')} &bull; ${m.chunk_count} chunk(s) &bull; ${escapeHtml(m.created_at)}</div>
                    <p class="mem-item-snippet">${escapeHtml(m.content.slice(0, 160))}...</p>
                </div>
            `).join("");
        } catch (err) {
            memoriesList.innerHTML = `<div style="color: #f87171;">Error loading memories: ${escapeHtml(err.message)}</div>`;
        }
    }

    // Form Paste Memory
    formPasteMemory.addEventListener("submit", async (e) => {
        e.preventDefault();
        const title = document.getElementById("mem-title").value.trim();
        const author = document.getElementById("mem-author").value.trim();
        const content = document.getElementById("mem-content").value.trim();

        try {
            const res = await fetch("/api/memories", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ title, author, content })
            });
            if (!res.ok) throw new Error("Could not add memory");
            formPasteMemory.reset();
            alert("Memory added and indexed successfully into local ChromaDB!");
            loadMemories();
        } catch (err) {
            alert(`Error: ${err.message}`);
        }
    });

    // Form Upload Memory
    formUploadMemory.addEventListener("submit", async (e) => {
        e.preventDefault();
        const fileInput = document.getElementById("upload-file");
        const title = document.getElementById("upload-title").value.trim();
        const author = document.getElementById("upload-author").value.trim();

        if (!fileInput.files || fileInput.files.length === 0) {
            alert("Please select a file to upload.");
            return;
        }

        const formData = new FormData();
        formData.append("file", fileInput.files[0]);
        if (title) formData.append("title", title);
        if (author) formData.append("author", author);

        try {
            const res = await fetch("/api/memories/upload", {
                method: "POST",
                body: formData
            });
            if (!res.ok) throw new Error("Could not upload memory");
            formUploadMemory.reset();
            alert("Document uploaded, parsed, and indexed into local ChromaDB!");
            loadMemories();
        } catch (err) {
            alert(`Upload error: ${err.message}`);
        }
    });

    // -----------------------------------------------------------------------
    // Interactive Citation Popovers
    // -----------------------------------------------------------------------
    function attachCitationEvents() {
        const phrases = document.querySelectorAll(".grounded-phrase");
        phrases.forEach(phrase => {
            phrase.addEventListener("mouseenter", (e) => {
                const dataRaw = phrase.getAttribute("data-citation");
                if (!dataRaw) return;
                try {
                    const cit = JSON.parse(decodeURIComponent(dataRaw));
                    popoverQuoteText.textContent = `"${cit.quote}"`;
                    popoverSourceMeta.textContent = `Source: ${cit.source_title || 'Memory'} [${cit.chunk_id}]`;

                    const rect = phrase.getBoundingClientRect();
                    globalPopover.classList.remove("hidden");

                    const popWidth = 320;
                    let left = rect.left + (rect.width / 2) - (popWidth / 2);
                    if (left < 10) left = 10;
                    if (left + popWidth > window.innerWidth - 10) left = window.innerWidth - popWidth - 10;

                    let top = rect.top - globalPopover.offsetHeight - 10;
                    if (top < 10) top = rect.bottom + 10;

                    globalPopover.style.left = `${left}px`;
                    globalPopover.style.top = `${top}px`;
                } catch (err) {
                    console.error("Citation parse error", err);
                }
            });

            phrase.addEventListener("mouseleave", () => {
                globalPopover.classList.add("hidden");
            });
        });
    }

    // Helper
    function escapeHtml(str) {
        if (!str) return "";
        return str
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    // Run initial checks
    checkHealth();
    loadMemories();
});
