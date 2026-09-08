# 连环 —— 一个容器就是整屋（薄后端 ＋ 前端）。
# 云上跑（Render / Koyeb / 任何能跑 Docker 的地方）都用这一份；本机双击 start.command 的人不需要它。
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8420

CMD ["sh", "-c", "python scripts/restore_seed.py && (until python scripts/backup_loop.py >> /tmp/backup.log 2>&1; do echo 'backup_loop exited, restarting' >> /tmp/backup.log; sleep 5; done &) && python -m core.server --lan --port ${PORT:-8420}"]