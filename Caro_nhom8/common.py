CHARS = ["X", "O"]

class Code:
    MESSAGE_CODE = "MESSAGE"
    MOVE_CODE = "MOVE"
    FRIEND_CODE = "FRIEND"
    CHANCE_CODE = "CHANCE"
    CHAR_CODE = "CHAR"
    MATCH_CODE = "MATCH"

class Char:
    MATCH_WIN_CHAR = "WON"
    MATCH_LOSS_CHAR = "LOSS"
    MATCH_DRAW_CHAR = "DRAW"
    MATCH_NORMAL_CHAR = "NORMAL"
    MATCH_LEFT_CODE = "LEFT"

won_conditions = [
    [0, 1, 2],
    [3, 4, 5],
    [6, 7, 8],
    [0, 3, 6],
    [1, 4, 7],
    [2, 5, 8],
    [0, 4, 8],
    [2, 4, 6],
]

__all__ = ["CHARS", "Code", "Char", "won_conditions"]
