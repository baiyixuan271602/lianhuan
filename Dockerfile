# 连环 —— 一个容器就是整屋（薄后端 ＋ 前端）。
# 自建版：Render/Koyeb/任何能跑 Docker 的地方都用这一份。
FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt
EXPOSE 8420
CMD ["sh", "-c", "python scripts/restore_seed.py && python -m core.server --lan --port ${PORT:-8420}"]