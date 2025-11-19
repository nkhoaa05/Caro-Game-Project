# server.py
import socket
import threading
import uuid
from common import Code, send_msg, recv_msg
from helper import safe_start_thread

# Data structures kept in RAM:
# rooms: room_id -> { 'players': [ (sock, addr, player_id) , ...], 'state': {...} , 'created': ts }
rooms = {}
# mapping from socket to room_id and player_id
clients = {}

LOCK = threading.Lock()

def server_handler(host="127.0.0.1", port=5000):
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((host, port))
    srv.listen(50)
    print("Server listening on", host, port)
    try:
        while True:
            client_sock, addr = srv.accept()
            print("Client connected", addr)
            safe_start_thread(handle_client, (client_sock, addr))
    finally:
        srv.close()

def handle_client(sock, addr):
    try:
        while True:
            msg = recv_msg(sock)
            if msg is None:
                print("Client disconnected", addr)
                handle_disconnect(sock)
                break
            code = msg.get('code')
            payload = msg.get('payload')
            if code == Code.JOIN_ROOM:
                handle_join_room(sock, addr, payload)
            elif code == Code.ROOM_CODE:
                if payload == "LIST":
                    send_room_list(sock)
            elif code == Code.MESSAGE_CODE:
                handle_chat(sock, payload)
            elif code == Code.MATCH_MOVE:
                handle_move(sock, payload)
            elif code == Code.MATCH_RESTART:
                handle_restart_request(sock, payload)
            elif code == Code.ROOM_LEAVE:
                handle_leave_room(sock, payload)
            elif code == Code.MATCH_DRAW_REQUEST:
                handle_draw_request(sock, payload)
            elif code == Code.MATCH_DRAW_ACCEPT:
                handle_draw_accept(sock, payload)
            elif code == Code.MATCH_DRAW_REJECT:
                handle_draw_reject(sock, payload)
            else:
                send_msg(sock, {'code': Code.ERROR, 'payload': 'Unknown code'})
    except Exception as e:
        print("Exception in client handler:", e)
        handle_disconnect(sock)
    finally:
        try:
            sock.close()
        except:
            pass

def handle_join_room(sock, addr, payload):
    action = payload.get('action')
    with LOCK:
        if action == "CREATE":
            room_id = str(uuid.uuid4())[:6]
            rooms[room_id] = {
                'players': [(sock, addr, "Player 1")],
                'state': make_new_state(),
            }
            clients[sock] = {'room_id': room_id, 'player_id': "Player 1"}
            send_msg(sock, {'code': Code.JOIN_ROOM, 'payload': {'status': 'WAIT', 'room_id': room_id, 'player_id': "Player 1"}})
            print(f"Room {room_id} created by {addr}")
        elif action == "JOIN":
            room_id = payload.get('room_id')
            if not room_id or room_id not in rooms:
                send_msg(sock, {'code': Code.ERROR, 'payload': 'Room not found'})
                return
            room = rooms[room_id]
            if len(room['players']) >= 2:
                send_msg(sock, {'code': Code.ERROR, 'payload': 'Room full'})
                return
            assigned_id = "Player 2"
            room['players'].append((sock, addr, assigned_id))
            clients[sock] = {'room_id': room_id, 'player_id': assigned_id}

            if len(room['players']) == 2:
                # start match
                p1_sock, _, p1_id = room['players'][0]
                p2_sock, _, p2_id = room['players'][1]
                # initialize state
                room['state'] = make_new_state()
                room['state']['turn'] = p1_id  # p1 starts
                room['state']['symbols'] = {p1_id: 'X', p2_id: 'O'}
                # notify both
                send_msg(p1_sock, {'code': Code.MATCH_START,
                                   'payload': {'you': p1_id, 'opponent': p2_id, 'symbol': 'X', 'room_id': room_id, 'first_turn': p1_id}})
                send_msg(p2_sock, {'code': Code.MATCH_START,
                                   'payload': {'you': p2_id, 'opponent': p1_id, 'symbol': 'O', 'room_id': room_id, 'first_turn': p1_id}})
                print(f"Match started in room {room_id} between {p1_id} and {p2_id}")
            else:
                # waiting for opponent
                send_msg(sock, {'code': Code.JOIN_ROOM, 'payload': {'status': 'WAIT', 'room_id': room_id, 'player_id': assigned_id}})
                print(f"{assigned_id} joined room {room_id}, waiting for opponent")
        else:
            send_msg(sock, {'code': Code.ERROR, 'payload': 'Invalid JOIN_ROOM action'})

def send_room_list(sock):
    with LOCK:
        waiting = []
        for rid, r in rooms.items():
            if len(r['players']) == 1:
                waiting.append({'room_id': rid})
        send_msg(sock, {'code': Code.ROOM_LIST, 'payload': waiting})

def handle_chat(sock, payload):
    info = clients.get(sock)
    if not info:
        send_msg(sock, {'code': Code.ERROR, 'payload': 'Not in a room'})
        return
    room_id = info['room_id']
    with LOCK:
        room = rooms.get(room_id)
        if not room:
            send_msg(sock, {'code': Code.ERROR, 'payload': 'Room not found'})
            return
        for p_sock, _, p_id in room['players']:
            if p_sock != sock:
                send_msg(p_sock, {'code': Code.MESSAGE_CODE, 'payload': {'from': info['player_id'], 'text': payload.get('text')}})

def handle_move(sock, payload):
    info = clients.get(sock)
    if not info:
        send_msg(sock, {'code': Code.ERROR, 'payload': 'Not in room'})
        return
    room_id = info['room_id']
    player_id = info['player_id']
    with LOCK:
        room = rooms.get(room_id)
        if not room:
            send_msg(sock, {'code': Code.ERROR, 'payload': 'Room missing'})
            return
        state = room['state']
        if len(room['players']) < 2:
            send_msg(sock, {'code': Code.ERROR, 'payload': 'Opponent missing'})
            return
        if state.get('finished'):
            send_msg(sock, {'code': Code.ERROR, 'payload': 'Match finished'})
            return
        if state.get('turn') != player_id:
            send_msg(sock, {'code': Code.ERROR, 'payload': 'Not your turn'})
            return
        x = payload.get('x'); y = payload.get('y')
        if not (0 <= x < 10 and 0 <= y < 10):
            send_msg(sock, {'code': Code.ERROR, 'payload': 'Invalid move'})
            return
        if state['board'][y][x] != '':
            send_msg(sock, {'code': Code.ERROR, 'payload': 'Cell occupied'})
            return
        sym = state['symbols'][player_id]
        state['board'][y][x] = sym
        winner = check_winner(state['board'], x, y, sym)
        # determine opponent socket
        opponent_sock = None
        for p_sock, _, p_id in room['players']:
            if p_id != player_id:
                opponent_sock = p_sock
                opp_id = p_id
                break
        if not winner:
            state['turn'] = opp_id
        else:
            state['finished'] = True
            state['result'] = {'winner': player_id}
        for p_sock, _, p_id in room['players']:
            send_msg(p_sock, {'code': Code.MATCH_MOVE, 'payload': {'x': x, 'y': y, 'symbol': sym, 'by': player_id, 'winner': winner}})
        if winner:
            print(f"Winner in room {room_id}: {player_id}")

def handle_restart_request(sock, payload):
    info = clients.get(sock)
    if not info:
        return
    room_id = info['room_id']
    player_id = info['player_id']
    with LOCK:
        room = rooms.get(room_id)
        if not room:
            return
        state = room['state']
        if 'restart_votes' not in state:
            state['restart_votes'] = set()
        vote = payload.get('agree', False)
        if vote:
            state['restart_votes'].add(player_id)
        else:
            state['restart_votes'] = set()
        if len(state['restart_votes']) >= 2:
            room['state'] = make_new_state()
            if len(room['players']) == 2:
                p1_id = room['players'][0][2]
                room['state']['turn'] = p1_id
                room['state']['symbols'] = {room['players'][0][2]: 'X', room['players'][1][2]: 'O'}
            for p_sock, _, _ in room['players']:
                send_msg(p_sock, {'code': Code.MATCH_RESTART, 'payload': {}})
            print(f"Room {room_id} restarted by mutual agreement")
        else:
            for p_sock, _, p_id in room['players']:
                if p_id != player_id:
                    send_msg(p_sock, {'code': Code.MATCH_RESTART, 'payload': {'request_from': player_id}})

def handle_leave_room(sock, payload):
    info = clients.get(sock)
    if not info:
        return
    room_id = info['room_id']
    player_id = info['player_id']
    with LOCK:
        room = rooms.get(room_id)
        if not room:
            return
        new_players = [p for p in room['players'] if p[2] != player_id]
        room['players'] = new_players
        for p_sock, _, p_id in room['players']:
            send_msg(p_sock, {'code': Code.ROOM_LEAVE, 'payload': {'left_player': player_id}})
            send_msg(p_sock, {'code': Code.MATCH_LEFT, 'payload': {'left_player': player_id}})
        if len(room['players']) == 0:
            del rooms[room_id]
            print(f"🗑️ Room {room_id} deleted (empty)")
        send_msg(sock, {'code': Code.ROOM_LEAVE_SUCCESS, 'payload': {}})
        try:
            del clients[sock]
        except KeyError:
            pass
        print(f"Player {player_id} left room {room_id} voluntarily")

def handle_disconnect(sock):
    info = clients.get(sock)
    if not info:
        return
    room_id = info['room_id']
    player_id = info['player_id']
    with LOCK:
        room = rooms.get(room_id)
        if room:
            new_players = [p for p in room['players'] if p[2] != player_id]
            room['players'] = new_players
            for p_sock, _, p_id in room['players']:
                send_msg(p_sock, {'code': Code.MATCH_LEFT, 'payload': {'left_player': player_id}})
                send_msg(p_sock, {'code': Code.ROOM_LEAVE, 'payload': {'left_player': player_id}})
            if len(room['players']) == 0:
                del rooms[room_id]
                print(f"🗑️ Room {room_id} deleted (empty due to disconnect)")
        try:
            del clients[sock]
        except:
            pass
        print(f"Handled disconnect of {player_id} from room {room_id}")

def handle_draw_request(sock, payload):
    info = clients.get(sock)
    if not info:
        return
    room_id = info['room_id']
    player_id = info['player_id']
    with LOCK:
        room = rooms.get(room_id)
        if not room:
            return
        for p_sock, _, p_id in room['players']:
            if p_id != player_id:
                send_msg(p_sock, {'code': Code.MATCH_DRAW_REQUEST, 'payload': {'from': player_id}})

def handle_draw_accept(sock, payload):
    info = clients.get(sock)
    if not info:
        return
    room_id = info['room_id']
    with LOCK:
        room = rooms.get(room_id)
        if not room:
            return
        room['state']['finished'] = True
        room['state']['result'] = {'draw': True}
        for p_sock, _, _ in room['players']:
            send_msg(p_sock, {'code': Code.MATCH_DRAW_ACCEPT, 'payload': {}})

def handle_draw_reject(sock, payload):
    info = clients.get(sock)
    if not info:
        return
    room_id = info['room_id']
    player_id = info['player_id']
    with LOCK:
        room = rooms.get(room_id)
        if not room:
            return
        for p_sock, _, p_id in room['players']:
            if p_id != player_id:
                send_msg(p_sock, {'code': Code.MATCH_DRAW_REJECT, 'payload': {'from': player_id}})

# helpers
def make_new_state():
    return {
        'board': [['' for _ in range(10)] for __ in range(10)],
        'turn': None,
        'symbols': {},
        'finished': False,
        'result': None,
    }

def check_winner(board, x, y, sym):
    directions = [(1,0),(0,1),(1,1),(1,-1)]
    for dx, dy in directions:
        cnt = 1
        nx, ny = x+dx, y+dy
        while 0 <= nx < 10 and 0 <= ny < 10 and board[ny][nx] == sym:
            cnt += 1
            nx += dx; ny += dy
        nx, ny = x-dx, y-dy
        while 0 <= nx < 10 and 0 <= ny < 10 and board[ny][nx] == sym:
            cnt += 1
            nx -= dx; ny -= dy
        if cnt >= 5:
            return True
    return False
