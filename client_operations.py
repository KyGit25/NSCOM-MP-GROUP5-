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
    Creates and sends request packets to the server.
    """
    request = struct.pack(f'!H{len(filename) + 1}s{len(mode) + 1}s', opcode, filename.encode(), mode.encode())
    if blocksize:
        request += b'blksize\x00' + str(blocksize).encode() + b'\x00'
    if tsize and opcode == OPCODE_WRQ:
        request += b'tsize\x00' + str(tsize).encode() + b'\x00'
    sock.sendto(request, (server_ip, TFTP_PORT))

def handle_oack(sock, addr, blocksize):
    """
    Handles the OACK packet from the server, negotiating options like blksize and tsize.
    """
    tsize = None
    try:
        data, addr = sock.recvfrom(4 + BLOCK_SIZE)
        opcode = struct.unpack('!H', data[:2])[0]

        # If the response is OACK, parse the options
        if opcode == OPCODE_OACK:
            options = data[2:].split(b'\x00')
            options = [opt.decode() for opt in options if opt]

            # Check for negotiated blocksize and tsize
            for i in range(0, len(options), 2):
                if options[i].lower() == 'blksize':
                    blocksize = int(options[i+1])
                    print(f"Negotiated blocksize: {blocksize}")
                elif options[i].lower() == 'tsize':
                    tsize = int(options[i+1])
                    print(f"File size (tsize): {tsize} bytes")

            # Send ACK for block 0 to confirm OACK
            sock.sendto(struct.pack('!HH', OPCODE_ACK, 0), addr)
        else:
            print("No OACK received. Using default blocksize.")
    except socket.timeout:
        print("Timeout waiting for OACK. Using default blocksize.")

    return blocksize, tsize

def receive_file(sock, filename, server_ip):
    """
    Receives a file from the server to the client.
    """
    block_number = 1
    retries = 0
    temp_filename = filename + ".tmp"
    blocksize = BLOCK_SIZE  # Default blocksize

    # Check for OACK before starting the transfer
    blocksize, tsize = handle_oack(sock, (server_ip, TFTP_PORT), blocksize)

    if tsize:
        print(f"Starting download of {filename} ({tsize} bytes)...")

    try:
        with open(temp_filename, 'wb') as f:
            while True:
                try:
                    data, addr = sock.recvfrom(4 + blocksize)
                    opcode, recv_block_number = struct.unpack('!HH', data[:4])

                    if opcode == OPCODE_ERROR:
                        error_code = recv_block_number
                        print(f"Error: {ERROR_MESSAGES.get(error_code, 'Unknown error')}")
                        f.close()
                        os.remove(temp_filename)
                        return

                    if opcode == OPCODE_DATA and recv_block_number == block_number:
                        f.write(data[4:])
                        sock.sendto(struct.pack('!HH', OPCODE_ACK, block_number), addr)
                        block_number += 1
                        retries = 0
                        if len(data[4:]) < blocksize:
                            break
                except socket.timeout:
                    retries += 1
                    print(f"Warning: Timeout occurred, retrying {retries}/{MAX_RETRIES}...")
                    if retries >= MAX_RETRIES:
                        print("Error: Maximum retries reached, aborting download.")
                        f.close()
                        os.remove(temp_filename)
                        return
                    send_request(sock, server_ip, filename, "octet", OPCODE_RRQ, blocksize)
    except Exception as e:
        print(f"Unexpected error: {e}")
        return

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
    if not os.path.exists(filename):
        print("Error: File not found.")
        return

    # Check for OACK before starting the transfer
    blocksize, filesize = handle_oack(sock, (server_ip, TFTP_PORT), BLOCK_SIZE)

    print(f"Starting upload of {filename} ({filesize} bytes)...")

    with open(filename, 'rb') as f:
        block_number = 0

        while True:
            # Read the next block of data
            data_block = f.read(blocksize)
            block_number += 1

            # Create and send the data packet
            packet = struct.pack('!HH', OPCODE_DATA, block_number) + data_block
            sock.sendto(packet, (server_ip, TFTP_PORT))

            retries = 0
            while True:
                try:
                    # Wait for ACK
                    ack, _ = sock.recvfrom(4 + blocksize)
                    print(f"Received packet: {ack} (Length: {len(ack)}), {block_number}")
                    opcode, ack_block = struct.unpack('!HH', ack[:4])
                    print(f"block: {ack_block}")

                    # Check if ACK is received for the correct block number
                    if opcode == OPCODE_ACK and ack_block == block_number:
                        print(f"ACK received for block {block_number}")
                        break
                    else:
                        print(f"Unexpected packet received, ignoring...")

                except socket.timeout:
                    retries += 1
                    print(f"Warning: Timeout occurred, retrying {retries}/{MAX_RETRIES}...")

                    # Retry sending the same block if timeout occurs
                    if retries >= MAX_RETRIES:
                        print("Error: Maximum retries reached, aborting upload.")
                        f.close()
                        return
                    sock.sendto(packet, (server_ip, TFTP_PORT))

            # If the length of data is less than blocksize, it's the last block
            if len(data_block) < blocksize:
                break

    print("Upload complete!")


def operations_proper(client_socket, server_address):
    loop_flag = True

    while loop_flag:
        inner_loop_flag = True
        filename = ""
        packet = None

        # user will input request type
        print("\nWrite 'exit' to disconnect from the server.")
        request_type = input("Enter request type (RRQ for download, WRQ for upload): ").strip().upper()

        if request_type == "RRQ" or request_type == "WRQ":
            while inner_loop_flag:
                print("\nWrite 'exit' to return to main menu.")
                filename = input("Enter filename: ")

                if filename == 'exit':
                    print("Returning to main menu...")
                    inner_loop_flag = False
                else:
                    # check if file exists only for WRQ (upload)
                    if request_type == "WRQ":
                        if os.path.isfile(filename):
                            # break out of loop is file exists
                            inner_loop_flag = False
                        else:
                            print("Error: File not found locally.")
                            continue
                    else:
                        # allow any filename for RRQ (download)
                        inner_loop_flag = False

            if not filename == 'exit':
                # prompt for blocksize afterwards
                blksize_input = input("Enter blocksize (leave blank to skip): ")
                # turn string input into integer
                blksize = int(blksize_input) if blksize_input.isdigit() else 512

                # determine tsize for uploads
                tsize = None
                if request_type == "WRQ" and os.path.isfile(filename):
                    tsize = os.path.getsize(filename)

                try:
                    # create packet based on request type
                    if request_type == "RRQ":
                        send_request(client_socket, server_address, filename, mode='octet', opcode=OPCODE_RRQ,
                                     blocksize=blksize)
                        receive_file(client_socket, filename, server_address)
                    elif request_type == "WRQ":
                        send_request(client_socket, server_address, filename, mode='octet', opcode=OPCODE_WRQ,
                                     blocksize=blksize, tsize=tsize)
                        send_file(client_socket, filename, server_address)
                    else:
                        print("Unable to reach TFTP server or received an error.")
                except Exception as e:
                    print(f"An error occurred during communication: {e}")

        elif request_type == "EXIT":
            print("Disconnecting from the server...")
            client_socket.close()
            loop_flag = False
        else:
            print("Invalid request type.")