# server.py
from socket import AF_INET, SOCK_STREAM, socket
import socket as s
from helper import decoder, encoder, add_client_to_room, start_room_game
from common import Code
from threading import Thread

def _handle_connected_client(client_sock: socket, addr):
    """
    Thread cho mỗi client:
    - Nhận {Code.ROOM_CODE: "<room_name>"}
    - Nếu phòng còn trống: chờ
    - Nếu đủ 2 người: bắt đầu trò chơi
    """
    try:
        raw = client_sock.recv(4096)
        if not raw:
            client_sock.close()
            return
        data = decoder(raw)
        room = data.get(Code.ROOM_CODE)
        if not room:
            client_sock.close()
            return

        ok, status = add_client_to_room(room, client_sock)
        if not ok:
            client_sock.sendall(encoder({Code.FRIEND_CODE: -1, "ERROR": "Room full"}))
            client_sock.close()
            return

        if status == "WAITING":
            client_sock.sendall(encoder({Code.FRIEND_CODE: 0}))
            return

        if status == "START":
            from helper import _rooms, _rooms_lock
            with _rooms_lock:
                pair = _rooms.get(room, [])
            # gửi thông báo friend found
            for sck in pair:
                try:
                    sck.sendall(encoder({Code.FRIEND_CODE: 1}))
                except:
                    pass
            # khởi động luồng trò chơi
            start_room_game(room)

    except Exception as e:
        print(f"Error handling client {addr}: {e}")
        try:
            client_sock.close()
        except:
            pass

def server_handler(HOST: str = "127.0.0.1", PORT: int = 8000) -> None:
    server = socket(AF_INET, SOCK_STREAM)
    server.setsockopt(s.SOL_SOCKET, s.SO_REUSEADDR, 1)  # ✅ sửa đúng cú pháp
    server.bind((HOST, PORT))
    server.listen()
    print(f"Server started on {HOST}:{PORT}")

    try:
        while True:
            client, addr = server.accept()
            print(f"Client connected from {addr}")
            Thread(target=_handle_connected_client, args=(client, addr), daemon=True).start()
    except KeyboardInterrupt:
        print("Server shutting down...")
    finally:
        server.close()
