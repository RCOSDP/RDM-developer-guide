"""Minimal TOON (Token-Oriented Object Notation) encoder for reports (SPEC-06 §4).

Encodes JSON-compatible data: dicts become `key: value` lines, lists of flat dicts with the same
keys become tabular arrays `name[N]{k1,k2}:` followed by CSV rows, other lists become `- item`
lines. Strings containing a delimiter (`,` `:` `"` newline) or surrounding spaces are quoted.
The encoder is deliberately small; it is not a full TOON implementation.
"""
from __future__ import annotations

import json
from typing import Any

_DELIMS = (",", ":", '"', "\n", "[", "]", "{", "}")


def _scalar(v: Any) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return json.dumps(v)
    s = str(v)
    if s == "" or s != s.strip() or any(d in s for d in _DELIMS) or s in ("true", "false", "null"):
        return json.dumps(s, ensure_ascii=False)
    return s


def _is_table(items: list) -> bool:
    if not items or not all(isinstance(i, dict) for i in items):
        return False
    keys = list(items[0].keys())
    return all(list(i.keys()) == keys for i in items) and all(
        not isinstance(v, (dict, list)) for i in items for v in i.values()
    )


def encode(data: Any, indent: int = 0, name: str | None = None) -> str:
    pad = "  " * indent
    out: list[str] = []
    if isinstance(data, dict):
        if name is not None:
            out.append(f"{pad}{name}:")
            indent += 1
            pad = "  " * indent
        for k, v in data.items():
            if isinstance(v, (dict, list)):
                out.append(encode(v, indent, k))
            else:
                out.append(f"{pad}{k}: {_scalar(v)}")
        return "\n".join(out)
    if isinstance(data, list):
        label = name if name is not None else "items"
        if _is_table(data):
            keys = list(data[0].keys())
            out.append(f"{pad}{label}[{len(data)}]{{{','.join(keys)}}}:")
            for row in data:
                out.append(pad + "  " + ",".join(_scalar(row[k]) for k in keys))
            return "\n".join(out)
        out.append(f"{pad}{label}[{len(data)}]:")
        for item in data:
            if isinstance(item, (dict, list)):
                # "- " occupies the first two columns of the item; continuation lines align with
                # the text after the dash (one indent level deeper than the dash itself).
                sub = encode(item, indent + 2)
                first, _, rest = sub.partition("\n")
                out.append(pad + "  - " + first.strip())
                if rest:
                    out.append(rest)
            else:
                out.append(pad + "  - " + _scalar(item))
        return "\n".join(out)
    return f"{pad}{name + ': ' if name else ''}{_scalar(data)}"
