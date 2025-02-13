import socket
import ipaddress
import struct

TFTP_PORT = 69
OPCODE_RRQ = 1  # Read request
OPCODE_WRQ = 2  # Write request
OPCODE_DATA = 3  # Data packet
OPCODE_ACK = 4  # Acknowledgment
OPCODE_ERROR = 5  # Error packet
BLOCK_SIZE = 512

# Error messages for TFTP error codes
ERROR_MESSAGES = {
    0: "Not defined, see error message",
    1: "File not found",
    2: "Access violation",
    3: "Disk full or allocation exceeded",
    4: "Illegal TFTP operation",
    5: "Unknown transfer ID",
    6: "File already exists",
    7: "No such user"
}

def menu(client_socket, server_address):
    mode = "octet"
    loop_flag = True

    while loop_flag is True:
        print("\nEnter 'help' to check commands.")
        user_input = input("> ")

        if user_input == 'help':
            print("'get <filename>' - get a file from the server.")
            print("'put <filename>' - put a file in the server.")
            print("'exit' - disconnect from the connected server.")
        elif user_input == 'exit':
            print(f"Disconnecting from {server_address}:{TFTP_PORT}...")
            loop_flag = False

def create_packet(filename, opcode, mode, blocksize=None):
    request = struct.pack(f'!H{len(filename) + 1}s{len(mode) + 1}s', opcode, filename.encode(), mode.encode())

    # blocksize negotiation
    if blocksize:
        request += b'blksize\x00' + str(blocksize).encode() + b'\x00'

    return request
