"""Four chunking strategies over the same cleaned Markdown.

Every chunker returns a list of Chunk objects whose `text` is an exact substring of
the cleaned document starting at `start`, so any chunk can be traced back to its
position (and therefore its heading) in the original file.

  fixed      - fixed character windows with overlap, ignores all structure
  recursive  - LangChain-style recursive splitting on a separator hierarchy, with overlap
  markdown   - structure-aware: one section per heading, oversized sections split
               recursively, heading breadcrumb added to the text that is embedded
  semantic   - sentence/list/code units, split where the embedding distance between
               neighbouring windows spikes (Kamradt-style percentile breakpoints)
"""
from dataclasses import dataclass
import math
import re

FIXED_SIZE, FIXED_OVERLAP = 1000, 150
REC_SIZE, REC_OVERLAP = 1000, 150
REC_SEPARATORS = ["\n## ", "\n### ", "\n#### ", "\n\n", "\n", ". ", " ", ""]
MD_MAX, MD_MIN, MD_OVERLAP = 1200, 200, 100
SEM_MIN, SEM_MAX, SEM_PERCENTILE, SEM_BUFFER = 300, 1200, 85, 1

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")


@dataclass
class Chunk:
    text: str
    start: int
    embed_text: str = ""     # what is sent to the embedding model (defaults to text)
    heading_path: str = ""   # filled in by attach_headings()


def _mk(doc, start, end):
    """Chunk for doc[start:end] with surrounding whitespace trimmed (offsets stay exact)."""
    seg = doc[start:end]
    lead = len(seg) - len(seg.lstrip())
    text = seg.strip()
    return Chunk(text, start + lead) if text else None


# --------------------------------------------------------------------------- headings
def heading_spans(doc):
    """[(offset, level, title)] for every Markdown heading outside fenced code."""
    out, pos, in_fence = [], 0, False
    for line in doc.splitlines(keepends=True):
        if FENCE_RE.match(line):
            in_fence = not in_fence
        elif not in_fence:
            m = HEADING_RE.match(line.rstrip("\n"))
            if m:
                out.append((pos, len(m.group(1)), m.group(2)))
        pos += len(line)
    return out


def path_at(spans, offset, title):
    """Heading breadcrumb in force at `offset` (title > H2 > H3 ...)."""
    stack = []
    for pos, level, name in spans:
        if pos > offset:
            break
        stack = [s for s in stack if s[0] < level] + [(level, name)]
    return " > ".join([title] + [n for _, n in stack if n != title])


def attach_headings(chunks, doc, title):
    spans = heading_spans(doc)
    for c in chunks:
        c.heading_path = path_at(spans, c.start, title)  # heading in force where the chunk begins
        if not c.embed_text:
            c.embed_text = c.text
    return chunks


# --------------------------------------------------------------------------- 1. fixed
def fixed_chunks(doc, size=FIXED_SIZE, overlap=FIXED_OVERLAP):
    out, step = [], size - overlap
    for s in range(0, len(doc), step):
        c = _mk(doc, s, min(s + size, len(doc)))
        if c:
            out.append(c)
        if s + size >= len(doc):
            break
    return out


# --------------------------------------------------------------------------- 2. recursive
def _split_spans(doc, start, end, seps, size):
    """Split doc[start:end] into contiguous (s, e) pieces, each <= size where possible."""
    if end - start <= size:
        return [(start, end)]
    text = doc[start:end]
    for i, sep in enumerate(seps):
        if sep == "":
            return [(s, min(s + size, end)) for s in range(start, end, size)]
        if sep in text:
            cuts, idx = [], text.find(sep)
            while idx != -1:
                # sentence separators stay with the left piece, structural ones start the right piece
                cut = idx + len(sep) if sep == ". " else idx
                if 0 < cut < len(text):
                    cuts.append(cut)
                idx = text.find(sep, idx + 1)
            bounds = [0] + cuts + [len(text)]
            pieces = []
            for a, b in zip(bounds, bounds[1:]):
                if b - a > size:
                    pieces += _split_spans(doc, start + a, start + b, seps[i + 1:], size)
                elif b > a:
                    pieces.append((start + a, start + b))
            return pieces
    return [(start, end)]


def _merge_spans(pieces, size, overlap):
    """Greedy merge of contiguous pieces into windows <= size, carrying `overlap` chars of tail pieces."""
    windows, cur = [], []
    for p in pieces:
        if cur and p[1] - cur[0][0] > size:
            windows.append((cur[0][0], cur[-1][1]))
            keep = []
            for q in reversed(cur):  # tail pieces totalling <= overlap
                if cur[-1][1] - q[0] > overlap:
                    break
                keep.insert(0, q)
            cur = keep if keep and p[1] - keep[0][0] <= size else []
        cur.append(p)
    if cur:
        windows.append((cur[0][0], cur[-1][1]))
    return windows


def recursive_chunks(doc, size=REC_SIZE, overlap=REC_OVERLAP, seps=REC_SEPARATORS, base=0, end=None):
    end = len(doc) if end is None else end
    spans = _merge_spans(_split_spans(doc, base, end, seps, size), size, overlap)
    return [c for c in (_mk(doc, s, e) for s, e in spans) if c]


# --------------------------------------------------------------------------- 3. markdown
def markdown_chunks(doc, title, max_chars=MD_MAX, min_chars=MD_MIN, overlap=MD_OVERLAP):
    spans = heading_spans(doc)
    starts = [0] + [p for p, _, _ in spans if p > 0]
    sections = [(s, e) for s, e in zip(starts, starts[1:] + [len(doc)]) if doc[s:e].strip()]
    # merge heading-only / tiny sections forward so a heading never stands alone
    merged, carry = [], None
    for s, e in sections:
        s = carry if carry is not None else s
        if e - s < min_chars and (s, e) != (sections[-1][0], sections[-1][1]):
            carry = s
            continue
        merged.append((s, e)); carry = None
    if carry is not None:
        merged.append((carry, len(doc)))
    out = []
    for s, e in merged:
        crumb = path_at(spans, s, title)
        if e - s <= max_chars:
            pieces = [c for c in [_mk(doc, s, e)] if c]
        else:
            pieces = recursive_chunks(doc, max_chars, overlap, ["\n\n", "\n", ". ", " ", ""], s, e)
        for c in pieces:
            c.heading_path = crumb
            c.embed_text = f"{crumb}\n\n{c.text}"
            out.append(c)
    return out


# --------------------------------------------------------------------------- 4. semantic
SENT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z`*\[(\"])")
LIST_RE = re.compile(r"^\s*(?:[*+-]|\d+\.)\s+")


def semantic_units(doc):
    """Sentences, list items, tables and code blocks as (start, end) units.
    A heading is glued to the unit that follows it."""
    blocks, pos, cur, in_fence = [], 0, None, False
    for line in doc.splitlines(keepends=True):
        if FENCE_RE.match(line):
            in_fence = not in_fence
        blank = not line.strip() and not in_fence
        if blank:
            if cur is not None:
                blocks.append(cur); cur = None
        elif cur is None:
            cur = [pos, pos + len(line)]
        else:
            cur[1] = pos + len(line)
        pos += len(line)
    if cur:
        blocks.append(cur)

    units = []
    for s, e in blocks:
        block = doc[s:e]
        first = block.lstrip()
        if first.startswith(("```", "~~~", "|")) or HEADING_RE.match(first.split("\n")[0]):
            units.append([s, e]); continue
        lines = block.splitlines(keepends=True)
        if LIST_RE.match(lines[0]):
            off = s
            for ln in lines:
                if LIST_RE.match(ln) or not units or units[-1][1] != off:
                    units.append([off, off + len(ln)])
                else:
                    units[-1][1] = off + len(ln)
                off += len(ln)
            continue
        cuts = [0] + [m.end() for m in SENT_RE.finditer(block)] + [len(block)]
        units += [[s + a, s + b] for a, b in zip(cuts, cuts[1:]) if block[a:b].strip()]
    # glue headings forward
    glued, pending = [], None
    for u in units:
        if HEADING_RE.match(doc[u[0]:u[1]].strip().split("\n")[0]) and "\n" not in doc[u[0]:u[1]].strip():
            pending = u[0] if pending is None else pending
            continue
        if pending is not None:
            u = [pending, u[1]]; pending = None
        glued.append(u)
    if pending is not None:
        glued.append([pending, len(doc)])
    return [tuple(u) for u in glued]


def _cos_dist(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)); nb = math.sqrt(sum(y * y for y in b))
    return 0.0 if na * nb == 0 else 1 - dot / (na * nb)  # no signal -> no breakpoint


def _percentile(xs, p):
    xs = sorted(xs)
    if not xs:
        return 1.0
    k = (len(xs) - 1) * p / 100
    f, c = math.floor(k), math.ceil(k)
    return xs[f] + (xs[c] - xs[f]) * (k - f)


def semantic_chunks(doc, embed_fn, min_chars=SEM_MIN, max_chars=SEM_MAX,
                    percentile=SEM_PERCENTILE, buffer=SEM_BUFFER):
    units = semantic_units(doc)
    if not units:
        return []
    windows = [doc[units[max(0, i - buffer)][0]:units[min(len(units) - 1, i + buffer)][1]]
               for i in range(len(units))]
    vecs = embed_fn(windows)
    dists = [_cos_dist(vecs[i], vecs[i + 1]) for i in range(len(units) - 1)]
    threshold = _percentile(dists, percentile)
    out, cs = [], units[0][0]
    for i, (us, ue) in enumerate(units):
        if ue - us > max_chars:  # a single huge unit (e.g. a long code block): hard split
            if us > cs:
                out.append((cs, us))
            out += [(p, min(p + max_chars, ue)) for p in range(us, ue, max_chars)]
            cs = ue
            continue
        length = ue - cs
        last = i == len(units) - 1
        nxt = 0 if last else units[i + 1][1] - units[i + 1][0]
        semantic_break = not last and dists[i] > threshold and length >= min_chars
        size_break = not last and length + nxt > max_chars
        if semantic_break or size_break or last:
            out.append((cs, ue)); cs = units[i + 1][0] if not last else ue
    return [c for c in (_mk(doc, s, e) for s, e in out) if c]


# --------------------------------------------------------------------------- dispatcher
def chunk_document(strategy, doc, title, embed_fn=None):
    if strategy == "fixed":
        chunks = fixed_chunks(doc)
    elif strategy == "recursive":
        chunks = recursive_chunks(doc)
    elif strategy == "markdown":
        chunks = markdown_chunks(doc, title)
    elif strategy == "semantic":
        chunks = semantic_chunks(doc, embed_fn)
    else:
        raise ValueError(strategy)
    return attach_headings(chunks, doc, title) if strategy != "markdown" else chunks


PARAMS = {
    "fixed": f"{FIXED_SIZE} chars, {FIXED_OVERLAP} overlap",
    "recursive": f"{REC_SIZE} chars, {REC_OVERLAP} overlap, separators ## > ### > #### > blank line > line > sentence > word",
    "markdown": f"split at every heading; sections > {MD_MAX} chars split recursively ({MD_OVERLAP} overlap); sections < {MD_MIN} chars merged forward; breadcrumb prepended for embedding",
    "semantic": f"sentence/list/code units, window +/-{SEM_BUFFER}, break at > p{SEM_PERCENTILE} cosine distance, min {SEM_MIN} / max {SEM_MAX} chars",
}
OVERLAP = {"fixed": FIXED_OVERLAP, "recursive": REC_OVERLAP, "markdown": MD_OVERLAP, "semantic": 0}
