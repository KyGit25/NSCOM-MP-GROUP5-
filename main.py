import socket
import ipaddress
import client_operations

#  default port
TFTP_PORT = 69
BUFFER_SIZE = 516

def is_valid_ip(ip_address):
    """
     A function used to validate the parameter 'ip_address'
     :param ip_address: the "address" to be validated
     :return: True if the given 'ip_address' is a valid IP address
     """
    try:
        # check if the given ip_address is a correct IP address
        ipaddress.ip_address(ip_address)
        return True
    except ValueError:
        # if there is an exception (address is not an IP address)
        return False

def validate_input(user_input):
    """
    A function used to validate a user's input
    :param user_input: The input of the user.
    :return: The user_input if it is correct, else None
    """
    if is_valid_ip(user_input):
        return user_input
    elif user_input == 'exit':
        return user_input
    else:
        return None

def connect_to_server(server_ip):
    """
    A function used to connect to the server and set the timeout counter.
    :param server_ip: the server IP address to be used
    :return: the socket of the client that is connected to the server
    """
    # create socket
    # AF_INET = used to communicate with IPv4 addresses
    # SOCK_DGRAM = datagrams, used for UDP
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.settimeout(10)  # timeout after 10 seconds

    print(f"Connecting to TFTP server at {server_ip}:{TFTP_PORT}...")
    return client_socket

if __name__ == "__main__":
    print("TFTP Client Application")

    # loop for validating IP address input
    while True:
        # get user inputs
        print("\nWrite 'exit' to close the program.")
        user_input = input("Enter TFTP server IP address: ")
        user_input = validate_input(user_input)

        # if user inputs 'exit', exit the program.
        if user_input == 'exit':
            print("Exiting TFTP Client Application...")
            break
        # else if the input is valid and not 'exit', connect to server and start the main menu.
        elif user_input is not None:
            client_socket = connect_to_server(user_input)
            client_operations.operations_proper(client_socket, user_input)
        # print an error message if input is invalid
        else:
            print("Incorrect IP address format! Try again!\n")
            continue