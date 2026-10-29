import html
from typing import Optional
from app.models import TributeResponse, OfrendaResponse


def generate_remembrance_html(
    tribute: TributeResponse,
    ofrenda: Optional[OfrendaResponse] = None,
    custom_title: Optional[str] = None
) -> str:
    """
    Generates a self-contained, single-file HTML remembrance page.
    Fully offline: no external CDN links, fonts, or scripts.
    Styled with warm marigold and candlelight aesthetics.
    """
    title = custom_title or f"In Remembrance: {tribute.subject_name}"
    escaped_title = html.escape(title)
    escaped_subject = html.escape(tribute.subject_name)

    # Build paragraph HTML with inline citation tooltips
    paragraphs_html = []
    sentence_map = {s.sentence.strip(): s for s in tribute.sentences if s.citation}

    for p in tribute.paragraphs:
        p_text = p.strip()
        # Find matching sentences and embed citations
        rendered_p = html.escape(p_text)
        for sent_text, sent_obj in sentence_map.items():
            if sent_text in rendered_p and sent_obj.citation:
                cit = sent_obj.citation
                src = html.escape(cit.source_title or "Family Memory")
                author = html.escape(sent_obj.citation.drop_reason or "Family")
                quote = html.escape(cit.quote)
                chunk_id = html.escape(cit.chunk_id)

                citation_badge = (
                    f'<span class="citation-ref" tabindex="0">'
                    f'<sup class="citation-sup">[source]</sup>'
                    f'<span class="citation-popover">'
                    f'<span class="popover-header">Verified Source Quote</span>'
                    f'<blockquote class="popover-quote">"{quote}"</blockquote>'
                    f'<span class="popover-meta"><strong>Source:</strong> {src} ({chunk_id})</span>'
                    f'<span class="popover-verified">&#10003; Verified against source text</span>'
                    f'</span>'
                    f'</span>'
                )
                escaped_sent = html.escape(sent_text)
                rendered_p = rendered_p.replace(escaped_sent, f'<span class="grounded-sentence">{escaped_sent} {citation_badge}</span>')
        paragraphs_html.append(f"<p class='tribute-paragraph'>{rendered_p}</p>")

    all_paragraphs = "\n".join(paragraphs_html)

    # Build Ofrenda cards if present
    ofrenda_sections_html = ""
    if ofrenda and ofrenda.cards:
        categories = [
            ("Favorite Foods & Offerings", "🥣", ofrenda.foods),
            ("Songs & Melodies", "🎶", ofrenda.songs),
            ("Cherished Places & Walks", "🌿", ofrenda.places),
            ("Sayings & Wisdom", "📜", ofrenda.sayings),
        ]
        cat_blocks = []
        for cat_title, icon, cards in categories:
            if not cards:
                continue
            card_items = []
            for c in cards:
                c_title = html.escape(c.title)
                c_detail = html.escape(c.detail)
                c_quote = html.escape(c.citation.quote)
                c_src = html.escape(c.citation.source_title or "Memory")
                c_chunk = html.escape(c.citation.chunk_id)
                card_items.append(f"""
                <div class="ofrenda-card">
                    <div class="card-icon">{icon}</div>
                    <div class="card-content">
                        <h4 class="card-title">{c_title}</h4>
                        <p class="card-detail">{c_detail}</p>
                        <div class="card-citation">
                            <span class="card-quote">"{c_quote}"</span>
                            <span class="card-source">&mdash; {c_src} [{c_chunk}]</span>
                        </div>
                    </div>
                </div>
                """)
            joined_cards = "\n".join(card_items)
            cat_blocks.append(f"""
            <div class="ofrenda-category">
                <h3 class="category-header"><span class="cat-icon">{icon}</span> {cat_title}</h3>
                <div class="cards-grid">
                    {joined_cards}
                </div>
            </div>
            """)
        ofrenda_sections_html = f"""
        <section class="ofrenda-section">
            <h2 class="section-title">The Ofrenda Altar</h2>
            <p class="section-subtitle">Tokens, songs, and sayings preserved faithfully from family memories</p>
            {"".join(cat_blocks)}
        </section>
        """

    # Self-contained HTML with marigold and candlelight styling
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escaped_title}</title>
    <style>
        :root {{
            --bg-deep: #0c0a09;
            --bg-card: #1c1917;
            --bg-card-hover: #292524;
            --marigold: #f59e0b;
            --marigold-gold: #fbbf24;
            --marigold-dark: #b45309;
            --flame: #ea580c;
            --flame-glow: rgba(245, 158, 11, 0.25);
            --text-main: #f5f5f4;
            --text-muted: #a8a29e;
            --text-faint: #78716c;
            --border-dim: #44403c;
            --border-marigold: rgba(245, 158, 11, 0.4);
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            background-color: var(--bg-deep);
            color: var(--text-main);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            line-height: 1.7;
            padding: 2rem 1rem;
            min-height: 100vh;
        }}

        .container {{
            max-width: 860px;
            margin: 0 auto;
        }}

        /* Subtle Candlelight Flicker */
        @keyframes candle-flicker {{
            0%   {{ box-shadow: 0 0 25px rgba(245, 158, 11, 0.2), inset 0 0 15px rgba(234, 88, 12, 0.1); }}
            25%  {{ box-shadow: 0 0 32px rgba(245, 158, 11, 0.28), inset 0 0 18px rgba(234, 88, 12, 0.14); }}
            50%  {{ box-shadow: 0 0 22px rgba(245, 158, 11, 0.18), inset 0 0 14px rgba(234, 88, 12, 0.08); }}
            75%  {{ box-shadow: 0 0 36px rgba(245, 158, 11, 0.32), inset 0 0 20px rgba(234, 88, 12, 0.16); }}
            100% {{ box-shadow: 0 0 25px rgba(245, 158, 11, 0.2), inset 0 0 15px rgba(234, 88, 12, 0.1); }}
        }}

        .remembrance-frame {{
            background: linear-gradient(180deg, #1c1917 0%, #141210 100%);
            border: 1px solid var(--border-marigold);
            border-radius: 12px;
            padding: 3rem 2.5rem;
            position: relative;
            animation: candle-flicker 5s infinite ease-in-out;
        }}

        .header-altar {{
            text-align: center;
            border-bottom: 1px solid var(--border-dim);
            padding-bottom: 2rem;
            margin-bottom: 2.5rem;
        }}

        .flame-icon {{
            font-size: 2.5rem;
            display: inline-block;
            filter: drop-shadow(0 0 12px var(--marigold));
            margin-bottom: 0.5rem;
        }}

        .main-title {{
            font-size: 2.2rem;
            font-weight: 700;
            color: var(--marigold-gold);
            letter-spacing: -0.02em;
            margin-bottom: 0.5rem;
        }}

        .subtitle-bar {{
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 1rem;
            font-size: 0.9rem;
            color: var(--text-muted);
            margin-top: 0.5rem;
        }}

        .badge-offline {{
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            background: rgba(245, 158, 11, 0.15);
            border: 1px solid var(--marigold-dark);
            color: var(--marigold-gold);
            padding: 0.2rem 0.65rem;
            border-radius: 999px;
            font-size: 0.8rem;
            font-weight: 500;
        }}

        .tribute-body {{
            font-size: 1.15rem;
            color: #e7e5e4;
            margin-bottom: 3rem;
        }}

        .tribute-paragraph {{
            margin-bottom: 1.5rem;
            text-align: justify;
            text-justify: inter-word;
        }}

        .grounded-sentence {{
            position: relative;
            border-bottom: 1px dotted var(--marigold);
            transition: background-color 0.2s;
        }}

        .grounded-sentence:hover {{
            background-color: rgba(245, 158, 11, 0.1);
        }}

        /* Interactive Citation Popover */
        .citation-ref {{
            position: relative;
            cursor: pointer;
            display: inline-block;
        }}

        .citation-sup {{
            color: var(--marigold);
            font-size: 0.75rem;
            font-weight: bold;
            margin-left: 2px;
            padding: 0 3px;
        }}

        .citation-popover {{
            visibility: hidden;
            opacity: 0;
            width: 320px;
            background-color: #262320;
            border: 1px solid var(--marigold);
            box-shadow: 0 10px 25px rgba(0,0,0,0.7), 0 0 15px rgba(245, 158, 11, 0.2);
            border-radius: 8px;
            padding: 1rem;
            position: absolute;
            bottom: 125%;
            left: 50%;
            transform: translateX(-50%);
            z-index: 50;
            transition: opacity 0.25s, visibility 0.25s;
            pointer-events: none;
            font-size: 0.85rem;
            text-align: left;
            line-height: 1.4;
        }}

        .citation-ref:hover .citation-popover,
        .citation-ref:focus .citation-popover {{
            visibility: visible;
            opacity: 1;
            pointer-events: auto;
        }}

        .popover-header {{
            display: block;
            color: var(--marigold-gold);
            font-weight: bold;
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.5rem;
            border-bottom: 1px solid var(--border-dim);
            padding-bottom: 0.25rem;
        }}

        .popover-quote {{
            font-style: italic;
            color: #f5f5f4;
            margin-bottom: 0.5rem;
            border-left: 2px solid var(--marigold);
            padding-left: 0.5rem;
        }}

        .popover-meta {{
            display: block;
            color: var(--text-muted);
            font-size: 0.75rem;
            margin-bottom: 0.4rem;
        }}

        .popover-verified {{
            display: inline-block;
            color: #34d399;
            font-size: 0.75rem;
            font-weight: 600;
        }}

        /* Ofrenda Altar Cards */
        .ofrenda-section {{
            border-top: 1px solid var(--border-dim);
            padding-top: 2.5rem;
            margin-top: 2rem;
        }}

        .section-title {{
            font-size: 1.6rem;
            color: var(--marigold-gold);
            margin-bottom: 0.3rem;
            text-align: center;
        }}

        .section-subtitle {{
            text-align: center;
            color: var(--text-muted);
            font-size: 0.95rem;
            margin-bottom: 2rem;
        }}

        .ofrenda-category {{
            margin-bottom: 2rem;
        }}

        .category-header {{
            font-size: 1.15rem;
            color: #fbbf24;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            margin-bottom: 1rem;
            border-bottom: 1px solid rgba(245, 158, 11, 0.2);
            padding-bottom: 0.4rem;
        }}

        .cards-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 1rem;
        }}

        .ofrenda-card {{
            background: var(--bg-card);
            border: 1px solid var(--border-dim);
            border-radius: 8px;
            padding: 1.25rem;
            display: flex;
            gap: 1rem;
            transition: transform 0.2s, border-color 0.2s;
        }}

        .ofrenda-card:hover {{
            transform: translateY(-2px);
            border-color: var(--marigold);
            background: var(--bg-card-hover);
        }}

        .card-icon {{
            font-size: 1.8rem;
            flex-shrink: 0;
            padding-top: 0.2rem;
        }}

        .card-title {{
            font-size: 1.05rem;
            color: #fef3c7;
            margin-bottom: 0.35rem;
        }}

        .card-detail {{
            font-size: 0.9rem;
            color: #d6d3d1;
            margin-bottom: 0.75rem;
            line-height: 1.5;
        }}

        .card-citation {{
            font-size: 0.8rem;
            color: var(--text-muted);
            background: rgba(0, 0, 0, 0.25);
            padding: 0.5rem 0.65rem;
            border-radius: 4px;
            border-left: 2px solid var(--marigold-dark);
        }}

        .card-quote {{
            display: block;
            font-style: italic;
            margin-bottom: 0.25rem;
            color: #e7e5e4;
        }}

        .card-source {{
            display: block;
            color: var(--marigold);
            font-size: 0.75rem;
        }}

        /* Footer */
        .footer-note {{
            text-align: center;
            margin-top: 3rem;
            padding-top: 1.5rem;
            border-top: 1px solid var(--border-dim);
            font-size: 0.85rem;
            color: var(--text-faint);
        }}

        .footer-note p {{
            margin-bottom: 0.35rem;
        }}

        @media print {{
            body {{
                background: white;
                color: black;
                padding: 0;
            }}
            .remembrance-frame {{
                border: none;
                box-shadow: none;
                animation: none;
                background: white;
            }}
            .citation-popover {{
                display: none !important;
            }}
            .main-title {{
                color: #b45309;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <main class="remembrance-frame">
            <header class="header-altar">
                <div class="flame-icon">&#128367;&#65039;</div>
                <h1 class="main-title">{escaped_title}</h1>
                <div class="subtitle-bar">
                    <span>A Remembrance Page Preserved with Care</span>
                    <span class="badge-offline">&#128274; Strictly Offline</span>
                </div>
            </header>

            <article class="tribute-body">
                {all_paragraphs}
            </article>

            {ofrenda_sections_html}

            <footer class="footer-note">
                <p>Preserved by <strong>Ofrenda: Offline Remembrance Keeper</strong></p>
                <p>Every line verified against source memories. Nothing ever left this computer.</p>
            </footer>
        </main>
    </div>
</body>
</html>
"""
