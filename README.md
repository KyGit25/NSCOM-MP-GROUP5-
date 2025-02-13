# NSCOM-MP-GROUP5

# TFTP Client

## Description
This project is a TFTP (Trivial File Transfer Protocol) client implemented in Python. It allows users to upload and download binary files from a TFTP server using UDP, following TFTP v2 (RFC 1350) and extensions from RFCs 2347, 2348, and 2349.

## Features
- **Upload (`put`) and Download (`get`) support**
- **Customizable block size (blksize) negotiation**
- **Transfer size communication (tsize) for uploads**
- **Timeout handling with retries (max 3 attempts)**
- **Duplicate ACK handling**
- **File sequencing to ensure correct transfer**
- **Handles TFTP error messages properly**

## Requirements
- Python 3.x
- A running TFTP server (e.g., `tftpd-hpa` on Linux, `PumpKIN` on Windows/macOS)

## Installation
1. Clone or download the project repository.
2. Ensure Python 3 is installed on your system.
3. Navigate to the project directory.

## Usage
### Running the TFTP Client

Run the following command:
python tftp_client.py

The script will prompt for the required information:
Enter TFTP server IP address: 192.168.1.1
Enter operation (get/put): get
Enter local filename: example.txt
Enter filename to use on the server: example_server.txt

### Example Usage
#### Download a File from the Server

Run the following command:
python tftp_client.py

The script will prompt for the required information:
Enter TFTP server IP address: 192.168.1.1
Enter operation (get/put): get
Enter local filename: download.txt
Enter filename to use on the server: example.txt

#### Upload a File to the Server
```bash
python tftp_client.py
```
```
Enter TFTP server IP address: 192.168.1.1
Enter operation (get/put): put
Enter local filename: upload.txt
Enter filename to use on the server: example_server.txt
```

## Testing the Client
To test the client, you can use a local TFTP server like `tftpd-hpa` (Linux) or `PumpKIN` (Windows/macOS):

### Setting Up a TFTP Server (Linux)
sudo apt install tftpd-hpa
sudo systemctl start tftpd-hpa


## Error Handling
The client gracefully handles:
- **Timeouts** (retries up to 3 times before aborting)
- **File not found errors**
- **Duplicate ACKs**
- **Illegal TFTP operations**

## Deliverables
- **Source Code**: Full implementation of the TFTP client.
- **Documentation**: Includes a README with setup instructions and test cases.


