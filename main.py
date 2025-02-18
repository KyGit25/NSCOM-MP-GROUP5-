import socket
import ipaddress
import client_operations

#  default port
TFTP_PORT = 69
BUFFER_SIZE = 516

def is_valid_ip(ip_address):
    try:
        ipaddress.ip_address(ip_address)
        return True
    except ValueError:
        return False

def validate_input(user_input):
    if is_valid_ip(user_input):
        return user_input
    elif user_input == 'exit':
        return user_input
    else:
        return None

def connect_to_server(server_ip):
    # create socket
    # AF_INET = used to communicate with IPv4 addresses
    # SOCK_DGRAM = datagrams, used for UDP
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.settimeout(10)  # timeout after 10 seconds

    print(f"Connecting to TFTP server at {server_ip}:{TFTP_PORT}...")
    return client_socket

if __name__ == "__main__":
    print("TFTP Client Application")
    loop_flag = True

    while loop_flag is True:
        print("\nWrite 'exit' to close the program.")
        user_input = input("Enter TFTP server IP address: ")
        user_input = validate_input(user_input)

        if user_input == 'exit':
            print("Exiting TFTP Client Application...")
            loop_flag = False
        elif user_input is not None:
            client_socket = connect_to_server(user_input)
            client_operations.operations_proper(client_socket, user_input)
        else:
            print("Incorrect IP address format! Try again!\n")
            loop_flag = True