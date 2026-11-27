"""Exercise A - evidence-based comparison of the four chunking strategies.

Reads the chunks that ingest.py stored (same 30 documents for every strategy) and writes
  results/chunking_comparison.md   (tables + boundary examples + recommendation evidence)
  results/chunking_comparison.json (raw numbers)

Structural metrics come from the chunk text itself. Retrieval quality is measured on
data/eval_questions.json (21 questions labelled with the document(s) that answer them).
This is an offline quality evaluation run with the admin connection over ALL chunks,
so it measures chunking, not permissions. Permission tests live in test_security.py.
"""
import json, re, statistics
from collections import defaultdict
from pathlib import Path
from common import connect, embed_query, STRATEGIES, EMBEDDER_LABEL
from chunkers import PARAMS, OVERLAP, HEADING_RE, LIST_RE

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "results"
K = 5


def ends_clean(t):
    last = t.rstrip().split("\n")[-1].strip()
    return (last.endswith((".", "!", "?", ":", ")", "`", "|", '"', "```"))
            or bool(LIST_RE.match(last)) or bool(HEADING_RE.match(last)))


def starts_clean(t):
    first = t.lstrip()[:3]
    return bool(first) and (first[0].isupper() or first[0] in "#*-|`(>[_\"0123456789" or first.startswith("**"))


def unbalanced_fence(t):
    return len(re.findall(r"^\s*```", t, flags=re.M)) % 2 == 1


def orphan_heading(t):
    """chunk ends with a heading whose body is in the next chunk"""
    lines = [l for l in t.rstrip().split("\n") if l.strip()]
    return bool(lines) and bool(HEADING_RE.match(lines[-1].strip())) and len(lines) > 1


def has_inner_heading(t):
    return any(HEADING_RE.match(l) for l in t.split("\n")[1:])


def structural_metrics(rows):
    by_doc = defaultdict(list)
    for r in rows:
        by_doc[r["document_id"]].append(r)
    overlaps = []
    for chunks in by_doc.values():
        chunks.sort(key=lambda r: r["chunk_no"])
        for a, b in zip(chunks, chunks[1:]):
            overlaps.append(max(0, a["start_char"] + a["char_count"] - b["start_char"]))
    chars = [r["char_count"] for r in rows]
    toks = [r["token_count"] for r in rows]
    n = len(rows)
    pct = lambda k: round(100 * k / n, 1)
    return {
        "chunks": n,
        "chunks_per_doc": round(n / len(by_doc), 1),
        "chars_avg": round(statistics.mean(chars)), "chars_median": round(statistics.median(chars)),
        "chars_min": min(chars), "chars_max": max(chars),
        "chars_stdev": round(statistics.pstdev(chars)),
        "tokens_avg": round(statistics.mean(toks)), "tokens_max": max(toks),
        "pct_over_512_tokens": pct(sum(t > 512 for t in toks)),
        "pct_under_100_chars": pct(sum(c < 100 for c in chars)),
        "overlap_configured": OVERLAP[rows[0]["strategy"]],
        "overlap_measured_avg": round(statistics.mean(overlaps)) if overlaps else 0,
        "pct_start_at_heading": pct(sum(r["chunk_text"].lstrip().startswith("#") for r in rows)),
        "pct_heading_context_in_embedding": pct(sum(
            r["chunk_text"].lstrip().startswith("#") or r["embed_text"] != r["chunk_text"] for r in rows)),
        "pct_mixes_sections": pct(sum(has_inner_heading(r["chunk_text"]) for r in rows)),
        "pct_orphan_heading": pct(sum(orphan_heading(r["chunk_text"]) for r in rows)),
        "pct_start_mid_sentence": pct(sum(not starts_clean(r["chunk_text"]) for r in rows)),
        "pct_end_mid_sentence": pct(sum(not ends_clean(r["chunk_text"]) for r in rows)),
        "pct_split_code_block": pct(sum(unbalanced_fence(r["chunk_text"]) for r in rows)),
    }


def retrieval_metrics(db, strategy, questions, qvecs):
    hits1 = hits5 = rr = prec = 0
    per_q = []
    for q, v in zip(questions, qvecs):
        got = [r[0] for r in db.execute(
            """SELECT document_id FROM raglab.chunks WHERE strategy=%s
               ORDER BY embedding <=> %s::vector LIMIT %s""", (strategy, v, K)).fetchall()]
        rel = set(q["relevant"])
        first = next((i for i, d in enumerate(got, 1) if d in rel), None)
        hits1 += first == 1
        hits5 += first is not None
        rr += 1 / first if first else 0
        prec += sum(d in rel for d in got) / K
        per_q.append({"q": q["q"], "top": got, "first_relevant_rank": first})
    n = len(questions)
    return {"hit@1": round(hits1 / n, 3), "hit@5": round(hits5 / n, 3), "MRR@5": round(rr / n, 3),
            "precision@5": round(prec / n, 3)}, per_q


def examples(rows, strategy):
    """One good and one poor boundary per strategy, taken from the first documents in order."""
    by_doc = defaultdict(list)
    for r in rows:
        by_doc[r["document_id"]].append(r)
    good = poor = None
    for doc in sorted(by_doc):
        cs = sorted(by_doc[doc], key=lambda r: r["chunk_no"])
        for a, b in zip(cs, cs[1:]):
            clean = ends_clean(a["chunk_text"]) and b["chunk_text"].lstrip().startswith("#") and not unbalanced_fence(a["chunk_text"])
            bad = (not ends_clean(a["chunk_text"]) and not starts_clean(b["chunk_text"])) or unbalanced_fence(a["chunk_text"]) or orphan_heading(a["chunk_text"])
            snippet = lambda: {"doc": doc, "chunk": a["chunk_no"],
                               "end_of_chunk": " ".join(a["chunk_text"][-140:].split()),
                               "start_of_next": " ".join(b["chunk_text"][:140].split()),
                               "next_heading_path": b["heading_path"]}
            if clean and good is None:
                good = snippet()
            if bad and poor is None:
                poor = snippet()
        if good and poor:
            break
    return good, poor


def main():
    OUT.mkdir(exist_ok=True)
    questions = json.loads((ROOT / "data/eval_questions.json").read_text(encoding="utf-8"))
    qvecs = [embed_query(q["q"]) for q in questions]
    report = {"embedder": EMBEDDER_LABEL, "k": K, "strategies": {}}
    with connect(admin=True) as db:
        for s in STRATEGIES:
            cur = db.execute("""SELECT document_id, strategy, chunk_no, heading_path, chunk_text, embed_text,
                                       start_char, char_count, token_count
                                FROM raglab.chunks WHERE strategy=%s""", (s,))
            cols = [c.name for c in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
            if not rows:
                print(f"skip {s}: no chunks (run ingest.py)"); continue
            m = structural_metrics(rows)
            r, per_q = retrieval_metrics(db, s, questions, qvecs)
            good, poor = examples(rows, s)
            report["strategies"][s] = {"params": PARAMS[s], "structure": m, "retrieval": r,
                                       "per_question": per_q, "good_boundary": good, "poor_boundary": poor}
            print(f"{s:9} chunks={m['chunks']:4} avg={m['chars_avg']:4} hit@5={r['hit@5']} MRR={r['MRR@5']} "
                  f"P@5={r['precision@5']} endMid={m['pct_end_mid_sentence']}% splitCode={m['pct_split_code_block']}%")
    (OUT / "chunking_comparison.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (OUT / "chunking_comparison.md").write_text(render(report, questions), encoding="utf-8")
    print(f"Wrote {OUT/'chunking_comparison.md'}")


def render(rep, questions):
    S = [s for s in STRATEGIES if s in rep["strategies"]]
    st = lambda s, k: rep["strategies"][s]["structure"][k]
    rt = lambda s, k: rep["strategies"][s]["retrieval"][k]
    L = [f"# Exercise A - Chunking comparison\n",
         f"Embedder: **{rep['embedder']}** | corpus: 30 Kubernetes docs | identical input for every strategy\n",
         "## Parameters\n", "| Strategy | Configuration |", "|---|---|"]
    L += [f"| {s} | {rep['strategies'][s]['params']} |" for s in S]
    L += ["\n## Size and overlap\n", "| Metric | " + " | ".join(S) + " |", "|---" * (len(S) + 1) + "|"]
    for key, label in [("chunks", "Total chunks"), ("chunks_per_doc", "Chunks per document"),
                       ("chars_avg", "Avg size (chars)"), ("chars_median", "Median size (chars)"),
                       ("chars_min", "Min size (chars)"), ("chars_max", "Max size (chars)"),
                       ("chars_stdev", "Std-dev size (chars)"), ("tokens_avg", "Avg tokens (embedded text)"),
                       ("tokens_max", "Max tokens"), ("pct_over_512_tokens", "% chunks > 512 tokens (truncated)"),
                       ("pct_under_100_chars", "% tiny chunks (< 100 chars)"),
                       ("overlap_configured", "Overlap configured (chars)"),
                       ("overlap_measured_avg", "Overlap measured avg (chars)")]:
        L.append(f"| {label} | " + " | ".join(str(st(s, key)) for s in S) + " |")
    L += ["\n## Heading preservation and boundary quality (lower is better unless marked +)\n",
          "| Metric | " + " | ".join(S) + " |", "|---" * (len(S) + 1) + "|"]
    for key, label in [("pct_start_at_heading", "+ % chunks starting at a heading"),
                       ("pct_heading_context_in_embedding", "+ % chunks whose embedded text carries its heading"),
                       ("pct_mixes_sections", "% chunks spanning 2+ sections"),
                       ("pct_orphan_heading", "% chunks ending in an orphan heading"),
                       ("pct_start_mid_sentence", "% chunks starting mid-sentence"),
                       ("pct_end_mid_sentence", "% chunks ending mid-sentence"),
                       ("pct_split_code_block", "% chunks cutting a code block")]:
        L.append(f"| {label} | " + " | ".join(f"{st(s, key)}%" for s in S) + " |")
    L += [f"\n## Retrieval quality ({len(questions)} labelled questions, top-{rep['k']}, all chunks)\n",
          "| Metric | " + " | ".join(S) + " |", "|---" * (len(S) + 1) + "|"]
    for key in ("hit@1", "hit@5", "MRR@5", "precision@5"):
        best = max(rt(s, key) for s in S)
        L.append(f"| {key} | " + " | ".join((f"**{rt(s, key)}**" if rt(s, key) == best else str(rt(s, key))) for s in S) + " |")
    L += ["\n### Rank of first relevant document per question (- = not in top 5)\n",
          "| Question | Expected | " + " | ".join(S) + " |", "|---" * (len(S) + 2) + "|"]
    for i, q in enumerate(questions):
        ranks = [rep["strategies"][s]["per_question"][i]["first_relevant_rank"] for s in S]
        L.append(f"| {q['q']} | {', '.join(q['relevant'])} | " + " | ".join(str(r or "-") for r in ranks) + " |")
    L.append("\n## Boundary examples (taken automatically from the data)\n")
    for s in S:
        for kind in ("good_boundary", "poor_boundary"):
            e = rep["strategies"][s][kind]
            if e:
                L.append(f"**{s} - {kind.split('_')[0]}** ({e['doc']}, after chunk {e['chunk']}):  ")
                L.append(f"> ...{e['end_of_chunk']}  \n> **‖ next chunk:** {e['start_of_next']}...\n")
    L.append("\nMetric definitions: *mid-sentence* = chunk does not start with a capital/Markdown marker, or does not "
             "end with sentence punctuation, a list item, table row or code fence; *cutting a code block* = odd "
             "number of ``` fences; *orphan heading* = chunk's last line is a heading whose body went to the next chunk.")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    main()
