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
    player_id = str(uuid.uuid4())[:8]
    try:
        while True:
            msg = recv_msg(sock)
            if msg is None:
                print("Client disconnected", addr)
                handle_disconnect(sock)
                break
            code = msg.get('code')
            payload = msg.get('payload')
            # print("Received", code, payload)
            if code == Code.JOIN_ROOM:
                # payload: { 'action': 'CREATE' } or { 'action': 'JOIN', 'room_id': '...' }
                handle_join_room(sock, addr, player_id, payload)
            elif code == Code.ROOM_CODE:
                # payload: "LIST"
                if payload == "LIST":
                    send_room_list(sock)
            elif code == Code.MESSAGE_CODE:
                # relay chat in room
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

def handle_join_room(sock, addr, player_id, payload):
    action = payload.get('action')
    with LOCK:
        if action == "CREATE":
            room_id = str(uuid.uuid4())[:6]
            rooms[room_id] = {
                'players': [(sock, addr, player_id)],
                'state': make_new_state(),
            }
            clients[sock] = {'room_id': room_id, 'player_id': player_id}
            send_msg(sock, {'code': Code.JOIN_ROOM, 'payload': {'status': 'WAIT', 'room_id': room_id}})
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
            room['players'].append((sock, addr, player_id))
            clients[sock] = {'room_id': room_id, 'player_id': player_id}
            # start match
            p1_sock, _, p1_id = room['players'][0]
            p2_sock, _, p2_id = room['players'][1]
            # initialize state
            room['state'] = make_new_state()
            room['state']['turn'] = p1_id  # p1 starts
            # assign symbols
            room['state']['symbols'] = {p1_id: 'X', p2_id: 'O'}
            # notify both
            send_msg(p1_sock, {'code': Code.MATCH_START, 'payload': {'you': p1_id, 'opponent': p2_id, 'symbol': 'X', 'room_id': room_id}})
            send_msg(p2_sock, {'code': Code.MATCH_START, 'payload': {'you': p2_id, 'opponent': p1_id, 'symbol': 'O', 'room_id': room_id}})
            print(f"Match started in room {room_id} between {p1_id} and {p2_id}")
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
    # payload: {'text': '...'}
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
        # relay to other player
        for p_sock, _, p_id in room['players']:
            if p_sock != sock:
                send_msg(p_sock, {'code': Code.MESSAGE_CODE, 'payload': {'from': info['player_id'], 'text': payload.get('text')}})

def handle_move(sock, payload):
    # payload: {'x': int, 'y': int}
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
        # If match not started or not two players, ignore
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
        # check win
        winner = check_winner(state['board'], x, y, sym)
        # determine opponent socket
        opponent_sock = None
        for p_sock, _, p_id in room['players']:
            if p_id != player_id:
                opponent_sock = p_sock
                opp_id = p_id
                break
        # update turn
        if not winner:
            state['turn'] = opp_id
        else:
            state['finished'] = True
            state['result'] = {'winner': player_id}
        # relay move to opponent and ack to mover
        for p_sock, _, p_id in room['players']:
            send_msg(p_sock, {'code': Code.MATCH_MOVE, 'payload': {'x': x, 'y': y, 'symbol': sym, 'by': player_id, 'winner': winner}})
        if winner:
            print(f"Winner in room {room_id}: {player_id}")

def handle_restart_request(sock, payload):
    # For simplicity: if one player requests restart, wait for both to send MATCH_RESTART with payload {'agree': True}
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
            # any disagree cancels votes
            state['restart_votes'] = set()
        if len(state['restart_votes']) >= 2:
            # reset board and notify both
            room['state'] = make_new_state()
            # assign same turn to previous starter randomly; we'll set turn to first player's id
            if len(room['players']) == 2:
                p1_id = room['players'][0][2]
                room['state']['turn'] = p1_id
                room['state']['symbols'] = {room['players'][0][2]: 'X', room['players'][1][2]: 'O'}
            for p_sock, _, _ in room['players']:
                send_msg(p_sock, {'code': Code.MATCH_RESTART, 'payload': {}})
            print(f"Room {room_id} restarted by mutual agreement")
        else:
            # notify other player that someone wants restart (optional)
            for p_sock, _, p_id in room['players']:
                if p_id != player_id:
                    send_msg(p_sock, {'code': Code.MATCH_RESTART, 'payload': {'request_from': player_id}})

def handle_leave_room(sock, payload):
    # payload may be empty
    info = clients.get(sock)
    if not info:
        return
    room_id = info['room_id']
    player_id = info['player_id']
    with LOCK:
        room = rooms.get(room_id)
        if not room:
            return
        # remove player from room
        new_players = [p for p in room['players'] if p[2] != player_id]
        room['players'] = new_players
        # notify remaining player
        for p_sock, _, p_id in room['players']:
            send_msg(p_sock, {'code': Code.ROOM_LEAVE, 'payload': {'left_player': player_id}})
            # also signal match left if match was ongoing
            send_msg(p_sock, {'code': Code.MATCH_LEFT, 'payload': {'left_player': player_id}})
        # if room empty, delete
        if len(room['players']) == 0:
            del rooms[room_id]
        # cleanup client mapping for leaving socket
        send_msg(sock, {'code': Code.ROOM_LEAVE_SUCCESS, 'payload': {}})
        print(f"Player {player_id} left room {room_id} voluntarily")
        try:
            del clients[sock]
        except KeyError:
            pass
        print(f"Player {player_id} left room {room_id}")

def handle_disconnect(sock):
    info = clients.get(sock)
    if not info:
        return
    room_id = info['room_id']
    player_id = info['player_id']
    with LOCK:
        room = rooms.get(room_id)
        if not room:
            try:
                del clients[sock]
            except:
                pass
            return
        # remove this player
        new_players = [p for p in room['players'] if p[2] != player_id]
        room['players'] = new_players
        # notify remaining
        for p_sock, _, p_id in room['players']:
            send_msg(p_sock, {'code': Code.MATCH_LEFT, 'payload': {'left_player': player_id}})
            send_msg(p_sock, {'code': Code.ROOM_LEAVE, 'payload': {'left_player': player_id}})
        if len(room['players']) == 0:
            # delete room
            del rooms[room_id]
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
        # forward request to opponent
        for p_sock, _, p_id in room['players']:
            if p_id != player_id:
                send_msg(p_sock, {'code': Code.MATCH_DRAW_REQUEST, 'payload': {'from': player_id}})

def handle_draw_accept(sock, payload):
    info = clients.get(sock)
    if not info:
        return
    room_id = info['room_id']
    player_id = info['player_id']
    with LOCK:
        room = rooms.get(room_id)
        if not room:
            return
        # mark finish with draw
        room['state']['finished'] = True
        room['state']['result'] = {'draw': True}
        # notify both
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
        # forward reject to opponent
        for p_sock, _, p_id in room['players']:
            if p_id != player_id:
                send_msg(p_sock, {'code': Code.MATCH_DRAW_REJECT, 'payload': {'from': player_id}})

# helpers for game state
def make_new_state():
    return {
        'board': [['' for _ in range(10)] for __ in range(10)],
        'turn': None,
        'symbols': {},
        'finished': False,
        'result': None,
    }

def check_winner(board, x, y, sym):
    # check 5 in a row (gomoku style) horizontally, vertically, both diagonals
    directions = [(1,0),(0,1),(1,1),(1,-1)]
    for dx, dy in directions:
        cnt = 1
        # forward
        nx, ny = x+dx, y+dy
        while 0 <= nx < 10 and 0 <= ny < 10 and board[ny][nx] == sym:
            cnt += 1
            nx += dx; ny += dy
        # backward
        nx, ny = x-dx, y-dy
        while 0 <= nx < 10 and 0 <= ny < 10 and board[ny][nx] == sym:
            cnt += 1
            nx -= dx; ny -= dy
        if cnt >= 5:
            return True
    return False
