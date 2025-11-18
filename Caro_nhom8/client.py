# client.py
import socket
import threading
import tkinter as tk
from tkinter import messagebox, simpledialog, scrolledtext
from common import Code, send_msg, recv_msg
from helper import safe_start_thread
import json

# We'll provide client_handler(host, port) as main entry point

class ClientApp:
    def highlight_last_move(self, x, y):
        # reset màu tất cả ô về mặc định
        for row in self.cells:
            for btn in row:
                btn.configure(bg="SystemButtonFace")  # hoặc "white"

        # tô màu ô vừa đánh
        if self.board[y][x] == self.symbol:
            self.cells[y][x].configure(bg="lightgreen")  # ô của mình
        else:
            self.cells[y][x].configure(bg="lightblue")   # ô của đối thủ

        # lưu lại
        self.last_move = (x, y)



    def __init__(self, host, port):
        self.host = host; self.port = port
        self.sock = None
        self.root = tk.Tk()
        self.root.title("Caro 10x10 - Client")
        self.player_id = None
        self.opponent_id = None
        self.room_id = None
        self.symbol = None
        self.board = [['' for _ in range(10)] for __ in range(10)]
        self.turn = None
        self.in_match = False
        self.last_move = None  # lưu ô vừa đánh để highlight

        # build UI
        self.build_ui()

        # connect
        try:
            self.connect_to_server()
        except Exception as e:
            messagebox.showerror("Connection error", f"Cannot connect to server: {e}")
            self.root.destroy()
            return

        # start receiver thread
        safe_start_thread(self.receiver_thread, ())

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.mainloop()

    def build_ui(self):
        # main frames
        left = tk.Frame(self.root)
        right = tk.Frame(self.root, width=300)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        right.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)

        # Board canvas (left)
        self.cells = []
        board_frame = tk.Frame(left)
        board_frame.pack(padx=10, pady=10)
        for y in range(10):
            row = []
            for x in range(10):
                btn = tk.Button(board_frame, text=" ", width=3, height=1,
                                command=lambda xx=x, yy=y: self.click_cell(xx, yy))
                btn.grid(row=y, column=x)
                row.append(btn)
            self.cells.append(row)

        # Right side: chat + controls + room list
        chat_label = tk.Label(right, text="Chat")
        chat_label.pack()
        self.chat_box = scrolledtext.ScrolledText(right, width=40, height=12, state=tk.DISABLED)
        self.chat_box.pack(padx=5, pady=5)

        chat_entry_frame = tk.Frame(right)
        chat_entry_frame.pack(fill=tk.X, pady=(0,5))
        self.chat_entry = tk.Entry(chat_entry_frame)
        self.chat_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,5))
        send_btn = tk.Button(chat_entry_frame, text="Gửi", command=self.send_chat)
        send_btn.pack(side=tk.RIGHT)

        # Control buttons
        ctrl_frame = tk.Frame(right)
        ctrl_frame.pack(fill=tk.X, pady=5)
        self.btn_create = tk.Button(ctrl_frame, text="Tạo phòng", command=self.create_room)
        self.btn_create.pack(fill=tk.X)
        self.btn_list = tk.Button(ctrl_frame, text="Xem danh sách phòng", command=self.request_room_list)
        self.btn_list.pack(fill=tk.X)
        # Room join by ID
        room_id_frame = tk.Frame(right)
        room_id_frame.pack(fill=tk.X, pady=5)
        tk.Label(room_id_frame, text="Nhập mã phòng:").pack()
        self.room_entry = tk.Entry(room_id_frame)
        self.room_entry.pack(fill=tk.X, padx=5, pady=2)
        join_by_id_btn = tk.Button(room_id_frame, text="Tham gia phòng", command=self.join_room_by_id)
        join_by_id_btn.pack(fill=tk.X, padx=5, pady=2)

        self.btn_join = tk.Button(ctrl_frame, text="Join room", command=self.join_selected_room)
        self.btn_join.pack(fill=tk.X)
        self.btn_leave = tk.Button(ctrl_frame, text="Rời phòng", command=self.leave_room)
        self.btn_leave.pack(fill=tk.X)
        self.btn_rematch = tk.Button(ctrl_frame, text="Chơi lại", command=self.request_rematch)
        self.btn_rematch.pack(fill=tk.X)
        self.btn_draw = tk.Button(ctrl_frame, text="Cầu hòa", command=self.request_draw)
        self.btn_draw.pack(fill=tk.X)

        # Room list
        room_label = tk.Label(right, text="Phòng chờ")
        room_label.pack()
        self.room_listbox = tk.Listbox(right, width=40, height=8)
        self.room_listbox.pack(padx=5, pady=5)

    def connect_to_server(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))

    def receiver_thread(self):
        try:
            while True:
                msg = recv_msg(self.sock)
                if msg is None:
                    self.on_server_disconnect()
                    break
                code = msg.get('code')
                payload = msg.get('payload')
                # dispatch
                if code == Code.JOIN_ROOM:
                    self.handle_join_response(payload)
                elif code == Code.ROOM_LIST:
                    self.update_room_list(payload)
                elif code == Code.MESSAGE_CODE:
                    self.append_chat(f"[{payload.get('from')}] {payload.get('text')}")
                elif code == Code.MATCH_START:
                    self.handle_match_start(payload)
                elif code == Code.MATCH_MOVE:
                    self.handle_move(payload)
                elif code == Code.MATCH_RESTART:
                    self.handle_restart(payload)
                elif code == Code.MATCH_LEFT:
                    self.handle_opponent_left(payload)
                elif code == Code.ROOM_LEAVE:
                    self.handle_room_leave(payload)
                elif code == Code.MATCH_DRAW_REQUEST:
                    self.handle_draw_request(payload)
                elif code == Code.MATCH_DRAW_ACCEPT:
                    self.handle_draw_accept(payload)
                elif code == Code.MATCH_DRAW_REJECT:
                    self.handle_draw_reject(payload)
                elif code == Code.ERROR:
                    self.append_chat(f"[Server ERROR] {payload}")
                elif code == Code.ROOM_LEAVE_SUCCESS:
                    self.handle_room_leave_success(payload)
                else:
                    print("Unknown code from server:", code, payload)
        except Exception as e:
            print("Receiver thread error:", e)
            self.on_server_disconnect()

    def append_chat(self, text):
        def task():
            self.chat_box.configure(state=tk.NORMAL)
            self.chat_box.insert(tk.END, text + "\n")
            self.chat_box.configure(state=tk.DISABLED)
            self.chat_box.see(tk.END)
        self.root.after(0, task)

    # UI actions
    def join_room_by_id(self):
        room_id = self.room_entry.get().strip()
        if not room_id:
            messagebox.showinfo("Thông báo", "Vui lòng nhập mã phòng.")
            return
        send_msg(self.sock, {'code': Code.JOIN_ROOM, 'payload': {'action': 'JOIN', 'room_id': room_id}})

    def send_chat(self):
        text = self.chat_entry.get().strip()
        if not text:
            return
        if not self.room_id:
            messagebox.showinfo("Thông báo", "Bạn chưa vào phòng.")
            return
        send_msg(self.sock, {'code': Code.MESSAGE_CODE, 'payload': {'text': text}})
        self.append_chat(f"[You] {text}")
        self.chat_entry.delete(0, tk.END)

    def create_room(self):
        send_msg(self.sock, {'code': Code.JOIN_ROOM, 'payload': {'action': 'CREATE'}})

    def request_room_list(self):
        send_msg(self.sock, {'code': Code.ROOM_CODE, 'payload': 'LIST'})

    def update_room_list(self, payload):
        # payload: list of {'room_id':...}
        def task():
            self.room_listbox.delete(0, tk.END)
            for r in payload:
                self.room_listbox.insert(tk.END, r['room_id'])
        self.root.after(0, task)

    def join_selected_room(self):
        sel = self.room_listbox.curselection()
        if not sel:
            messagebox.showinfo("Thông báo", "Chọn phòng để join")
            return
        room_id = self.room_listbox.get(sel[0])
        send_msg(self.sock, {'code': Code.JOIN_ROOM, 'payload': {'action': 'JOIN', 'room_id': room_id}})

    def leave_room(self):
        if not self.room_id:
            messagebox.showinfo("Thông báo", "Bạn đang không ở trong phòng")
            return
        send_msg(self.sock, {'code': Code.ROOM_LEAVE, 'payload': {}})
        # local cleanup will be triggered by ROOM_LEAVE from server

    def request_rematch(self):
        if not self.room_id:
            messagebox.showinfo("Thông báo", "Bạn chưa vào phòng")
            return
        # send agree True
        send_msg(self.sock, {'code': Code.MATCH_RESTART, 'payload': {'agree': True}})

    def request_draw(self):
        if not self.room_id:
            messagebox.showinfo("Thông báo", "Bạn chưa vào phòng")
            return
        send_msg(self.sock, {'code': Code.MATCH_DRAW_REQUEST, 'payload': {}})

    # incoming handlers
    def handle_join_response(self, payload):
        status = payload.get('status')
        room_id = payload.get('room_id')
        if status == 'WAIT':
            self.room_id = room_id
            self.append_chat(f"[System] Tạo phòng thành công: {room_id}. Đang chờ đối thủ...")
        else:
            self.append_chat(f"[System] Join response: {payload}")

    def handle_match_start(self, payload):
        # you, opponent, symbol, room_id
        self.player_id = payload.get('you')
        self.opponent_id = payload.get('opponent')
        self.symbol = payload.get('symbol')
        self.room_id = payload.get('room_id')
        self.board = [['' for _ in range(10)] for __ in range(10)]
        self.in_match = True
        # set all buttons to blank
        def task():
            for y in range(10):
                for x in range(10):
                    self.cells[y][x].configure(text=" ", state=tk.NORMAL)
            messagebox.showinfo("Match start", f"Match started vs {self.opponent_id}. You are '{self.symbol}'")
        self.root.after(0, task)

    def handle_move(self, payload):
        x = payload.get('x'); y = payload.get('y'); sym = payload.get('symbol'); by = payload.get('by')
        winner = payload.get('winner', False)
        self.board[y][x] = sym
        def task():
            self.cells[y][x].configure(text=sym, state=tk.DISABLED)
            self.highlight_last_move(x, y)
            if winner:
                if by == self.player_id:
                    messagebox.showinfo("Kết quả", "Bạn thắng!")
                else:
                    messagebox.showinfo("Kết quả", "Bạn thua!")
                self.ask_rematch_prompt()
        self.root.after(0, task)

    def handle_restart(self, payload):
        # payload could be {} for actual restart, or {'request_from': player_id} to indicate request
        if 'request_from' in payload:
            from_id = payload['request_from']
            r = messagebox.askyesno("Yêu cầu chơi lại", f"Đối thủ ({from_id}) muốn chơi lại. Đồng ý?")
            send_msg(self.sock, {'code': Code.MATCH_RESTART, 'payload': {'agree': r}})
        else:
            # actual restart - reset board
            def task():
                self.board = [['' for _ in range(10)] for __ in range(10)]
                for y in range(10):
                    for x in range(10):
                        self.cells[y][x].configure(text=" ", state=tk.NORMAL)
                messagebox.showinfo("Thông báo", "Ván mới bắt đầu")
            self.root.after(0, task)

    def handle_opponent_left(self, payload):
        left_id = payload.get('left_player')
        def task():
            messagebox.showinfo("Thông báo", "Đối thủ đã rời trận. Trận đấu kết thúc.")
            # disable board
            for y in range(10):
                for x in range(10):
                    self.cells[y][x].configure(state=tk.DISABLED)
            self.in_match = False
        self.root.after(0, task)

    def handle_room_leave(self, payload):
        left_id = payload.get('left_player')
        def task():
            # go back to lobby
            messagebox.showinfo("Thông báo", "Phòng đã bị rời. Quay về màn hình chọn phòng.")
            self.room_id = None
            self.in_match = False
            # clear board
            for y in range(10):
                for x in range(10):
                    self.cells[y][x].configure(text=" ", state=tk.DISABLED)
        self.root.after(0, task)

    def handle_draw_request(self, payload):
        from_id = payload.get('from')
        r = messagebox.askyesno("Yêu cầu hòa", f"Đối thủ ({from_id}) yêu cầu hòa. Chấp nhận?")
        if r:
            send_msg(self.sock, {'code': Code.MATCH_DRAW_ACCEPT, 'payload': {}})
        else:
            send_msg(self.sock, {'code': Code.MATCH_DRAW_REJECT, 'payload': {}})

    def handle_draw_accept(self, payload):
        def task():
            messagebox.showinfo("Hòa", "Đối thủ đồng ý hòa. Trận đấu kết thúc: Hòa.")
            self.in_match = False
            # disable board
            for y in range(10):
                for x in range(10):
                    self.cells[y][x].configure(state=tk.DISABLED)
        self.root.after(0, task)

    def handle_draw_reject(self, payload):
        def task():
            messagebox.showinfo("Từ chối", "Đối thủ từ chối yêu cầu hòa.")
        self.root.after(0, task)

    def handle_server_message(self, msg):
        pass

    def on_server_disconnect(self):
        def task():
            messagebox.showerror("Kết nối", "Mất kết nối tới server.")
            self.root.destroy()
        self.root.after(0, task)

    def on_close(self):
        try:
            if self.sock:
                self.sock.close()
        except:
            pass
        self.root.destroy()

    def ask_rematch_prompt(self):
        # show popup asking whether player wants rematch
        r = messagebox.askyesno("Chơi lại?", "Bạn có muốn chơi lại?")
        if r:
            send_msg(self.sock, {'code': Code.MATCH_RESTART, 'payload': {'agree': True}})
        else:
            # do nothing; if opponent wants rematch they'll see request
            pass

    def click_cell(self, x, y):
        if not self.in_match:
            messagebox.showinfo("Thông báo", "Chưa có trận đấu.")
            return
        # local optimistic update is not applied; wait for server response
        send_msg(self.sock, {'code': Code.MATCH_MOVE, 'payload': {'x': x, 'y': y}})
    def handle_room_leave_success(self, payload):
        def task():
            messagebox.showinfo("Thông báo", "Bạn đã rời phòng thành công.")
            self.room_id = None
            self.in_match = False
            for y in range(10):
                for x in range(10):
                    self.cells[y][x].configure(text=" ", state=tk.DISABLED)
        self.root.after(0, task)


def client_handler(host="127.0.0.1", port=5000):
    ClientApp(host, port)
