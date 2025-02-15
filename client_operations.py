import socket
import struct
import os

TFTP_PORT = 69
OPCODE_RRQ = 1  # Read request
OPCODE_WRQ = 2  # Write request
OPCODE_DATA = 3  # Data packet
OPCODE_ACK = 4  # Acknowledgment
OPCODE_ERROR = 5  # Error packet
BUFFER_SIZE = 512
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

def create_packet(filename, opcode, mode, blksize=None, tsize=None):
    '''
    The function is used for creation of request packets to be sent to the server.
    :param filename: the filename to be used in the request.
    :param opcode: the opcode of the request (1 for RRQ, 2 for WRQ)
    :param mode:
    :param blksize: the block size to be used
    :return:
    '''
    request = struct.pack(f'!H{len(filename) + 1}s{len(mode) + 1}s', opcode, filename.encode(), mode.encode())

    # block size negotiation
    if blksize:
        request += b'blksize\x00' + str(blksize).encode() + b'\x00'
    if tsize:
        request += b'tsize\x00' + str(tsize).encode() + b'\x00'

    return request

def send_packet(client_socket, server_address, packet):
    '''
    a function used to send packets from the client to the server.
    :param client_socket: the socket of the device of the client.
    :param server_address: the IP address of the server.
    :param packet: the packet to be sent to the server.
    :return: a boolean value that returns true if sending is successful. False otherwise.
    '''
    retries = 0

    while retries < MAX_RETRIES:
        try:
            # send the packet to the server
            client_socket.sendto(packet, (server_address, TFTP_PORT))
            # get response from server
            response, _ = client_socket.recvfrom(BUFFER_SIZE)
            print("Server Response:", response)

            # Check for OACK (Option Acknowledgment)
            if response[:2] == b'\x00\x06':  # OACK Opcode = 6
                print("Option Acknowledgment (OACK) received.")
                print("OACK Data:", response[2:])
                return True
            elif response[:2] == b'\x00\x05':  # Error Opcode = 5
                error_code = struct.unpack('!H', response[2:4])[0]
                error_msg = response[4:-1].decode()
                print(f"TFTP Error {error_code}: {error_msg}")
                if error_code == 1:  # File Not Found
                    print("File not found on the server.")
                return False
            else:
                print("Unexpected server response.")
                return False

        except socket.timeout:
            retries += 1
            print(f"Timeout! No response from the server. Retrying... ({retries}/{MAX_RETRIES})")

        except Exception as e:
            print(f"Error: {e}")
            return False

        finally:
            client_socket.close()

    print(f"Max retries ({retries}/{MAX_RETRIES}) has been reached. Server is unresponsive.")
    return False

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
                blksize = int(blksize_input) if blksize_input.isdigit() else None

                # determine tsize for uploads
                tsize = None
                if request_type == "WRQ" and os.path.isfile(filename):
                    tsize = os.path.getsize(filename)

                # create packet based on request type
                if request_type == "RRQ":
                    packet = create_packet(filename, opcode=OPCODE_RRQ, mode='octet', blksize=blksize, tsize=tsize)
                elif request_type == "WRQ":
                    packet = create_packet(filename, opcode=OPCODE_WRQ, mode='octet', blksize=blksize, tsize=tsize)

                # try sending the packet
                try:
                    if send_packet(client_socket, server_address, packet):
                        print("Gumana.")
                    else:
                        print("Unable to reach TFTP server or received an error.")
                except Exception as e:
                    print(f"An error occurred during communication: {e}")

        elif request_type == "EXIT":
            print("Disconnecting from the server...")
            loop_flag = False
        else:
            print("Invalid request type.")
