#!/usr/bin/env python3
import sys
import argparse
import time
from typing import Optional

from app.services.analyzer import (
    ask_keeper,
    generate_tribute,
    extract_ofrenda,
    list_memories,
    load_synthetic_samples_if_empty,
    index_memory
)
from app.services.extractor import extract_from_file


def format_header(title: str) -> str:
    line = "=" * 64
    return f"\n{line}\n  {title}\n{line}"


def cmd_init_samples():
    print(format_header("OFRENDA: Initializing Synthetic Samples"))
    count = load_synthetic_samples_if_empty()
    print(f"Loaded and indexed {count} sample stories from samples/.")
    mems = list_memories()
    print(f"Total memories in database: {len(mems)}")
    for m in mems:
        print(f" - [{m.id}] {m.title} (by {m.author or 'Unknown'}) | {m.chunk_count} chunks")


def cmd_list_memories():
    print(format_header("OFRENDA: Registered Memories"))
    mems = list_memories()
    if not mems:
        print("No memories currently registered. Run with --init-samples to load Abuela Rosa's stories.")
        return
    for idx, m in enumerate(mems, 1):
        print(f"{idx}. {m.title}")
        print(f"   ID: {m.id} | Author: {m.author or 'Family'} | Chunks: {m.chunk_count}")
        print(f"   Created: {m.created_at}")


def cmd_add_memory(title: str, author: Optional[str], file_path: Optional[str], text_content: Optional[str]):
    print(format_header("OFRENDA: Adding Memory"))
    if file_path:
        segments = extract_from_file(file_path, file_path)
        content = "\n\n".join(s["text"] for s in segments)
    elif text_content:
        content = text_content
    else:
        print("Error: Must provide either --file or --text.")
        sys.exit(1)

    mem = index_memory(title=title, content=content, author=author)
    print(f"Successfully added memory: '{mem.title}' (ID: {mem.id})")
    print(f"Chunks generated and indexed: {mem.chunk_count}")


def cmd_ask(question: str):
    print(format_header("OFRENDA: Ask the Keeper"))
    print(f"Question: \"{question}\"\n")
    print("Consulting memories with Gemma 3 4B (offline localhost)...")

    response = ask_keeper(question=question)

    print("\n--- The Keeper's Answer ---")
    print(response.answer)
    print("-" * 32)

    if response.not_mentioned:
        print("[Status] Refusal Confirmed: Fact not found in memories.")
    else:
        print(f"[Verification] Grounded & Verified: {response.verified}")
        if response.citations:
            print(f"\n[Source Citations] ({len(response.citations)} verified)")
            for idx, cit in enumerate(response.citations, 1):
                print(f"  {idx}. Chunk: [{cit.chunk_id}] (Source: {cit.source_title or 'Memory'})")
                print(f"     Quote: \"{cit.quote}\"")
                print(f"     Verified in Source Text: {cit.verified}")

    print(f"\n[Metrics] Latency: {response.latency_ms:.1f}ms | Model: {response.model} | Tokens: {response.prompt_tokens} in, {response.completion_tokens} out")


def cmd_tribute():
    print(format_header("OFRENDA: Remembrance Page Tribute"))
    print("Generating grounded tribute from memories...")

    response = generate_tribute()

    print(f"\nSubject: {response.subject_name}\n")
    for idx, p in enumerate(response.paragraphs, 1):
        print(f"{p}\n")

    print("-" * 64)
    print(f"[Citation Verification Summary]")
    print(f"Verified Sentences: {len(response.sentences)}")
    print(f"Dropped Sentences:  {response.dropped_count}")

    if response.drop_reasons:
        print("\nDrop Log:")
        for r in response.drop_reasons:
            print(f"  - {r}")

    print(f"\n[Sentence-Level Citation Audit]")
    for idx, s in enumerate(response.sentences, 1):
        cit = s.citation
        print(f"  [{idx}] \"{s.sentence}\"")
        if cit:
            print(f"      -> Chunk: [{cit.chunk_id}] (Source: {cit.source_title or 'Memory'})")
            print(f"      -> Quote: \"{cit.quote}\" (Verified: {cit.verified})")

    print(f"\n[Metrics] Latency: {response.latency_ms:.1f}ms | Model: {response.model}")


def cmd_ofrenda():
    print(format_header("OFRENDA: Altar View (Food, Song, Place, Saying)"))
    print("Scanning memories deterministically and rewording with Gemma 3 4B...")

    response = extract_ofrenda()

    categories = [
        ("Foods & Offerings", response.foods),
        ("Songs & Melodies", response.songs),
        ("Places & Walks", response.places),
        ("Sayings & Wisdom", response.sayings)
    ]

    for cat_name, cards in categories:
        print(f"\n=== {cat_name} ({len(cards)}) ===")
        for c in cards:
            print(f" * {c.title}")
            print(f"   Detail: {c.detail}")
            print(f"   Source Quote: \"{c.citation.quote}\" (Chunk: [{c.citation.chunk_id}], Verified: {c.citation.verified})")

    print(f"\n[Summary] Total Cards: {response.total_cards} | Dropped: {response.dropped_count} | Latency: {response.latency_ms:.1f}ms")


def main():
    parser = argparse.ArgumentParser(
        description="Ofrenda: Offline Remembrance Keeper CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--ask", type=str, help="Ask the Keeper a question about the memories")
    parser.add_argument("--tribute", action="store_true", help="Generate a verified 3-4 paragraph remembrance tribute")
    parser.add_argument("--ofrenda", action="store_true", help="Generate ofrenda altar cards (food, song, place, saying)")
    parser.add_argument("--init-samples", action="store_true", help="Load synthetic sample stories into the vector store")
    parser.add_argument("--list-memories", action="store_true", help="List all registered memories")
    parser.add_argument("--add-memory", action="store_true", help="Add a new memory")
    parser.add_argument("--title", type=str, help="Memory title")
    parser.add_argument("--author", type=str, help="Author/storyteller")
    parser.add_argument("--file", type=str, help="Path to .txt/.md/.docx/.pdf file")
    parser.add_argument("--text", type=str, help="Raw memory text")

    args = parser.parse_args()

    if args.init_samples:
        cmd_init_samples()
    elif args.list_memories:
        cmd_list_memories()
    elif args.add_memory:
        if not args.title:
            print("Error: --title is required when adding a memory.")
            sys.exit(1)
        cmd_add_memory(args.title, args.author, args.file, args.text)
    elif args.ask:
        cmd_ask(args.ask)
    elif args.tribute:
        cmd_tribute()
    elif args.ofrenda:
        cmd_ofrenda()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
