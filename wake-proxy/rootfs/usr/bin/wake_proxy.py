#!/usr/bin/env python3
"""
wake-proxy — reverse proxy с пробуждением сервера через Home Assistant.

Когда приходит запрос, а upstream (Ollama) недоступен:
  1. проверяет, не работает ли машина сейчас под Windows — тогда будить нечего;
  2. просит HA переключить bootnext-симлинк на Ubuntu;
  3. просит HA отправить magic packet;
  4. ждёт, пока откроется порт upstream;
  5. проксирует запрос как обычно.

Зависимостей нет, только стандартная библиотека.
"""

import http.client
import json
import os
import socket
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# --- конфигурация ---------------------------------------------------------

# Внутри add-on'а Home Assistant настройки лежат в options.json, а Supervisor
# выдаёт собственный токен и проксирует Core на http://supervisor/core —
# тогда long-lived token заводить не нужно. Вне add-on'а всё берётся из
# переменных окружения, как в обычном docker-compose.
OPTIONS_FILE = os.environ.get("WAKE_PROXY_OPTIONS", "/data/options.json")

try:
    with open(OPTIONS_FILE) as _f:
        _opts = json.load(_f)
except (OSError, ValueError):
    _opts = {}

SUPERVISOR_TOKEN = os.environ.get("SUPERVISOR_TOKEN")


def _env(name, default=None, required=False, option=None):
    v = os.environ.get(name)
    if v in (None, "") and option is not None:
        o = _opts.get(option)
        if o not in (None, ""):
            v = str(o)
    if v in (None, ""):
        v = default
    if required and not v:
        where = f"{name} (или {option} в настройках add-on'а)" if option else name
        sys.exit(f"wake-proxy: не задано: {where}")
    return v

LISTEN_HOST   = _env("LISTEN_HOST", "0.0.0.0")
LISTEN_PORT   = int(_env("LISTEN_PORT", "11435", option="listen_port"))

UPSTREAM_HOST = _env("UPSTREAM_HOST", required=True, option="upstream_host")
UPSTREAM_PORT = int(_env("UPSTREAM_PORT", "11434", option="upstream_port"))

HA_URL   = _env("HA_URL",
                "http://supervisor/core" if SUPERVISOR_TOKEN else None,
                required=True, option="ha_url")
HA_TOKEN = _env("HA_TOKEN", SUPERVISOR_TOKEN, required=True)

# сущности из пакета home_server.yaml
HA_WAKE_BUTTON    = _env("HA_WAKE_BUTTON", "button.home_server_wake",
                         option="wake_entity")
HA_BOOT_UBUNTU    = _env("HA_BOOT_UBUNTU", "shell_command.home_server_boot_ubuntu",
                         option="boot_ubuntu_entity")
HA_NEXT_BOOT      = _env("HA_NEXT_BOOT", "sensor.home_server_next_boot",
                         option="next_boot_entity")
HA_WINDOWS_SENSOR = _env("HA_WINDOWS_SENSOR", "binary_sensor.home_server_windows_online",
                         option="windows_entity")

WAKE_TIMEOUT   = int(_env("WAKE_TIMEOUT", "240", option="wake_timeout"))
PROBE_INTERVAL = float(_env("PROBE_INTERVAL", "3", option="probe_interval"))
PROBE_TIMEOUT  = float(_env("PROBE_TIMEOUT", "2", option="probe_timeout"))
BOOT_SETTLE    = float(_env("BOOT_SETTLE", "5", option="boot_settle"))

_wake_lock = threading.Lock()
HOP_BY_HOP = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade",
}


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# --- проверка upstream ----------------------------------------------------

def upstream_is_up():
    s = socket.socket()
    s.settimeout(PROBE_TIMEOUT)
    try:
        return s.connect_ex((UPSTREAM_HOST, UPSTREAM_PORT)) == 0
    finally:
        s.close()


# --- Home Assistant -------------------------------------------------------

def ha_request(path, payload=None, method=None):
    url = f"{HA_URL.rstrip('/')}{path}"
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {HA_TOKEN}")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=10) as r:
        body = r.read()
    return json.loads(body) if body else None


def ha_state(entity_id):
    """Состояние сущности или None, если HA недоступен."""
    try:
        return ha_request(f"/api/states/{entity_id}").get("state")
    except (urllib.error.URLError, OSError, ValueError, AttributeError) as e:
        log(f"HA: не удалось прочитать {entity_id}: {e}")
        return None


def ha_call(entity_id):
    """Вызов сервиса по entity_id вида domain.service или нажатие кнопки."""
    domain, name = entity_id.split(".", 1)
    if domain in ("button", "switch", "input_button"):
        service = "press" if domain in ("button", "input_button") else "turn_on"
        return ha_request(f"/api/services/{domain}/{service}",
                          {"entity_id": entity_id})
    return ha_request(f"/api/services/{domain}/{name}", {})


# --- логика пробуждения ---------------------------------------------------

class WakeError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


def ensure_upstream():
    """Поднимает машину, если нужно. Исключение — если это невозможно."""
    if upstream_is_up():
        return

    with _wake_lock:
        # пока ждали блокировку, машину мог поднять соседний запрос
        if upstream_is_up():
            return

        if ha_state(HA_WINDOWS_SENSOR) == "on":
            raise WakeError(503, "Машина сейчас работает под Windows. "
                                 "Переключите загрузку на Ubuntu вручную.")

        try:
            if ha_state(HA_NEXT_BOOT) != "Ubuntu":
                log("следующая загрузка не Ubuntu — переключаю")
                ha_call(HA_BOOT_UBUNTU)
                time.sleep(BOOT_SETTLE)
            log("отправляю magic packet")
            ha_call(HA_WAKE_BUTTON)
        except (urllib.error.URLError, OSError, ValueError) as e:
            raise WakeError(502, f"Home Assistant недоступен: {e}") from e

        deadline = time.monotonic() + WAKE_TIMEOUT
        while time.monotonic() < deadline:
            time.sleep(PROBE_INTERVAL)
            if upstream_is_up():
                log("upstream поднялся")
                return

        raise WakeError(504, f"Машина не ответила за {WAKE_TIMEOUT} с.")


# --- проксирование --------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "wake-proxy"

    def log_message(self, fmt, *args):
        pass  # свой лог ниже, стандартный только шумит

    def _error(self, status, message):
        body = json.dumps({"error": message}).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

    def _proxy(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else None

        if self.path == "/wake-proxy/health":
            state = "up" if upstream_is_up() else "down"
            payload = json.dumps({"upstream": state}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return

        try:
            ensure_upstream()
        except WakeError as e:
            log(f"{self.command} {self.path} -> {e.status}: {e.message}")
            self._error(e.status, e.message)
            return

        headers = {k: v for k, v in self.headers.items()
                   if k.lower() not in HOP_BY_HOP}
        headers["Host"] = f"{UPSTREAM_HOST}:{UPSTREAM_PORT}"

        conn = http.client.HTTPConnection(UPSTREAM_HOST, UPSTREAM_PORT,
                                          timeout=None)
        try:
            conn.request(self.command, self.path, body=body, headers=headers)
            resp = conn.getresponse()

            self.send_response(resp.status)
            chunked = False
            for k, v in resp.getheaders():
                if k.lower() in HOP_BY_HOP:
                    continue
                self.send_header(k, v)
            if resp.getheader("Content-Length") is None:
                # длина заранее неизвестна (стриминг) — отдаём по частям
                self.send_header("Transfer-Encoding", "chunked")
                chunked = True
            self.end_headers()

            while True:
                # read1, а не read: отдаёт то, что уже пришло, не дожидаясь
                # заполнения буфера — иначе токены Ollama копятся до конца ответа
                chunk = resp.read1(8192)
                if not chunk:
                    break
                if chunked:
                    self.wfile.write(b"%x\r\n%s\r\n" % (len(chunk), chunk))
                else:
                    self.wfile.write(chunk)
                self.wfile.flush()
            if chunked:
                self.wfile.write(b"0\r\n\r\n")
                self.wfile.flush()

            log(f"{self.command} {self.path} -> {resp.status}")
        except (http.client.HTTPException, OSError) as e:
            log(f"{self.command} {self.path} -> ошибка upstream: {e}")
            try:
                self._error(502, f"Upstream недоступен: {e}")
            except OSError:
                pass
        finally:
            conn.close()

    do_GET = do_POST = do_PUT = do_DELETE = do_PATCH = do_HEAD = _proxy


def main():
    srv = ThreadingHTTPServer((LISTEN_HOST, LISTEN_PORT), Handler)
    srv.daemon_threads = True
    log(f"слушаю {LISTEN_HOST}:{LISTEN_PORT} -> "
        f"{UPSTREAM_HOST}:{UPSTREAM_PORT}, HA {HA_URL}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
