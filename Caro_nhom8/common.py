# common.py
CHARS = ["X", "O"]

class Code:
    MESSAGE_CODE = "MESSAGE"
    MOVE_CODE = "MOVE"
    FRIEND_CODE = "FRIEND"
    CHANCE_CODE = "CHANCE"
    CHAR_CODE = "CHAR"
    MATCH_CODE = "MATCH"
    ROOM_CODE = "ROOM"   # client gửi tên phòng

class Char:
    MATCH_WIN_CHAR = "WON"
    MATCH_LOSS_CHAR = "LOSS"
    MATCH_DRAW_CHAR = "DRAW"
    MATCH_NORMAL_CHAR = "NORMAL"
    MATCH_LEFT_CODE = "LEFT"

__all__ = ["CHARS", "Code", "Char"]
