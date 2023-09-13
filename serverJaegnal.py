import socket
import select

welcome_message = "Welcome to Jaegnal! \n \n If you'd like to register under a new username, plase follow the format:\nregister [username] [password] \n \n If you'd like to log in to an existing account, plaese follow the format: \n login [username] [password] \n \n If you'd like to connecto the Jaegnal network, please follow the format: \n connect \n \n "

passwords_table = dict()

connector_ip = ""
connector_port = ""

def start_server():
    #sets up server post on ip address and sets up listening socket
    #ip_address = input("What's the ip you'd like to use? ")
    localhost = socket.gethostname()
    ip_address = socket.gethostbyname(localhost)
    print(ip_address)
    port = input("What's the port you'd like to use for the server? ")

    sock =socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((ip_address, int(port)))
    sock.listen()

    return sock

def run_server(sock):
    global connector_ip, connector_port
    socket_list = [sock,]
    while True:
        r_sockets, w_sockets, e_sockets = select.select(socket_list, [], [])
        for r_sock in r_sockets:
            if r_sock == sock:
            #listening sock
                conn, addr = r_sock.accept()
                conn.send(welcome_message.encode())
                socket_list.append(conn)
            else:
                #register, login, connect, connectorupdate. the last two disconnect the socket
                data = r_sock.recv(1024)
                if not data:
                    print("Error receving message from Jaeman")
                    continue
                data = data.decode()
                data = data.split()
                if data[0] == "register":
                    #format: register username password
                    sign_up_user(r_sock, data[1], data[2])
                elif data[0] == "login":
                    #format: register username password
                    log_in_user(r_sock, data[1], data[2])
                elif data[0] == "connect":
                    #send connector ip_address port
                    #format
                    socket_list = connect_user(r_sock, socket_list)
                elif data[0] == "connectorupdate":
                    #format: connectorupdate ip_address port
                    socket_list = update_connector(r_sock, data[1], data[2], socket_list)
                else:  
                    print("Error in messsage format")
                    r_sock.send("Error in message format".encode())
        
def sign_up_user(conn, name, password):
    if name in passwords_table:
        conn.send("Username taken!".encode())    
        print("Username taken!\n")
    else:
        passwords_table[name] = password
        conn.send("Sign up successful!".encode())    
        print("Sign up successful!\n")

def log_in_user(conn, name, password):
    if name not in passwords_table:
        conn.send("Username not registered!".encode())    
        print("Username not registered!\n")
    elif password != passwords_table[name]:
        conn.send("The password you entered is wrong!".encode())    
        print("The password you entered is wrong!\n") 
    else:
        conn.send("Log in successful!".encode())    
        print("Log in successful!\n")

def connect_user(r_sock, socket_list):
    #format: connector ip_address port if connector exists. else set
    if connector_ip == "":
        r_sock.send(("setupconnector %s %s" % (connector_ip, connector_port)).encode())
    else:
        r_sock.send(("connector %s %s" % (connector_ip, connector_port)).encode())
        r_sock.close()
        socket_list.remove(r_sock)
    return socket_list

def update_connector(r_sock, new_ip, new_port, socket_list):
    #format: connectorupdate ip_address_port
    global connector_ip, connector_port
    connector_ip = new_ip
    connector_port = new_port
    r_sock.close()
    socket_list.remove(r_sock)
    return socket_list


if __name__ == "__main__":
    sock = start_server()
    run_server(sock)
