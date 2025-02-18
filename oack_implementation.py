import socket
import struct
import os
import ipaddress

TFTP_PORT = 69
OPCODE_RRQ = 1  # Read request
OPCODE_WRQ = 2  # Write request
OPCODE_DATA = 3  # Data packet
OPCODE_ACK = 4  # Acknowledgment
OPCODE_ERROR = 5  # Error packet
OPCODE_OACK = 6  # Option Acknowledgment
BLOCK_SIZE = 512
MAX_RETRIES = 3  # Maximum number of retries for timeouts

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

def is_valid_ip(ip_address):
    """
    A function used to validate the parameter 'ip_address'
    :param ip_address: the "address" to be validated
    :return: True if the given 'ip_address' is a valid IP address
    """
    try:
        ipaddress.ip_address(ip_address)
        return True
    except ValueError:
        return False

def send_request(sock, server_ip, filename, mode, opcode, blocksize=None, tsize=None):
    """
    A function used to create and send request packets to the server.
    :param sock: the socket of the client.
    :param server_ip: the IP address of the server.
    :param filename: the name of the file to be used in the request.
    :param mode: the mode of data transfer, specified in the request.
    :param opcode: specifies the request to be made.
    :param blocksize: the size of the data blocks used during transfers.
    :param tsize: the size of the file being transferred.
    :return: None
    """

    # Create the request packet
    request = struct.pack(f'!H{len(filename) + 1}s{len(mode) + 1}s', opcode, filename.encode(), mode.encode())

    # Append options if specified
    if blocksize:
        request += b'blksize\x00' + str(blocksize).encode() + b'\x00'
    if tsize is not None:
        request += b'tsize\x00' + str(tsize).encode() + b'\x00'

    # Send the created packet to the server
    sock.sendto(request, (server_ip, TFTP_PORT))

def process_oack(data):
    """
    Processes the Option Acknowledgment (OACK) packet to handle option negotiations.
    :param data: The received OACK data from the server.
    :return: True if OACK was successfully processed, False otherwise.
    """
    global BLOCK_SIZE
    options = data[2:].split(b'\x00')

    for i in range(0, len(options) - 1, 2):
        key = options[i].decode()
        value = options[i + 1].decode()
        if key == "blksize":
            BLOCK_SIZE = min(int(value), 65464)  # Enforce max block size per RFC 2348

    return True

def handle_tftp_error(data):
    """
    Handles received TFTP error packets and prints appropriate error messages.
    :param data: The received error packet.
    :return: None.
    
    Features:
    - Specifically handles "File Not Found" errors.
    - Extracts and displays error codes with corresponding messages.
    """
    error_code = struct.unpack('!H', data[2:4])[0]
    error_msg = data[4:].decode(errors='ignore').strip("\x00")

    if error_code == 1:
        print("Error: The requested file was not found on the server.")
    else:
        print(f"TFTP Error {error_code}: {ERROR_MESSAGES.get(error_code, 'Unknown error')}")
    
    print(f"Server message: {error_msg}")

def receive_file(sock, filename, server_ip):
    """
    This function listens for incoming data packets and processes them.
    :param sock: The socket of the client.
    :param filename: The name of the file to be received.
    :param server_ip: The IP address of the server.
    :return: None. If an error occurs, the function will print an error message and return early.
    """

    global BLOCK_SIZE
    block_number = 1
    retries = 0
    temp_filename = filename + ".tmp"

    try:
        with open(temp_filename, 'wb') as f:
            while True:
                try:
                    data, addr = sock.recvfrom(4 + BLOCK_SIZE)
                    opcode = struct.unpack('!H', data[:2])[0]

                    if opcode == OPCODE_OACK:
                        process_oack(data)
                        sock.sendto(struct.pack('!HH', OPCODE_ACK, 0), addr)
                        continue

                    elif opcode == OPCODE_DATA:
                        recv_block_number = struct.unpack('!H', data[2:4])[0]

                        # Ignore duplicate data blocks
                        if recv_block_number < block_number:
                            print(f"Warning: Duplicate block {recv_block_number} received, ignoring...")
                            continue

                        if recv_block_number == block_number:
                            f.write(data[4:])
                            sock.sendto(struct.pack('!HH', OPCODE_ACK, block_number), addr)
                            block_number += 1
                            retries = 0

                            # Correctly handle the final data block
                            if len(data[4:]) < BLOCK_SIZE:
                                print("Final block received, closing file.")
                                break

                except socket.timeout:
                    retries += 1
                    print(f"Warning: Timeout occurred, retrying {retries}/{MAX_RETRIES}...")
                    if retries >= MAX_RETRIES:
                        print("Error: Maximum retries reached, aborting download.")
                        os.remove(temp_filename)
                        return
                    send_request(sock, server_ip, filename, "octet", OPCODE_RRQ, BLOCK_SIZE)

    except Exception as e:
        print(f"Unexpected error: {e}")
        return

    os.rename(temp_filename, filename)
    print("Download complete!")

def send_file(sock, filename, server_ip):
    """
    A function that handles the proper sending of a file from the client to the server.
    :param sock: The socket of the client.
    :param filename: The name of the file to be sent.
    :param server_ip: The IP address of the server.
    :return: None. If an error occurs during the file transfer, the function will print an 
             error message and return early.
    """

    global BLOCK_SIZE

    if not os.path.exists(filename):
        print("Error: File not found.")
        return

    filesize = os.path.getsize(filename)
    
    # Send write request (WRQ) with block size and file size
    send_request(sock, server_ip, filename, "octet", OPCODE_WRQ, BLOCK_SIZE, filesize)

    try:
        # Wait for response (ACK or OACK)
        response, addr = sock.recvfrom(4 + BLOCK_SIZE)
        opcode = struct.unpack('!H', response[:2])[0]

        if opcode == OPCODE_OACK:
            process_oack(response)
            sock.sendto(struct.pack('!HH', OPCODE_ACK, 0), addr)
        elif opcode == OPCODE_ACK:
            _, ack_block = struct.unpack('!HH', response)
            if ack_block != 0:
                print("Unexpected ACK block number.")
                return
        else:
            print("Error: Unexpected response from server.")
            return

    except socket.timeout:
        print("Error: No response from server after WRQ.")
        return

    with open(filename, 'rb') as f:
        block_number = 1
        retries = 0

        while True:
            data_block = f.read(BLOCK_SIZE)
            packet = struct.pack('!HH', OPCODE_DATA, block_number) + data_block
            sock.sendto(packet, (server_ip, TFTP_PORT))

            try:
                # Wait for ACK for the sent data block
                ack, _ = sock.recvfrom(4)
                _, ack_block = struct.unpack('!HH', ack)

                if ack_block != block_number:
                    print(f"Warning: Unexpected ACK {ack_block}, expected {block_number}. Retrying...")
                    retries += 1
                    if retries >= MAX_RETRIES:
                        print("Error: Maximum retries reached. Upload aborted.")
                        return
                    continue  # Retransmit the block

                retries = 0  # Reset retry counter
            except socket.timeout:
                print(f"Warning: Timeout while waiting for ACK for block {block_number}. Retrying...")
                retries += 1
                if retries >= MAX_RETRIES:
                    print("Error: Maximum retries reached. Upload aborted.")
                    return
                continue  # Retransmit the block

            if len(data_block) < BLOCK_SIZE:
                if len(data_block) == BLOCK_SIZE:
                    sock.sendto(struct.pack('!HH', OPCODE_DATA, block_number + 1), (server_ip, TFTP_PORT))
                break

            block_number += 1

    print("Upload complete!")

def tftp_client(server_ip, operation, local_filename, remote_filename):
    """
    The main function of the program. This function is responsible for using all other functions in the file.
    :param server_ip: the IP address of the server.
    :param operation: the operation the client will make.
    :param local_filename: the name of the file to be used from the client.
    :param remote_filename: the name of the file to be used from the server.
    :return:
    """

    # create the socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # set the socket's timeout
    sock.settimeout(5)
    # set the mode of data transfer to 'octet'
    mode = "octet"

    # try running the operation
    try:
        # if operation is 'get'
        if operation.lower() == "get":
            # run the send_request(), then try to receive file
            send_request(sock, server_ip, remote_filename, mode, OPCODE_RRQ, BLOCK_SIZE)
            receive_file(sock, local_filename, server_ip)
        elif operation.lower() == "put":
            # run the send_request(), then try to send file
            send_request(sock, server_ip, remote_filename, mode, OPCODE_WRQ, BLOCK_SIZE)
            send_file(sock, local_filename, server_ip)
    except Exception as e:
        print(f"An error occurred while receiving file: {e}")
    # close the socket after the operation
    finally:
        sock.close()

if __name__ == "__main__":
    # declare as empty strings
    local_filename = ""
    remote_filename = ""

    # loop for invalid inputs
    while True:
        print("Enter 'exit' to exit the program.")
        server_ip = input("Enter TFTP server IP address: ")

        # check if user input is a valid ip address
        if is_valid_ip(server_ip):
            # continue with the program, connect to server if it is valid
            print(f"Connecting to TFTP server at {server_ip}:{TFTP_PORT}...\n")
            # loop for invalid operation input
            while True:
                operation = input("Enter operation (get/put): ").strip().lower()

                # check if valid input
                if operation in ['get', 'put']:
                    # loop for invalid inputs
                    while True:
                        # get necessary filenames
                        if operation == 'get':
                            print("\nEnter 'exit' to return.")
                            remote_filename = input("Enter filename to get from the server: ")

                            # break out of loop if 'exit' is entered
                            if remote_filename.lower() == 'exit':
                                print("\nReturning...")
                                break

                            print("\nEnter 'exit' to return.")
                            local_filename = input("Enter filename to use locally: ")

                            # break out of loop if 'exit' is entered
                            if local_filename.lower() == 'exit':
                                print("\nReturning...")
                                break

                        elif operation == 'put':
                            print("\nEnter 'exit' to return.")
                            local_filename = input("Enter filename to get locally: ")

                            # break out of loop if 'exit' is entered
                            if local_filename.lower() == 'exit':
                                print("\nReturning...")
                                break

                            print("\nEnter 'exit' to return.")
                            remote_filename = input("Enter filename to use on the server: ")
                            
                            # break out of loop if 'exit' is entered
                            if remote_filename.lower() == 'exit':
                                print("\nReturning...")
                                break

                        if not local_filename or not remote_filename:
                            print("\nError: Invalid filename!")
                        # run main program if correct inputs
                        else:
                            # run the main program
                            tftp_client(server_ip, operation, local_filename, remote_filename)
                # error message for invalid operation input
                else:
                    print("Error: Invalid operation!")
                    continue
        # close the program if 'exit' is entered
        elif server_ip.lower() == 'exit':
            print("\nExiting program...")
            break
        # error message for invalid ip address input
        else:
            print("\nError: Invalid IP address!")
            continue
