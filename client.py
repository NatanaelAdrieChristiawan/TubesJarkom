import socket
import time
import statistics
import argparse


def tcp_request(proxy_host, proxy_port, url_path):
    request = (
        f'GET {url_path} HTTP/1.1\r\n'
        f'Host: {proxy_host}\r\n'
        f'\r\n'
    ).encode()

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5)

    try:
        start = time.time()
        s.connect((proxy_host, proxy_port))
        s.sendall(request)

        chunks = []
        while True:
            chunk = s.recv(4096)
            if not chunk:
                break
            chunks.append(chunk)

        elapsed = (time.time() - start) * 1000
        response = b''.join(chunks)

        header_end = response.find(b'\r\n\r\n')
        if header_end == -1:
            print('Error: Malformed response (no header boundary)')
            return

        header_part = response[:header_end].decode('utf-8', errors='replace')
        body_part = response[header_end + 4:]

        print(f'--- Response from {proxy_host}:{proxy_port} ---')
        print(f'URL: {url_path}')
        print(f'Time: {elapsed:.2f} ms')
        print(f'--- Headers ---')
        print(header_part)
        print(f'--- Body ({len(body_part)} bytes) ---')
        print(body_part.decode('utf-8', errors='replace'))

    except socket.timeout:
        print(f'Error: Connection timed out to {proxy_host}:{proxy_port}')
    except ConnectionRefusedError:
        print(f'Error: Connection refused by {proxy_host}:{proxy_port}')
    except Exception as e:
        print(f'Error: {e}')
    finally:
        s.close()


def udp_ping(target, port, count):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(1.0)

    rtts = []
    total_bytes_sent = 0
    total_bytes_received = 0
    test_start = time.time()

    print(f'Pinging {target}:{port} with {count} packets...\n')

    for seq in range(1, count + 1):
        payload = f'Ping {seq} {time.time()}'.encode()
        total_bytes_sent += len(payload)
        t_send = time.time()

        s.sendto(payload, (target, port))

        try:
            data, _ = s.recvfrom(4096)
            rtt = (time.time() - t_send) * 1000
            total_bytes_received += len(data)
            rtts.append(rtt)
            print(f'Ping {seq}: RTT = {rtt:.2f} ms')
        except socket.timeout:
            print(f'Ping {seq}: Request timed out')

    s.close()
    test_duration = time.time() - test_start

    sent = count
    received = len(rtts)
    lost = sent - received
    loss_pct = (lost / sent) * 100

    print(f'\n--- QoS Statistics ---')
    print(f'Packets: {sent} sent, {received} received, {lost} lost ({loss_pct:.1f}%)')

    if rtts:
        rtt_min = min(rtts)
        rtt_avg = sum(rtts) / len(rtts)
        rtt_max = max(rtts)
        print(f'RTT min/avg/max = {rtt_min:.2f}/{rtt_avg:.2f}/{rtt_max:.2f} ms')

        if len(rtts) > 1:
            diffs = [abs(rtts[i] - rtts[i - 1]) for i in range(1, len(rtts))]
            jitter = statistics.mean(diffs)
            print(f'Jitter = {jitter:.2f} ms')
        else:
            print('Jitter = N/A (need at least 2 successful pings)')

        total_bits = (total_bytes_sent + total_bytes_received) * 8
        throughput_kbps = (total_bits / test_duration) / 1000 if test_duration > 0 else 0
        print(f'Throughput = {throughput_kbps:.2f} kbps')
    else:
        print('No successful pings — cannot compute statistics')


def main():
    parser = argparse.ArgumentParser(description='Client for TCP HTTP and UDP QoS testing')

    parser.add_argument('-mode', required=True, choices=['tcp', 'udp'],
                        help='Operation mode: tcp (HTTP request) or udp (QoS ping)')
    parser.add_argument('-url', default='/index.html',
                        help='URL path for TCP mode (default: /index.html)')
    parser.add_argument('-proxy', default='127.0.0.1',
                        help='Proxy/target host address')
    parser.add_argument('-target', default='127.0.0.1',
                        help='Target host for UDP mode')
    parser.add_argument('-port', type=int, default=8080,
                        help='Port number (default: 8080 for TCP, 9000 for UDP)')
    parser.add_argument('-count', type=int, default=10,
                        help='Number of UDP ping packets (default: 10)')

    args = parser.parse_args()

    if args.mode == 'tcp':
        tcp_request(args.proxy, args.port, args.url)
    else:
        port = args.port if args.port != 8080 else 9000
        udp_ping(args.target, port, args.count)


if __name__ == '__main__':
    main()
