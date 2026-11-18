"""Restricted LaTeX math markup validator and deterministic offline formatters.

Implements Proposal Section 5.4 (WP-2) to validate, normalize, and format
calculation equations for CalculationResult.trace without treating arbitrary
strings as trusted HTML or introducing external network dependencies.
"""

from dataclasses import dataclass
import html
import re
from typing import Dict, List, Optional, Sequence, Tuple, Union


# Explicit allowlist of 0-argument math commands and their Unicode representations.
SYMBOL_UNICODE_MAP: Dict[str, str] = {
    # Operators & relations
    "cdot": "·",
    "times": "×",
    "leq": "≤",
    "le": "≤",
    "geq": "≥",
    "ge": "≥",
    "neq": "≠",
    "ne": "≠",
    "pm": "±",
    "mp": "∓",
    "approx": "≈",
    "sim": "~",
    "min": "min",
    "max": "max",
    "sum": "∑",
    "sin": "sin",
    "cos": "cos",
    "tan": "tan",
    "log": "log",
    "ln": "ln",
    # Greek & engineering symbols
    "phi": "φ",
    "Phi": "Φ",
    "Omega": "Ω",
    "omega": "ω",
    "Delta": "Δ",
    "delta": "δ",
    "theta": "θ",
    "Theta": "Θ",
    "lambda": "λ",
    "Lambda": "Λ",
    "alpha": "α",
    "beta": "β",
    "gamma": "γ",
    "Gamma": "Γ",
    "psi": "ψ",
    "Psi": "Ψ",
    "mu": "μ",
    "rho": "ρ",
    "sigma": "σ",
    "Sigma": "Σ",
    "tau": "τ",
    "pi": "π",
    "epsilon": "ε",
    "varepsilon": "ε",
    "eta": "η",
    "ell": "\u2113",  # Literal 'ℓ' (never '&ell;')
    "parallel": "∥",
    "perp": "⊥",
    "prime": "′",
    "circ": "°",
}

WORD_FUNCTION_COMMANDS = frozenset({"min", "max", "sin", "cos", "tan", "log", "ln"})
STRUCTURAL_COMMANDS = frozenset({"frac", "sqrt", "text", "mathrm", "left", "right"})
ALLOWED_MATH_COMMANDS = frozenset(SYMBOL_UNICODE_MAP.keys()) | STRUCTURAL_COMMANDS

FORBIDDEN_LATEX_COMMANDS = frozenset({
    "input",
    "include",
    "write",
    "def",
    "gdef",
    "edef",
    "xdef",
    "newcommand",
    "renewcommand",
    "providecommand",
    "csname",
    "expandafter",
    "catcode",
    "url",
    "href",
    "begin",
    "end",
    "usepackage",
    "documentclass",
    "openout",
    "openin",
    "read",
    "immediate",
    "special",
    "htmlData",
    "htmlClass",
    "htmlStyle",
    "htmlId",
    "style",
    "class",
    "unicode",
})

ALLOWED_LEFT_DELIMITERS = frozenset({"(", "[", "|", "."})
ALLOWED_RIGHT_DELIMITERS = frozenset({")", "]", "|", "."})

_ALLOWED_PLAIN_PUNCTUATION = frozenset(" +-*/=<>!()[]|,.:;'\"")
_SCRIPTABLE_PUNCTUATION = frozenset(")]|.'\"")
_SINGLE_SCRIPT_OPERAND_CHARS = frozenset("+-*'")

_HTML_ENTITY_RE = re.compile(r"&(?:#\d+|#x[0-9A-Fa-f]+|[A-Za-z][A-Za-z0-9]*);")
_HTML_TAG_RE = re.compile(
    r"(?:"
    r"</?[A-Za-z][A-Za-z0-9:-]*\s*/?>"
    r"|</?[A-Za-z][A-Za-z0-9:-]*(?:\s+|/)[^>]*=\s*[^>]*>"
    r"|<!(?:--[\s\S]*?--|[^>]*?)>"
    r"|<\?[^>]*?>"
    r"|<\s*/?\s*(?:script|style|iframe|object|embed|svg|img|div|span|body|html|head|link|meta|form|input|button|a|p|h[1-6]|table|tr|td|th|ul|ol|li)\b"
    r")",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Internal AST Nodes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class _TextRun:
    text: str


@dataclass(frozen=True)
class _Symbol:
    name: str


@dataclass(frozen=True)
class _TextBox:
    kind: str
    content: str


@dataclass(frozen=True)
class _MathRm:
    children: Tuple["_MathNode", ...]


@dataclass(frozen=True)
class _Group:
    children: Tuple["_MathNode", ...]


@dataclass(frozen=True)
class _Frac:
    numerator: Tuple["_MathNode", ...]
    denominator: Tuple["_MathNode", ...]


@dataclass(frozen=True)
class _Sqrt:
    radicand: Tuple["_MathNode", ...]
    index: Optional[Tuple["_MathNode", ...]] = None


@dataclass(frozen=True)
class _Delimited:
    left: str
    body: Tuple["_MathNode", ...]
    right: str


@dataclass(frozen=True)
class _Script:
    base: "_MathNode"
    sub: Optional[Tuple["_MathNode", ...]] = None
    sup: Optional[Tuple["_MathNode", ...]] = None


_MathNode = Union[
    _TextRun,
    _Symbol,
    _TextBox,
    _MathRm,
    _Group,
    _Frac,
    _Sqrt,
    _Delimited,
    _Script,
]


# ---------------------------------------------------------------------------
# Pre-checks & Parser
# ---------------------------------------------------------------------------

def _precheck_and_normalize(expr: str) -> str:
    if not isinstance(expr, str):
        raise ValueError(f"Math markup expression must be a string, got {type(expr).__name__}.")

    for ch in expr:
        code = ord(ch)
        if code < 32 and ch not in "\t\n\r":
            raise ValueError("Control characters are not allowed in math markup.")

    normalized = re.sub(r"\s+", " ", expr.strip())
    if not normalized:
        raise ValueError("Math markup expression cannot be empty.")

    if "$" in normalized:
        raise ValueError("Math delimiters ('$' or '$$') are not allowed in restricted math markup.")

    if _HTML_TAG_RE.search(normalized):
        raise ValueError("HTML/XML tags are not allowed in restricted math markup.")

    if _HTML_ENTITY_RE.search(normalized):
        raise ValueError(
            "Raw HTML entities (e.g., '&ell;', '&times;') are not allowed; use restricted LaTeX commands."
        )

    for ch in normalized:
        code = ord(ch)
        if code > 127:
            raise ValueError(
                f"Non-ASCII character '{ch}' (U+{code:04X}) is not allowed; use restricted LaTeX commands."
            )
        if ch in ("&", "%", "#", "~", "@", "`"):
            raise ValueError(f"Unsupported character '{ch}' is not allowed in restricted math markup.")

    return normalized


class _MathParser:
    """Recursive-descent parser and validator for the restricted LaTeX subset."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.n = len(text)
        self.pos = 0

    def parse(self) -> Tuple[_MathNode, ...]:
        nodes = self._parse_sequence(stop_on_brace=False, stop_on_right=False)
        if self.pos < self.n:
            ch = self.text[self.pos]
            if ch == "}":
                raise ValueError("Unbalanced braces: unexpected '}' with no matching '{'.")
            raise ValueError(f"Unexpected trailing token at position {self.pos}: '{self.text[self.pos:]}'.")
        return nodes

    def _skip_spaces(self) -> None:
        while self.pos < self.n and self.text[self.pos] == " ":
            self.pos += 1

    def _peek_command_name(self) -> Optional[str]:
        if self.pos >= self.n or self.text[self.pos] != "\\":
            return None
        j = self.pos + 1
        while j < self.n and self.text[j].isalpha():
            j += 1
        if j == self.pos + 1:
            return ""
        return self.text[self.pos + 1:j]

    def _consume_command_name(self) -> str:
        assert self.text[self.pos] == "\\"
        self.pos += 1
        if self.pos >= self.n:
            raise ValueError("Trailing backslash '\\' is not allowed in math markup.")
        if not self.text[self.pos].isalpha():
            bad = self.text[self.pos]
            raise ValueError(f"Unsupported LaTeX escape '\\{bad}' in restricted math markup.")
        start = self.pos
        while self.pos < self.n and self.text[self.pos].isalpha():
            self.pos += 1
        cmd = self.text[start:self.pos]
        if cmd in FORBIDDEN_LATEX_COMMANDS:
            raise ValueError(f"Forbidden LaTeX command '\\{cmd}' is not allowed in restricted math markup.")
        if cmd not in ALLOWED_MATH_COMMANDS:
            raise ValueError(f"Unsupported LaTeX command '\\{cmd}' in restricted math markup.")
        return cmd

    def _parse_braced_group(self, context: str, allow_empty: bool = False) -> Tuple[_MathNode, ...]:
        self._skip_spaces()
        if self.pos >= self.n or self.text[self.pos] != "{":
            raise ValueError(f"Expected '{{...}}' argument for {context}.")
        self.pos += 1
        children = self._parse_sequence(stop_on_brace=True, stop_on_right=False)
        if self.pos >= self.n or self.text[self.pos] != "}":
            raise ValueError(f"Unbalanced braces: missing '}}' for {context}.")
        self.pos += 1
        if not allow_empty and not _has_visible_content(children):
            raise ValueError(f"Empty argument '{{}}' is not allowed in {context}.")
        return children

    def _parse_text_box(self, kind: str) -> _TextBox:
        self._skip_spaces()
        if self.pos >= self.n or self.text[self.pos] != "{":
            raise ValueError(f"Expected '{{...}}' argument for '\\{kind}'.")
        self.pos += 1
        depth = 1
        chars: List[str] = []
        while self.pos < self.n:
            ch = self.text[self.pos]
            if ch == "\\":
                raise ValueError(f"LaTeX commands are not allowed inside '\\{kind}{{...}}'.")
            if ch == "{":
                depth += 1
                chars.append(ch)
                self.pos += 1
            elif ch == "}":
                depth -= 1
                self.pos += 1
                if depth == 0:
                    content = "".join(chars).strip()
                    if not content:
                        raise ValueError(f"Empty argument '{{}}' is not allowed in '\\{kind}'.")
                    return _TextBox(kind=kind, content=content)
                chars.append(ch)
            else:
                chars.append(ch)
                self.pos += 1
        raise ValueError(f"Unbalanced braces: unclosed '{{\\{kind}}}' group.")

    def _parse_bracket_group(self, context: str) -> Tuple[_MathNode, ...]:
        assert self.text[self.pos] == "["
        self.pos += 1
        chars_start = self.pos
        # Parse inner nodes until matching ']' at bracket depth 0
        inner: List[_MathNode] = []
        while self.pos < self.n:
            ch = self.text[self.pos]
            if ch == "]":
                self.pos += 1
                nodes = tuple(inner)
                if not _has_visible_content(nodes):
                    raise ValueError(f"Empty optional argument '[]' in {context}.")
                return nodes
            if ch == "}" or ch == "{":
                raise ValueError(f"Unexpected brace inside optional '[...]' argument of {context}.")
            if ch == "[":
                raise ValueError(f"Nested '[' is not allowed inside optional argument of {context}.")
            self._parse_next_into(inner)
        raise ValueError(f"Unclosed '[' at position {chars_start - 1} in {context}.")

    def _parse_script_operand(self, op_char: str) -> Tuple[_MathNode, ...]:
        self._skip_spaces()
        if self.pos >= self.n:
            raise ValueError(f"Dangling '{op_char}' at end of math expression.")
        ch = self.text[self.pos]
        if ch == "{":
            return self._parse_braced_group(f"'{op_char}'", allow_empty=False)
        if ch == "\\":
            cmd = self._consume_command_name()
            if cmd not in SYMBOL_UNICODE_MAP:
                raise ValueError(
                    f"Command '\\{cmd}' after '{op_char}' must be wrapped in braces '{{...}}'."
                )
            return (_Symbol(cmd),)
        if ch.isalnum() or ch in _SINGLE_SCRIPT_OPERAND_CHARS:
            self.pos += 1
            return (_TextRun(ch),)
        raise ValueError(f"Invalid token '{ch}' following '{op_char}'.")

    def _parse_next_into(self, items: List[_MathNode]) -> None:
        ch = self.text[self.pos]

        if ch == "{":
            self.pos += 1
            children = self._parse_sequence(stop_on_brace=True, stop_on_right=False)
            if self.pos >= self.n or self.text[self.pos] != "}":
                raise ValueError("Unbalanced braces: unclosed '{'.")
            self.pos += 1
            items.append(_Group(children))
            return

        if ch in ("_", "^"):
            op = ch
            self.pos += 1
            # Attach to preceding scriptable item (ignoring separating whitespace)
            had_trailing_space = bool(items and isinstance(items[-1], _TextRun) and items[-1].text == " ")
            target_idx = len(items) - 2 if had_trailing_space else len(items) - 1
            if target_idx < 0 or not _is_scriptable_node(items[target_idx]):
                raise ValueError(f"Missing base expression before '{op}'.")
            if had_trailing_space:
                items.pop()
            base_node = items.pop()
            operand = self._parse_script_operand(op)

            if isinstance(base_node, _Script):
                if op == "_" and base_node.sub is not None:
                    raise ValueError("Double subscript '_' requires grouping braces '{...}'.")
                if op == "^" and base_node.sup is not None:
                    raise ValueError("Double superscript '^' requires grouping braces '{...}'.")
                if op == "_":
                    items.append(_Script(base=base_node.base, sub=operand, sup=base_node.sup))
                else:
                    items.append(_Script(base=base_node.base, sub=base_node.sub, sup=operand))
            else:
                if op == "_":
                    items.append(_Script(base=base_node, sub=operand, sup=None))
                else:
                    items.append(_Script(base=base_node, sub=None, sup=operand))
            return

        if ch == "\\":
            cmd = self._consume_command_name()
            if cmd == "frac":
                num = self._parse_braced_group("'\\frac' numerator", allow_empty=False)
                den = self._parse_braced_group("'\\frac' denominator", allow_empty=False)
                items.append(_Frac(numerator=num, denominator=den))
            elif cmd == "sqrt":
                self._skip_spaces()
                idx_nodes: Optional[Tuple[_MathNode, ...]] = None
                if self.pos < self.n and self.text[self.pos] == "[":
                    idx_nodes = self._parse_bracket_group("'\\sqrt'")
                rad = self._parse_braced_group("'\\sqrt'", allow_empty=False)
                items.append(_Sqrt(radicand=rad, index=idx_nodes))
            elif cmd == "text":
                items.append(self._parse_text_box(cmd))
            elif cmd == "mathrm":
                items.append(_MathRm(self._parse_braced_group("'\\mathrm'", allow_empty=False)))
            elif cmd == "left":
                self._skip_spaces()
                if self.pos >= self.n or self.text[self.pos] not in ALLOWED_LEFT_DELIMITERS:
                    found = self.text[self.pos] if self.pos < self.n else "<EOF>"
                    raise ValueError(
                        f"Invalid delimiter '{found}' after '\\left'; expected one of (, [, |, or ."
                    )
                left_delim = self.text[self.pos]
                self.pos += 1
                body = self._parse_sequence(stop_on_brace=False, stop_on_right=True)
                peek = self._peek_command_name()
                if peek != "right":
                    raise ValueError("Unbalanced delimiter: '\\left' is missing matching '\\right'.")
                self._consume_command_name()  # consumes 'right'
                self._skip_spaces()
                if self.pos >= self.n or self.text[self.pos] not in ALLOWED_RIGHT_DELIMITERS:
                    found = self.text[self.pos] if self.pos < self.n else "<EOF>"
                    raise ValueError(
                        f"Invalid delimiter '{found}' after '\\right'; expected one of ), ], |, or ."
                    )
                right_delim = self.text[self.pos]
                self.pos += 1
                items.append(_Delimited(left=left_delim, body=body, right=right_delim))
            elif cmd == "right":
                raise ValueError("Unbalanced delimiter: unexpected '\\right' without matching '\\left'.")
            else:
                items.append(_Symbol(cmd))
            return

        if ch.isalnum() or ch in _ALLOWED_PLAIN_PUNCTUATION:
            self.pos += 1
            items.append(_TextRun(ch))
            return

        raise ValueError(f"Unsupported character '{ch}' in restricted math markup.")

    def _parse_sequence(self, stop_on_brace: bool, stop_on_right: bool) -> Tuple[_MathNode, ...]:
        items: List[_MathNode] = []
        while self.pos < self.n:
            ch = self.text[self.pos]
            if ch == "}":
                if stop_on_right:
                    raise ValueError("Unbalanced delimiter: '\\left' missing matching '\\right' before '}'.")
                if stop_on_brace:
                    break
                raise ValueError("Unbalanced braces: unexpected '}' with no matching '{'.")
            if ch == "\\":
                peek = self._peek_command_name()
                if peek == "right":
                    if stop_on_right:
                        break
                    raise ValueError("Unbalanced delimiter: unexpected '\\right' without matching '\\left'.")
            self._parse_next_into(items)
        return tuple(items)


def _has_visible_content(nodes: Sequence[_MathNode]) -> bool:
    for node in nodes:
        if isinstance(node, _TextRun):
            if node.text.strip():
                return True
        elif isinstance(node, _Group):
            if _has_visible_content(node.children):
                return True
        else:
            return True
    return False


def _is_scriptable_node(node: _MathNode) -> bool:
    if isinstance(node, _TextRun):
        return node.text.isalnum() or node.text in _SCRIPTABLE_PUNCTUATION
    return isinstance(node, (_Symbol, _TextBox, _MathRm, _Group, _Frac, _Sqrt, _Delimited, _Script))


def _parse_math_markup(expr: str) -> Tuple[str, Tuple[_MathNode, ...]]:
    normalized = _precheck_and_normalize(expr)
    ast = _MathParser(normalized).parse()
    return normalized, ast


# ---------------------------------------------------------------------------
# Rendering Helpers (Plain Text & Rich HTML)
# ---------------------------------------------------------------------------

def _trim_outer_space_nodes(nodes: Sequence[_MathNode]) -> List[_MathNode]:
    start = 0
    end = len(nodes)
    while start < end and isinstance(nodes[start], _TextRun) and nodes[start].text == " ":
        start += 1
    while end > start and isinstance(nodes[end - 1], _TextRun) and nodes[end - 1].text == " ":
        end -= 1
    return list(nodes[start:end])


def _is_simple_fraction_part(nodes: Sequence[_MathNode]) -> bool:
    trimmed = _trim_outer_space_nodes(nodes)
    if not trimmed:
        return True
    for node in trimmed:
        if isinstance(node, _TextRun):
            if node.text == " " or node.text in "+-*/=<>!":
                return False
        elif isinstance(node, _Symbol):
            if node.name in ("cdot", "times", "leq", "le", "geq", "ge", "neq", "ne", "pm", "mp", "approx"):
                return False
        elif isinstance(node, _Group):
            if not _is_simple_fraction_part(node.children):
                return False
        elif isinstance(node, (_Frac, _Delimited)):
            return False
    return True


def _is_simple_plain_script(nodes: Sequence[_MathNode]) -> bool:
    trimmed = _trim_outer_space_nodes(nodes)
    for node in trimmed:
        if isinstance(node, _TextRun):
            if node.text == " " or node.text in "+-*/=<>!,":
                return False
        elif isinstance(node, _Symbol):
            if node.name in ("cdot", "times", "leq", "le", "geq", "ge", "neq", "ne", "pm", "mp"):
                return False
        elif isinstance(node, (_Frac, _Delimited)):
            return False
    return True


def _is_single_symbol(nodes: Optional[Sequence[_MathNode]], name: str) -> bool:
    if not nodes:
        return False
    trimmed = _trim_outer_space_nodes(nodes)
    return len(trimmed) == 1 and isinstance(trimmed[0], _Symbol) and trimmed[0].name == name


def _needs_space_after_word_cmd(prev: _MathNode, curr: _MathNode) -> bool:
    if not isinstance(prev, _Symbol) or prev.name not in WORD_FUNCTION_COMMANDS:
        return False
    if isinstance(curr, _Symbol):
        return curr.name not in ("prime", "circ")
    if isinstance(curr, _TextRun):
        return curr.text.isalnum()
    return isinstance(curr, (_Script, _TextBox))


def _render_sequence(nodes: Sequence[_MathNode], *, rich_html: bool) -> str:
    parts: List[str] = []
    prev_node: Optional[_MathNode] = None
    for node in nodes:
        if prev_node is not None and _needs_space_after_word_cmd(prev_node, node):
            parts.append(" ")
        parts.append(_render_node(node, rich_html=rich_html))
        prev_node = node
    return "".join(parts)


def _render_node(node: _MathNode, *, rich_html: bool) -> str:
    if isinstance(node, _TextRun):
        return html.escape(node.text, quote=False) if rich_html else node.text

    if isinstance(node, _Symbol):
        sym = SYMBOL_UNICODE_MAP[node.name]
        return html.escape(sym, quote=False) if rich_html else sym

    if isinstance(node, _TextBox):
        return html.escape(node.content, quote=False) if rich_html else node.content

    if isinstance(node, _MathRm):
        return _render_sequence(node.children, rich_html=rich_html)

    if isinstance(node, _Group):
        return _render_sequence(node.children, rich_html=rich_html)

    if isinstance(node, _Frac):
        num_nodes = _trim_outer_space_nodes(node.numerator)
        den_nodes = _trim_outer_space_nodes(node.denominator)
        num_str = _render_sequence(num_nodes, rich_html=rich_html)
        den_str = _render_sequence(den_nodes, rich_html=rich_html)
        if not _is_simple_fraction_part(num_nodes):
            num_str = f"({num_str})"
        if not _is_simple_fraction_part(den_nodes):
            den_str = f"({den_str})"
        return f"{num_str} / {den_str}"

    if isinstance(node, _Sqrt):
        rad_str = _render_sequence(_trim_outer_space_nodes(node.radicand), rich_html=rich_html)
        if node.index is not None:
            idx_str = _render_sequence(_trim_outer_space_nodes(node.index), rich_html=rich_html)
            if rich_html:
                return f"({rad_str})<sup>1/{idx_str}</sup>"
            return f"({rad_str})^(1/{idx_str})"
        return f"√({rad_str})"

    if isinstance(node, _Delimited):
        left_s = "" if node.left == "." else node.left
        right_s = "" if node.right == "." else node.right
        body_str = _render_sequence(_trim_outer_space_nodes(node.body), rich_html=rich_html)
        return f"{left_s}{body_str}{right_s}"

    if isinstance(node, _Script):
        out = _render_node(node.base, rich_html=rich_html)
        if node.sub is not None:
            sub_nodes = _trim_outer_space_nodes(node.sub)
            sub_str = _render_sequence(sub_nodes, rich_html=rich_html)
            if rich_html:
                out += f"<sub>{sub_str}</sub>"
            else:
                out += f"_{sub_str}" if _is_simple_plain_script(sub_nodes) else f"_({sub_str})"
        if node.sup is not None:
            sup_nodes = _trim_outer_space_nodes(node.sup)
            if _is_single_symbol(sup_nodes, "circ"):
                out += "°"
            elif _is_single_symbol(sup_nodes, "prime"):
                out += "′"
            else:
                sup_str = _render_sequence(sup_nodes, rich_html=rich_html)
                if rich_html:
                    out += f"<sup>{sup_str}</sup>"
                else:
                    out += f"^{sup_str}" if _is_simple_plain_script(sup_nodes) else f"^({sup_str})"
        return out

    raise ValueError(f"Unsupported AST node: {type(node).__name__}")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_math_markup(expr: str) -> str:
    """Validate and normalize a restricted LaTeX math markup expression.

    Returns the whitespace-normalized restricted LaTeX string if valid, or raises
    ValueError with a clear diagnostic message on unsupported or unsafe markup.
    """
    normalized, _ = _parse_math_markup(expr)
    return normalized


def is_valid_math_markup(expr: str) -> bool:
    """Return True if expr conforms to the approved restricted LaTeX math subset."""
    try:
        validate_math_markup(expr)
        return True
    except ValueError:
        return False


def math_markup_to_plain_text(expr: str) -> str:
    """Convert validated restricted LaTeX markup to deterministic UTF-8 plain text."""
    _, ast = _parse_math_markup(expr)
    return _render_sequence(ast, rich_html=False)


def math_markup_to_rich_html(expr: str) -> str:
    """Convert validated restricted LaTeX markup to safe rich-text HTML using UTF-8 symbols."""
    _, ast = _parse_math_markup(expr)
    return _render_sequence(ast, rich_html=True)
