import socket
import time
import subprocess
import threading
import os
import sys

def run_udp_test(num_packets):
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.settimeout(2.0)
    target = ('127.0.0.1', 9000)
    
    paket_dikirim = 0
    paket_diterima = 0
    total_rtt = 0.0
    rtts = []
    
    for i in range(1, num_packets + 1):
        pesan = f"Ping UDP Sequence {i}"
        paket_dikirim += 1
        waktu_kirim = time.time()
        try:
            udp_socket.sendto(pesan.encode('utf-8'), target)
            data, server = udp_socket.recvfrom(4096)
            waktu_terima = time.time()
            rtt = (waktu_terima - waktu_kirim) * 1000
            total_rtt += rtt
            rtts.append(rtt)
            paket_diterima += 1
        except socket.timeout:
            pass
        time.sleep(0.01)
    
    udp_socket.close()
    
    packet_loss = ((paket_dikirim - paket_diterima) / paket_dikirim) * 100 if paket_dikirim > 0 else 0
    avg_rtt = (total_rtt / paket_diterima) if paket_diterima > 0 else 0
    
    if len(rtts) > 1:
        jitter = sum(abs(rtts[i] - rtts[i-1]) for i in range(1, len(rtts))) / (len(rtts) - 1)
    else:
        jitter = 0.0
        
    return paket_dikirim, packet_loss, avg_rtt, jitter

def run_http_request(port, path):
    start = time.time()
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(10)
    try:
        s.connect(('127.0.0.1', port))
        req = f"GET {path} HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n"
        s.sendall(req.encode())
        res = b""
        while True:
            chunk = s.recv(4096)
            if not chunk: break
            res += chunk
    except Exception as e:
        res = b""
    end = time.time()
    s.close()
    return (end - start) * 1000, len(res)

print("Starting servers...")
server_proc = subprocess.Popen([sys.executable, "webserver.py"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
proxy_proc = subprocess.Popen([sys.executable, "proxy.py"], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    proxy_proc.stdin.write(b"\n")
    proxy_proc.stdin.flush()
except Exception as e:
    print("Error writing to proxy:", e)

time.sleep(2) # Wait for servers to bind and start

print("--- RTT LOSS JITTER ---")
for pkts in [10, 50, 100, 50, 100]:
    p, l, r, j = run_udp_test(pkts)
    print(f"| | {p} | {l:.2f} | {r:.2f} | {j:.2f} |")

print("--- CACHE HIT MISS ---")
tests = [
    ('/HTML/index.html', 'MISS'),
    ('/HTML/index.html', 'HIT'),
    ('/HTML/osi.html', 'MISS'),
    ('/HTML/osi.html', 'HIT'),
    ('/HTML/tcpip.html', 'MISS')
]
for path, expected in tests:
    t, s = run_http_request(8080, path)
    print(f"{expected} {path}: {t:.2f}ms size: {s}")

print("--- MULTI CLIENT ---")
results = []
def worker(idx, port, path, is_udp=False):
    if is_udp:
        start = time.time()
        run_udp_test(1)
        end = time.time()
        results.append((idx, "UDP Ping", "Echo Server", 9000, "Echo Reply", (end-start)*1000))
    else:
        t, s = run_http_request(port, path)
        status = "200 OK" if s > 0 else "Failed"
        target = "Proxy" if port == 8080 else "Web Server"
        results.append((idx, path, target, port, status, t))

threads = [
    threading.Thread(target=worker, args=(1, 8080, '/HTML/index.html')),
    threading.Thread(target=worker, args=(2, 8080, '/HTML/index.html')),
    threading.Thread(target=worker, args=(3, 8000, '/HTML/qos.html')),
    threading.Thread(target=worker, args=(4, 8080, '/HTML/osi.html')),
    threading.Thread(target=worker, args=(5, 9000, '', True)),
]
for th in threads: th.start()
for th in threads: th.join()

results.sort(key=lambda x: x[0])
for r in results:
    print(r)

server_proc.terminate()
proxy_proc.terminate()
print("Servers stopped.")
