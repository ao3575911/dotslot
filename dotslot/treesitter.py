"""Optional tree-sitter comment detection (`pip install dotslot[treesitter]`).
comment_ranges(text, path) -> {line: [(start_char, end_char), ...]} of comment text, or None when tree-sitter or the
grammar for this extension is not installed (the caller then falls back to the line heuristic).
Set DOTSLOT_NO_TREESITTER=1 to force the heuristic."""
from __future__ import annotations
import importlib, os

_GRAMMARS = {   # extension -> (module, language function)
    '.py': ('tree_sitter_python', 'language'),
    '.js': ('tree_sitter_javascript', 'language'), '.mjs': ('tree_sitter_javascript', 'language'),
    '.cjs': ('tree_sitter_javascript', 'language'), '.jsx': ('tree_sitter_javascript', 'language'),
    '.ts': ('tree_sitter_typescript', 'language_typescript'), '.tsx': ('tree_sitter_typescript', 'language_tsx'),
    '.go': ('tree_sitter_go', 'language'), '.rs': ('tree_sitter_rust', 'language'),
    '.c': ('tree_sitter_c', 'language'), '.h': ('tree_sitter_c', 'language'),
    '.java': ('tree_sitter_java', 'language'),
    '.sh': ('tree_sitter_bash', 'language'), '.bash': ('tree_sitter_bash', 'language'),
}
_cache = {}

def _parser(ext):
    if ext in _cache: return _cache[ext]
    p = None
    spec = _GRAMMARS.get(ext)
    if spec:
        try:
            import tree_sitter as ts
            mod = importlib.import_module(spec[0])
            p = ts.Parser(ts.Language(getattr(mod, spec[1])()))
        except Exception:   # not installed or ABI mismatch: fall back
            p = None
    _cache[ext] = p
    return p

def available(path='x.py'):
    return not os.environ.get('DOTSLOT_NO_TREESITTER') and _parser(os.path.splitext(path)[1].lower()) is not None

def comment_ranges(text, path):
    if os.environ.get('DOTSLOT_NO_TREESITTER'): return None
    p = _parser(os.path.splitext(path or '')[1].lower())
    if p is None: return None
    blines = text.encode('utf-8').split(b'\n')
    def ch(row, col): return len(blines[row][:col].decode('utf-8', 'ignore'))
    out, stack = {}, [p.parse(text.encode('utf-8')).root_node]
    while stack:
        n = stack.pop()
        if 'comment' in n.type:
            (r0, c0), (r1, c1) = n.start_point, n.end_point
            for r in range(r0, r1 + 1):
                a = ch(r, c0) if r == r0 else 0
                b = ch(r, c1) if r == r1 else len(blines[r].decode('utf-8', 'ignore'))
                out.setdefault(r, []).append((a, b))
            continue
        stack.extend(n.children)
    return out
