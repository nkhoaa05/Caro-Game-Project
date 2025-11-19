# Caro 10x10 Multi-Room (TCP Socket)

**Mô tả dự án**  

Đây là dự án trò chơi Caro (10x10, Win 5) được phát triển bằng Python, sử dụng mô hình Multi Client–Server với Socket TCP. Hệ thống hỗ trợ:  

- Nhiều phòng (room), mỗi phòng tối đa 2 người chơi.  
- Chat trong phòng giữa các người chơi.  
- Tạo phòng, xem danh sách phòng, tham gia phòng bằng mã phòng.  
- Thoát phòng, rời phòng an toàn.  
- Chơi lại (Rematch) hoặc yêu cầu hòa (Draw).  
- Thông báo lượt đi, kết quả thắng/thua/hòa.  
- Giao diện người dùng được xây dựng bằng Tkinter, chạy trực tiếp trên desktop.  

**Yêu cầu cài đặt**  

- Python 3.8+  
- Các gói cần thiết:  

```bash
pip install --upgrade pip
pip install tk
````

*Lưu ý*: Tkinter thường được tích hợp sẵn trong Python. Nếu gặp lỗi liên quan đến Tkinter, cài đặt lại Python với tùy chọn tích hợp Tkinter.

**Cấu trúc dự án**

```
Caro10x10/
│
├── main.py          # File chạy chính (server hoặc client)
├── server.py        # Logic server quản lý phòng, trận đấu
├── client.py        # GUI client + xử lý sự kiện
├── common.py        # Định nghĩa mã lệnh, gửi/nhận JSON qua socket
├── helper.py        # Hàm hỗ trợ, thread, timestamp
└── README.md
```

**Hướng dẫn chạy trên máy local (localhost)**

1. **Chạy Server**

```bash
python main.py server 127.0.0.1 5000
```

* `127.0.0.1` là địa chỉ localhost.
* `5000` là port server lắng nghe (có thể thay đổi nếu muốn).

2. **Chạy Client**

Mỗi client chạy một cửa sổ GUI:

```bash
python main.py client 127.0.0.1 5000
```

Nhập địa chỉ host và port trùng với server.

3. **Sử dụng GUI Client**

* Tạo phòng → chờ đối thủ.
* Hoặc xem danh sách phòng → chọn phòng để tham gia.
* Chat với đối thủ trong phòng.
* Chơi, yêu cầu hòa, hoặc chơi lại sau trận đấu.

**Chơi giữa 2 máy tính khác nhau trong cùng mạng LAN**

Giả sử máy A là server, máy B là client:

* Trên máy A (server) chạy:

```bash
python main.py server 0.0.0.0 5000
```

> `0.0.0.0` cho phép server lắng nghe tất cả IP trong mạng LAN.

* Trên máy B (client) chạy:

```bash
python main.py client <IP của máy A> 5000
```

Thay `<IP của máy A>` bằng địa chỉ IPv4 của máy A trong mạng LAN, ví dụ `192.168.1.14`.

Firewall trên cả 2 máy cần cho phép Python truy cập mạng và mở port 5000. Không cần tắt hoàn toàn tường lửa.

Giờ máy A và B có thể chơi với nhau bằng GUI, tạo và join phòng, chat trực tiếp.

**Lưu ý**

* Mỗi phòng tối đa 2 người chơi.
* Nếu 1 người rời phòng, phòng sẽ thông báo và xóa player đó.
* Trường hợp mất kết nối, client sẽ thông báo “Mất kết nối tới server”.
* Game có cơ chế Rematch/Draw giữa 2 người chơi trong phòng.

**Ví dụ nhanh**

* **Local 1 máy (2 client)**

```bash
Terminal 1: python main.py server 127.0.0.1 5000
Terminal 2: python main.py client 127.0.0.1 5000
Terminal 3: python main.py client 127.0.0.1 5000
```

* **LAN (2 máy)**

```bash
Máy A (Server): python main.py server 0.0.0.0 5000
Máy B (Client): python main.py client 192.168.1.14 5000
```

```
