from socket import AF_INET, SOCK_STREAM, socket
from helper import server_starter

def server_handler(HOST="127.0.0.1", PORT=5000):
    server = socket(AF_INET, SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()
    print(f"Server started on {HOST}:{PORT}")
    server_starter(server)
    server.close()
