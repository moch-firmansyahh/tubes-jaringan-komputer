# Bahan Persiapan Responsi Jaringan Komputer

Berdasarkan output terminal (error) yang kamu dapatkan saat uji coba, berikut adalah rekam jejak (*log*) terminalnya dan daftar pertanyaan yang sangat mungkin ditanyakan oleh asisten praktikum atau dosen saat responsi (tanya jawab).

---

## 1. Log Terminal (Skenario Error Connection Refused)

```text
==================================================
             CLIENT JARINGAN KOMPUTER             
==================================================
1. Request HTTP (Uji coba Proxy Server / Web Server)
2. Pengujian QoS (Uji coba UDP Echo Server)
3. Keluar
==================================================
Pilih menu (1/2/3): 1

--- Fitur HTTP Client (TCP) ---
1. Request via Proxy (Port 8080) - Disarankan untuk test Caching
2. Request langsung ke Web Server (Port 8000)
Masukkan IP Target (contoh: 192.168.1.5, biarkan kosong untuk 127.0.0.1): 10.60.32.1
Pilih target port (1/2): 1
[*] Target diset ke Proxy (Port 8080)
Masukkan path file yang ingin di-request (misal: /HTML/index.html): /HTML/index.html
[*] Menghubungi 10.60.32.1:8080...
[!] Koneksi Ditolak: Pastikan server target sedang berjalan.
```

---

## 2. Prediksi Pertanyaan Responsi & Cara Menjawabnya

Dosen atau asisten praktikum biasanya sangat menyukai mahasiswa yang paham konsep *troubleshooting* (cara memecahkan masalah) jaringan. Jika skenario error di atas terjadi, berikut prediksi pertanyaannya:

### Pertanyaan 1: "Apa maksud dari pesan error `Koneksi Ditolak` (Connection Refused) di situ?"
**Jawaban yang Tepat:** 
Pesan *Connection Refused* berarti paket TCP yang dikirim oleh Client sebenarnya berhasil sampai ke mesin tujuan (IP `10.60.32.1`), **TETAPI** sistem operasi di tujuan menolak koneksi tersebut karena tidak ada aplikasi yang sedang "mendengarkan" (*listening*) di Port `8080`. Berbeda dengan *Timeout*, jika ditolak artinya jalurnya ada, tapi pintunya dikunci.

### Pertanyaan 2: "Menurut kamu, apa penyebab utama dari error tersebut saat menguji dengan 3 perangkat berbeda?"
**Jawaban yang Tepat:** 
Ada beberapa kemungkinan utama, Pak/Bu:
1. **Kesalahan IP Address:** IP `10.60.32.1` mungkin bukan IP lokal (Host) dari Android yang menjalankan Proxy, melainkan IP jaringan lain (seperti jaringan WiFi publik).
2. **AP Isolation:** Jika kami menggunakan WiFi publik (seperti eduroam atau WiFi kampus), biasanya router publik mengaktifkan fitur *Client Isolation*, sehingga memblokir antar-perangkat untuk saling bertukar data demi keamanan.
3. **Konfigurasi Listen IP (BIND):** Proxy di Android mungkin mati (*force close* oleh sistem), atau firewall/OS Android memblokir request masuk ke port 8080.

### Pertanyaan 3: "Lalu bagaimana cara kalian mengatasi masalah arsitektur multi-device tersebut?"
**Jawaban yang Tepat:**
Kami memecahkannya dengan **memastikan semua perangkat berada di dalam satu segmen jaringan lokal (*Local Area Network*) yang sama tanpa restriksi**. Solusi terbaik yang kami pakai adalah menjadikan Android sebagai *Mobile Hotspot*, sehingga Android menjadi *router* (Default Gateway). Kemudian kedua laptop terhubung ke hotspot tersebut. 
Setelah itu, kami memastikan kode `client.py` dan `proxy.py` menggunakan IP Address dinamis dari jaringan hotspot tersebut (misal `192.168.43.x`), bukan lagi ter-*hardcode* ke IP lokal `127.0.0.1` (localhost).

### Pertanyaan 4: "Jelaskan alur data (alur request) saat request berhasil dilakukan melalui Proxy!"
**Jawaban yang Tepat:**
1. **Client** membuat TCP Socket dan mengirim HTTP GET ke IP Proxy (Port 8080).
2. **Proxy** menerima request, lalu mengecek memori *Cache*-nya.
3. Karena ini request pertama (*Cache Miss*), Proxy membuat TCP Socket baru dan mengirim HTTP GET tersebut ke IP Web Server (Port 8000).
4. **Web Server** merespons dengan konten `index.html`.
5. **Proxy** menerima konten tersebut, menyimpannya ke memori (*Caching*), dan meneruskannya kembali ke **Client**.
6. Pada request kedua ke file yang sama, proses 3 dan 4 dilewati (*Cache Hit*).

### Pertanyaan 5: "Apa bedanya UDP yang kalian pakai untuk tes QoS dengan TCP yang dipakai untuk Web Server?"
**Jawaban yang Tepat:**
TCP (*Transmission Control Protocol*) berorientasi pada koneksi (*connection-oriented*) dan menjamin data sampai dengan utuh (ada *three-way handshake*). Sangat cocok untuk transfer file HTML agar file tidak *corrupt*. 
Sedangkan UDP (*User Datagram Protocol*) adalah *connectionless*. Tidak ada jaminan paket sampai, sehingga sangat cepat. Makanya UDP sangat cocok kami gunakan untuk mengirim *ping* guna mengukur RTT (Delay) dan menghitung persentase *Packet Loss*.
