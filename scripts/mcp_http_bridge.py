#!/usr/bin/env python3
"""stdio <-> HTTP MCP 桥：把远程 HTTP/SSE MCP 变成本地 stdio MCP。
用法：python scripts/mcp_http_bridge.py <MCP_URL>
安全：只转发本进程收到的 JSON-RPC 行，不读任何本地文件。"""
import sys, json, urllib.request

URL = sys.argv[1].strip()

def send_http(req_obj):
    body = json.dumps(req_obj, ensure_ascii=False).encode()
    r = urllib.request.Request(URL, data=body, headers={
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    })
    with urllib.request.urlopen(r, timeout=180) as resp:
        ct = resp.headers.get("Content-Type", "")
        data = resp.read().decode("utf-8", "replace")
    if "text/event-stream" in ct:
        for line in data.split("
"):
            line = line.strip()
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if not payload or payload == "[DONE]":
                continue
            try:
                obj = json.loads(payload)
                if isinstance(obj, dict) and "jsonrpc" in obj:
                    return obj
            except Exception:
                pass
        return None
    return json.loads(data)

def out(obj):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "
")
    sys.stdout.flush()

def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except Exception:
            continue
        if not isinstance(req, dict) or "id" not in req:
            continue  # 通知类，不要求响应
        try:
            resp = send_http(req)
            if resp is None:
                resp = {"jsonrpc": "2.0", "id": req["id"],
                        "error": {"code": -32603, "message": "empty response"}}
            out(resp)
        except Exception as e:
            out({"jsonrpc": "2.0", "id": req["id"],
                 "error": {"code": -32603, "message": str(e)[:200]}})

if __name__ == "__main__":
    main()
