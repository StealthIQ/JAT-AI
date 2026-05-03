import json
from pathlib import Path

from clients.database import Database
from clients.supabase import SupabaseClient
from config import load_settings

settings = load_settings()

_config_path = Path("config.json")
_db_config = {"mode": "local", "local_path": "./data/jat.db", "sync_interval": 30}
if _config_path.exists():
    try:
        raw = json.loads(_config_path.read_text())
        _db_config = raw.get("database", _db_config)
    except Exception:
        pass

db = Database(
    mode=_db_config.get("mode", "local"),
    local_path=_db_config.get("local_path", "./data/jat.db"),
    sync_interval=_db_config.get("sync_interval", 30),
)

if _db_config.get("mode") in ("supabase", "hybrid") and settings.supabase_url and settings.supabase_key:
    db.set_remote(SupabaseClient(settings.supabase_url, settings.supabase_key))
