# webserver_v2.py
import os
import socket
import threading
import time
from datetime import datetime

SERVER_HOST = '0.0.0.0'
TCP_PORT = 8000
UDP_PORT = 9000
BASE_DIR = os.path.abspath("html") # Menentukan root direktori web secara absolut

def get_content_type(filepath):
    """Menentukan ekstensi konten HTTP secara dinamis sesuai standar browser"""
    ext = os.path.splitext(filepath)[1].lower()
    if ext == '.html': return 'text/html'
    if ext == '.css': return 'text/css'
    if ext == '.js': return 'application/javascript'
    if ext == '.png': return 'image/png'
    if ext == '.jpg' or ext == '.jpeg': return 'image/jpeg'
    return 'application/octet-stream'

def handle_tcp_client(connection_socket, client_addr):
    try:
        # Pembacaan request non-blocking yang aman
        request_data = connection_socket.recv(2048)
        if not request_data:
            return
            
        request_string = request_data.decode('utf-8', errors='ignore')
        lines = request_string.split("\r\n")
        if len(lines) == 0 or len(lines[0].split()) < 2:
            return
            
        first_line = lines[0].split()
        method = first_line[0]
        url_path = first_line[1]
        
        if url_path == "/" or url_path == "":
            url_path = "/index.html"
            
        # --- PERBAIKAN SECURITY: PROTEKSI PATH TRAVERSAL ---
        # Membersihkan path dan merakit ke lokasi absolut direktori html
        target_path = os.path.abspath(os.path.join(BASE_DIR, url_path.lstrip("/")))
        
        # Cetak log aktivitas server sesuai spesifikasi dokumen TUBES
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] TCP Request dari {client_addr[0]} -> {method} {url_path}")
        
        # Validasi apakah folder tujuan berada di bawah kendali direktori BASE_DIR
        if not target_path.startswith(BASE_DIR):
            body = "<html><body><h1>403 Forbidden</h1><p>Akses ditolak.</p></body></html>"
            response = f"HTTP/1.1 403 Forbidden\r\nContent-Type: text/html\r\nContent-Length: {len(body)}\r\n\r\n{body}"
            connection_socket.sendall(response.encode())
            return

        # --- PROSES UNTUK MEMBACA ASSET FILE ---
        try:
            # Membaca file dengan mode biner universal (rb) untuk menjamin file gambar aman
            with open(target_path, 'rb') as f:
                content = f.read()
                
            content_type = get_content_type(target_path)
            header = f"HTTP/1.1 200 OK\r\nContent-Type: {content_type}\r\nContent-Length: {len(content)}\r\nConnection: close\r\n\r\n"
            
            # Kirim header teks dan biner body secara utuh
            connection_socket.sendall(header.encode() + content)
            
        except FileNotFoundError:
            body = "<html><body><h1>410 Not Found</h1><p>Halaman praktikum tidak ditemukan.</p></body></html>"
            response = f"HTTP/1.1 404 Not Found\r\nContent-Type: text/html\r\nContent-Length: {len(body)}\r\nConnection: close\r\n\r\n{body}"
            connection_socket.sendall(response.encode())
            
    except Exception as e:
        # Proteksi Error 500: Menjaga server tetap hidup jika terjadi kegagalan tidak terduga
        body = "<html><body><h1>500 Internal Server Error</h1></body></html>"
        err_res = f"HTTP/1.1 500 Internal Server Error\r\nContent-Length: {len(body)}\r\n\r\n{body}"
        try: connection_socket.sendall(err_res.encode()) 
        except: pass
    finally:
        connection_socket.close()

def start_tcp_server():
    """Mengelola lalu lintas web HTTP berbasis koneksi TCP"""
    tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    tcp_socket.bind((SERVER_HOST, TCP_PORT))
    tcp_socket.listen(15)
    print(f"[*] Web Server TCP aktif mendengarkan di port {TCP_PORT}")
    
    while True:
        conn, addr = tcp_socket.accept()
        t = threading.Thread(target=handle_tcp_client, args=(conn, addr))
        t.daemon = True
        t.start()

def start_udp_echo_server():
    """Mengelola pemantulan paket pinger berbasis komunikasi UDP"""
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind((SERVER_HOST, UDP_PORT))
    print(f"[*] UDP Echo Server aktif mendengarkan di port {UDP_PORT}")
    
    while True:
        try:
            data, client_addr = udp_socket.recvfrom(2048)
            # Menampilkan log kedatangan pinger di konsol server
            # Format pesan pinger: "Ping <seq> <timestamp>"
            msg = data.decode('utf-8', errors='ignore')
            print(f"[QoS Log] Menerima UDP echo dari {client_addr}: {msg}")
            
            # Pantulkan kembali pesan secara instan tanpa modifikasi
            udp_socket.sendto(data, client_addr)
        except Exception as e:
            print(f"[!] UDP Server Error: {e}")

if __name__ == "__main__":
    # Menjamin pembuatan direktori placeholder html untuk kemudahan pengujian pertama
    if not os.path.exists("html"):
        os.makedirs("html")
        with open("html/index.html", "w") as f:
            f.write("<html><body><h1>Selamat Datang di Laboratorium Informatika</h1></body></html>")
            
    # Menjalankan Server TCP dan Server UDP secara simultan menggunakan multi-threading induk
    tcp_thread = threading.Thread(target=start_tcp_server)
    udp_thread = threading.Thread(target=start_udp_echo_server)
    
    tcp_thread.daemon = True
    udp_thread.daemon = True
    
    tcp_thread.start()
    udp_thread.start()
    
    # Menjaga thread utama tetap hidup mengawal kedua layanan background
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[*] Mematikan seluruh layanan Web Server. Selesai.")