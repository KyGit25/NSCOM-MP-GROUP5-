import socket
import struct
import os
import sys

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

def send_request(sock, server_ip, filename, mode, opcode, blocksize=None, tsize=None):
    request = struct.pack(f'!H{len(filename) + 1}s{len(mode) + 1}s', opcode, filename.encode(), mode.encode())
    
    if blocksize:
        request += b'blksize\x00' + str(blocksize).encode() + b'\x00'
    if tsize and opcode == OPCODE_WRQ:
        request += b'tsize\x00' + str(tsize).encode() + b'\x00'
    
    sock.sendto(request, (server_ip, TFTP_PORT))

def receive_file(sock, filename, server_ip):
    block_number = 1
    retries = 0
    temp_filename = filename + ".tmp"
    
    try:
        with open(temp_filename, 'wb') as f:
            while True:
                try:
                    data, addr = sock.recvfrom(4 + BLOCK_SIZE)
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
                        retries = 0  # Reset retries on success
                        if len(data[4:]) < BLOCK_SIZE:
                            break  # Last block received
                except socket.timeout:
                    retries += 1
                    print(f"Warning: Timeout occurred, retrying {retries}/{MAX_RETRIES}...")
                    if retries >= MAX_RETRIES:
                        print("Error: Maximum retries reached, aborting download.")
                        f.close()
                        os.remove(temp_filename)
                        return
                    send_request(sock, server_ip, filename, "octet", OPCODE_RRQ, BLOCK_SIZE)
    except Exception as e:
        print(f"Unexpected error: {e}")
        return
    os.rename(temp_filename, filename)
    print("Download complete!")

def send_file(sock, filename, server_ip):
    if not os.path.exists(filename):
        print("Error: File not found.")
        return
    
    filesize = os.path.getsize(filename)
    send_request(sock, server_ip, filename, "octet", OPCODE_WRQ, BLOCK_SIZE, filesize)
    
    with open(filename, 'rb') as f:
        block_number = 0
        while True:
            data_block = f.read(BLOCK_SIZE)
            block_number += 1
            packet = struct.pack('!HH', OPCODE_DATA, block_number) + data_block
            sock.sendto(packet, (server_ip, TFTP_PORT))
            
            try:
                ack, _ = sock.recvfrom(4)
                _, ack_block = struct.unpack('!HH', ack)
                if ack_block != block_number:
                    print("Error: Duplicate ACK received, retrying...")
                    continue
            except socket.timeout:
                print("Error: Timeout occurred while sending file.")
                return
            
            if len(data_block) < BLOCK_SIZE:
                break  # Last block sent
    print("Upload complete!")

def tftp_client(server_ip, operation, local_filename, remote_filename):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(5)
    mode = "octet"
    
    try:
        if operation.lower() == "get":
            send_request(sock, server_ip, remote_filename, mode, OPCODE_RRQ, BLOCK_SIZE)
            receive_file(sock, local_filename, server_ip)
        elif operation.lower() == "put":
            send_request(sock, server_ip, remote_filename, mode, OPCODE_WRQ, BLOCK_SIZE)
            send_file(sock, local_filename, server_ip)
        else:
            print("Invalid operation. Use 'get' or 'put'.")
    finally:
        sock.close()

if __name__ == "__main__":
    server_ip = input("Enter TFTP server IP address: ")
    operation = input("Enter operation (get/put): ")
    local_filename = input("Enter local filename: ")
    remote_filename = input("Enter filename to use on the server: ")
    
    if not server_ip or operation not in ["get", "put"] or not local_filename or not remote_filename:
        print("Error: Invalid input. Please provide valid details.")
        sys.exit(1)
    
    tftp_client(server_ip, operation, local_filename, remote_filename)
