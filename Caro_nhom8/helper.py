from json import dumps, loads
from socket import socket
from threading import Thread
from typing import Any, Literal
from random import shuffle
from common import CHARS, Char, Code

# ================== Encode/Decode ==================

def encoder(data: dict[str, Any]) -> bytes:
    return dumps(data).encode()

def decoder(data: bytes) -> dict[str, Any]:
    return loads(data)

# ================== Game Logic ==================

BOARD_SIZE = 10   # 10x10
WIN_COUNT = 5     # cần 5 dấu liên tiếp để thắng

def is_draw(board_position: list[str]) -> bool:
    for char in board_position:
        if char not in CHARS:
            return False
    return True

def is_won(board_position: list[str], char: str) -> bool:
    # Chuyển list 1D thành ma trận 2D
    board = [board_position[i * BOARD_SIZE:(i + 1) * BOARD_SIZE] for i in range(BOARD_SIZE)]

    # Kiểm tra thắng ngang, dọc, chéo
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            if board[r][c] != char:
                continue

            # Ngang →
            if c + WIN_COUNT <= BOARD_SIZE and all(board[r][c + k] == char for k in range(WIN_COUNT)):
                return True
            # Dọc ↓
            if r + WIN_COUNT <= BOARD_SIZE and all(board[r + k][c] == char for k in range(WIN_COUNT)):
                return True
            # Chéo ↘
            if r + WIN_COUNT <= BOARD_SIZE and c + WIN_COUNT <= BOARD_SIZE and all(board[r + k][c + k] == char for k in range(WIN_COUNT)):
                return True
            # Chéo ↙
            if r + WIN_COUNT <= BOARD_SIZE and c - WIN_COUNT >= -1 and all(board[r + k][c - k] == char for k in range(WIN_COUNT)):
                return True
    return False

# ================== Server Communication ==================

def handle_client(client: socket, friend: socket, chance: Literal[1, 0], char: str) -> None:
    client.send(encoder({Code.CHANCE_CODE: chance, Code.CHAR_CODE: char}))

    while True:
        try:
            recived_data = decoder(client.recv(4096))
        except:
            break

        if not recived_data:
            break

        friend.sendall(encoder(recived_data))

        if recived_data[Code.MATCH_CODE] != Char.MATCH_NORMAL_CHAR:
            break

def handle_friends(_friends: tuple[socket, socket]) -> None:
    turn_list = [0, 1]
    char_list = CHARS
    shuffle(turn_list)
    shuffle(char_list)

    Thread(target=handle_client, args=(*_friends, turn_list[0], char_list)).start()
    Thread(target=handle_client, args=(*_friends[::-1], turn_list[1], char_list[::-1])).start()

def server_starter(server: socket) -> None:
    waiting_client: socket | None = None

    while True:
        try:
            client, _ = server.accept()
            print(f"Client connected from {client.getpeername()}")
        except Exception as e:
            print("Error while waiting for client:", e)
            server.close()
            break

        if waiting_client is None:
            waiting_client = client
            client.send(encoder({Code.FRIEND_CODE: 0}))
        else:
            client.send(encoder({Code.FRIEND_CODE: 1}))
            waiting_client.send(encoder({Code.FRIEND_CODE: 1}))
            Thread(target=handle_friends, args=((client, waiting_client),)).start()
            waiting_client = None
