# Tugas Besar Jaringan Komputer — Modul 8

## Implementasi dan Analisis Kinerja Sistem Client–Proxy–Server Berbasis Socket Python

Proyek ini mengimplementasikan arsitektur **Client–Proxy–Server** menggunakan socket programming Python 3 murni (tanpa framework), mencakup protokol **TCP** untuk komunikasi HTTP dan **UDP** untuk pengujian Quality of Service (QoS).

---

## Anggota Kelompok

| Nama | NIM | Peran |
|------|-----|-------|
| Natanael Adrie Christiawan | 103012400334 | Web Server (`webserver.py`) |
| Muhammad Revikhasha Farabi Putera | 103012400287 | Proxy Server (`proxy.py`) |
| Diki Sugiantoro | 103012400401 | Client (`client.py`) |

---

## Arsitektur Sistem

```
Client (client.py)
    │
    │  TCP port 8080 (HTTP request)
    │  UDP port 9000 (QoS ping)
    ▼
Proxy Server (proxy.py)  ── port 8080
    │
    │  TCP port 8000 (HTTP forward)
    ▼
Web Server (webserver.py) ── port 8000 (TCP) / 9000 (UDP)
```

Semua HTTP request dari client ke web server **wajib melewati proxy**. Client tidak boleh berkomunikasi langsung ke web server via TCP.

---

## Struktur Direktori

```
Tubes/
├── webserver.py          # TCP HTTP server + UDP echo server
├── proxy.py              # Forwarding proxy dengan caching
├── client.py             # HTTP client + UDP QoS pinger
├── README.md
├── HTML/                 # Konten web statis
│   ├── index.html        # Halaman utama
│   ├── osi.html          # Materi OSI Model
│   ├── tcpip.html        # Materi TCP/IP
│   ├── qos.html          # Materi Quality of Service
│   ├── implementation.html  # Materi Socket Programming
│   ├── css/
│   │   └── style.css     # Stylesheet utama
│   ├── assets/
│   │   ├── iflab.png     # Logo IFLAB
│   │   ├── network.png   # Gambar jaringan
│   │   ├── osi.png       # Diagram OSI
│   │   ├── osi.mp4       # Video penjelasan OSI
│   │   ├── tcpip.png     # Diagram TCP/IP
│   │   └── tcpip-flow.png
│   └── status/
│       ├── 404.html      # Custom error: Not Found
│       ├── 500.html      # Custom error: Internal Server Error
│       ├── 502.html      # Custom error: Bad Gateway
│       └── 504.html      # Custom error: Gateway Timeout
└── cache/                # Auto-generated cache proxy
```

---

## Cara Menjalankan

### Prasyarat

- Python 3.6 atau lebih baru
- Tidak memerlukan library external (hanya standard library)

### 1. Jalankan Web Server

```bash
python3 webserver.py
```

Output:
```
[2026-05-20 17:00:00] [MAIN] Web Server started (TCP:8000, UDP:9000)
[2026-05-20 17:00:00] [TCP] HTTP Server running on port 8000
[2026-05-20 17:00:00] [UDP] Echo server running on port 9000
```

### 2. Jalankan Proxy Server

```bash
python3 proxy.py
```

Output:
```
[2026-05-20 17:00:05] [MainThread] Proxy listening on port 8080 -> forwarding to 127.0.0.1:8000
```

### 3. Jalankan Client

**Mode TCP (HTTP request via proxy):**

```bash
python3 client.py -mode tcp -url /index.html -proxy 127.0.0.1 -port 8080
```

**Mode UDP (QoS ping ke web server):**

```bash
python3 client.py -mode udp -target 127.0.0.1 -port 9000 -count 10
```

### 4. Akses via Browser

Buka browser dan kunjungi `http://localhost:8080` untuk mengakses melalui proxy, atau `http://localhost:8000` untuk langsung ke web server.

---

## Konfigurasi Jaringan (Multi-Laptop via WiFi)

Ketiga laptop cukup terhubung ke **WiFi yang sama**. Selama berada di satu jaringan WiFi, semua device sudah berada dalam satu LAN dan bisa saling berkomunikasi.

### Langkah 1 — Cari IP Address Masing-masing Laptop

Jalankan perintah berikut di terminal setiap laptop:

| OS | Perintah |
|----|----------|
| **macOS** | `ipconfig getifaddr en0` |
| **Linux** | `hostname -I` |
| **Windows** | `ipconfig` → cari **IPv4 Address** pada adapter Wi-Fi |

Contoh hasil (IP akan berbeda tergantung router WiFi):

| Komponen | Laptop | Contoh IP | Port TCP | Port UDP |
|----------|--------|-----------|----------|----------|
| Web Server | Laptop A | `192.168.18.5` | 8000 | 9000 |
| Proxy Server | Laptop B | `192.168.18.8` | 8080 | — |
| Client | Laptop C | `192.168.18.12` | *ephemeral* | *ephemeral* |

> **Catatan:** IP di atas hanya contoh. Ganti dengan IP asli dari setiap laptop.

### Langkah 2 — Konfigurasi Proxy

Pada laptop **Proxy (B)**, ubah `SERVER_HOST` di `proxy.py` ke IP laptop **Web Server (A)**:

```python
SERVER_HOST = '192.168.18.5'  # ganti dengan IP laptop Web Server
```

### Langkah 3 — Jalankan Secara Berurutan

```bash
# Laptop A — Web Server
python3 webserver.py

# Laptop B — Proxy Server
python3 proxy.py

# Laptop C — Client (TCP via proxy)
python3 client.py -mode tcp -url /index.html -proxy 192.168.18.8 -port 8080

# Laptop C — Client (UDP langsung ke web server)
python3 client.py -mode udp -target 192.168.18.5 -port 9000 -count 10
```

### Langkah 4 — Pastikan Firewall Tidak Memblokir

Jika koneksi gagal, pastikan firewall di laptop Web Server dan Proxy mengizinkan koneksi masuk:

| OS | Cara |
|----|------|
| **macOS** | System Settings → Network → Firewall → matikan sementara, atau izinkan Python |
| **Windows** | Settings → Windows Security → Firewall → Allow an app → izinkan Python |
| **Linux** | `sudo ufw allow 8000,8080,9000/tcp && sudo ufw allow 9000/udp` |

---

## Fitur Utama

### Web Server (`webserver.py`)
- HTTP server berbasis TCP socket (port 8000)
- UDP echo server untuk QoS testing (port 9000)
- Thread-per-connection untuk concurrency
- Serving file statis dari folder `HTML/`
- Custom error pages (404, 500)
- Content-Type detection otomatis (HTML, CSS, PNG, JPG, MP4)

### Proxy Server (`proxy.py`)
- Forwarding HTTP request ke web server
- File-based caching di folder `cache/`
- `threading.Lock()` untuk proteksi race condition
- Custom error pages (502 Bad Gateway, 504 Gateway Timeout)
- Logging dengan cache HIT/MISS dan response time

### Client (`client.py`)
- Mode TCP: HTTP GET request melalui proxy
- Mode UDP: QoS ping dengan statistik lengkap
- Pengukuran: RTT, packet loss, jitter, throughput
- CLI dengan argparse

---

## Parameter QoS yang Diukur

| Parameter | Definisi |
|-----------|----------|
| **RTT** | Round-Trip Time — waktu paket pergi dan kembali |
| **Packet Loss** | Persentase paket yang hilang |
| **Jitter** | Variasi delay antar paket berurutan |
| **Throughput** | Kecepatan transfer data (kbps) |

---

## Contoh Output UDP QoS

```
Pinging 127.0.0.1:9000 with 10 packets...

Ping 1: RTT = 0.24 ms
Ping 2: RTT = 0.10 ms
Ping 3: RTT = 0.09 ms
...

--- QoS Statistics ---
Packets: 10 sent, 10 received, 0 lost (0.0%)
RTT min/avg/max = 0.06/0.10/0.24 ms
Jitter = 0.03 ms
Throughput = 3566.81 kbps
```

---

## Troubleshooting

| Masalah | Solusi |
|---------|--------|
| `Connection refused` | Pastikan urutan start: `webserver.py` → `proxy.py` → `client.py` |
| `Address already in use` | Kill proses lama: `lsof -ti:8000,8080,9000 \| xargs kill -9` |
| UDP timeout semua paket | Nonaktifkan firewall; pastikan UDP server berjalan |
| Cache selalu MISS | Periksa izin folder `cache/`; pastikan `os.makedirs` berjalan |
| Response kosong | Validasi format HTTP request menggunakan `\r\n\r\n` |

---

## Teknologi

- **Bahasa:** Python 3 (standard library only)
- **Protokol:** TCP (HTTP), UDP (echo/ping)
- **Concurrency:** `threading` (thread-per-connection, daemon threads)
- **Caching:** File-based dengan `threading.Lock()`

---

## Panduan Diagnostik & Solusi Masalah Jaringan (WiFi)

Jika laptop Proxy atau Client gagal terhubung ke Web Server meskipun sudah menggunakan WiFi yang sama, ikuti langkah diagnostik berikut:

### 1. Masalah Terbesar: AP Isolation (Isolasi Klien)
Banyak router WiFi (terutama WiFi Kampus, Kost, atau Kafe) mengaktifkan fitur **AP Isolation**. Fitur ini memblokir komunikasi antar perangkat yang terhubung ke router yang sama.

* **Cara Test:** Buka Terminal/CMD di laptop Proxy, lakukan ping ke IP Web Server:
  ```bash
  ping <IP_WEB_SERVER>
  # Contoh: ping 192.168.1.101
  ```
* **Solusi:** Jika hasilnya *Timed Out*, gunakan **Hotspot Tethering HP** salah satu anggota. Hubungkan semua laptop ke hotspot tersebut, lalu perbarui IP masing-masing.

### 2. Ubah Profil WiFi ke Private (Khusus Windows)
Windows secara default mengatur WiFi baru ke profil *Public* yang memblokir semua port koneksi masuk.
* **Solusi:** Klik ikon WiFi -> **Properties** -> Ubah Network Profile dari **Public** ke **Private** agar Windows Defender mengizinkan lalu lintas data lokal.

### 3. Tes Port Menggunakan Netcat / PowerShell
Untuk memastikan port server terbuka dan bisa dijangkau:
* **macOS/Linux (di laptop Proxy):**
  ```bash
  nc -zv <IP_WEB_SERVER> 8000
  # Harus mengembalikan status: Connection to ... port 8000 [tcp] succeeded!
  ```
* **Windows PowerShell (di laptop Proxy):**
  ```powershell
  Test-NetConnection -ComputerName <IP_WEB_SERVER> -Port 8000
  # Pastikan TcpTestSucceeded: True
  ```

### 4. Ganti Port jika Terjadi Konflik (Address already in use)
Jika port `8080` (proxy) atau `8000` (web server) sudah dipakai oleh aplikasi lain:
* Cari dan matikan aplikasi tersebut:
  ```bash
  # macOS/Linux
  lsof -ti:8080,8000 | xargs kill -9
  ```
* Atau ubah variabel port di file kode (`webserver.py` atau `proxy.py`) ke port alternatif seperti `8082`, `8888`, atau `9999`.

---

## Referensi

1. Python `socket` — https://docs.python.org/3/library/socket.html
2. Python `threading` — https://docs.python.org/3/library/threading.html
3. RFC 7230 — HTTP/1.1 Message Syntax and Routing
4. RFC 768 — User Datagram Protocol
5. RFC 793 — Transmission Control Protocol
