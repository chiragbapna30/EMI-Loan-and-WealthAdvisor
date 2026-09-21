"""
Disk storage for multiple chats and their attachments.

Layout (all next to this file):
    chats/<chat_id>.json        one file per chat: title, timestamps, agent memory
    chat_files/<chat_id>/...    files/images the user attached in that chat
"""
import json
import re
import shutil
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

BASE_DIR = Path(__file__).parent
CHATS_DIR = BASE_DIR / "chats"
FILES_DIR = BASE_DIR / "chat_files"
LEGACY_FILE = BASE_DIR / "chat_history.json"   # single-chat file from the earlier version

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


# ---------------------------------------------------------------- ids / paths
def new_id() -> str:
    return uuid.uuid4().hex[:12]


def _valid_id(chat_id: Optional[str]) -> bool:
    # ids can arrive from the URL (?chat=...), so never trust them as paths
    return bool(chat_id) and re.fullmatch(r"[0-9a-f]{12}", chat_id) is not None


def _chat_path(chat_id: str) -> Path:
    return CHATS_DIR / f"{chat_id}.json"


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)   # atomic swap: a crash can't leave a half-written file


# ---------------------------------------------------------------- titles
def _make_title(memory: Dict[str, Any]) -> str:
    for m in memory.get("conversation_history", []):
        if m.get("role") != "user":
            continue
        text = (m.get("content") or "").strip()
        if text:
            return text if len(text) <= 40 else text[:38].rstrip() + "…"
        atts = m.get("attachments") or []
        if atts:
            return f"File: {atts[0]['name']}"[:40]
    return "New chat"


# ---------------------------------------------------------------- chats
def save_chat(chat_id: str, memory: Dict[str, Any]) -> None:
    """Save a chat. Chats with no messages are not saved (no empty entries)."""
    if not _valid_id(chat_id) or not memory.get("conversation_history"):
        return
    existing = load_chat(chat_id)
    now = datetime.now().isoformat(timespec="seconds")
    _write_json(_chat_path(chat_id), {
        "id": chat_id,
        "title": existing["title"] if existing else _make_title(memory),
        "created": existing["created"] if existing else now,
        "updated": now,
        "memory": memory,
    })


def load_chat(chat_id: Optional[str]) -> Optional[Dict[str, Any]]:
    if not _valid_id(chat_id):
        return None
    try:
        data = json.loads(_chat_path(chat_id).read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("memory"), dict):
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return None


def list_chats() -> List[Dict[str, Any]]:
    """All saved chats, newest first. 'text' is the searchable content."""
    out = []
    if CHATS_DIR.exists():
        for p in CHATS_DIR.glob("*.json"):
            c = load_chat(p.stem)
            if not c:
                continue
            hist = c["memory"].get("conversation_history", [])
            text = " ".join(m.get("content", "") for m in hist)
            for m in hist:
                text += " " + " ".join(a.get("name", "") for a in (m.get("attachments") or []))
            out.append({"id": c["id"], "title": c["title"], "created": c["created"],
                        "updated": c["updated"], "text": f"{c['title']} {text}".lower()})
    return sorted(out, key=lambda c: c["updated"], reverse=True)


def search_chats(query: str) -> List[Dict[str, Any]]:
    q = (query or "").strip().lower()
    chats = list_chats()
    return [c for c in chats if q in c["text"]] if q else chats


def delete_chat(chat_id: str) -> None:
    if not _valid_id(chat_id):
        return
    try:
        _chat_path(chat_id).unlink(missing_ok=True)
    except OSError:
        pass
    shutil.rmtree(FILES_DIR / chat_id, ignore_errors=True)


# ---------------------------------------------------------------- attachments
def save_attachment(chat_id: str, filename: str, data: bytes) -> Dict[str, Any]:
    safe = re.sub(r"[^\w.\- ]", "_", Path(filename).name)[-80:] or "file"
    rel = f"{chat_id}/{uuid.uuid4().hex[:8]}_{safe}"
    path = FILES_DIR / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return {"name": Path(filename).name, "path": rel, "size": len(data),
            "is_image": Path(safe).suffix.lower() in IMAGE_EXTS}


def attachment_path(att: Dict[str, Any]) -> Optional[Path]:
    """Absolute path of a saved attachment, or None if missing / outside FILES_DIR."""
    try:
        p = (FILES_DIR / att["path"]).resolve()
        p.relative_to(FILES_DIR.resolve())
        return p if p.is_file() else None
    except (KeyError, ValueError, OSError):
        return None


def human_size(n: int) -> str:
    for unit in ("B", "KB", "MB"):
        if n < 1024 or unit == "MB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n} B"


# ---------------------------------------------------------------- misc
def group_label(iso: str) -> str:
    try:
        d = datetime.fromisoformat(iso).date()
    except ValueError:
        return "Older"
    today = datetime.now().date()
    if d == today:
        return "Today"
    if d == today - timedelta(days=1):
        return "Yesterday"
    if d >= today - timedelta(days=7):
        return "Previous 7 days"
    return "Older"


def migrate_legacy() -> None:
    """Import the old single-chat chat_history.json as one chat (runs once)."""
    if not LEGACY_FILE.exists():
        return
    try:
        memory = json.loads(LEGACY_FILE.read_text(encoding="utf-8"))
        if isinstance(memory, dict) and memory.get("conversation_history"):
            save_chat(new_id(), memory)
        LEGACY_FILE.rename(LEGACY_FILE.with_suffix(".json.migrated"))
    except (OSError, json.JSONDecodeError):
        pass