# Laporan Akhir Tugas Besar Jaringan Komputer — Modul 8

**Implementasi dan Analisis Kinerja Sistem Client–Proxy–Server Berbasis Socket Python:
Evaluasi Protokol TCP/UDP dan Parameter Quality of Service**

---

## Cover

| | |
|---|---|
| **Mata Kuliah** | Jaringan Komputer |
| **Modul** | 8 — Tugas Besar |
| **Judul** | Implementasi dan Analisis Kinerja Sistem Client–Proxy–Server Berbasis Socket Python |
| **Dosen Pengampu** | *(isi nama dosen)* |
| **Program Studi** | *(isi program studi)* |
| **Universitas** | *(isi nama universitas)* |
| **Tanggal Pengumpulan** | *(isi tanggal)* |

### Anggota Kelompok

| Nama | NIM | Peran |
|------|-----|-------|
| *(Natanael Adrie Christiawan)* | *(103012400334)* | Web Server (`webserver.py`) |
| *(Muhammad Revikhasha Farabi Putera)* | *(NIM103012400287)* | Proxy Server (`proxy.py`) |
| *(Diki Sugiantoro)* | *(103012400401)* | Client (`client.py`) |

---

## 1. Pembagian Tugas

| Anggota | Komponen Utama | Kontribusi Tambahan |
|---------|---------------|---------------------|
| Anggota A | Implementasi `webserver.py` (TCP HTTP + UDP echo server) | Penulisan bagian arsitektur & implementasi web server di laporan, setup GitHub repository |
| Anggota B | Implementasi `proxy.py` (forwarding + caching + error handling) | Penulisan analisis QoS dan multithreading di laporan, capture Wireshark |
| Anggota C | Implementasi `client.py` (HTTP client + UDP QoS pinger) | Penulisan kesimpulan & troubleshooting di laporan, pengujian integrasi multi-client |

---

## 2. Latar Belakang dan Arsitektur Sistem

### 2.1 Latar Belakang

Perkembangan jaringan komputer modern menuntut sistem komunikasi yang andal, efisien, dan terukur secara kuantitatif. Dalam praktiknya, arsitektur jaringan jarang bersifat langsung antara *client* dan *server*, melainkan sering menggunakan komponen perantara (*intermediary*) untuk meningkatkan kontrol, keamanan, dan performa.

Tugas besar ini mengimplementasikan arsitektur **Client–Proxy–Server** menggunakan *socket programming* berbasis Python 3, dengan dua protokol transport utama:

- **TCP** (*Transmission Control Protocol*): *connection-oriented*, andal, menjamin urutan paket — digunakan untuk komunikasi HTTP.
- **UDP** (*User Datagram Protocol*): *connectionless*, ringan — digunakan untuk pengujian QoS (*ping/echo*).

### 2.2 Topologi Sistem

```
Client (client.py)
    │
    │  TCP port 8080 (HTTP)
    │  UDP port 9000 (QoS ping)
    ▼
Proxy Server (proxy.py)  ── port 8080
    │
    │  TCP port 8000 (HTTP forward)
    ▼
Web Server (webserver.py) ── port 8000 (TCP) / 9000 (UDP)
```

Seluruh komunikasi HTTP dari *client* ke *web server* **wajib melewati proxy**. Client tidak diperbolehkan berkomunikasi langsung dengan web server melalui TCP.

### 2.3 Konfigurasi Jaringan

| Komponen | IP Address | Port TCP | Port UDP |
|----------|-----------|----------|----------|
| Web Server (Laptop A) | `192.168.1.10` | 8000 | 9000 |
| Proxy Server (Laptop B) | `192.168.1.11` | 8080 | — |
| Client (Laptop C) | `192.168.1.12` | *ephemeral* | *ephemeral* |

> Catatan: IP di atas adalah contoh. Sesuaikan dengan konfigurasi LAN aktual kelompok.

---

## 3. Implementasi Sistem

### 3.1 Web Server (`webserver.py`) — Anggota A

#### 3.1.1 TCP HTTP Server (port 8000)

Web server menggunakan `socket.SOCK_STREAM` dan model *thread-per-connection* untuk menangani beberapa klien secara simultan.

**Mekanisme utama:**

1. Bind socket ke `0.0.0.0:8000` dan mulai `listen()`
2. Main loop memanggil `accept()` dan melakukan `spawn` thread baru untuk setiap koneksi masuk
3. Setiap thread mem-*parse* HTTP GET request, membaca file dari folder `www/`, lalu mengirim response

**Format response HTTP yang valid:**

```
HTTP/1.1 200 OK\r\n
Content-Type: text/html; charset=utf-8\r\n
Content-Length: <ukuran_file>\r\n
\r\n
<isi file>
```

**Penanganan error:**

| Kondisi | Status Code |
|---------|-------------|
| File tidak ditemukan | `404 Not Found` |
| Error pembacaan file | `500 Internal Server Error` |

**Format log:**
```
[2024-01-15 10:23:45] 192.168.1.11:54321 GET /index.html → 200 OK
```

#### 3.1.2 UDP Echo Server (port 9000)

Server UDP menggunakan `socket.SOCK_DGRAM` dan berjalan di thread terpisah dari TCP server.

**Mekanisme:** menerima paket UDP via `recvfrom()`, lalu langsung mengembalikan (*echo*) payload yang sama tanpa modifikasi menggunakan `sendto()`.

#### 3.1.3 Konkurensi

Dua server (TCP dan UDP) berjalan secara bersamaan menggunakan dua thread `daemon=True`. Main thread hanya melakukan `while True: time.sleep(1)`.

**Cuplikan kode inti:**

```python
import socket, threading, os, time

SERVER_HOST = '0.0.0.0'
TCP_PORT    = 8000
UDP_PORT    = 9000
WWW_DIR     = './www'

def handle_tcp_client(conn, addr):
    # Parse HTTP request, baca file, kirim response
    ...

def run_tcp_server():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((SERVER_HOST, TCP_PORT))
    s.listen(10)
    print(f'[TCP] Server running on port {TCP_PORT}')
    while True:
        conn, addr = s.accept()
        t = threading.Thread(target=handle_tcp_client, args=(conn, addr), daemon=True)
        t.start()

def run_udp_server():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind((SERVER_HOST, UDP_PORT))
    print(f'[UDP] Echo server running on port {UDP_PORT}')
    while True:
        data, addr = s.recvfrom(4096)
        s.sendto(data, addr)

threading.Thread(target=run_tcp_server, daemon=True).start()
threading.Thread(target=run_udp_server, daemon=True).start()
while True:
    time.sleep(1)
```

---

### 3.2 Proxy Server (`proxy.py`) — Anggota B

#### 3.2.1 Forwarding

Proxy menerima HTTP request dari client di port 8080, lalu meneruskannya ke web server di port 8000. Response dari server dikembalikan ke client.

#### 3.2.2 Mekanisme Caching

Cache disimpan sebagai file di direktori `cache/` lokal proxy. Kunci cache adalah path URL (contoh: `/index.html` → `cache/index.html`).

**Alur logika:**

```
Request masuk → parse URL → cek file di cache/
    ├── ADA  → Cache HIT  → kirim dari cache (~1–5 ms)
    └── TIDAK → Cache MISS → forward ke server → simpan cache → kirim ke client (~50–200 ms)
```

#### 3.2.3 Proteksi Race Condition

Operasi tulis ke cache menggunakan `threading.Lock()` untuk mencegah korupsi data saat beberapa thread menulis bersamaan.

```python
cache_lock = threading.Lock()

def save_cache(path, data):
    with cache_lock:
        # tulis file cache
        ...
```

#### 3.2.4 Penanganan Error

| Kondisi | Response ke Client |
|---------|-------------------|
| Server tidak terjangkau / timeout | `504 Gateway Timeout` |
| Server mengembalikan error | `502 Bad Gateway` |

**Format log:**
```
[2024-01-15 10:23:45] 192.168.1.12:54001 /index.html MISS 98.6ms
[2024-01-15 10:23:47] 192.168.1.12:54002 /index.html HIT  2.4ms
```

**Cuplikan kode inti:**

```python
import socket, threading, os, time

PROXY_PORT   = 8080
SERVER_HOST  = '192.168.1.10'
SERVER_PORT  = 8000
CACHE_DIR    = './cache'
cache_lock   = threading.Lock()

os.makedirs(CACHE_DIR, exist_ok=True)

def handle_client(conn, addr):
    # parse request, cek cache, forward atau serve dari cache
    ...

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(('0.0.0.0', PROXY_PORT))
s.listen(10)
print(f'Proxy listening on port {PROXY_PORT}')
while True:
    conn, addr = s.accept()
    threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
```

---

### 3.3 Client (`client.py`) — Anggota C

Client memiliki dua mode operasi yang dipilih via argumen CLI.

#### 3.3.1 Mode TCP (HTTP)

Mengirim HTTP GET request ke proxy dan menampilkan response di terminal.

```bash
python client.py -mode tcp -url /index.html -proxy 192.168.1.11 -port 8080
```

#### 3.3.2 Mode UDP (QoS Ping)

Mengirim minimal 10 paket UDP ke web server dan mengukur parameter QoS.

```bash
python client.py -mode udp -target 192.168.1.10 -port 9000 -count 10
```

**Format payload:** `"Ping <seq> <timestamp>"`

**Timeout per paket:** 1 detik

**Output per paket:**
```
Ping 1: RTT = 2.34 ms
Ping 2: RTT = 2.11 ms
Ping 3: Request timed out
```

**Statistik akhir:**
```
--- QoS Statistics ---
Packets: 10 sent, 9 received, 1 lost (10.0%)
RTT min/avg/max = 1.98/2.24/3.01 ms
Jitter = 0.31 ms
Throughput = X.XX kbps
```

**Cuplikan kode inti:**

```python
import socket, time, statistics, argparse

def udp_ping(target, port, count=10):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(1.0)
    rtts = []
    for seq in range(1, count + 1):
        payload = f"Ping {seq} {time.time()}".encode()
        t_send = time.time()
        s.sendto(payload, (target, port))
        try:
            s.recvfrom(4096)
            rtt = (time.time() - t_send) * 1000
            rtts.append(rtt)
            print(f"Ping {seq}: RTT = {rtt:.2f} ms")
        except socket.timeout:
            print(f"Ping {seq}: Request timed out")
    # hitung statistik
    loss = (count - len(rtts)) / count * 100
    diffs = [abs(rtts[i] - rtts[i-1]) for i in range(1, len(rtts))]
    jitter = statistics.stdev(diffs) if len(diffs) > 1 else 0
    print(f"\nLoss: {loss:.1f}% | RTT min/avg/max: {min(rtts):.2f}/{sum(rtts)/len(rtts):.2f}/{max(rtts):.2f} ms | Jitter: {jitter:.2f} ms")
```

---

## 4. Analisis QoS dan Multithreading

### 4.1 Data Pengukuran QoS

> Isi tabel berikut dengan data nyata hasil pengujian kelompok.

#### Tabel RTT, Packet Loss, dan Jitter (3 skenario)

| Skenario | Min RTT (ms) | Avg RTT (ms) | Max RTT (ms) | Packet Loss (%) | Jitter (ms) |
|----------|-------------|-------------|-------------|-----------------|-------------|
| Idle (0 client lain aktif) | *...* | *...* | *...* | *...* | *...* |
| Beban sedang (3 client concurrent) | *...* | *...* | *...* | *...* | *...* |
| Beban tinggi (5 client concurrent) | *...* | *...* | *...* | *...* | *...* |

#### Tabel Throughput

| Skenario | Total Data (KB) | Durasi (s) | Throughput (kbps) |
|----------|----------------|-----------|------------------|
| Idle | *...* | *...* | *...* |
| Beban sedang | *...* | *...* | *...* |
| Beban tinggi | *...* | *...* | *...* |

### 4.2 Perbandingan Latency Cache HIT vs MISS

| Kondisi | Latency Rata-rata (ms) | Keterangan |
|---------|----------------------|-----------|
| Cache HIT | *...* | Proxy melayani dari lokal |
| Cache MISS | *...* | Proxy forward ke web server |
| Selisih | *...* | Efektivitas caching |

> Sisipkan grafik batang perbandingan HIT vs MISS di sini (screenshot dari terminal atau tool visualisasi).

### 4.3 Perbandingan Satu Client vs Multi-Client

| Metrik | 1 Client | 5 Client Concurrent | Rasio |
|--------|---------|---------------------|-------|
| Avg RTT (ms) | *...* | *...* | *...* |
| Throughput (kbps) | *...* | *...* | *...* |
| Waktu respons maks (ms) | *...* | *...* | *...* |

**Analisis:** *(isi observasi tim — apakah waktu respons meningkat drastis? apakah rasio > 2× yang menjadi batas degradasi performa?)*

### 4.4 Analisis Faktor yang Mempengaruhi QoS

*(Isi berdasarkan observasi nyata. Panduan pertanyaan:)*

- Apakah WiFi vs LAN kabel memberikan perbedaan RTT yang signifikan?
- Apakah ukuran file HTML berpengaruh pada throughput?
- Apakah jumlah thread aktif berpengaruh pada jitter?

### 4.5 Evaluasi Multithreading

**Model yang digunakan:** Thread-per-connection — setiap koneksi masuk di-*spawn* sebagai thread baru.

**Observasi perilaku thread:**

> Sisipkan cuplikan log yang menunjukkan output berselang (*interleaved*) dari beberapa thread. Contoh:
> ```
> [Thread-1] 192.168.1.12:54001 /index.html MISS
> [Thread-3] 192.168.1.12:54003 /page.html MISS
> [Thread-1] 192.168.1.12:54001 /index.html → 200 OK 98.2ms
> [Thread-2] 192.168.1.12:54002 /index.html HIT 2.1ms
> ```

**Race condition pada cache:**

- Apakah terjadi race condition? *(ya/tidak, dan penjelasan)*
- Bagaimana penanganannya? → menggunakan `threading.Lock()` pada operasi tulis cache
- Apakah terjadi korupsi data selama pengujian 5 client concurrent? *(ya/tidak)*

**Estimasi throughput maksimal:**

*(Berdasarkan pengujian, pada berapa client sistem mulai mengalami degradasi performa signifikan? Sebutkan angkanya.)*

---

## 5. Troubleshooting

| Masalah | Penyebab | Solusi yang Diterapkan |
|---------|----------|----------------------|
| `Connection refused` saat client start | Server/proxy belum berjalan atau port salah | Pastikan urutan start: `webserver.py` → `proxy.py` → `client.py` |
| UDP timeout semua paket | Firewall OS memblokir UDP / server crash | Nonaktifkan firewall sementara; pastikan UDP server berjalan di port 9000 |
| Cache tidak berfungsi (selalu MISS) | Direktori `cache/` tidak bisa ditulis / path salah | Periksa izin akses folder; pastikan `os.makedirs` dipanggil saat startup |
| Response HTML kosong | Parsing header HTTP salah, double CRLF tidak terdeteksi | Validasi format request: `GET /path HTTP/1.1\r\nHost: ...\r\n\r\n` |
| Multi-client blocking (client mengantri) | `thread.join()` dipanggil di dalam loop `accept()` | Hapus `join()` dari accept loop; thread berjalan sebagai daemon |
| Korupsi data cache (file terpotong) | Race condition — dua thread menulis ke file yang sama | Implementasi `threading.Lock()` pada fungsi `save_cache()` |
| Wireshark tidak capture traffic | Antarmuka jaringan salah dipilih | Pilih antarmuka aktif (WiFi/LAN); gunakan filter `tcp.port==8000 \|\| tcp.port==8080 \|\| udp.port==9000` |
| *(tambah kendala lain yang ditemui)* | *...* | *...* |

---

## 6. Analisis Wireshark

> Sisipkan screenshot Wireshark untuk setiap poin di bawah ini.

### 6.1 TCP Three-Way Handshake

*(Screenshot: filter `tcp.port==8080`, amati SYN → SYN-ACK → ACK antara client dan proxy)*

### 6.2 Alur HTTP Request/Response

*(Screenshot: amati struktur method, header, status code, dan content-length)*

### 6.3 Paket UDP QoS

*(Screenshot: filter `udp.port==9000`, validasi format payload dan urutan seq)*

### 6.4 Alur Concurrent (5 Client)

*(Screenshot: Statistics → Conversations, amati beberapa aliran TCP simultan)*

### 6.5 Verifikasi Topologi

*(Screenshot log web server: pastikan hanya IP proxy yang tercatat, bukan IP client langsung)*

---

## 7. Kesimpulan dan Saran

### 7.1 Kesimpulan

Melalui tugas besar ini, kelompok berhasil mengimplementasikan sistem Client–Proxy–Server berbasis *socket programming* Python 3 tanpa framework, mencakup:

1. **Web server** berbasis TCP dengan kemampuan melayani file statis dan menangani error HTTP standar (404, 500), serta UDP echo server untuk pengujian QoS.
2. **Proxy server** dengan mekanisme forwarding dan caching yang terbukti mengurangi latency rata-rata dari *(X ms)* (MISS) menjadi *(Y ms)* (HIT).
3. **Client** dengan dua mode operasi (HTTP dan UDP QoS) yang mampu mengukur parameter RTT, packet loss, jitter, dan throughput secara otomatis.
4. Sistem mampu menangani **5 client concurrent** tanpa crash dan tanpa race condition berkat implementasi `threading.Lock()`.

*(Isi capaian spesifik berdasarkan hasil pengujian nyata)*

### 7.2 Keterbatasan Implementasi

- Cache tidak memiliki mekanisme TTL (*time-to-live*) — konten yang sudah kadaluarsa tidak diperbarui secara otomatis.
- Model *thread-per-connection* tidak skalabel untuk ratusan koneksi simultan; lebih tepat menggunakan *thread pool*.
- Tidak ada enkripsi (HTTPS) — komunikasi bersifat plaintext.
- UDP ping hanya mengukur RTT satu arah; tidak ada mekanisme retransmisi.

### 7.3 Saran Pengembangan

- Implementasi **TTL cache** dengan header `Cache-Control` atau batas waktu berbasis `os.path.getmtime()`
- Ganti model threading dengan **thread pool** (`concurrent.futures.ThreadPoolExecutor`) untuk skalabilitas lebih baik
- Tambahkan dukungan **HTTPS** menggunakan modul `ssl` Python
- Implementasi **load balancing** pada proxy untuk mendistribusikan request ke beberapa web server

---

## 8. Referensi

1. Python Software Foundation. *socket — Low-level networking interface*. https://docs.python.org/3/library/socket.html
2. Python Software Foundation. *threading — Thread-based parallelism*. https://docs.python.org/3/library/threading.html
3. Fielding, R., et al. *RFC 7230: HTTP/1.1 Message Syntax and Routing*. IETF, 2014.
4. Postel, J. *RFC 768: User Datagram Protocol*. IETF, 1980.
5. Postel, J. *RFC 793: Transmission Control Protocol*. IETF, 1981.
6. *(Tambahkan referensi lain yang digunakan)*

---

*Laporan ini disusun sebagai bagian dari pemenuhan Tugas Besar Mata Kuliah Jaringan Komputer.*
