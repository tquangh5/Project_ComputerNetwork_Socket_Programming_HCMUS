import socket
import os
import hashlib

CHUNK_SIZE = 1024*8  
SERVER_PORT = 5555
TIMEOUT = 60
FILES_TXT = "file_list.txt"

def read_file_list():
    files = {}
    if os.path.exists(FILES_TXT):
        with open(FILES_TXT, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue  
                try:
                    name, size = line.split()
                    size_value, size_unit = int(size[:-2]), size[-2:]
                    if size_unit == "MB":
                        files[name] = size_value * 1024 * 1024
                    elif size_unit == "KB":
                        files[name] = size_value * 1024
                    else:
                        print(f"Lỗi: Đơn vị không hợp lệ trong dòng '{line}'.")
                except ValueError:
                    print(f"Lỗi: Dòng không hợp lệ '{line}', bỏ qua.")
    return files



def calculate_checksum(data):
    return hashlib.md5(data).hexdigest()

def send_chunk(server_socket, client_address, seq_num, data):
    retries = 5
    checksum = calculate_checksum(data)
    packet = f"{seq_num} {checksum}".encode() + b"|" + data

    while retries > 0:
        try:
            print(f"Đang gửi chunk {seq_num} đến {client_address}")
            server_socket.sendto(packet, client_address)
            server_socket.settimeout(TIMEOUT)
            ack, _ = server_socket.recvfrom(1024)
            if ack.decode() == f"ACK {seq_num}":
                print(f"Chunk {seq_num} đã gửi thành công.")
                return True
        except socket.timeout:
            print(f"Chunk {seq_num}: Timeout, thử lại...")
        retries -= 1
    print(f"Chunk {seq_num} gửi thất bại.")
    return False

def handle_download_request(server_socket, client_address, file_name, offset):
    try:
        with open(file_name, "rb") as f:
            f.seek(offset)
            data = f.read(CHUNK_SIZE)
            if data:
                seq_num = offset // CHUNK_SIZE
                send_chunk(server_socket, client_address, seq_num, data)
            else:
                server_socket.sendto(b"END", client_address)
    except Exception as e:
        print(f"Lỗi: {e}")
        server_socket.sendto(b"ERROR", client_address)


def main():
    SERVER_HOST = socket.gethostname()
    try:
        SERVER_IP = socket.gethostbyname(SERVER_HOST)
    except socket.gaierror:
        SERVER_IP = '127.0.0.1'

    print(f"Server hostname: {SERVER_HOST}")
    print(f"Server IP address: {SERVER_IP}")
    print(f"Server port: {SERVER_PORT}")

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind(("0.0.0.0", SERVER_PORT))
    print("Server đang lắng nghe...")

    files = read_file_list()

    try:
        while True:
            data, client_address = server_socket.recvfrom(1024)
            command = data.decode().split()
            if command[0] == "SIZE":
                file_name = command[1]
                if file_name in files:
                    server_socket.sendto(str(files[file_name]).encode(), client_address)
                else:
                    server_socket.sendto(b"ERROR: File not found", client_address)
            elif command[0] == "DOWNLOAD":
                file_name, offset = command[1], int(command[2])
                handle_download_request(server_socket, client_address, file_name, offset)
            elif command[0] == "LIST":
                file_list = "\n".join([f"{name} {size // (1024 * 1024)}MB" for name, size in files.items()])
                server_socket.sendto(file_list.encode(), client_address)
    except KeyboardInterrupt:
        print("\nServer đang dừng lại...")
    finally:
        server_socket.close()
        print("Server đã ngừng.")

if __name__ == "__main__":
    main()
