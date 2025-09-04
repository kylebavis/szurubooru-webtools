import asyncio
import json
from pathlib import Path

from app.core.config import settings

from .tag_logic import normalize_tag

GDL_BIN = 'gallery-dl'

class DownloadResult:
    def __init__(self, base_dir: Path, files: list[Path]):
        self.base_dir = base_dir
        self.files = files

async def run_gallery_dl(url: str, dest: Path | None = None) -> DownloadResult:
    dest = dest or settings.download_dir
    dest.mkdir(parents=True, exist_ok=True)
    # Use --write-metadata for JSON sidecars if supported
    cmd = [GDL_BIN, '--write-metadata', '--no-skip', '-D', str(dest), url]
    proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
    out = []
    async for line_b in proc.stdout:  # type: ignore
        line = line_b.decode(errors='ignore').rstrip()
        out.append(line)
    rc = await proc.wait()
    if rc != 0:
        raise RuntimeError(f"gallery-dl exit {rc}\n" + '\n'.join(out[-40:]))
    files = [p for p in dest.iterdir() if p.is_file() and not p.name.endswith('.json')]
    return DownloadResult(dest, files)

metadata_suffixes = ['.json', '.info.json']

def collect_tags_for_file(media_path: Path) -> list[str]:
    # try metadata json sidecars
    tags: set[str] = set()
    for suf in metadata_suffixes:
        mp = media_path.with_name(media_path.name + suf)
        if mp.exists():
            try:
                data = json.loads(mp.read_text(errors='ignore'))
                for key in ('tags','keywords'):
                    val = data.get(key)
                    if isinstance(val, list):
                        for t in val:
                            nt = normalize_tag(str(t))
                            if nt:
                                tags.add(nt)
            except Exception:
                pass
    return sorted(tags)

def collect_source_for_file(media_path: Path) -> str | None:
    # try metadata json sidecars for source URL
    for suf in metadata_suffixes:
        mp = media_path.with_name(media_path.name + suf)
        if mp.exists():
            try:
                data = json.loads(mp.read_text(errors='ignore'))
                # Common source URL fields from gallery-dl
                for key in ('source', 'webpage_url', 'url', 'original_url', 'extractor_url'):
                    val = data.get(key)
                    if val and isinstance(val, str) and val.startswith('http'):
                        return val
            except Exception:
                pass
    return None
