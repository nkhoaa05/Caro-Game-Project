import sys

from client import client_handler
from server import server_handler

HOST = "127.0.0.1"
PORT = 5000

if len(sys.argv) == 1 or sys.argv[1] not in {"server", "client", "help"}:
    print("Usage: python main.py [server|client] [host] [port]")
    sys.exit(1)

if sys.argv[1] == "help":
    print("Usage: python main.py [server|client] [host] [port]")
    print("Example: python main.py server 0.0.0.0 5000")
    print("Example: python main.py client 192.168.1.42 5000")
    sys.exit(0)

if len(sys.argv) >= 3:
    HOST = sys.argv[2]

if len(sys.argv) == 4:
    PORT = int(sys.argv[3])

if sys.argv[1] == "server":
    server_handler(HOST, PORT)

elif sys.argv[1] == "client":
    client_handler(HOST, PORT)
