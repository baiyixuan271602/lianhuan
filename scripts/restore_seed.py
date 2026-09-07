#!/usr/bin/env python3
"""空库自动播种：数据库不存在或为空时，把 seed/house.json 灌进去。
部署重建后靠它恢复沈衍的人设、记忆和对话。"""
import sys, json
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
print("restored:", r)