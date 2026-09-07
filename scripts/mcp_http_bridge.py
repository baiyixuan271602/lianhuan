#!/usr/bin/env python3
"""stdio <-> HTTP MCP 桥：把远程 HTTP/SSE MCP 变成本地 stdio MCP。
用法：python scripts/mcp_http_bridge.py <MCP_URL>"""
import sys, json, urllib.request, time

URL = sys.argv[1].strip()

def send_http(req_obj):
    body = json.dumps(req_obj, ensure_ascii=False).encode()
    last = None
    for i in range(40):
        try:
            r = urllib.request.Request(URL, data=body, headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            })
            with urllib.request.urlopen(r, timeout=45) as resp:
                ct = resp.headers.get("Content-Type", "")
                data = resp.read().decode("utf-8", "replace")
            if "text/event-stream" in ct:
                for line in data.split(chr(10)):
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
        except Exception as e:
            last = e
            time.sleep(8)
    raise last

def out(obj):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + chr(10))
    sys.stdout.flush()


def _heartbeat() -> None:
    # 每 10 分钟轻量 ping 一次上游，防 Render 免费档 15 分钟休眠。
    import threading
    def beat():
        while True:
            time.sleep(600)
            try:
                req = urllib.request.Request(URL, data=b'{"jsonrpc":"2.0","method":"ping"}',
                                             headers={"Content-Type": "application/json",
                                                      "Accept": "application/json, text/event-stream"})
                with urllib.request.urlopen(req, timeout=20) as resp:
                    resp.read()
            except Exception:
                pass
    threading.Thread(target=beat, daemon=True).start()

def main():
    _heartbeat()
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except Exception:
            continue
        if not isinstance(req, dict) or "id" not in req:
            continue
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
