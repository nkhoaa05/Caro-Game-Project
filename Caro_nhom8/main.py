# main.py
import sys
from client import client_handler
from server import server_handler

HOST = "127.0.0.1"
PORT = 5000

def usage():
    print("Usage: python main.py [server|client] [host] [port]")
    print("Examples:")
    print("  python main.py server 0.0.0.0 5000")
    print("  python main.py client 127.0.0.1 5000")

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in {"server", "client", "help"}:
        usage()
        sys.exit(1)

    mode = sys.argv[1]
    host = HOST
    port = PORT
    if len(sys.argv) >= 3:
        host = sys.argv[2]
    if len(sys.argv) >= 4:
        port = int(sys.argv[3])

    if mode == "server":
        print(f"Starting server on {host}:{port}")
        server_handler(host, port)
    elif mode == "client":
        print(f"Starting client connecting to {host}:{port}")
        client_handler(host, port)
    else:
        usage()
