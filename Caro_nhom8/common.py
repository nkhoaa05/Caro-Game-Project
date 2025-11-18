# common.py
import json
import struct
import socket

class Code:
    # Basic game / match codes
    JOIN_ROOM = "JOIN_ROOM"          # client -> server: join/create room payload
    ROOM_CODE = "ROOM_CODE"          # for room list requests
    ROOM_LIST = "ROOM_LIST"          # server -> client: list of waiting rooms
    MESSAGE_CODE = "MESSAGE_CODE"    # chat message in-room
    MATCH_START = "MATCH_START"      # server -> both: match started
    MATCH_MOVE = "MATCH_MOVE"        # client -> server -> other: move
    MATCH_RESTART = "MATCH_RESTART"  # server -> both: reset board
    MATCH_LEFT = "MATCH_LEFT"        # server -> other: opponent disconnected mid-match
    ROOM_LEAVE = "ROOM_LEAVE"        # server -> both: player left room (not necessarily disconnect)
    ROOM_LEAVE_SUCCESS = "ROOM_LEAVE_SUCCESS"  # server -> client who left room successfully
    MATCH_DRAW_REQUEST = "MATCH_DRAW_REQUEST"
    MATCH_DRAW_ACCEPT = "MATCH_DRAW_ACCEPT"
    MATCH_DRAW_REJECT = "MATCH_DRAW_REJECT"
    ERROR = "ERROR"                  # server -> client: error

# utility to send/receive JSON messages with 4-byte length prefix
def send_msg(sock: socket.socket, obj: dict):
    b = json.dumps(obj, ensure_ascii=False).encode('utf-8')
    header = struct.pack('!I', len(b))
    sock.sendall(header + b)

def recv_msg(sock: socket.socket):
    # read 4 bytes length
    header = recvn(sock, 4)
    if not header:
        return None
    length = struct.unpack('!I', header)[0]
    body = recvn(sock, length)
    if not body:
        return None
    return json.loads(body.decode('utf-8'))

def recvn(sock: socket.socket, n: int):
    data = b''
    while len(data) < n:
        try:
            chunk = sock.recv(n - len(data))
        except ConnectionResetError:
            return None
        if not chunk:
            return None
        data += chunk
    return data
