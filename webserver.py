import socket
import threading
import os
import time
from datetime import datetime

SERVER_HOST = '0.0.0.0'
TCP_PORT = 8000
UDP_PORT = 9000
WWW_DIR = './HTML'

CONTENT_TYPES = {
    '.html': 'text/html; charset=utf-8',
    '.css': 'text/css; charset=utf-8',
    '.js': 'application/javascript; charset=utf-8',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.gif': 'image/gif',
    '.mp4': 'video/mp4',
    '.txt': 'text/plain; charset=utf-8',
    '.ico': 'image/x-icon',
}


def log(protocol, message):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f'[{timestamp}] [{protocol}] {message}')


def get_content_type(path):
    ext = os.path.splitext(path)[1].lower()
    return CONTENT_TYPES.get(ext, 'application/octet-stream')


def build_response(status_code, status_text, body=b'', content_type='text/html; charset=utf-8'):
    header = (
        f'HTTP/1.1 {status_code} {status_text}\r\n'
        f'Content-Type: {content_type}\r\n'
        f'Content-Length: {len(body)}\r\n'
        f'\r\n'
    )
    return header.encode() + body


def load_error_page(status_code):
    error_file = os.path.join(WWW_DIR, 'status', f'{status_code}.html')
    if os.path.isfile(error_file):
        with open(error_file, 'rb') as f:
            return f.read()
    return f'<h1>{status_code}</h1>'.encode()


def handle_tcp_client(conn, addr):
    try:
        raw_request = conn.recv(4096).decode('utf-8', errors='replace')
        if not raw_request:
            return

        request_line = raw_request.split('\r\n')[0]
        parts = request_line.split()
        if len(parts) < 2 or parts[0] != 'GET':
            body = load_error_page(500)
            response = build_response(400, 'Bad Request', body)
            conn.sendall(response)
            log('TCP', f'{addr[0]}:{addr[1]} {request_line} -> 400 Bad Request')
            return

        path = parts[1]
        if path == '/':
            path = '/index.html'

        safe_path = os.path.normpath(path).lstrip('/')
        file_path = os.path.join(WWW_DIR, safe_path)

        if not os.path.isfile(file_path):
            body = load_error_page(404)
            response = build_response(404, 'Not Found', body)
            conn.sendall(response)
            log('TCP', f'{addr[0]}:{addr[1]} GET {path} -> 404 Not Found')
            return

        try:
            with open(file_path, 'rb') as f:
                body = f.read()
            content_type = get_content_type(file_path)
            response = build_response(200, 'OK', body, content_type)
            conn.sendall(response)
            log('TCP', f'{addr[0]}:{addr[1]} GET {path} -> 200 OK')
        except Exception as e:
            body = load_error_page(500)
            response = build_response(500, 'Internal Server Error', body)
            conn.sendall(response)
            log('TCP', f'{addr[0]}:{addr[1]} GET {path} -> 500 Internal Server Error ({e})')

    except Exception as e:
        log('TCP', f'{addr[0]}:{addr[1]} Connection error: {e}')
    finally:
        conn.close()


def run_tcp_server():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((SERVER_HOST, TCP_PORT))
    s.listen(10)
    log('TCP', f'HTTP Server running on port {TCP_PORT}')

    while True:
        conn, addr = s.accept()
        t = threading.Thread(target=handle_tcp_client, args=(conn, addr), daemon=True)
        t.start()


def run_udp_server():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind((SERVER_HOST, UDP_PORT))
    log('UDP', f'Echo server running on port {UDP_PORT}')

    while True:
        data, addr = s.recvfrom(4096)
        s.sendto(data, addr)
        log('UDP', f'Echo {len(data)} bytes to {addr[0]}:{addr[1]}')


if __name__ == '__main__':
    os.makedirs(WWW_DIR, exist_ok=True)

    threading.Thread(target=run_tcp_server, daemon=True).start()
    threading.Thread(target=run_udp_server, daemon=True).start()

    log('MAIN', f'Web Server started (TCP:{TCP_PORT}, UDP:{UDP_PORT})')
    log('MAIN', f'Serving files from: {os.path.abspath(WWW_DIR)}')

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log('MAIN', 'Server shutting down')
