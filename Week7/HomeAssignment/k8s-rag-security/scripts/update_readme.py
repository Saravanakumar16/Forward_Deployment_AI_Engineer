"""Refresh the generated sections of README.md from results/*.json|txt and data/manifest.json.

Sections live between <!-- AUTO:name --> and <!-- /AUTO:name --> markers, so the
README always shows the numbers from the most recent run (and which embedder made them).
"""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from preprocess import clean_markdown  # noqa: E402

R = ROOT / "results"
STRATS = ("fixed", "recursive", "markdown", "semantic")


def dataset():
    m = json.loads((ROOT / "data/manifest.json").read_text(encoding="utf-8"))
    L = ["| ID | Access category | Permitted groups | Original file (source path) | Title | Published page |",
         "|---|---|---|---|---|---|"]
    for d in m["documents"]:
        title, _, _ = clean_markdown((ROOT / "data/k8s-docs" / d["source_path"]).read_text(encoding="utf-8"))
        gh = f"{m['repository']}/blob/{m['commit']}/{d['source_path']}"
        L.append(f"| {d['document_id']} | {d['category'].title()} | {', '.join(d['permitted_groups'])} | "
                 f"[`{d['source_path'].replace('content/en/docs/', '')}`]({gh}) | {title} | [link]({d['source_url']}) |")
    return "\n".join(L)


def chunking():
    rep = json.loads((R / "chunking_comparison.json").read_text(encoding="utf-8"))
    S = [s for s in STRATS if s in rep["strategies"]]
    st = lambda s, k: rep["strategies"][s]["structure"][k]
    rt = lambda s, k: rep["strategies"][s]["retrieval"][k]
    L = [f"_Generated with embedder: **{rep['embedder']}**. Full report: [results/chunking_comparison.md](results/chunking_comparison.md)_\n",
         "| Metric | " + " | ".join(S) + " |", "|---" * (len(S) + 1) + "|"]
    rows = [("Total chunks", "chunks", ""), ("Avg / median size (chars)", None, ""),
            ("Min / max size (chars)", None, ""), ("Avg / max tokens", None, ""),
            ("Overlap configured / measured (chars)", None, ""),
            ("Chunks starting at a heading", "pct_start_at_heading", "%"),
            ("Embedded text carries its heading", "pct_heading_context_in_embedding", "%"),
            ("Chunks spanning 2+ sections", "pct_mixes_sections", "%"),
            ("Chunks ending mid-sentence", "pct_end_mid_sentence", "%"),
            ("Chunks starting mid-sentence", "pct_start_mid_sentence", "%"),
            ("Chunks cutting a code block", "pct_split_code_block", "%")]
    for label, key, unit in rows:
        if key:
            vals = [f"{st(s, key)}{unit}" for s in S]
        elif label.startswith("Avg / median"):
            vals = [f"{st(s, 'chars_avg')} / {st(s, 'chars_median')}" for s in S]
        elif label.startswith("Min / max size"):
            vals = [f"{st(s, 'chars_min')} / {st(s, 'chars_max')}" for s in S]
        elif label.startswith("Avg / max tokens"):
            vals = [f"{st(s, 'tokens_avg')} / {st(s, 'tokens_max')}" for s in S]
        else:
            vals = [f"{st(s, 'overlap_configured')} / {st(s, 'overlap_measured_avg')}" for s in S]
        L.append(f"| {label} | " + " | ".join(vals) + " |")
    n = len(json.loads((ROOT / "data/eval_questions.json").read_text(encoding="utf-8")))
    for key in ("hit@1", "hit@5", "MRR@5", "precision@5"):
        best = max(rt(s, key) for s in S)
        L.append(f"| Retrieval {key} ({n} labelled Qs) | " +
                 " | ".join(f"**{rt(s, key)}**" if rt(s, key) == best else str(rt(s, key)) for s in S) + " |")
    L.append("\n**Boundary examples** (extracted automatically; `‖` marks the chunk boundary):\n")
    for s in S:
        for kind in ("good_boundary", "poor_boundary"):
            e = rep["strategies"][s].get(kind)
            if e:
                a, b = (x.replace("`", "'").replace("|", "/") for x in (e["end_of_chunk"][-90:], e["start_of_next"][:90]))
                L.append(f"- **{s} / {kind.split('_')[0]}** ({e['doc']}): _…{a}_ **‖** _{b}…_")
            else:
                L.append(f"- **{s} / {kind.split('_')[0]}**: no clean boundary found (every boundary scanned was cut)")
    return "\n".join(L)


def exercise_d():
    data = json.loads((R / "exercise_d.json").read_text(encoding="utf-8"))
    users = list(data[0]["by_user"])
    L = ["_Top-5 document IDs per identity (duplicates = several chunks from the same document). "
         "Full tables with headings, source links and distances: [results/exercise_d.md](results/exercise_d.md)_\n",
         "| Question | " + " | ".join(u.title() for u in users) + " |", "|---" * (len(users) + 1) + "|"]
    viol = 0
    for e in data:
        cells = []
        for u in users:
            r = e["by_user"][u]
            viol += sum(not x["authorized"] for x in r["results"])
            top = ", ".join(f"{x['document_id']} ({x['distance']:.3f})" for x in r["results"][:3])
            wh = r["withheld_relevant_docs"]
            cells.append(top + (f"<br>**withheld:** {', '.join(wh)}" if wh else ""))
        L.append(f"| {e['question']} | " + " | ".join(cells) + " |")
    L.append(f"\nTop-3 shown with cosine distance. Unauthorized results returned: **{viol}** "
             "(every result is re-checked against an independent ACL oracle).")
    return "\n".join(L)


def exercise_e():
    return "```text\n" + (R / "exercise_e_security_tests.txt").read_text(encoding="utf-8").strip() + "\n```"


def main():
    readme = ROOT / "README.md"
    text = readme.read_text(encoding="utf-8")
    for name, fn in (("dataset", dataset), ("chunking", chunking), ("exercise_d", exercise_d), ("exercise_e", exercise_e)):
        try:
            body = fn()
        except FileNotFoundError as e:
            print(f"skip {name}: {e.filename} not found"); continue
        text = re.sub(rf"(<!-- AUTO:{name} -->).*?(<!-- /AUTO:{name} -->)",
                      lambda m: m.group(1) + "\n" + body + "\n" + m.group(2), text, flags=re.S)
        print(f"updated README section: {name}")
    readme.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
