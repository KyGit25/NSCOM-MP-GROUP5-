import socket
import struct
import os
import sys
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
        # check if the given ip_address is a correct IP address
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
    :return:
    """

    # create the request packet
    request = struct.pack(f'!H{len(filename) + 1}s{len(mode) + 1}s', opcode, filename.encode(), mode.encode())

    # modify the packet if blocksize and/or tsize is specified
    if blocksize:
        request += b'blksize\x00' + str(blocksize).encode() + b'\x00'
    if tsize and opcode == OPCODE_WRQ:
        request += b'tsize\x00' + str(tsize).encode() + b'\x00'

    # send the created packet to the server
    sock.sendto(request, (server_ip, TFTP_PORT))

def receive_file(sock, filename, server_ip):
    """
    This function listens for incoming data packets and processes them.
    :param sock: The socket of the client.
    :param filename: The name of the file to be received.
    :param server_ip: The IP address of the server.
    :return: None. If an error occurs, the function will print an error message and return early.
    """
    
    global BLOCK_SIZE  # Update block size if negotiated
    block_number = 1
    retries = 0
    temp_filename = filename + ".tmp"

    try:
        # Open a temporary file to store the incoming data
        with open(temp_filename, 'wb') as f:
            while True:
                try:
                    # Receive a packet from the server
                    data, addr = sock.recvfrom(4 + BLOCK_SIZE)
                    opcode = struct.unpack('!H', data[:2])[0]

                    if opcode == OPCODE_OACK:
                        # Process OACK packet to handle option negotiations
                        options = data[2:].split(b'\x00')
                        for i in range(0, len(options) - 1, 2):
                            key = options[i].decode()
                            value = options[i + 1].decode()
                            if key == "blksize":
                                BLOCK_SIZE = int(value)

                        # Acknowledge the OACK and proceed to receive data
                        sock.sendto(struct.pack('!HH', OPCODE_ACK, 0), addr)
                        continue  # Continue to receive actual data packets

                    elif opcode == OPCODE_DATA:
                        # Handle received data block
                        recv_block_number = struct.unpack('!H', data[2:4])[0]
                        if recv_block_number == block_number:
                            f.write(data[4:])  # Write data excluding the header
                            sock.sendto(struct.pack('!HH', OPCODE_ACK, block_number), addr)
                            block_number += 1
                            retries = 0
                            if len(data[4:]) < BLOCK_SIZE:
                                break  # End download if data length is less than BLOCK_SIZE

                except socket.timeout:
                    # Handle timeout errors by retrying the request
                    retries += 1
                    print(f"Warning: Timeout occurred, retrying {retries}/{MAX_RETRIES}...")
                    if retries >= MAX_RETRIES:
                        # Abort download if maximum retries are reached
                        print("Error: Maximum retries reached, aborting download.")
                        f.close()
                        os.remove(temp_filename)
                        return
                    send_request(sock, server_ip, filename, "octet", OPCODE_RRQ, BLOCK_SIZE)

    except Exception as e:
        # Handle any other unexpected errors
        print(f"Unexpected error: {e}")
        return

    # Rename the temporary file to the desired filename after successful download
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

    # Check if the file exists; if not, return an error
    if not os.path.exists(filename):
        print("Error: File not found.")
        return

    # Get the size of the file
    filesize = os.path.getsize(filename)

    # Send the write request (WRQ) to the server with block size and file size options
    send_request(sock, server_ip, filename, "octet", OPCODE_WRQ, BLOCK_SIZE, filesize)

    # Open the file in binary read mode
    with open(filename, 'rb') as f:
        block_number = 0

        # Continuously read and send blocks of the file until it's completely sent
        while True:
            # Read the next block of data (BLOCK_SIZE bytes)
            data_block = f.read(BLOCK_SIZE)
            block_number += 1
            # Create a data packet with the current block number and the data
            packet = struct.pack('!HH', OPCODE_DATA, block_number) + data_block
            # Send the data packet to the server
            sock.sendto(packet, (server_ip, TFTP_PORT))

            try:
                # Wait for an ACK from the server
                ack, _ = sock.recvfrom(4)
                _, ack_block = struct.unpack('!HH', ack)

                # If the ACK block number is not equal to the current block number,
                # it indicates a duplicate ACK, so we retry sending the block
                if ack_block != block_number:
                    print("Error: Duplicate ACK received, retrying...")
                    continue

            except socket.timeout:
                # Handle timeout error if the ACK is not received in time
                print("Error: Timeout occurred while sending file.")
                return

            # If the length of data block is less than BLOCK_SIZE, it signifies the last block
            if len(data_block) < BLOCK_SIZE:
                break  # Exit the loop as the file transfer is complete

    # Print success message upon completion of the upload
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
