#!/usr/bin/env python3
"""每 10 分钟把家里的全部账本（人设/聊天/记忆/日记等）备份到 GitHub 私有仓库。
Render 免费档重建会清盘 —— 这份备份让重建后最多只丢 10 分钟。"""
import sys, os, time, json, base64, urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

REPO = "baiyixuan271602/lianhuan-backup"
FILE = "chat_backup.json"
TOKEN = os.environ.get("LIANHUAN_GITHUB_TOKEN", "")


def gh(method, url, body=None):
    if not TOKEN:
        raise RuntimeError("no token")
    req = urllib.request.Request(url, method=method)
    req.add_header("Authorization", "Bearer " + TOKEN)
    req.add_header("Accept", "application/vnd.github+json")
    data = None
    if body is not None:
        req.add_header("Content-Type", "application/json")
        data = json.dumps(body).encode()
    with urllib.request.urlopen(req, data=data, timeout=60) as r:
        return json.loads(r.read().decode()) if r.status != 204 else {}


def backup():
    from core.store.sqlite import SqliteStore
    db = Path(os.environ.get("LIANHUAN_DB", "data/lianhuan.db"))
    store = SqliteStore(str(db))
    snap = store.export_all()
    # 界面填的引擎配置（data/secrets.json，0600）也带上 —— 重建后不用重新贴 key
    sec_path = db.parent / "secrets.json"
    if sec_path.exists():
        snap["secrets_file"] = base64.b64encode(sec_path.read_bytes()).decode()
    url = f"https://api.github.com/repos/{REPO}/contents/{FILE}"
    # ★ 防覆盖①：冷启动恢复失败时立了 flag —— 绝不用空库覆盖远端的好备份
    flag = db.parent / ".restore_failed"
    if flag.exists():
        print("skip backup: restore_failed flag present", flush=True)
        return "skip(flag)"
    content = json.dumps(snap, ensure_ascii=False).encode()
    body = {"message": "auto backup", "content": base64.b64encode(content).decode()}
    try:
        meta = gh("GET", url)
        if meta.get("sha"):
            body["sha"] = meta["sha"]
        # ★ 防覆盖②：本地账本全空、远端却有数据 —— 大概率是空库启动/恢复没跟上，
        #   这趟先不覆盖，保住远端那一份（下一轮本地有数据了再正常备份）。
        if not (snap.get("turns") or snap.get("memories")):
            try:
                remote = json.loads(base64.b64decode(meta.get("content") or "").decode("utf-8"))
                if (remote.get("turns") or remote.get("memories")):
                    print("skip backup: local empty but remote has data", flush=True)
                    return "skip(local_empty)"
            except Exception:
                pass
    except Exception:
        pass
    gh("PUT", url, body)
    return f"turns={len(snap.get('turns') or [])} mems={len(snap.get('memories') or [])}"


def main():
    while True:
        try:
            print("backup ok:", backup(), flush=True)
        except Exception as e:
            print("backup fail:", e, flush=True)
        time.sleep(180)


if __name__ == "__main__":
    main()
