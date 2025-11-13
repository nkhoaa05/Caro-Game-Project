from socket import AF_INET, SOCK_STREAM

from helper import server_starter, socket

def server_handler(HOST: str = "127.0.0.1", PORT: int = 8000) -> None:
    server = socket(AF_INET, SOCK_STREAM)
    server.bind((HOST, PORT))

    server.listen()
    print("Server started")

    server_starter(server)
    server.close()
