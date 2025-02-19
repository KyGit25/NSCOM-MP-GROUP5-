import socket
import struct
import os

TFTP_PORT = 69
OPCODE_RRQ = 1  # Read request
OPCODE_WRQ = 2  # Write request
OPCODE_DATA = 3  # Data packet
OPCODE_ACK = 4  # Acknowledgment
OPCODE_ERROR = 5  # Error packet
OPCODE_OACK = 6
BLOCK_SIZE = 512
MAX_RETRIES = 5

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

def handle_oack(sock, addr, blocksize):
    """
    Handles the OACK packet from the server, negotiating options like blksize and tsize.
    :param sock: The socket of the client.
    :param blocksize: the blocksize of the data transfer to be used.
    :return: The negotiated blocksize and tsize. Returns the default value if there is no OACK.
    """

    # initialize tsize to None as this is the default value
    tsize = None

    # try block for socket timeouts
    try:
        # get the server's response and unpack
        data, addr = sock.recvfrom(4 + BLOCK_SIZE)
        opcode = struct.unpack('!H', data[:2])[0]

        # if the response is OACK, parse the options
        if opcode == OPCODE_OACK:
            # take out the null byte strings
            options = data[2:].split(b'\x00')
            # decode each options, put them into a list
            options = [opt.decode() for opt in options if opt]

            # check the list for the negotiated options
            for i in range(0, len(options), 2):
                # if 'blksize' is included in the OACK
                if options[i].lower() == 'blksize':
                    # extract the blocksize
                    blocksize = int(options[i+1])
                    print(f"Negotiated blocksize: {blocksize}")
                # if 'tsize' is included in the OACK
                elif options[i].lower() == 'tsize':
                    # extract the tsize
                    tsize = int(options[i+1])
                    print(f"File size (tsize): {tsize} bytes")

            # send ACK for block 0 to confirm OACK
            sock.sendto(struct.pack('!HH', OPCODE_ACK, 0), addr)
        # if there are no OACK received, use default values.
        else:
            print("No OACK received. Using default values.")
    # if timeout happens before the reply, use default values.
    except socket.timeout:
        print("Timeout waiting for OACK. Using default values.")

    # return the blocksize and tsize values whether negotiation was successful or not
    return blocksize, tsize

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
    blocksize = BLOCK_SIZE  # default blocksize

    # check for OACK before starting the transfer
    blocksize, tsize = handle_oack(sock, (server_ip, TFTP_PORT), blocksize)

    # if for some reason tsize is included, then print a message including tsize
    if tsize:
        print(f"Starting download of {filename} ({tsize} bytes)...")
    else:
        print(f"Starting download of {filename}...")

    # try block for unexpected errors
    try:
        # create the file, open as binary write mode
        with open(temp_filename, 'wb') as f:
            # loop to listen continuously for packets of 4 + BLOCK_SIZE bytes
            while True:
                # try block for timeouts
                try:
                    # try to receive packets from server and unpack
                    data, addr = sock.recvfrom(4 + blocksize)
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
                        if len(data[4:]) < blocksize:
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
                    send_request(sock, server_ip, filename, "octet", OPCODE_RRQ, blocksize)
    # error handling
    except Exception as e:
        print(f"Unexpected error: {e}")
        return

    # if file download is successful, rename the file back to the original file
    os.rename(temp_filename, filename)
    print("Download complete!")


def send_file(sock, filename, server_ip):
    """
    Sends a file from the client to the server.
    :param sock: the socket of the client.
    :param filename: the name of the file to be sent.
    :param server_ip: the IP address of the server.
    :return: return whenever there is an error in the data transfer.
    """

    # exit the function if the file does not exist
    if not os.path.exists(filename):
        print("Error: File not found.")
        return

    # check for OACK before starting the transfer
    blocksize, filesize = handle_oack(sock, (server_ip, TFTP_PORT), BLOCK_SIZE)

    # start the upload
    print(f"Starting upload of {filename} ({filesize} bytes)...")

    # create the file, open as read binary mode
    with open(filename, 'rb') as f:
        # declare the block_number
        block_number = 0

        # loop to keep on reading until end of file reached
        while True:
            # read the next block of data of file to be sent
            data_block = f.read(blocksize)
            # increment the block number for next data block
            block_number += 1

            # create and send the data packet
            packet = struct.pack('!HH', OPCODE_DATA, block_number) + data_block
            sock.sendto(packet, (server_ip, TFTP_PORT))

            # set retries to 0 for a succesful attempt
            retries = 0
            while True:
                try:
                    # wait for ACK
                    ack, _ = sock.recvfrom(blocksize + 4)

                    # check if it's an error packet
                    if ack[1] == OPCODE_ERROR:
                        # unpack the error and print
                        error_code, = struct.unpack('!H', ack[2:4])
                        print(f"Error: {ERROR_MESSAGES.get(error_code, 'Unknown error')}")
                    # else, if it is an ACK block
                    else:
                        # unpack the data block
                        opcode, ack_block = struct.unpack('!HH', ack)
                        # check if ACK is received for the correct block number
                        if opcode == OPCODE_ACK and ack_block == block_number:
                            print(f"ACK received for block {block_number}")
                            break
                        # else if it is an incorrect block (not the same block numbers on both sides), retry
                        else:
                            print(f"Unexpected packet received, ignoring...")
                # timeout handling
                except socket.timeout:
                    # increments the retries counter as program retries the request
                    retries += 1
                    print(f"Warning: Timeout occurred, retrying {retries}/{MAX_RETRIES}...")

                    # if retries have reached max retries possible
                    if retries >= MAX_RETRIES:
                        # cancel the file upload, exit the program
                        print("Error: Maximum retries reached, aborting upload.")
                        f.close()
                        return
                    # retry sending the packet of data
                    sock.sendto(packet, (server_ip, TFTP_PORT))

            # if the length of data is less than BLOCK_SIZE, it signifies the last block
            if len(data_block) < blocksize:
                # break out of the loop when that happens
                break

    # print a message whenever the upload is complete
    print("Upload complete!")


def operations_proper(client_socket, server_address):
    """
    The main function of the program. This function is responsible for using all other functions in the file.
    :param client_socket: The socket of the client.
    :param server_address: The IP address of the server.
    """
    # loop for parsing operation inputs
    while True:
        # user will input operation
        print("\nWrite 'exit' to disconnect from the server.")
        request_type = input("Enter operation (RRQ for download, WRQ for upload): ").strip().upper()

        # if input is correct
        if request_type == "RRQ" or request_type == "WRQ":
            # loop for parsing filename inputs
            while True:
                # get filename input
                print("\nWrite 'exit' to return to main menu.")
                filename = input("Enter filename: ")

                # if input is 'exit', break out of loop
                if filename == 'exit':
                    print("Returning to main menu...")
                    break
                else:
                    # check if file exists only for WRQ (upload)
                    if request_type == "WRQ":
                        if os.path.isfile(filename):
                            # break out of loop if file exists
                            break
                        else:
                            # print error message if file does not exist
                            print("Error: File not found locally.")
                            continue
                    # break loop if request is RRQ
                    else:
                        break

            if filename != 'exit':
                # prompt for blocksize afterwards
                blksize_input = input("Enter blocksize (leave blank to skip): ")
                # turn string input into integer
                blksize = int(blksize_input) if blksize_input.isdigit() else 512

                # determine tsize for uploads
                tsize = None
                if request_type == "WRQ" and os.path.isfile(filename):
                    tsize = os.path.getsize(filename)

                try:
                    # create and send packet based on request type
                    if request_type == "RRQ":
                        send_request(client_socket, server_address, filename, mode='octet', opcode=OPCODE_RRQ,
                                    blocksize=blksize)
                        receive_file(client_socket, filename, server_address)
                    elif request_type == "WRQ":
                        send_request(client_socket, server_address, filename, mode='octet', opcode=OPCODE_WRQ,
                                    blocksize=blksize, tsize=tsize)
                        send_file(client_socket, filename, server_address)
                    else:
                        # error handling if unexpected issue comes up
                        print("Unable to reach TFTP server or received an error.")
                # error handling if unexpected issue comes up
                except Exception as e:
                    print(f"An error occurred during communication: {e}")
        # check if input for operation is 'exit', then disconnect from server
        elif request_type == "EXIT":
            print("Disconnecting from the server...")
            client_socket.close()
            break
        # if an unexpected input is entered, loop again
        else:
            print("Invalid request type.")
            continue