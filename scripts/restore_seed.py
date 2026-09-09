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
    # ★ 冷启动恢复是命门：只试一次、失败就空库启动，会被 backup_loop 用"空"覆盖掉好备份。
    #   改为重试 3 次；仍失败就立一个 flag，backup_loop 看到 flag 就不会拿空库覆盖远端备份。
    fail_flag = Path(DB).parent / ".restore_failed"
    for attempt in range(3):
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
            try:
                fail_flag.unlink()
            except Exception:
                pass
            break
        except Exception as e:
            print(f"backup restore fail (try {attempt + 1}/3):", e)
            if attempt < 2:
                import time as _t
                _t.sleep(5)
    else:
        # 三次都失败：立 flag 防覆盖，服务照起（用户还能聊新的，旧账本等手动救）
        try:
            fail_flag.write_text("restore failed at startup\n")
        except Exception:
            pass
        print("!!! RESTORE FAILED after 3 tries — backup_loop will NOT overwrite remote backup while flag exists")