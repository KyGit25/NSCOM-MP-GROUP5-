import socket
import struct
import os

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

def send_request(sock, server_ip, filename, mode, opcode, blocksize=None):
    request = struct.pack(f'!H{len(filename) + 1}s{len(mode) + 1}s', opcode, filename.encode(), mode.encode())
    
    if blocksize:
        request += b'blksize\x00' + str(blocksize).encode() + b'\x00'
    
    sock.sendto(request, (server_ip, TFTP_PORT))

def receive_file(sock, filename, server_ip):
    with open(filename, 'wb') as f:
        block_number = 1
        while True:
            try:
                data, addr = sock.recvfrom(4 + BLOCK_SIZE)
                opcode, recv_block_number = struct.unpack('!HH', data[:4])
                
                if opcode == OPCODE_ERROR:
                    error_code = recv_block_number
                    print(f"Error: {ERROR_MESSAGES.get(error_code, 'Unknown error')}")
                    return
                
                if opcode == OPCODE_DATA and recv_block_number == block_number:
                    f.write(data[4:])
                    sock.sendto(struct.pack('!HH', OPCODE_ACK, block_number), addr)
                    block_number += 1
                    if len(data[4:]) < BLOCK_SIZE:
                        break  # Last block received
            except socket.timeout:
                print("Error: Timeout occurred.")
                return

def send_file(sock, filename, server_ip):
    if not os.path.exists(filename):
        print("Error: File not found.")
        return
    
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
                print("Error: Timeout occurred.")
                return
            
            if len(data_block) < BLOCK_SIZE:
                break  # Last block sent

def tftp_client(server_ip, operation, filename):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(5)
    mode = "octet"
    
    try:
        if operation.lower() == "get":
            send_request(sock, server_ip, filename, mode, OPCODE_RRQ)
            receive_file(sock, filename, server_ip)
        elif operation.lower() == "put":
            send_request(sock, server_ip, filename, mode, OPCODE_WRQ)
            send_file(sock, filename, server_ip)
        else:
            print("Invalid operation. Use 'get' or 'put'.")
    finally:
        sock.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="TFTP Client")
    parser.add_argument("server_ip", help="TFTP server IP address")
    parser.add_argument("operation", choices=["get", "put"], help="Operation: 'get' for download, 'put' for upload")
    parser.add_argument("filename", help="Filename to transfer")
    args = parser.parse_args()
    
    tftp_client(args.server_ip, args.operation, args.filename)
