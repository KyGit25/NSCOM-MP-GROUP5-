# NSCOM-MP-GROUP5

# TFTP Client

## Description
This project is a **TFTP (Trivial File Transfer Protocol) client** implemented in Python. It allows users to **upload (`put`) and download (`get`) binary files** from a **TFTP server** using UDP, following **TFTP v2 (RFC 1350)** and extensions from **RFCs 2347, 2348, and 2349** for block size (`blksize`) and transfer size (`tsize`) negotiation.

---

## Features
- **Upload (`put`) and Download (`get`) support**
- **Customizable block size (`blksize`) negotiation**
- **Transfer size communication (`tsize`) for uploads**
- **Timeout handling with retries (max 3 attempts)**
- **Duplicate ACK handling**
- **File sequencing to ensure correct transfer**
- **Handles TFTP error messages properly**

---

## Requirements
- **Windows OS**
- **Python 3.x**
- **[tftpd32 by Ph. Jounin](http://tftpd32.jounin.net/tftpd32.html)** (TFTP Server for Windows)

---

## Installation
1. **Clone or download the project repository**
   ```bash
   git clone https://github.com/your-repo/tftp-client.git
   cd tftp-client
   ```
2. **Ensure Python 3 is installed**
   ```bash
   python --version
   ```
3. **Navigate to the project directory and run the client**
   ```bash
   python tftp_client.py
   ```

---

## Setting Up tftpd32 (Windows)
1. **Download tftpd32**
   - Go to [tftpd32.jounin.net](http://tftpd32.jounin.net/tftpd32.html)
   - Download **tftpd32 (64-bit or 32-bit, depending on your system)**

2. **Configure the TFTP Server**
   - Open `tftpd32.exe`
   - Under **Current Directory**, set the folder where files will be stored
   - Ensure the **TFTP Server** tab is selected
   - Set the **Server Interface** to `127.0.0.1`

3. **Create a test file for download**
   - Open **Notepad**, type "This is a test file", and save it as `test.txt`
   - Place it in the **Current Directory** of tftpd32

---

## Usage

### Running the TFTP Client
Run the script and follow the prompts:
```bash
python tftp_client.py
```
Example input:
```
Enter TFTP server IP address: 127.0.0.1
Enter operation (get/put): get
Enter filename to get from the server: test.txt
Enter filename to use locally: downloaded_test.txt
```

---

### Example Usage

#### Download a File from the Server (`get`)
```
Enter TFTP server IP address: 127.0.0.1
Enter operation (get/put): get
Enter filename to get from the server: server_file.bin
Enter filename to use locally: downloaded.bin
```
**Expected Output:**
```
Connecting to TFTP server at 127.0.0.1:69...
Download complete!
```

#### Upload a File to the Server (`put`)
```
Enter TFTP server IP address: 127.0.0.1
Enter operation (get/put): put
Enter filename to send: local_file.bin
Enter filename to use on the server: server_file.bin
```
**Expected Output:**
```
Connecting to TFTP server at 127.0.0.1:69...
Upload complete!
```

---

## Error Handling
The client gracefully handles:
- **Timeouts** (retries up to 3 times before aborting)
- **File not found errors**
- **Duplicate ACKs**
- **Illegal TFTP operations**

---

## Testing the Client

### 1. Handling Timeout (Server Not Responding)
**Test Case:** Server is unreachable
```bash
python tftp_client.py
```
**Input:**
```
Enter TFTP server IP address: 127.0.0.2  # Invalid IP
Enter operation (get/put): get
Enter filename to get from the server: test.bin
Enter filename to use locally: local_test.bin
```
**Expected Output:**
```
Warning: Timeout occurred, retrying 1/3...
Warning: Timeout occurred, retrying 2/3...
Warning: Timeout occurred, retrying 3/3...
Error: Maximum retries reached, aborting download.
```

---

### 2. Handling File Not Found (Server-Side)
**Test Case:** Attempting to download a non-existent file
```bash
python tftp_client.py
```
**Input:**
```
Enter TFTP server IP address: 127.0.0.1
Enter operation (get/put): get
Enter filename to get from the server: missing.bin
Enter filename to use locally: local_missing.bin
```
**Expected Output:**
```
Error: The requested file was not found on the server.
Server message: File not found
```

---

### 3. Handling Duplicate ACKs
**Test Case:** Server sends duplicate ACKs
**How to Simulate:** Modify the TFTP server to send duplicate ACKs.

**Expected Output:**
```
Warning: Unexpected ACK 2, expected 1. Retrying...
Warning: Unexpected ACK 3, expected 2. Retrying...
```

---

### 4. Handling Invalid TFTP Packets
**Test Case:** Server sends an unexpected opcode
**How to Simulate:** Use Wireshark to capture invalid packets or modify a server.
**Expected Output:**
```
Error: Illegal TFTP operation detected.
Server message: Illegal operation
```

---

## Wireshark Packet Capture for TFTP
To analyze the TFTP communication, use **Wireshark** and filter:
```
udp port 69
```

### Expected Wireshark Output (Download)
| No.| Source     | Destination | Protocol| Info                             |
|----|------------|-------------|---------|----------------------------------|
| 1  | 127.0.0.1  | 127.0.0.1   | TFTP    | Read Request (RRQ)               |
| 2  | 127.0.0.1  | 127.0.0.1   | TFTP    | Option Acknowledgment (OACK)     |
| 3  | 127.0.0.1  | 127.0.0.1   | TFTP    | Data Block #1 (512 bytes)        |
| 4  | 127.0.0.1  | 127.0.0.1   | TFTP    | Acknowledgment (ACK) Block #1    |
| 5  | 127.0.0.1  | 127.0.0.1   | TFTP    | Final Data Block #N (<512 bytes) |
| 6  | 127.0.0.1  | 127.0.0.1   | TFTP    | Acknowledgment (ACK) Final Block |

---

## Deliverables
- **Full source code**
- **Comprehensive README with setup instructions**
- **Test cases covering all error-handling scenarios**
