import base64
import json
from typing import Any, Dict, Sequence

import httpx

from app.core.config import settings

from .tag_logic import normalize_tag


class SzuruClient:
    def __init__(self, base_url: str | None = None, auth_mode: str | None = None):
        if base_url:
            self.base_url = base_url.rstrip('/')
        elif settings.base:
            self.base_url = str(settings.base).rstrip('/')
        else:
            raise RuntimeError("SZURU_BASE is required but not configured")
        self.auth_mode = auth_mode or settings.auth_mode
        self._client = httpx.AsyncClient(base_url=self.base_url)

    def _auth_header(self) -> Dict[str, str]:
        if self.auth_mode == 'token' or (self.auth_mode == 'auto' and settings.token):
            if not (settings.user and settings.token):
                raise RuntimeError("Token auth requires SZURU_USER and SZURU_TOKEN")
            raw = f"{settings.user}:{settings.token}".encode()
            return {"Authorization": f"Token {base64.b64encode(raw).decode()}"}
        # basic
        if not (settings.user and settings.password):
            raise RuntimeError("Basic auth requires SZURU_USER and SZURU_PASSWORD")
        raw = f"{settings.user}:{settings.password}".encode()
        return {"Authorization": f"Basic {base64.b64encode(raw).decode()}"}

    async def _req(self, method: str, path: str, json: Any | None = None, files: Dict[str, Any] | None = None):
        headers = {"Accept": "application/json", **self._auth_header()}
        url = path if path.startswith('http') else f"{self.base_url}/{path.lstrip('/')}"
        r = await self._client.request(method, url, json=json, files=files, headers=headers)
        if r.status_code >= 400:
            raise RuntimeError(f"Szuru {method} {url} failed {r.status_code}: {r.text[:400]}")
        if 'application/json' in r.headers.get('content-type',''):
            return r.json()
        return r.text

    async def ensure_category(self, name: str, color: str = '#808080', order: int = 0):
        try:
            await self._req('GET', f'api/tag-category/{name}')
            return
        except Exception:
            pass
        await self._req('POST', 'api/tag-categories', json={"name": name, "color": color, "order": order})

    async def ensure_tag(self, tag: str, category: str):
        try:
            await self._req('GET', f'api/tag/{tag}')
            return 'exists'
        except Exception:
            pass
        await self._req('POST', 'api/tags', json={"names": [tag], "category": category})
        return 'created'

    async def upload_post(self, file_path: str, tags: Sequence[str], safety: str = 'safe', source: str | None = None) -> dict:
        metadata: Dict[str, Any] = {"tags": list(tags), "safety": safety}
        if source:
            metadata['source'] = source

        with open(file_path, 'rb') as f:
            files = {
                'metadata': (None, json.dumps(metadata), 'application/json'),
                'content': (file_path.split('/')[-1], f.read(), 'application/octet-stream')
            }
            return await self._req('POST', 'api/posts/', files=files)

    async def get_implications(self, tag: str) -> list[str]:
        # naive: list implications by querying tag endpoint details if available
        data = await self._req('GET', f'api/tag/{tag}')
        # placeholder path; adjust to actual field names when known
        imps = []
        for rel in data.get('implications', []) or []:
            name = rel.get('names', [None])[0]
            if name:
                normalized = normalize_tag(name)
                if normalized:  # Only append if normalize_tag returns a non-None value
                    imps.append(normalized)
        return imps

    async def search_posts(self, query: str, limit: int = 100, offset: int = 0) -> dict:
        """Search for posts using Szurubooru query syntax"""
        params = {'query': query, 'limit': limit, 'offset': offset}
        url = f"api/posts/?{'&'.join(f'{k}={v}' for k, v in params.items())}"
        return await self._req('GET', url)

    async def get_post(self, post_id: int) -> dict:
        """Get a single post by ID"""
        return await self._req('GET', f'api/post/{post_id}')

    async def update_post_tags(self, post_id: int, tags: list[str], version: int) -> dict:
        """Update tags for a post - requires current version for optimistic locking"""
        return await self._req('PUT', f'api/post/{post_id}', json={'tags': tags, 'version': version})

    async def get_all_tags_with_implications(self) -> list[str]:
        """Get all tags that have implications defined"""
        tags_with_implications = []
        offset = 0
        limit = 100  # Maximum allowed by Szurubooru

        print("DEBUG: Starting pagination to get all tags with implications...")

        while True:
            print(f"DEBUG: Requesting tags offset={offset}, limit={limit}")
            data = await self._req('GET', f'api/tags/?limit={limit}&offset={offset}')
            results = data.get('results', [])
            print(f"DEBUG: Got {len(results)} tags in this batch")

            if not results:
                break

            for tag_data in results:
                tag_names = tag_data.get('names', [])
                implications = tag_data.get('implications', [])

                if implications:  # Only check if implications exist
                    print(f"DEBUG: Tag {tag_names[0] if tag_names else 'unknown'} has {len(implications)} implications")

                if tag_names and implications:
                    # Use the primary name (first in names array)
                    primary_name = tag_names[0]
                    normalized = normalize_tag(primary_name)
                    if normalized:  # Only append if normalize_tag returns a non-None value
                        tags_with_implications.append(normalized)

            # Check if we got fewer results than the limit, meaning we're done
            if len(results) < limit:
                break

            offset += limit

        print(f"DEBUG: Found {len(tags_with_implications)} tags with implications: {tags_with_implications}")
        return tags_with_implications

szuru_client = SzuruClient()
