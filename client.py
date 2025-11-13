# Client.py (GUI version using Tkinter)
import threading
import tkinter as tk
from socket import AF_INET, SOCK_STREAM, socket
from helper import encoder, decoder, Code, Char, is_won, is_draw, CHARS

class TicTacToeClient(tk.Tk):
    def __init__(self, HOST="127.0.0.1", PORT=5000):
        super().__init__()
        self.title("Tic-Tac-Toe Client")
        self.geometry("300x350")

        # Trạng thái bàn cờ
        self.board_position = [str(i + 1) for i in range(9)]
        self.char = ["X", "O"]
        self.first_turn = False
        self.game_over = False

        # Label thông báo trạng thái
        self.status_label = tk.Label(self, text="Connecting to server...", font=("Arial", 12))
        self.status_label.pack(pady=10)

        # Tạo khung bàn cờ
        self.buttons = []
        frame = tk.Frame(self)
        frame.pack()
        for i in range(9):
            btn = tk.Button(
                frame,
                text=self.board_position[i],
                font=("Arial", 20),
                width=5,
                height=2,
                command=lambda i=i: self.make_move(i)
            )
            btn.grid(row=i//3, column=i%3)
            self.buttons.append(btn)

        # Kết nối server
        self.server = socket(AF_INET, SOCK_STREAM)
        try:
            self.server.connect((HOST, PORT))
        except Exception as e:
            self.status_label.config(text=f"Connection failed: {e}")
            return

        # Thread nhận dữ liệu từ server
        threading.Thread(target=self.receive_data, daemon=True).start()

    def make_move(self, position):
        if self.game_over:
            return  # trận đấu đã kết thúc

        if self.board_position[position] in CHARS:
            return  # ô đã được đánh

        if not self.first_turn:
            return  # chưa đến lượt

        # Đánh dấu vị trí
        self.board_position[position] = self.char[0]
        self.update_board()

        # Kiểm tra thắng/hòa
        if is_won(self.board_position, self.char[0]):
            self.server.sendall(
                encoder({Code.MOVE_CODE: position, Code.MATCH_CODE: Char.MATCH_WIN_CHAR})
            )
            self.status_label.config(text="You win!")
            self.game_over = True
        elif is_draw(self.board_position):
            self.server.sendall(
                encoder({Code.MOVE_CODE: position, Code.MATCH_CODE: Char.MATCH_DRAW_CHAR})
            )
            self.status_label.config(text="Draw!")
            self.game_over = True
        else:
            # Gửi move bình thường
            self.server.sendall(
                encoder({Code.MOVE_CODE: position, Code.MATCH_CODE: Char.MATCH_NORMAL_CHAR})
            )
            self.status_label.config(text="Waiting for friend's move...")
            self.first_turn = False

    def update_board(self):
        for i in range(9):
            self.buttons[i].config(text=self.board_position[i])

    def receive_data(self):
        while True:
            try:
                data = decoder(self.server.recv(1024))
            except:
                break  # lỗi kết nối hoặc server đóng
            if not data:
                continue

            # Nhận thông tin lượt đi và ký hiệu
            if Code.CHANCE_CODE in data:
                self.first_turn = data[Code.CHANCE_CODE]
                self.char = data[Code.CHAR_CODE]
                self.status_label.config(
                    text=f"You are {'first' if self.first_turn else 'second'} ({self.char[0]})"
                )
                continue

            # Nhận lượt đi của bạn bè
            if Code.MOVE_CODE in data:
                position = data[Code.MOVE_CODE]
                self.board_position[position] = self.char[1]
                self.update_board()

                # Xử lý trạng thái trận đấu từ server
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
                    self.status_label.config(text="Friend left the game")
                    self.game_over = True
                    break

                # Lượt tiếp theo của client
                if not self.game_over:
                    self.first_turn = True
                    self.status_label.config(text="Your turn!")

def client_handler(HOST="127.0.0.1", PORT=5000):
    app = TicTacToeClient(HOST, PORT)
    app.mainloop()
