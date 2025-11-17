# helper.py
from json import dumps, loads
from socket import socket
from threading import Thread, Lock
from typing import Any, Literal
from random import shuffle
from common import CHARS, Char, Code

# Game constants
BOARD_SIZE = 10
WIN_COUNT = 5

# ================== encoder / decoder ==================
def encoder(data: dict[str, Any]) -> bytes:
    return dumps(data).encode()

def decoder(data: bytes) -> dict[str, Any]:
    try:
        if isinstance(data, bytes):
            return loads(data.decode())
        if isinstance(data, str):
            return loads(data)
    except Exception:
        return {}

# ================== Game logic for 1D board (len = BOARD_SIZE*BOARD_SIZE) ==================
def is_draw(board_position: list[str]) -> bool:
    # board_position is a list of length BOARD_SIZE*BOARD_SIZE
    for cell in board_position:
        if cell not in CHARS:
            return False
    return True

def is_won(board_position: list[str], char: str) -> bool:
    # Interpret board_position as row-major
    size = BOARD_SIZE
    N = WIN_COUNT

    def at(r, c):
        return board_position[r * size + c]

    for r in range(size):
        for c in range(size):
            if at(r, c) != char:
                continue

            # horizontal
            if c + N <= size and all(at(r, c + k) == char for k in range(N)):
                return True
            # vertical
            if r + N <= size and all(at(r + k, c) == char for k in range(N)):
                return True
            # diagonal down-right
            if r + N <= size and c + N <= size and all(at(r + k, c + k) == char for k in range(N)):
                return True
            # diagonal down-left
            if r + N <= size and c - N >= -1 and all(at(r + k, c - k) == char for k in range(N)):
                return True
    return False

# ================== Server room management & relay ==================
_rooms_lock = Lock()
_rooms: dict[str, list[socket]] = {}  # room_name -> list of sockets (max 2)

def _send_json_safe(sock: socket, data: dict[str, Any]) -> None:
    try:
        sock.sendall(encoder(data))
    except Exception:
        # ignore send errors here
        pass

def _relay(src: socket, dst: socket) -> None:
    """Relay loop from src to dst until connection closes or match ends."""
    try:
        while True:
            raw = src.recv(4096)
            if not raw:
                # inform dst that opponent left
                _send_json_safe(dst, {Code.MATCH_CODE: Char.MATCH_LEFT_CODE})
                break
            try:
                msg = decoder(raw)
            except Exception:
                break
            if not msg:
                continue
            # forward message to dst
            _send_json_safe(dst, msg)
            # if message ends the match, break
            if msg.get(Code.MATCH_CODE) and msg[Code.MATCH_CODE] != Char.MATCH_NORMAL_CHAR:
                break
    except Exception:
        pass
    finally:
        try:
            src.close()
        except Exception:
            pass

def add_client_to_room(room_name: str, client_sock: socket) -> tuple[bool, str]:
    """
    Add client to room.
    Returns (ok, message). ok=True if joined or paired successfully.
    """
    with _rooms_lock:
        lst = _rooms.get(room_name)
        if lst is None:
            _rooms[room_name] = [client_sock]
            return True, "WAITING"
        else:
            if len(lst) == 0:
                _rooms[room_name].append(client_sock)
                return True, "WAITING"  # should not happen usually
            elif len(lst) == 1:
                lst.append(client_sock)
                return True, "START"
            else:
                return False, "FULL"

def start_room_game(room_name: str) -> None:
    """Start game for the room (assumes two sockets present)."""
    with _rooms_lock:
        pair = _rooms.get(room_name)
        if not pair or len(pair) < 2:
            return
        a, b = pair[0], pair[1]

    # Decide turns and chars
    turn_list = [1, 0]  # 1 means first player gets chance=1 (first move)
    shuffle(turn_list)
    chars = CHARS[:]  # ["X","O"]
    shuffle(chars)

    # For client a: chance = turn_list[0], char list = chars (so a sees char[0] as theirs)
    # For client b: chance = turn_list[1], char list = chars[::-1]
    _send_json_safe(a, {Code.CHANCE_CODE: turn_list[0], Code.CHAR_CODE: chars})
    _send_json_safe(b, {Code.CHANCE_CODE: turn_list[1], Code.CHAR_CODE: chars[::-1]})

    # Start relay threads both directions
    Thread(target=_relay, args=(a, b), daemon=True).start()
    Thread(target=_relay, args=(b, a), daemon=True).start()

def remove_room(room_name: str) -> None:
    with _rooms_lock:
        _rooms.pop(room_name, None)
