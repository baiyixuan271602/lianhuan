#!/usr/bin/env python3
"""空库自动播种：先把 seed/house.json（顾衍人设）灌进去，
再从 GitHub 备份仓库拉最新账本 merge 回来（聊天、记忆都能恢复）。"""
import sys, os, json, base64, urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DB = Path(sys.argv[1] if len(sys.argv) > 1 else "data/lianhuan.db")
SEED = Path("seed/house.json")

if DB.exists() and DB.stat().st_size > 4096:
    print("db exists, skip restore")
    sys.exit(0)

from core.store.sqlite import SqliteStore

store = SqliteStore(str(DB))
house = json.loads(SEED.read_text(encoding="utf-8"))
r = store.import_all(house, "merge")
print("restored seed:", r)

# 引擎固化：重建后别掉回 echo 假AI。环境变量里有 DeepSeek key 就用 api 引擎。
try:
    if not (store.get_setting("engine", "") or ""):
        store.set_setting("engine", "api")
        print("engine set: api")
except Exception as e:
    print("engine set fail:", e)

token = os.environ.get("LIANHUAN_GITHUB_TOKEN", "")
if token:
    try:
        req = urllib.request.Request(
            "https://api.github.com/repos/baiyixuan271602/lianhuan-backup/contents/chat_backup.json")
        req.add_header("Authorization", "Bearer " + token)
        req.add_header("Accept", "application/vnd.github+json")
        with urllib.request.urlopen(req, timeout=60) as resp:
            meta = json.loads(resp.read().decode())
        backup = json.loads(base64.b64decode(meta["content"]).decode("utf-8"))
        sec_b64 = backup.pop("secrets_file", None)
        r2 = store.import_all(backup, "merge")
        print("restored backup:", r2)
        if sec_b64:
            sec = Path(DB).parent / "secrets.json"
            sec.write_bytes(base64.b64decode(sec_b64))
            os.chmod(sec, 0o600)
            print("restored secrets.json")
    except Exception as e:
        print("no backup or fail:", e)