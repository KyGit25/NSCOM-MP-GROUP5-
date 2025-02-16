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
    A function used for the proper receiving of file from server to client.
    :param sock: the socket of the client.
    :param filename: the name of the file to be received.
    :param server_ip: the IP address of the server.
    :return: returns whenever there is an error in the data transfer.
    """

    # variable declarations
    block_number = 1
    retries = 0
    temp_filename = filename + ".tmp"

    try:
        # create the file, open as binary write mode
        with open(temp_filename, 'wb') as f:
            # loop to listen continuously for packets of 4 + BLOCK_SIZE bytes
            while True:
                try:
                    data, addr = sock.recvfrom(4 + BLOCK_SIZE)
                    opcode, recv_block_number = struct.unpack('!HH', data[:4])

                    # if packet is error packet
                    if opcode == OPCODE_ERROR:
                        # print the error message
                        error_code = recv_block_number
                        print(f"Error: {ERROR_MESSAGES.get(error_code, 'Unknown error')}")
                        # close and delete the file
                        f.close()
                        os.remove(temp_filename)
                        # exit the function
                        return

                    # if packet is data packet
                    if opcode == OPCODE_DATA and recv_block_number == block_number:
                        # write the data, excluding the 4 byte header
                        f.write(data[4:])
                        # send an ACK packet to the server with the same block_number
                        sock.sendto(struct.pack('!HH', OPCODE_ACK, block_number), addr)
                        # increment the block_number for the next block
                        block_number += 1
                        # reset retries on success
                        retries = 0
                        # if the length of data is less than BLOCK_SIZE, it signifies the last block
                        if len(data[4:]) < BLOCK_SIZE:
                            # break out of the loop when that happens
                            break
                # timeout handling
                except socket.timeout:
                    # increments the retries counter as program retries the request
                    retries += 1
                    print(f"Warning: Timeout occurred, retrying {retries}/{MAX_RETRIES}...")
                    # if retries have reached max retries possible
                    if retries >= MAX_RETRIES:
                        # cancel the file download, exit the program
                        print("Error: Maximum retries reached, aborting download.")
                        f.close()
                        os.remove(temp_filename)
                        return
                    # retry the request
                    send_request(sock, server_ip, filename, "octet", OPCODE_RRQ, BLOCK_SIZE)
    # error handling
    except Exception as e:
        print(f"Unexpected error: {e}")
        return

    # if file download is successful, rename the file back to the original file
    os.rename(temp_filename, filename)
    print("Download complete!")

def send_file(sock, filename, server_ip):
    """
    A function used for the proper sending of file from client to server.
    :param sock: the socket of the client.
    :param filename: the name of the file to be sent.
    :param server_ip: the IP address of the server.
    :return: return whenever there is an error in the data transfer.
    """

    # check if file exists, return if it does not exist
    if not os.path.exists(filename):
        print("Error: File not found.")
        return

    # get the tsize of the file
    filesize = os.path.getsize(filename)

    # send the request to the server with indication of the tsize
    send_request(sock, server_ip, filename, "octet", OPCODE_WRQ, BLOCK_SIZE, filesize)

    # create the file, open as read binary mode
    with open(filename, 'rb') as f:
        # declare the block_number
        block_number = 0

        # loop to keep on reading until end of file reached
        while True:
            # read data of BLOCK_SIZE bytes
            data_block = f.read(BLOCK_SIZE)
            # increment block_number to read next data block
            block_number += 1
            # create data packet containing the data block
            packet = struct.pack('!HH', OPCODE_DATA, block_number) + data_block
            # send the data packet to the server
            sock.sendto(packet, (server_ip, TFTP_PORT))

            # after each block sent, try to receive an ACK from the server
            try:
                # receive the ACK
                ack, _ = sock.recvfrom(4)
                _, ack_block = struct.unpack('!HH', ack)
                # if the ack_block is not the same as the current block_number,
                # it signifies duplicate ACK received
                if ack_block != block_number:
                    print("Error: Duplicate ACK received, retrying...")
                    # retry if that happens, loop again
                    continue
            # timeout handling
            except socket.timeout:
                # print an error when a timeout happens
                print("Error: Timeout occurred while sending file.")
                # exit the function
                return

            # if the length of data is less than BLOCK_SIZE, it signifies the last block
            if len(data_block) < BLOCK_SIZE:
                # break out of the loop when that happens
                break
    # print a message whenever the upload is complete
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
