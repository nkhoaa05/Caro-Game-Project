# client.py
import threading
import tkinter as tk
from socket import AF_INET, SOCK_STREAM, socket
from helper import encoder, decoder, is_won, is_draw, BOARD_SIZE
from common import Code, Char, CHARS

class GomokuClient(tk.Tk):
    def __init__(self, HOST="127.0.0.1", PORT=5000):
        super().__init__()
        self.title("Gomoku 10x10 - Client")
        self.resizable(False, False)

        self.HOST = HOST
        self.PORT = PORT

        # Game state
        self.size = BOARD_SIZE
        self.board = ["" for _ in range(self.size * self.size)]  # 1D list
        self.char = ["X", "O"]
        self.first_turn = False
        self.game_over = False
        self.last_enemy_move = -1

        # Socket (created when joining a room)
        self.server = None

        # UI: room selection area
        top = tk.Frame(self)
        top.pack(pady=8)
        tk.Label(top, text="Room name:").pack(side=tk.LEFT)
        self.room_entry = tk.Entry(top)
        self.room_entry.pack(side=tk.LEFT, padx=6)
        self.join_btn = tk.Button(top, text="Join Room", command=self.join_room)
        self.join_btn.pack(side=tk.LEFT)

        self.status_label = tk.Label(self, text="Not connected", font=("Arial", 12))
        self.status_label.pack(pady=6)

        # Board frame (initially disabled until joined)
        self.board_frame = tk.Frame(self)
        self.board_frame.pack(padx=8, pady=8)
        self.buttons = []
        for i in range(self.size * self.size):
            btn = tk.Button(self.board_frame, text="", width=3, height=1,
                            font=("Arial", 12), command=lambda i=i: self.make_move(i))
            btn.grid(row=i // self.size, column=i % self.size, padx=1, pady=1)
            self.buttons.append(btn)

        # Disable board until game starts
        self._set_board_state("disabled")

    def _set_board_state(self, state: str):
        for b in self.buttons:
            b.config(state=state)

    # --- Network / join room ---
    def join_room(self):
        room = self.room_entry.get().strip()
        if not room:
            self.status_label.config(text="Enter a room name")
            return

        # create socket and connect
        self.server = socket(AF_INET, SOCK_STREAM)
        try:
            self.server.connect((self.HOST, self.PORT))
        except Exception as e:
            self.status_label.config(text=f"Connect failed: {e}")
            return

        # send room name
        try:
            self.server.sendall(encoder({Code.ROOM_CODE: room}))
        except Exception as e:
            self.status_label.config(text=f"Send room failed: {e}")
            self.server.close()
            return

        # start recv thread
        threading.Thread(target=self._recv_loop, daemon=True).start()
        self.status_label.config(text="Joined room, waiting server response...")
        # disable join controls to avoid rejoin
        self.join_btn.config(state="disabled")
        self.room_entry.config(state="disabled")

    # --- Game actions ---
    def make_move(self, position: int):
        if self.game_over or not self.first_turn:
            return
        if self.board[position] in CHARS:
            return

        # mark locally
        self.board[position] = self.char[0]
        self._update_board_ui()

        # check win/draw and send appropriate match code
        try:
            if is_won(self.board, self.char[0]):
                self.server.sendall(encoder({Code.MOVE_CODE: position, Code.MATCH_CODE: Char.MATCH_WIN_CHAR}))
                self.status_label.config(text="You win!")
                self.game_over = True
                self._set_board_state("disabled")
                return
            if is_draw(self.board):
                self.server.sendall(encoder({Code.MOVE_CODE: position, Code.MATCH_CODE: Char.MATCH_DRAW_CHAR}))
                self.status_label.config(text="Draw!")
                self.game_over = True
                self._set_board_state("disabled")
                return
            # normal move
            self.server.sendall(encoder({Code.MOVE_CODE: position, Code.MATCH_CODE: Char.MATCH_NORMAL_CHAR}))
            self.status_label.config(text="Waiting for opponent...")
            self.first_turn = False
            self._set_board_state("disabled")
        except Exception:
            pass

    def _update_board_ui(self):
        for i in range(self.size * self.size):
            txt = self.board[i] if self.board[i] in CHARS else ""
            bg = "SystemButtonFace"
            if i == self.last_enemy_move:
                bg = "lightgreen"
            self.buttons[i].config(text=txt, bg=bg)

    # --- Receive loop ---
    def _recv_loop(self):
        try:
            while True:
                raw = self.server.recv(4096)
                if not raw:
                    self.status_label.config(text="Server disconnected")
                    break
                msg = decoder(raw)
                if not msg:
                    continue

                # ROOM join response: FRIEND_CODE: 0 -> waiting; 1 -> friend found
                if Code.FRIEND_CODE in msg:
                    val = msg[Code.FRIEND_CODE]
                    if val == 0:
                        self.status_label.config(text="Waiting for opponent to join...")
                    elif val == 1:
                        # friend found; next we'll receive CHANCE/CHAR from server
                        self.status_label.config(text="Opponent found, setting up...")
                    elif val == -1:
                        self.status_label.config(text="Room full or error")
                        try:
                            self.server.close()
                        except:
                            pass
                        break
                    continue

                # CHANCE and CHAR (game start info)
                if Code.CHANCE_CODE in msg:
                    self.first_turn = bool(msg[Code.CHANCE_CODE])
                    self.char = msg[Code.CHAR_CODE]
                    self.status_label.config(text=f"You are {'first' if self.first_turn else 'second'} ({self.char[0]})")
                    # enable board for playing if it's your turn
                    if self.first_turn:
                        self._set_board_state("normal")
                        self.status_label.config(text="Your turn!")
                    else:
                        self._set_board_state("disabled")
                    continue

                # MOVE from opponent (or echoed move)
                if Code.MOVE_CODE in msg:
                    pos = msg[Code.MOVE_CODE]
                    # mark opponent
                    self.board[pos] = self.char[1]
                    self.last_enemy_move = pos
                    self._update_board_ui()

                    match_code = msg.get(Code.MATCH_CODE, Char.MATCH_NORMAL_CHAR)
                    if match_code == Char.MATCH_WIN_CHAR:
                        self.status_label.config(text="You lose!")
                        self.game_over = True
                        self._set_board_state("disabled")
                        break
                    elif match_code == Char.MATCH_DRAW_CHAR:
                        self.status_label.config(text="Draw!")
                        self.game_over = True
                        self._set_board_state("disabled")
                        break
                    elif match_code == Char.MATCH_LOSS_CHAR:
                        self.status_label.config(text="You win!")
                        self.game_over = True
                        self._set_board_state("disabled")
                        break
                    elif match_code == Char.MATCH_LEFT_CODE:
                        self.status_label.config(text="Opponent left")
                        self.game_over = True
                        self._set_board_state("disabled")
                        break

                    # now it's our turn
                    if not self.game_over:
                        self.first_turn = True
                        self._set_board_state("normal")
                        self.status_label.config(text="Your turn!")
                        # keep highlight for a moment; GUI already updated
                    continue

        except Exception:
            pass
        finally:
            try:
                if self.server:
                    self.server.close()
            except:
                pass

def client_handler(HOST="127.0.0.1", PORT=5000):
    app = GomokuClient(HOST, PORT)
    app.mainloop()
