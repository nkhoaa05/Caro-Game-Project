import threading
import tkinter as tk
from socket import AF_INET, SOCK_STREAM, socket
from helper import encoder, decoder, Code, Char, is_won, is_draw, CHARS, BOARD_SIZE

class TicTacToeClient(tk.Tk):
    def __init__(self, HOST="127.0.0.1", PORT=5000):
        super().__init__()
        self.title("Caro 10x10 - Client")
        self.resizable(False, False)

        self.board_position = ["" for _ in range(BOARD_SIZE * BOARD_SIZE)]
        self.char = ["X", "O"]
        self.first_turn = False
        self.game_over = False
        self.last_enemy_move = -1

        self.status_label = tk.Label(self, text="Connecting to server...", font=("Arial", 12))
        self.status_label.pack(pady=10)

        frame = tk.Frame(self)
        frame.pack()

        self.buttons = []
        for i in range(BOARD_SIZE * BOARD_SIZE):
            btn = tk.Button(
                frame,
                text="",
                font=("Arial", 14),
                width=3,
                height=1,
                command=lambda i=i: self.make_move(i)
            )
            btn.grid(row=i // BOARD_SIZE, column=i % BOARD_SIZE)
            self.buttons.append(btn)

        # socket
        self.server = socket(AF_INET, SOCK_STREAM)
        try:
            self.server.connect((HOST, PORT))
        except Exception as e:
            self.status_label.config(text=f"Connection failed: {e}")
            return

        threading.Thread(target=self.receive_data, daemon=True).start()

    def make_move(self, position):
        if self.game_over:
            return
        if self.board_position[position] in CHARS:
            return
        if not self.first_turn:
            return

        self.board_position[position] = self.char[0]
        self.update_board()

        if is_won(self.board_position, self.char[0]):
            self.server.sendall(encoder({Code.MOVE_CODE: position, Code.MATCH_CODE: Char.MATCH_WIN_CHAR}))
            self.status_label.config(text="You win!")
            self.game_over = True
        elif is_draw(self.board_position):
            self.server.sendall(encoder({Code.MOVE_CODE: position, Code.MATCH_CODE: Char.MATCH_DRAW_CHAR}))
            self.status_label.config(text="Draw!")
            self.game_over = True
        else:
            self.server.sendall(encoder({Code.MOVE_CODE: position, Code.MATCH_CODE: Char.MATCH_NORMAL_CHAR}))
            self.status_label.config(text="Waiting for opponent...")
            self.first_turn = False

    def update_board(self):
        for i in range(BOARD_SIZE * BOARD_SIZE):
            color = "SystemButtonFace"
            if i == self.last_enemy_move:
                color = "lightcoral"
            self.buttons[i].config(text=self.board_position[i], bg=color)

    def receive_data(self):
        while True:
            try:
                data = decoder(self.server.recv(4096))
            except:
                break
            if not data:
                continue

            if Code.CHANCE_CODE in data:
                self.first_turn = data[Code.CHANCE_CODE]
                self.char = data[Code.CHAR_CODE]
                self.status_label.config(
                    text=f"You are {'first' if self.first_turn else 'second'} ({self.char[0]})"
                )
                continue

            if Code.MOVE_CODE in data:
                position = data[Code.MOVE_CODE]
                self.last_enemy_move = position
                self.board_position[position] = self.char[1]
                self.update_board()

                match_code = data.get(Code.MATCH_CODE, Char.MATCH_NORMAL_CHAR)
                if match_code == Char.MATCH_WIN_CHAR:
                    self.status_label.config(text="You lose!")
                    self.game_over = True
                    break
                elif match_code == Char.MATCH_DRAW_CHAR:
                    self.status_label.config(text="Draw!")
                    self.game_over = True
                    break
                elif match_code == Char.MATCH_LOSS_CHAR:
                    self.status_label.config(text="You win!")
                    self.game_over = True
                    break
                elif match_code == Char.MATCH_LEFT_CODE:
                    self.status_label.config(text="Opponent left the game")
                    self.game_over = True
                    break

                if not self.game_over:
                    self.first_turn = True
                    self.status_label.config(text="Your turn!")

def client_handler(HOST="127.0.0.1", PORT=5000):
    app = TicTacToeClient(HOST, PORT)
    app.mainloop()
