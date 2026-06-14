import socket
import threading
import datetime
import sys
import os
import hashlib
import time

# Konfigurasi
PROXY_HOST = "0.0.0.0"
PROXY_PORT = 8080

print("=== KONFIGURASI PROXY ===")
WEB_SERVER_HOST = input("Masukkan IP Laptop Web Server (contoh: 192.168.1.5, biarkan kosong untuk 127.0.0.1): ")
if not WEB_SERVER_HOST:
    WEB_SERVER_HOST = "127.0.0.1"
WEB_SERVER_PORT = 8000

CONNECT_TIMEOUT = 5   # detik untuk koneksi ke web server
RECV_TIMEOUT    = 10  # detik untuk menerima respons dari web server

# Cache: File-based caching
CACHE_DIR = "cache_dir"
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)
cache_lock = threading.Lock()

def get_cache_filename(path):
    # Buat hash MD5 dari path agar aman jadi nama file
    filename = hashlib.md5(path.encode('utf-8')).hexdigest()
    return os.path.join(CACHE_DIR, filename)


# Helper: logging
def log(tag: str, msg: str):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [{tag}] {msg}", flush=True)


# Helper: parse request line
def parse_request(raw: bytes):
    """Kembalikan (method, path) atau (None, None) jika malformed."""
    try:
        first_line = raw.split(b"\r\n")[0].decode()
        parts = first_line.split()
        if len(parts) < 2:
            return None, None
        return parts[0], parts[1]
    except Exception:
        return None, None


# Helper: build error responses
def make_error_response(code: int, text: str) -> bytes:
    body = f"<h1>{code} {text}</h1>".encode()
    header = (
        f"HTTP/1.1 {code} {text}\r\n"
        f"Content-Type: text/html; charset=utf-8\r\n"
        f"Content-Length: {len(body)}\r\n"
        f"Connection: close\r\n"
        f"\r\n"
    )
    return header.encode() + body


# Forward request ke Web Server
def forward_to_server(raw_request: bytes) -> bytes:
    """
    Kirim raw_request ke web server, kembalikan response bytes.
    Raise socket.timeout jika timeout, raise Exception untuk error lain.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(CONNECT_TIMEOUT)
    s.connect((WEB_SERVER_HOST, WEB_SERVER_PORT))
    s.sendall(raw_request)

    response = b""
    s.settimeout(RECV_TIMEOUT)
    while True:
        chunk = s.recv(4096)
        if not chunk:
            break
        response += chunk
    s.close()
    return response


# Handler per koneksi client
def handle_client(conn: socket.socket, addr):
    start_time = time.time()
    client_ip = addr[0]
    try:
        # Terima request dari client
        raw = b""
        conn.settimeout(5)
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                break
            raw += chunk
            if b"\r\n\r\n" in raw:
                break

        if not raw:
            conn.close()
            return

        method, path = parse_request(raw)

        # Malformed
        if method is None:
            conn.sendall(make_error_response(400, "Bad Request"))
            log("PROXY", f"{client_ip} - 400 Bad Request (malformed)")
            return

        # Normalisasi path untuk cache key
        cache_key = path if path else "/"
        cache_file = get_cache_filename(cache_key)

        # ── Cek cache ──
        cached = None
        with cache_lock:
            if os.path.exists(cache_file):
                with open(cache_file, "rb") as f:
                    cached = f.read()

        if cached is not None:
            # CACHE HIT
            conn.sendall(cached)
            elapsed_ms = (time.time() - start_time) * 1000
            log("PROXY", f"{client_ip} {method} {path} - HIT (from cache, {len(cached)} bytes) - Waktu Respons: {elapsed_ms:.2f} ms")
            return

        # CACHE MISS → forward ke server
        log("PROXY", f"{client_ip} {method} {path} - MISS (forwarding to server)")
        try:
            response = forward_to_server(raw)
        except socket.timeout:
            conn.sendall(make_error_response(504, "Gateway Timeout"))
            log("PROXY", f"{client_ip} {method} {path} - 504 Gateway Timeout")
            return
        except ConnectionRefusedError:
            conn.sendall(make_error_response(502, "Bad Gateway"))
            log("PROXY", f"{client_ip} {method} {path} - 502 Bad Gateway (connection refused)")
            return
        except Exception as e:
            conn.sendall(make_error_response(502, "Bad Gateway"))
            log("PROXY", f"{client_ip} {method} {path} - 502 Bad Gateway: {e}")
            return

        # Cek apakah response dari server mengandung error (502/504 dari server sendiri)
        if not response:
            conn.sendall(make_error_response(502, "Bad Gateway"))
            log("PROXY", f"{client_ip} {method} {path} - 502 Bad Gateway (empty response)")
            return

        # Simpan ke cache hanya untuk response 200 OK
        try:
            first_line = response.split(b"\r\n")[0].decode()
            if "200" in first_line:
                with cache_lock:
                    with open(cache_file, "wb") as f:
                        f.write(response)
                log("PROXY", f"{client_ip} {method} {path} - cached response ({len(response)} bytes)")
        except Exception:
            pass  # Jika tidak bisa parse, tetap kirimkan response

        conn.sendall(response)
        elapsed_ms = (time.time() - start_time) * 1000
        log("PROXY", f"{client_ip} {method} {path} - forwarded response ({len(response)} bytes) - Waktu Respons: {elapsed_ms:.2f} ms")

    except socket.timeout:
        log("PROXY", f"{client_ip} - client timeout")
    except Exception as e:
        log("PROXY", f"{client_ip} - error: {e}")
    finally:
        try:
            conn.close()
        except Exception:
            pass


# Main proxy loop
def run_proxy():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((PROXY_HOST, PROXY_PORT))
    server.listen(100)
    log("PROXY", f"Proxy listening on port {PROXY_PORT}")
    log("PROXY", f"Forwarding to Web Server at {WEB_SERVER_HOST}:{WEB_SERVER_PORT}")
    log("PROXY", "Multi-threading aktif")

    while True:
        try:
            conn, addr = server.accept()
            t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            t.start()
        except Exception as e:
            log("PROXY", f"Accept error: {e}")


# Entry Point
if __name__ == "__main__":
    try:
        run_proxy()
    except KeyboardInterrupt:
        log("PROXY", "Proxy dihentikan.")
        sys.exit(0)
