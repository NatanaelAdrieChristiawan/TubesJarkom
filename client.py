# client_v2.py
import socket
import sys
import time

def run_http_mode(proxy_host, proxy_port, path):
    """Mode HTTP (TCP): Mengirim permintaan halaman web melalui Proxy Server"""
    print(f"[*] Menjalankan Mode HTTP - Menghubungi Proxy di {proxy_host}:{proxy_port}")
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client_socket.connect((proxy_host, proxy_port))
        # Merakit request HTTP GET sesuai standar RFC
        request = f"GET {path} HTTP/1.1\r\nHost: {proxy_host}\r\nConnection: close\r\n\r\n"
        client_socket.sendall(request.encode('utf-8'))
        
        # Menerima seluruh response stream secara dinamis
        response = b""
        while True:
            chunk = client_socket.recv(4096)
            if not chunk:
                break
            response += chunk
            
        print("\n========== RESPONS DARI PROXY ==========")
        print(response.decode('utf-8', errors='replace'))
        print("========================================")
    except Exception as e:
        print(f"[!] Error Koneksi HTTP: {e}")
    finally:
        client_socket.close()

def run_qos_mode(server_host, server_port):
    """Mode QoS (UDP): Mengukur parameter performa jaringan (RTT, Loss, Jitter)"""
    print(f"[*] Menjalankan Mode QoS UDP - Target Server: {server_host}:{server_port}")
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.settimeout(1.0) # Proteksi anti-freeze jika paket loss
    
    rtts = []
    packets_sent = 10
    packets_received = 0
    
    for seq in range(1, packets_sent + 1):
        timestamp_send = time.time()
        # Format string spesifik sesuai instruksi Soal TUBES
        message = f"Ping {seq} {timestamp_send}"
        try:
            client_socket.sendto(message.encode('utf-8'), (server_host, server_port))
            data, _ = client_socket.recvfrom(2048)
            timestamp_recv = time.time()
            
            rtt = (timestamp_recv - timestamp_send) * 1000 # Mengubah ke milidetik (ms)
            rtts.append(rtt)
            packets_received += 1
            print(f"Reply dari {server_host}: bytes={len(data)} seq={seq} RTT={rtt:.2f} ms")
        except socket.timeout:
            print(f"Request seq={seq} timed out (Batas waktu 1 detik terlampaui)")
        
        time.sleep(0.1) # Jeda pengiriman paket 100ms
        
    client_socket.close()
    
    # Menghitung Analisis Parameter Statistik QoS
    print("\n================ STATISTIK QoS ================")
    if packets_received > 0:
        min_rtt = min(rtts)
        max_rtt = max(rtts)
        avg_rtt = sum(rtts) / packets_received
        
        # Menghitung Fluktuasi Latensi (Jitter) berturutan
        jitter = 0
        if len(rtts) > 1:
            diffs = [abs(rtts[i] - rtts[i-1]) for i in range(1, len(rtts))]
            jitter = sum(diffs) / len(diffs)
            
        loss_pct = ((packets_sent - packets_received) / packets_sent) * 100
        
        print(f" Paket: Dikirim = {packets_sent}, Diterima = {packets_received}, Loss = {loss_pct:.1f}%")
        print(f" Waktu Pulang-Pergi (RTT): Min = {min_rtt:.2f} ms, Max = {max_rtt:.2f} ms, Rata-rata = {avg_rtt:.2f} ms")
        print(f" Jitter (Variasi Latensi): {jitter:.2f} ms")
    else:
        print("[!] Semua paket hilang (Loss = 100%)")
    print("===============================================")

if __name__ == "__main__":
    # Parsing argumen CLI secara aman dan intuitif tanpa dependensi eksternal
    if len(sys.argv) < 3:
        print("Penggunaan:")
        print("  Mode HTTP: python client_v2.py -http [IP_Proxy] [Port_Proxy] [Path_File]")
        print("  Mode QoS : python client_v2.py -qos [IP_Server] [Port_Server]")
        sys.exit(1)
        
    mode = sys.argv[1]
    if mode == "-http" and len(sys.argv) >= 5:
        run_http_mode(sys.argv[2], int(sys.argv[3]), sys.argv[4])
    elif mode == "-qos" and len(sys.argv) >= 4:
        run_qos_mode(sys.argv[2], int(sys.argv[3]))
    else:
        print("[!] Argumen tidak valid.")