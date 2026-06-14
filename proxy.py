# proxy_v2.py
import socket
import threading
import time

PROXY_HOST = '0.0.0.0' # Portable: Mendengarkan semua interface lokal
PROXY_PORT = 8080
WEB_SERVER_HOST = '127.0.0.1' # IP default Web Server tujuan
WEB_SERVER_PORT = 8000

# Manajemen Cache Thread-Safe dengan TTL Expiration
cache = {} # Key: path, Value: {"data": bytes, "expiry": timestamp}
cache_lock = threading.Lock()
CACHE_TTL = 15 # Waktu kedaluwarsa cache (15 detik)

def handle_client(client_socket, client_addr):
    try:
        # Membaca request header secara aman hingga delimiter baris ganda
        request_data = b""
        while b"\r\n\r\n" not in request_data:
            chunk = client_socket.recv(1024)
            if not chunk:
                break
            request_data += chunk
            
        if not request_data:
            return
            
        request_string = request_data.decode('utf-8', errors='ignore')
        lines = request_string.split("\r\n")
        if len(lines) == 0 or len(lines[0].split()) < 2:
            return
            
        first_line = lines[0].split()
        method = first_line[0]
        path = first_line[1]
        
        if method != "GET":
            # Menolak metode selain GET secara elegan
            err_response = "HTTP/1.1 405 Method Not Allowed\r\nContent-Length: 0\r\n\r\n"
            client_socket.sendall(err_response.encode())
            return

        # --- EVALUASI MEKANISME CACHE ---
        current_time = time.time()
        with cache_lock:
            if path in cache and current_time < cache[path]["expiry"]:
                print(f"[CACHE HIT] Melayani {path} langsung dari memori lokal Proxy.")
                client_socket.sendall(cache[path]["data"])
                return

        print(f"[CACHE MISS] Meminta {path} dari Web Server utama.")
        
        # --- HUBUNGKAN KE WEB SERVER UTAMA ---
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.settimeout(3.0) # Batas tunggu koneksi ke server backend
        try:
            server_socket.connect((WEB_SERVER_HOST, WEB_SERVER_PORT))
            server_socket.sendall(request_data) # Meneruskan request client asli
            
            # Membaca seluruh response balik dari server utama
            server_response = b""
            while True:
                response_chunk = server_socket.recv(4096)
                if not response_chunk:
                    break
                server_response += response_chunk
                
            # Simpan data respons valid ke dalam tabel cache global
            if b"200 OK" in server_response:
                with cache_lock:
                    cache[path] = {
                        "data": server_response,
                        "expiry": time.time() + CACHE_TTL
                    }
                    print(f"[*] Berhasil memperbarui Cache untuk path: {path}")
            
            # Kirim balik respons web server ke klien asal
            client_socket.sendall(server_response)
        except (ConnectionRefusedError, socket.timeout):
            # Penanganan Graceful Error 502/504 menggantikan crash server
            print(f"[!] Gagal terhubung ke Web Server. Mengirimkan 502 Bad Gateway.")
            body = "<html><body><h1>502 Bad Gateway</h1><p>Web Server utama tidak terjangkau.</p></body></html>"
            gateway_err = f"HTTP/1.1 502 Bad Gateway\r\nContent-Type: text/html\r\nContent-Length: {len(body)}\r\nConnection: close\r\n\r\n{body}"
            client_socket.sendall(gateway_err.encode())
        finally:
            server_socket.close()
            
    except Exception as e:
        print(f"[!] Internal Proxy Error: {e}")
    finally:
        client_socket.close()

def main():
    proxy_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    proxy_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # Anti port-locking
    try:
        proxy_server.bind((PROXY_HOST, PROXY_PORT))
        proxy_server.listen(10)
        print(f"[*] Proxy Server aktif dan mendengarkan di http://localhost:{PROXY_PORT}")
        
        while True:
            client_sock, client_addr = proxy_server.accept()
            # Multithreading per koneksi masuk berjalan secara konkuren
            thread = threading.Thread(target=handle_client, args=(client_sock, client_addr))
            thread.daemon = True
            thread.start()
    except Exception as e:
        print(f"[!] Gagal memulai Proxy: {e}")
    finally:
        proxy_server.close()

if __name__ == "__main__":
    main()