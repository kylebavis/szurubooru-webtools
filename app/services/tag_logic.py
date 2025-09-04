from __future__ import annotations

import re
from typing import Iterable, List, Protocol, Set

RECOGNIZED = {"page","creator","person","series","character","title","meme","meta"}
DEFAULT_CAT = "default"
_ws_re = re.compile(r"\s+")

def normalize_tag(line: str | None) -> str | None:
    if not line:
        return None
    t = line.strip().lower()
    if not t:
        return None
    t = _ws_re.sub(" ", t)
    t = t.replace(' ', '_')
    return t

def split_namespace(tag: str) -> tuple[str | None, str]:
    idx = tag.find(':')
    if idx > 0:
        prefix = tag[:idx]
        if prefix in RECOGNIZED:
            return prefix, tag[idx+1:]
    return None, tag

def tags_for_upload(raw_tags: Iterable[str]) -> tuple[dict[str, Set[str]], list[str]]:
    categories: dict[str, Set[str]] = {}
    upload: Set[str] = set()
    for raw in raw_tags:
        norm = normalize_tag(raw)
        if not norm:
            continue
        cat, name = split_namespace(norm)
        if cat:
            categories.setdefault(cat, set()).add(name)
            upload.add(name)
        else:
            categories.setdefault(DEFAULT_CAT, set())
            upload.add(norm)
    return categories, sorted(upload)


class ImplicationProvider(Protocol):
    async def get_implications(self, tag: str) -> List[str]: ...


async def enrich_with_implications(upload_tags: list[str], provider: ImplicationProvider) -> list[str]:
    """Return a new list including implications (deduped) using provider.

    Future: could add caching, batching, or different enrichment strategies.
    """
    seen = set(upload_tags)
    enriched = list(upload_tags)
    for tag in list(upload_tags):
        try:
            implications = await provider.get_implications(tag)
        except Exception:
            continue
        for imp in implications:
            if imp not in seen:
                seen.add(imp)
                enriched.append(imp)
    return enriched
