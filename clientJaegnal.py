import socket
import select
import sys
from threading import Timer

M = 16

name = ""
ip_address = ""
client_key = 0
port = ""
conversing = False

peer_sock = ""
peer_name = ""

succ_sock = ""
pred_sock = ""
pred = dict()
succ = dict()

isNode = False
isConnector = False
responsible_keys = dict()
# responsible_socks = []

max_res_nodes = 3
finger_table = dict()

server_ip = ""
server_port = 0
server_sock = ""

connector_sock = ""


def setup_jaeman():
    global ip_address, port
    #creates a listening sock based on the port given
    localhost = socket.gethostname()
    ip_address = socket.gethostbyname(localhost)
    print(ip_address)
    port = input("Welcome, Jaeman! What's the port you'd like to use for your client? ")
    sock =socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((ip_address, int(port)))
    sock.listen()
    return sock


def connect_to_server():
    #connects to the server's socket based on the server ip and port given
    global server_ip, server_port, server_sock
    first_input = input("What's the IP Address and the port of the server you'd like to connect to?\nPlease follow the format:\n[server ip address] [server port]\n\n")
    first_input = first_input.split()
    server_ip = first_input[0]
    server_port = int(first_input[1])
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.connect((server_ip, int(server_port)))
    return server_sock

def run_jaeman(sock, server_sock):
    socket_list = [sys.stdin, sock, server_sock]

    while True:
        r_sockets, w_sockets, e_sockets = select.select(socket_list, [], [])
        for r_sock in r_sockets:
            if r_sock == sock:
                #listning socket. handles join, stabilize, lookup, found, converse, newpred
                conn, addr = r_sock.accept()
                socket_list = handle_listen(conn, socket_list)
            elif r_sock == server_sock:
                socket_list = handle_server(r_sock, socket_list)
            elif r_sock == peer_sock:
                #peer socket, handles converse, quit, busy, connected
                #formar for connected: connect succ_ip_address succ_port
                socket_list == handle_peer(r_sock, socket_list)
            elif r_sock == sys.stdin:
                socket_list = handle_send(r_sock, socket_list)
            else:
                data = r_sock.recv(1024)
                if not data:
                    pass


def handle_send(r_sock, socket_list):
    global name, client_key, conversing, peer_name, peer_sock, isNode, isConnector, succ_sock, succ
    message = sys.stdin.readline()
    if conversing:
        peer_sock.send(message.encode())
        if message.split()[0] == "quit":
            print("You just quit the conversation with Jaeman %s" % (peer_name,))
            r_sock.close()
            peer_name = ""
            peer_sock = ""
            conversing = False
            socket_list.remove(peer_sock)
            return socket_list
    elif message.split()[0] == "register":
        name = message.split()[1]
        client_key = hash_name(name)
        server_sock.send(message.encode())
    elif message.split()[0] == "exit":
        if not isNode:
            succ_sock.send(("exit %s" % (client_key,)).encode())
        else:
            table_length = len(responsible_keys)
            pred_key = list(pred.keys())[0]
            pred_ip, pred_port = pred[pred_key][1], pred[pred_key][2]
            if isConnector:
                header_succ = "exit %s %s %s %s connectorupdate" % (table_length, pred_key, pred_ip, pred_port)
            else:
                header_succ = "exit %s %s %s %s" % (table_length, pred_key, pred_ip, pred_port)
            succ_sock.send(header_succ.encode())

            keys_list = list(responsible_keys.keys())
            for i in range(table_length):
                key = keys_list[i]
                resp_name, resp_ip, resp_port = responsible_keys[key]
                succ_sock.send(("%s %s %s" % (resp_name, resp_ip, resp_port)).encode())
        for tc_socket in socket_list:
            tc_socket.close()
        sys.exit("Quit Jaegnal!")

    elif message.split()[0] in ["register", "login", "connect", "connectorupdate"]:
        server_sock.send(message.encode())
    elif message.split()[0] == "lookup":
        user_key = hash_name(message.split()[1])
        data = message.split()
        #special local cases for lookup
        if not isNode:
            if list(succ.keys())[0] == user_key:
                lookup_name, lookup_ip, lookup_port = succ[user_key]
                lookup_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                lookup_sock.connect((lookup_ip, int(lookup_port)))
                lookup_sock.send(("converse %s" % (name,)).encode())
                peer_name, peer_sock, conversing = message.split()[1], lookup_sock, True
                if peer_sock not in socket_list:
                    socket_list.append(peer_sock)
                print()
                print()
        elif user_key in responsible_keys:
            lookup_name, lookup_ip, lookup_port = responsible_keys[user_key]
            lookup_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            lookup_sock.connect((lookup_ip, int(lookup_port)))
            lookup_sock.send(("converse %s" % (name,)).encode())
            peer_name, peer_sock, conversing = message.split()[1], lookup_sock, True
            if peer_sock not in socket_list:
                socket_list.append(peer_sock)
            print()
            print()
        elif user_key in finger_table:
            lookup_name, lookup_ip, lookup_port = finger_table[user_key]
            lookup_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            lookup_sock.connect((lookup_ip, int(lookup_port)))
            lookup_sock.send(("converse %s" % (name,)).encode())
            peer_name, peer_sock, conversing = message.split()[1], lookup_sock, True
            if peer_sock not in socket_list:
                socket_list.append(peer_sock)
            print()
            print()
        else:
            data.append(ip_address)
            data.append(port)
            find_successor(data, socket_list)
    
    return socket_list


def handle_peer(r_sock, socket_list):
    global conversing, peer_name, peer_sock, isNode, isConnector
    data = r_sock.recv(4096)
    if not data:
        #print("Error receiving data from peer %s" % (peer_name,))
        return socket_list
    data = data.decode()
    if data == "quit" or data == "busy":
        msg = "Jaeman %s has just quit the conversation" % (peer_name,)
        if data == "busy":
            msg = "Jaeman %s is busy talking to someone else. You could try again in a bit" % (peer_name,)
        print(msg)
        r_sock.close()
        peer_name = ""
        peer_sock = ""
        conversing = False
        socket_list.remove(r_sock)
        return socket_list
    else:
        data = peer_name + ": " + data
        print(data[:-1])
        #print(data.split())
            #print("Yooooooo")
    return socket_list


def handle_server(r_sock, socket_list):
    global isNode, isConnector, succ, server_sock
    data = r_sock.recv(1024)
    if not data:
        print("Error receiving data from server")
        return socket_list
    data = data.decode()
    data = data.split()

    if data[0] == "setupconnector":
        #when the server sends this command, it's because this is the first node in the network
        isNode = True
        isConnector = True
        succ[client_key] = [name, ip_address, port]
        pred[client_key] = [name, ip_address, port]
        r_sock.send(("connectorupdate %s %s" % (ip_address, port)).encode())
        socket_list.remove(r_sock)
        r_sock.close()
        #print("Connectorupdatedddddddddddddddddddd")

    elif data[0] == "connector":
        r_sock.close()
        socket_list.remove(r_sock)
        connector_ip = data[1]
        connector_port = int(data[2])
        connector_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        connector_sock.connect((connector_ip, connector_port))
        connector_sock.send(("join %s %s %s" % (client_key, ip_address, port)).encode())
        #socket_list.remove(server_sock)
        server_sock.close()
        #print("Connector seeeeeeeeeeeeeeeeeeent")
        socket_list.append(connector_sock)
        #socket_list.remove(r_sock)
        #connector_sock.close()
        
    else:
        print(" ".join(data))
    return socket_list

def handle_listen(r_sock, socket_list):
    global peer_name, peer_sock, conversing, isNode, responsible_keys, succ, pred, succ_sock, isConnector, connector_sock
    #large because we may receive new responsibilty keys in case of "newnode"
    data = r_sock.recv(4092)
    if not data:
        print("Error receving message from a new Jaeman")
    data = data.decode()
    data = data.split()

    #handle commands
    if data[0] == "join":
        #this is a node & a connector node then
        #format: join joining_key OR join joining_key original_ip original_port (if join was forwarded)
        #print("jooooooooooooooooooooooooooooooooooooooooin received")
        #print(data)
        socket_list = find_successor(data, socket_list)
            
    elif data[0] == "lookup":
        #format: lookup username original_ip original_port
        user_key = hash_name(data[1])
        socket_list = find_successor(data, socket_list)
        #print("at the time of lookup read, successor was %s " % list(succ.keys())[0])
        #print("at the time of lookup read, pred was %s " % list(pred.keys())[0])

    elif data[0] == "found":
        #result of hearing back from lookup. binds on the socket, sends converse
        #format: found found_key ip_address port
        #the lookup socket is no longer necessary
        #r_sock.close()
        #socket_list.remove(r_sock)
        new_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        new_sock.connect((data[2], int(data[3])))
        new_sock.send(("converse %s" % (name,)).encode())
        print()
        print()
        data[1] = hash_reversal(int(data[1]))
        peer_sock = new_sock
        # if (data[1] == list(succ.keys())[0]):
        #     peer_sock = succ_sock
        peer_name = data[1]
        conversing = True
        if peer_sock not in socket_list:
            socket_list.append(peer_sock)
        
    elif data[0] == "converse":
        #format: converse name
        if conversing:
            r_sock.send("busy".encode())
            r_sock.close()
        else:
            peer_name = data[1]
            peer_sock = r_sock
            if (hash_name(data[1]) == list(succ.keys())[0]):
                peer_sock = succ_sock
            if peer_sock not in socket_list:
                socket_list.append(peer_sock)
            conversing = True
            print()
            print()
    
    elif data[0] == "connected":
        #format: connected succcessor_key successor_ip succesor_port
        #so far, this is not a node. this simply gets added to its successor's res table
        #################################################################
        #when successor of a new key is found after the new client with the new key calls "connect". 
        #Kicks of changing of successor relations and stabilization of (successor, newnode, successor's old predecessor):
        #1- The new client tells its successor to start the "stabilize" procedure.
        #2- succ adds the new key to its responsible key table. If the table is full, select the middle value key and asks it to turn into a node using the command "newnode", so it sends the new node (a) it's predecessor's key to it could stabilize it (b) the length of the number of keys the successor will offload to the new node (c) the keys themselves. 
        #3- The new node tells its successor to update its predecessor, and the successor's old predecessor to update its successor to the new node. The first is done with "newpred", the latter is done with "newsucc".
        ##################################################################
        new_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        new_sock.connect((data[2], int(data[3])))
        #print(data[1])
        succ_key = int(data[1])
        #print(succ_key)
        succ[succ_key] = [hash_reversal(succ_key), data[2], int(data[3])]
        succ_sock = new_sock
        if succ_sock not in socket_list:
            socket_list.append(succ_sock)
        #send (stabilize new_key new_ip new_port) to successor
        succ_sock.send(("stabilize %s %s %s" % (client_key, ip_address, port) ).encode())
        #print("connected receeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeived")

    elif data[0] == "stabilize":
        #format: stabilize new_key new_ip_address new_port
        #ordinarily, we just add the new key to its successor's responsibility table.
        #but if the responsibility table exceeds the limit set, we create a new node and split it up.
        new_key = int(data[1])        
        new_element = [hash_reversal(new_key), data[2], data[3]]
        responsible_keys[new_key] = new_element
        #create a new node if the responsibility table is too full
        #responsible_socks.append(r_sock)
        if len(responsible_keys) > max_res_nodes: 
            res_keys_copy = responsible_keys.copy()
            keys_to_delete = []
            #get new node's key and ip and port.
            #we split the interval the successor covers right down the middle.
            sorted_res_keys = sorted(list(responsible_keys.keys()))
            midpoint = len(sorted_res_keys)//2
            middle_key = sorted_res_keys[midpoint]
            middle_ip = responsible_keys[middle_key][1]
            middle_port = responsible_keys[middle_key][2]
            middle_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            middle_sock.connect((middle_ip, int(middle_port)))
            #send pred info to the new node
            # succ_key = list(pred.keys())[0]
            # header = "newsucc %s %s %s" % (client_key, ip_address, port)
            pred_key = list(pred.keys())[0]
            pred_ip, pred_port = pred[pred_key][1], pred[pred_key][2]
            header = "newnode %s %s %s %s %s %s %s" % (len(sorted_res_keys[:midpoint]), pred_key, pred_ip, pred_port, succ_key, succ_ip, succ_port)
            middle_sock.send(header.encode()) 
            #send keys for whom the new node will be the successor
            for k in sorted_res_keys[:midpoint]:
                keys_to_delete.append(k)
                new_name, new_ip, new_port = responsible_keys[k]
                new_line = "%s %s %s %s" % (k, name, new_ip, new_port)
                middle_sock.send(new_line.encode())
            #delete keys for whom the new node will be the successor
            for i in keys_to_delete:
                res_keys_copy.pop(i)
            res_keys_copy.pop(middle_key)
            responsible_keys = res_keys_copy

    elif data[0] == "exit":
        #predecessor or some key tell their successor it wants to exit the program
        #format: exit key OR exit n_new_keys pred_key pred_ip pred_port (if the client exiting is a node)
        #If exiting client is a key client the node is responsible for
        if len(data) == 2:
            responsible_keys.pop(int(data[1]))
            remove_ip, remove_port = responsible_keys[int(data[1])][1], responsible_keys[int(data[1])][2]
            remove_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            remove_socket.connect((remove_socket, int(remove_port)))
            socket_list.remove(remove_socket)
        #Else if the exiting client is the predecessor
        else:
            table_length = int(data[1])
            if len(data) == 6:
                server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                server_sock.connect((server_ip, server_port))
                server_sock.send(("connectorupdate %s %s" % (ip_address, port)).encode())
                server_sock.close()
                isConnector = True

            pred_key, pred_ip, pred_port = int(data[2]), data[3], int(data[4])
            pred_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            pred_sock.connect((pred_ip, pred_port))
            pred_sock.send(("newsucc %s %s %s" % (client_key, ip_address, port)).encode())
            pred_sock.close()

            for i in range(table_length):
                data = r_sock.recv(4096)
                if not data:
                    print("Error receving data from exiting predecessor")
                data = data.decode()
                data = data.split()
                new_key, new_ip, new_port = int(data[0]), data[1], int(data[2])
                responsible_keys[new_key] = [hash_reversal(new_key), new_ip, new_port]
                new_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                new_sock.connect((new_ip, new_port))
                new_sock.send(("newsucc %s %s %s" % (client_key, ip_address, port)).encode())
                new_sock.close()

        if len(responsible_keys) > max_res_nodes:
            middle_sock = create_newnode()
            # socket_list.append(middle_sock)

    elif data[0] == "newpred":
        #format: newpred new_pred_key new_pred_ip new_pred_port
        pred[int(data[1])] = [hash_reversal(int(data[1])), data[2], data[3]]

    elif data[0] == "newsucc":
        #format: newsucc new_succ_key new_succ_ip new_succ_port
        succ_key, succ_ip, succ_port = int(data[1]), data[2], int(data[3])
        succ = dict()
        succ[succ_key] = [hash_reversal(succ_key), succ_ip, succ_port]
        succ_sock.close()
        succ_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        succ_sock.connect((succ_ip, succ_port))

    elif data[0] == "newnode":
        #WORST CASE have a new header for newnode keys sending after newpred
        #format: newnode nkeys succkey succip succport predkey predid predport
        #        ###number_of_new_keys times:
        #           key ip port
        isNode = True
        #Update successor
        succ[int(data[5])] = [hash_reversal(int(data[5])), data[6], int(data[7])]
        #Update predecessor's successor (stabilize successor)
        succ_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        succ_sock.connect((data[6], data[7]))

        pred[int(data[2])] = [hash_reversal(int(data[2])), data[3], int(data[4])]
        pred_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        pred_sock.connect((data[3], data[4]))
        update_pred_succ = "newsucc %s %s %s" % (client_key, ip_address, port)
        pred_sock.send(update_pred_succ.encode())
        pred_sock.close() #no need to keep a socket with predecessor, only key, ip, port
        pred_sock = ""
        #Populate responsibility table
        n_new_entries = int(data[1])
        for i in range(n_new_entries):
            #format: key ip port
            data = r_sock.recv(4096)
            if not data:
                print("Error receving data from successor")
            data[0] = int(data[0])
            responsible_keys[data[0]] = [hash_reversal(data[0]), data[1], int(data[2])]
        #update successors of the non-node clients
        for i,v in responsible_keys:
            new_key, new_ip_address, new_port = v
            new_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            new_sock.connect((new_ip_address, new_port))
            new_sock.send(("newsucc %s %s %s" % (client_key, ip_address, port)).encode())
            new_sock.close()
        #Update successor's predecessor to the new node
        update_succ_pred = "newpred %s %s %s" % (client_key, ip_address, port)
        succ_sock.send(update_succ_pred.encode())

    return socket_list


def find_successor(data, socket_list):
    global succ_sock
    if data[0] == "lookup":
        key = hash_name(data[1])
        return_command = "found"
    else:
        key = int(data[1])
        return_command = "connected"

    if not isNode:
        if succ_sock == "":
            succ_key = list(succ.keys())[0]
            succ_ip, succ_port = (succ[succ_key][1], succ[succ_key][2])
            succ_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            succ_sock.connect((succ_ip, succ_port))
            socket_list.append(succ_sock)
        succ_sock.send(("%s %s %s %s" % (data[0], data[1], data[2], data[3])).encode())
        return socket_list

    original_ip, original_port = data[2], int(data[3])
    original_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    original_sock.connect((original_ip, int(original_port)))

    #base case, when we have only one node
    if data[0] == "join":
        if list(succ.keys())[0] == client_key and list(pred.keys())[0] == client_key:
            original_sock.send(("%s %s %s %s" % (return_command, client_key, ip_address, port)).encode())
        if original_sock not in socket_list:
            socket_list.append(original_sock)
    elif key == client_key:
        original_sock.send(("%s %s %s %s" % (return_command, client_key, ip_address, port)).encode())
        if original_sock not in socket_list:
            socket_list.append(original_sock)
    elif key in responsible_keys:
        found_name, found_ip, found_port = responsible_keys[key]
        original_sock.send(("%s %s %s %s" % (return_command, key, found_ip, found_port)).encode())
        if original_sock not in socket_list:
            socket_list.append(original_sock)
    #if in finger table
    elif key in finger_table:
        successor_ip, successor_port = finger_table[key][1], finger_table[key][2]
        if original_sock not in socket_list:
            socket_list.append(original_sock)
        #if message had origin_ip and origin_port with it

        original_sock.send(("%s %s %s %s" % (return_command, key, successor_ip, successor_port)).encode())

    else:
        #not in fingertable, forward request
        forward_request(data[0], key, data[2], int(data[3]))
        #the client that made the request will hear back eventually possibly from a different node
    return socket_list


def forward_request(request, key, original_ip, original_port):
    forward_ip, forward_port = closest_preceding_node(key)
    forward_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    forward_sock.connect((forward_ip, int(forward_port)))
    forward_sock.send(("%s %s %s %s" % (request, key, original_ip, original_port)).encode()) 
    #forward_sock.close()   


def closest_preceding_node(key):
    #goes through the list of keys, finds the closes preceding one
    key_list = list(finger_table.keys())
    min_distance = sys.maxsize
    min_key = ""
    for i in reversed(range(len(key_list))):
        finger_key_modded = key_list[i] % M
        client_key_modded = client_key % M
        key_modded = key % M

        #the fingertable node identifier must be between the desired key's identifier and the current node's
        if (client_key_modded < finger_key_modded < key_modded) or (key_modded < client_key_modded < finger_key_modded) or (finger_key_modded < key_modded < client_key_modded) or (key_modded == finger_key_modded):
            
            distance = key_modded - client_key_modded
            if distance < min_distance < 0:
                min_distance = distance
                min_key = key_list[i]

    closest_ip, closest_port = finger_table[min_key][1], finger_table[min_key][2]
    return (closest_ip, closest_port)


def create_newnode():
    global responsible_keys

    res_keys_copy = responsible_keys.copy()
    keys_to_delete = []

    #get new node's key and ip and port.
    #we split the interval the successor covers right down the middle.
    sorted_res_keys = sorted(list(responsible_keys.keys()))
    midpoint = len(sorted_res_keys)//2
    middle_key = sorted_res_keys[midpoint]
    middle_ip = responsible_keys[middle_key][1]
    middle_port = responsible_keys[middle_key][2]

    middle_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    middle_sock.connect((middle_ip, int(middle_port)))

    #send succ and pred info to the new node
    pred_key = list(pred.keys())[0]
    pred_ip, pred_port = pred[pred_key][1], pred[pred_key][2]
    header = "newnode %s %s %" % (len(sorted_res_keys[:midpoint]), pred_key, pred_ip, pred_port )
    middle_sock.send(header.encode()) 

    #send keys for whom the new node will be the successor
    for k in sorted_res_keys[:midpoint]:
        keys_to_delete.append(k)
        new_name, new_ip, new_port = res_keys_copy[k]
        new_line = "%s %s %s %s" % (k, new_name, new_ip, new_port)
        middle_sock.send(new_line.encode())

    #delete keys for whom the new node will be the successor
    for i in keys_to_delete:
        res_keys_copy.pop(i)
    responsible_keys = res_keys_copy
    res_keys_copy.pop(middle_key)
    return middle_sock

binary_mapping = {
    '0': '000000', '1': '000001', '2': '000010', '3': '000011', '4': '000100',
    '5': '000101', '6': '000110', '7': '000111', '8': '001000', '9': '001001',
    'a': '001010', 'b': '001011', 'c': '001100', 'd': '001101', 'e': '001110',
    'f': '001111', 'g': '010000', 'h': '010001', 'i': '010010', 'j': '010011',
    'k': '010100', 'l': '010101', 'm': '010110', 'n': '010111', 'o': '011000',
    'p': '011001', 'q': '011010', 'r': '011011', 's': '011100', 't': '011101',
    'u': '011110', 'v': '011111', 'w': '100000', 'x': '100001', 'y': '100010',
    'z': '100011', '_': '100100'
}

binary_mapping_reverse = {
     '000000': '0', '000001': '1', '000010': '2', '000011': '3', '000100': '4', 
     '000101': '5', '000110': '6', '000111': '7', '001000': '8', '001001': '9', 
     '001010': 'a', '001011': 'b', '001100': 'c', '001101': 'd', '001110': 'e', 
     '001111': 'f', '010000': 'g', '010001': 'h', '010010': 'i', '010011': 'j', 
     '010100': 'k', '010101': 'l', '010110': 'm', '010111': 'n', '011000': 'o', 
     '011001': 'p', '011010': 'q', '011011': 'r', '011100': 's', '011101': 't', 
     '011110': 'u', '011111': 'v', '100000': 'w', '100001': 'x', '100010': 'y', 
     '100011': 'z', '100100': '_'
}

def hash_name(name):
    hash = ""
    for i in range(len(name)):
        hash = hash + binary_mapping[name[i]]
    #print(hash)
    return int(hash,2)

def hash_reversal(key):
    name = ""
    binar = bin(key)[2:]
    expected_length = (len(binar) % 6 )+1
    #print(len(binar))
    binary_key = binar.zfill(6 * expected_length)
    #print(binary_key)
    binary_character = ""
    for i in range(len(binary_key)):
        binary_character += binary_key[i]
        if (i+1) % 6 == 0:
            #print(binary_key)
            name += binary_mapping_reverse[binary_character]
            binary_character = ""
    return name

if __name__ == "__main__":
    sock = setup_jaeman()
    server_sock = connect_to_server()
    run_jaeman(sock, server_sock)