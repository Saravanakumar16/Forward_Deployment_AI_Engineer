"""Turn Kubernetes (Hugo) Markdown into clean Markdown suitable for chunking.

* front matter is parsed for title/description and removed from the body
* Hugo shortcodes ({{< ... >}} / {{% ... %}}) are rendered to plain text equivalents
* HTML comments are removed; Markdown links keep their visible text only
Headings, lists, tables and fenced code blocks are preserved, because the
structure-aware chunker relies on them.
"""
import re
import yaml

FRONT_MATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)
SHORTCODE = re.compile(r"\{\{[<%]\s*(/?)([\w-]+)(.*?)\s*[>%]\}\}", re.S)
ATTR = re.compile(r'(\w+)="([^"]*)"')
HEADING_NAMES = {"whatsnext": "What's next", "prerequisites": "Before you begin",
                 "objectives": "Objectives", "cleanup": "Clean up", "synopsis": "Synopsis",
                 "options": "Options", "seealso": "See also"}


def _render(m):
    closing, name, rest = m.group(1), m.group(2), m.group(3)
    attrs = dict(ATTR.findall(rest))
    positional = re.findall(r'"([^"]*)"', rest)
    if name == "glossary_tooltip":
        return attrs.get("text") or attrs.get("term_id", "").replace("-", " ")
    if name in ("note", "caution", "warning"):
        return "" if closing else f"**{name.capitalize()}:** "
    if name == "heading":
        key = positional[0] if positional else ""
        return HEADING_NAMES.get(key, key.replace("-", " ").title())
    if name == "feature-state":
        state = attrs.get("state", "")
        ver = attrs.get("for_k8s_version", "")
        gate = attrs.get("feature_gate_name", "")
        bits = " ".join(x for x in (state, ver) if x) or gate
        return f"(Feature state: {bits})" if bits else ""
    if name == "code_sample":
        return f"`[code sample: {attrs.get('file', '')}]`"
    if name == "highlight":
        return "```" if closing else "```" + (rest.split()[0] if rest.split() else "")
    if name == "mermaid":
        return "```" if closing else "```mermaid"
    if name == "tab":
        return "" if closing else f"**{attrs.get('name', '')}**\n"
    if name == "figure":
        return f"[Figure: {attrs.get('caption') or attrs.get('alt') or attrs.get('src', '')}]"
    if name == "glossary_definition":
        return f"{attrs.get('prepend', '')} {attrs.get('term_id', '').replace('-', ' ')}".strip()
    if name in ("skew", "param"):
        return f"<{positional[0] if positional else name}>"
    if name == "api-reference":
        return attrs.get("text") or attrs.get("page", "").split("/")[-1]
    return ""  # tabs, table, thirdparty-content, comment, alert, example, ...


def clean_markdown(raw):
    meta = {}
    m = FRONT_MATTER.match(raw)
    if m:
        meta = yaml.safe_load(m.group(1)) or {}
        raw = raw[m.end():]
    text = re.sub(r"<!--.*?-->", "", raw, flags=re.S)
    text = SHORTCODE.sub(_render, text)
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", text)      # [text](link) -> text
    text = re.sub(r"\[([^\]]+)\]\[[^\]]*\]", r"\1", text)        # [text][ref]  -> text
    text = re.sub(r"^\[[^\]]+\]:\s*\S+.*$", "", text, flags=re.M)  # ref definitions
    text = re.sub(r"^(#{1,6} .*?)\s*\{#[^}]*\}\s*$", r"\1", text, flags=re.M)  # heading anchors
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"
    title = str(meta.get("title", "")).strip()
    desc = " ".join(str(meta.get("description", "")).split())
    return title, desc, text
