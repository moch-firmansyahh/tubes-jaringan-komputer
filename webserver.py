import socket
import sys
import os
import threading
import datetime

TCP_PORT = 8000   # Port untuk HTTP Server (TCP)
UDP_PORT = 9000   # Port untuk QoS Echo Server (UDP)
HOST     = ''     # Bind ke semua interface yang tersedia

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def log(client_ip, filepath, status_code):
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {client_ip} | {filepath} | Status: {status_code}")

# kirim response
def send_response(conn, status_code, status_text, content_type, body_bytes):
    header = (
        f"HTTP/1.1 {status_code} {status_text}\r\n"
        f"Content-Type: {content_type}; charset=utf-8\r\n"
        f"Content-Length: {len(body_bytes)}\r\n"
        f"Connection: close\r\n"
        f"\r\n"
    )
    conn.sendall(header.encode('utf-8') + body_bytes)

# tentukan content type
def get_content_type(filepath):
    ext = os.path.splitext(filepath)[1].lower()
    types = {
        '.html': 'text/html',
        '.css':  'text/css',
        '.js':   'application/javascript',
        '.png':  'image/png',
        '.jpg':  'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.ico':  'image/x-icon',
    }
    return types.get(ext, 'application/octet-stream')

# tangani satu koneksi client
def handle_tcp_client(conn, addr):
    client_ip = addr[0]
    try:
        raw = b''
        while b'\r\n\r\n' not in raw:
            chunk = conn.recv(4096)
            if not chunk:
                break
            raw += chunk

        if not raw:
            conn.close()
            return

        request_text = raw.decode('utf-8', errors='replace')
        request_line = request_text.split('\r\n')[0]
        parts = request_line.split()

        if len(parts) < 2 or parts[0] != 'GET':
            body = b'<h1>400 Bad Request</h1>'
            send_response(conn, 400, 'Bad Request', 'text/html', body)
            log(client_ip, 'malformed', 400)
            return

        url_path = parts[1]

        if url_path == '/':
            url_path = '/index.html'

        filepath = os.path.join(BASE_DIR, url_path.lstrip('/'))
        filepath = os.path.normpath(filepath)

        if not filepath.startswith(BASE_DIR):
            body = b'<h1>403 Forbidden</h1>'
            send_response(conn, 403, 'Forbidden', 'text/html', body)
            log(client_ip, url_path, 403)
            return

        try:
            with open(filepath, 'rb') as f:
                content = f.read()
            content_type = get_content_type(filepath)
            send_response(conn, 200, 'OK', content_type, content)
            log(client_ip, url_path, 200)

        except FileNotFoundError:
            body = b'<h1>404 Not Found</h1><p>File tidak ditemukan.</p>'
            send_response(conn, 404, 'Not Found', 'text/html', body)
            log(client_ip, url_path, 404)

        except Exception:
            body = b'<h1>500 Internal Server Error</h1>'
            send_response(conn, 500, 'Internal Server Error', 'text/html', body)
            log(client_ip, url_path, 500)

    except Exception as e:
        print(f"[ERROR] Koneksi dari {client_ip}: {e}")

    finally:
        conn.close()

#run udp echo
def run_udp_server():
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.bind((HOST, UDP_PORT))
    print(f"[UDP] Echo server berjalan di port {UDP_PORT}")

    while True:
        try:
            data, client_addr = udp_sock.recvfrom(4096)
            udp_sock.sendto(data, client_addr)
            print(f"[UDP] Echo ke {client_addr[0]}: {data.decode('utf-8', errors='replace')}")
        except Exception as e:
            print(f"[UDP ERROR] {e}")

#run tcp 
def run_tcp_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, TCP_PORT))
    server_socket.listen(10)
    print(f"[TCP] HTTP server berjalan di port {TCP_PORT}")
    print("Ready to serve...")

    while True:
        try:
            conn, addr = server_socket.accept()
            t = threading.Thread(target=handle_tcp_client, args=(conn, addr))
            t.daemon = True
            t.start()
        except Exception as e:
            print(f"[TCP ERROR] {e}")

# main
if __name__ == '__main__':
    print("=" * 50)
    print("  WEB SERVER - Jaringan Komputer Modul 8")
    print(f"  TCP HTTP  : port {TCP_PORT}")
    print(f"  UDP Echo  : port {UDP_PORT}")
    print("=" * 50)

    udp_thread = threading.Thread(target=run_udp_server)
    udp_thread.daemon = True
    udp_thread.start()

    try:
        run_tcp_server()
    except KeyboardInterrupt:
        print("\n[INFO] Server dihentikan.")
        sys.exit(0)