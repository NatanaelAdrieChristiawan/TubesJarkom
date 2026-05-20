import socket
import threading
import os
import time
from datetime import datetime

PROXY_HOST = '0.0.0.0'
PROXY_PORT = 8080
SERVER_HOST = '127.0.0.1'
SERVER_PORT = 8000
CACHE_DIR = './cache'
FORWARD_TIMEOUT = 5
BUFFER_SIZE = 4096

cache_lock = threading.Lock()

ERROR_PAGES_DIR = './HTML/status'


def log(message):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    thread_name = threading.current_thread().name
    print(f'[{timestamp}] [{thread_name}] {message}')


def get_cache_path(url_path):
    safe = url_path.lstrip('/') or 'index.html'
    return os.path.join(CACHE_DIR, safe)


def read_cache(cache_path):
    if os.path.isfile(cache_path):
        with open(cache_path, 'rb') as f:
            return f.read()
    return None


def save_cache(cache_path, data):
    with cache_lock:
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        with open(cache_path, 'wb') as f:
            f.write(data)


def load_error_page(status_code):
    error_file = os.path.join(ERROR_PAGES_DIR, f'{status_code}.html')
    if os.path.isfile(error_file):
        with open(error_file, 'rb') as f:
            return f.read()
    return f'<h1>{status_code}</h1>'.encode()


def build_error_response(status_code, status_text):
    body = load_error_page(status_code)
    header = (
        f'HTTP/1.1 {status_code} {status_text}\r\n'
        f'Content-Type: text/html; charset=utf-8\r\n'
        f'Content-Length: {len(body)}\r\n'
        f'\r\n'
    )
    return header.encode() + body


def forward_to_server(request_data):
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.settimeout(FORWARD_TIMEOUT)
    try:
        server_sock.connect((SERVER_HOST, SERVER_PORT))
        server_sock.sendall(request_data)

        chunks = []
        while True:
            chunk = server_sock.recv(BUFFER_SIZE)
            if not chunk:
                break
            chunks.append(chunk)

        return b''.join(chunks)
    finally:
        server_sock.close()


def extract_status_code(response_data):
    try:
        status_line = response_data.split(b'\r\n')[0].decode()
        return int(status_line.split()[1])
    except (IndexError, ValueError):
        return 0


def handle_client(conn, addr):
    try:
        raw_request = conn.recv(BUFFER_SIZE)
        if not raw_request:
            return

        request_text = raw_request.decode('utf-8', errors='replace')
        request_line = request_text.split('\r\n')[0]
        parts = request_line.split()

        if len(parts) < 2:
            conn.sendall(build_error_response(400, 'Bad Request'))
            return

        url_path = parts[1]
        if url_path == '/':
            url_path = '/index.html'

        cache_path = get_cache_path(url_path)
        start_time = time.time()

        cached_data = read_cache(cache_path)
        if cached_data is not None:
            conn.sendall(cached_data)
            elapsed = (time.time() - start_time) * 1000
            log(f'{addr[0]}:{addr[1]} {url_path} HIT {elapsed:.1f}ms')
            return

        try:
            response_data = forward_to_server(raw_request)
        except socket.timeout:
            conn.sendall(build_error_response(504, 'Gateway Timeout'))
            elapsed = (time.time() - start_time) * 1000
            log(f'{addr[0]}:{addr[1]} {url_path} TIMEOUT {elapsed:.1f}ms')
            return
        except (ConnectionRefusedError, OSError):
            conn.sendall(build_error_response(504, 'Gateway Timeout'))
            elapsed = (time.time() - start_time) * 1000
            log(f'{addr[0]}:{addr[1]} {url_path} SERVER_UNREACHABLE {elapsed:.1f}ms')
            return

        status_code = extract_status_code(response_data)
        if status_code >= 500:
            conn.sendall(build_error_response(502, 'Bad Gateway'))
            elapsed = (time.time() - start_time) * 1000
            log(f'{addr[0]}:{addr[1]} {url_path} BAD_GATEWAY {elapsed:.1f}ms')
            return

        if status_code == 200:
            save_cache(cache_path, response_data)

        conn.sendall(response_data)
        elapsed = (time.time() - start_time) * 1000
        log(f'{addr[0]}:{addr[1]} {url_path} MISS {elapsed:.1f}ms')

    except Exception as e:
        log(f'{addr[0]}:{addr[1]} Error: {e}')
    finally:
        conn.close()


if __name__ == '__main__':
    os.makedirs(CACHE_DIR, exist_ok=True)

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((PROXY_HOST, PROXY_PORT))
    s.listen(10)

    log(f'Proxy listening on port {PROXY_PORT} -> forwarding to {SERVER_HOST}:{SERVER_PORT}')

    try:
        while True:
            conn, addr = s.accept()
            t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            t.start()
    except KeyboardInterrupt:
        log('Proxy shutting down')
