import socket
import time
import sys
import os

# Konfigurasi Default Server
DEFAULT_HOST = "127.0.0.1"
HTTP_SERVER_PORT = 8000
PROXY_PORT = 8080
UDP_ECHO_PORT = 9000

# Meminta user untuk memasukkan IP Server (jika ingin test beda device)
ip_input = input(f"Masukkan IP Server (tekan Enter untuk default {DEFAULT_HOST}): ")
if ip_input.strip():
    DEFAULT_HOST = ip_input.strip()

def http_client():
    print("\n--- Fitur HTTP Client (TCP) ---")
    print("Semua request HTTP dikirim melalui Proxy Server (Port 8080).")

    target_ip = input("Masukkan IP Proxy Server (biarkan kosong untuk 127.0.0.1): ")
    if not target_ip:
        target_ip = DEFAULT_HOST

    target_port = PROXY_PORT
    print(f"[*] Target diset ke Proxy (Port {target_port})")

    path = input("Masukkan path file yang ingin di-request (misal: /HTML/index.html): ")
    if not path.startswith('/'):
        path = '/' + path
    
    # Membangun HTTP GET Request
    request_line = f"GET {path} HTTP/1.1\r\nHost: {target_ip}\r\nConnection: close\r\n\r\n"
    
    # Membuat TCP Socket
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.settimeout(10)
    
    try:
        # Menghitung Waktu Request
        start_time = time.time()
        
        print(f"[*] Menghubungi {target_ip}:{target_port}...")
        client_socket.connect((target_ip, target_port))
        client_socket.sendall(request_line.encode('utf-8'))
        
        # Menerima Response
        response = b""
        while True:
            chunk = client_socket.recv(4096)
            if not chunk:
                break
            response += chunk
            
        end_time = time.time()
        
        # Kalkulasi Response Time
        response_time = (end_time - start_time) * 1000  # ms
        
        # Memisahkan header dan body
        if b"\r\n\r\n" in response:
            header_bytes, body_bytes = response.split(b"\r\n\r\n", 1)
            headers = header_bytes.decode('utf-8', errors='replace')
        else:
            headers = response.decode('utf-8', errors='replace')
            body_bytes = b""
            
        # Kalkulasi Throughput
        if response_time > 0:
            throughput = (len(response) * 8) / response_time
        else:
            throughput = 0.0

        # Menampilkan Informasi
        print("\n" + "="*50)
        print("               HASIL REQUEST HTTP               ")
        print("="*50)
        print(f"[>] Target URL   : http://{target_ip}:{target_port}{path}")
        print(f"[>] Waktu Respon : {response_time:.2f} ms")
        print(f"[>] Total Bytes  : {len(response)} bytes")
        print(f"[>] Throughput   : {throughput:.2f} kbps")
        print("-" * 50)
        print("--- HTTP HEADERS ---")
        print(headers)
        print("-" * 50)
        
        # Opsi simpan atau lihat file
        if len(body_bytes) > 0:
            simpan = input("\nApakah ingin melihat atau menyimpan file hasil request? (lihat/simpan/tidak): ").lower()
            if simpan == 'lihat':
                print("\n--- BODY ---")
                try:
                    print(body_bytes.decode('utf-8'))
                except UnicodeDecodeError:
                    print("[!] File biner (tidak bisa ditampilkan sebagai teks)")
            elif simpan == 'simpan':
                filename = path.split('/')[-1]
                if not filename:
                    filename = "downloaded_file.html"
                with open(filename, 'wb') as f:
                    f.write(body_bytes)
                print(f"[*] File berhasil disimpan di direktori saat ini dengan nama: {filename}")
                
    except socket.timeout:
        print("[!] Request Timeout: Server tidak merespons.")
    except ConnectionRefusedError:
        print("[!] Koneksi Ditolak: Pastikan server target sedang berjalan.")
    except Exception as e:
        print(f"[!] Terjadi error: {e}")
    finally:
        client_socket.close()

def udp_qos_client():
    print("\n--- Fitur UDP QoS Test Client ---")
    print("Fitur ini akan mengirimkan paket UDP ke Echo Server (Port 9000)")
    
    target_ip = input("Masukkan IP Web Server tujuan (biarkan kosong untuk 127.0.0.1): ")
    if not target_ip:
        target_ip = DEFAULT_HOST

    try:
        jumlah_paket = int(input("Masukkan jumlah paket yang ingin dikirim (misal: 10): "))
    except ValueError:
        print("[!] Input harus berupa angka.")
        return

    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.settimeout(2.0)  # Timeout 2 detik per paket
    
    target = (target_ip, UDP_ECHO_PORT)
    
    paket_dikirim = 0
    paket_diterima = 0
    total_rtt = 0.0
    rtt_list = []  # Menyimpan RTT tiap paket untuk kalkulasi min, max, dan jitter
    
    print("\nMemulai pengujian QoS...")
    print("-" * 50)
    
    for i in range(1, jumlah_paket + 1):
        pesan = f"Ping UDP Sequence {i}"
        paket_dikirim += 1
        
        waktu_kirim = time.time()
        try:
            # Kirim paket
            udp_socket.sendto(pesan.encode('utf-8'), target)
            
            # Terima balasan
            data, server = udp_socket.recvfrom(4096)
            waktu_terima = time.time()
            
            # Hitung RTT dalam millisecond
            rtt = (waktu_terima - waktu_kirim) * 1000
            total_rtt += rtt
            rtt_list.append(rtt)
            paket_diterima += 1
            
            print(f"Reply dari {server[0]}: seq={i} rtt={rtt:.2f} ms data=\"{data.decode('utf-8', errors='replace')}\"")
            
        except socket.timeout:
            print(f"Request Timeout untuk seq={i}")
        except Exception as e:
            print(f"Error seq={i}: {e}")
            
        time.sleep(0.1) # Jeda sedikit agar simulasi lebih natural
        
    udp_socket.close()
    
    # Hitung Statistik
    packet_loss = ((paket_dikirim - paket_diterima) / paket_dikirim) * 100 if paket_dikirim > 0 else 0

    if rtt_list:
        avg_rtt = total_rtt / len(rtt_list)
        min_rtt = min(rtt_list)
        max_rtt = max(rtt_list)
        # Jitter = rata-rata selisih absolut antar RTT berurutan
        jitter = sum(abs(rtt_list[i] - rtt_list[i - 1]) for i in range(1, len(rtt_list))) / (len(rtt_list) - 1) if len(rtt_list) > 1 else 0.0
    else:
        avg_rtt = min_rtt = max_rtt = jitter = 0.0

    print("-" * 50)
    print("              HASIL PENGUJIAN QoS               ")
    print("-" * 50)
    print(f"Paket Dikirim  : {paket_dikirim}")
    print(f"Paket Diterima : {paket_diterima}")
    print(f"Packet Loss    : {packet_loss:.2f}%")
    print(f"RTT Min        : {min_rtt:.2f} ms")
    print(f"RTT Avg        : {avg_rtt:.2f} ms")
    print(f"RTT Max        : {max_rtt:.2f} ms")
    print(f"Jitter         : {jitter:.2f} ms")
    print("=" * 50)

def main():
    while True:
        print("\n" + "=" * 50)
        print("             CLIENT JARINGAN KOMPUTER             ")
        print("=" * 50)
        print("1. Request HTTP (Uji coba Proxy Server / Web Server)")
        print("2. Pengujian QoS (Uji coba UDP Echo Server)")
        print("3. Keluar")
        print("=" * 50)
        
        pilihan = input("Pilih menu (1/2/3): ")
        
        if pilihan == '1':
            http_client()
        elif pilihan == '2':
            udp_qos_client()
        elif pilihan == '3':
            print("Terima kasih. Program dihentikan.")
            break
        else:
            print("Pilihan tidak valid, silakan coba lagi.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nProgram dihentikan secara paksa.")
        sys.exit(0)
