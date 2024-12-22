
import socket
import os
import hashlib
import time
from threading import Thread, Semaphore

SERVER_IP = ""
SERVER_PORT = 5555
CHUNK_SIZE = 1024 * 8
INPUT_FILE = "input.txt"
OUTPUT_FOLDER = "output"
TIMEOUT = 60
MAX_RETRIES = 10
MAX_THREADS = 1
CHECK_INTERVAL = 5

thread_limiter = Semaphore(MAX_THREADS)

def calculate_checksum(data):
    """Tính checksum bằng MD5"""
    return hashlib.md5(data).hexdigest()

def list_files():
    """Yêu cầu Server gửi danh sách file"""
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.settimeout(TIMEOUT)
    try:
        client_socket.sendto(b"LIST", (SERVER_IP, SERVER_PORT))
        response, _ = client_socket.recvfrom(4096)
        print("Danh sách các file có thể tải:")
        print(response.decode())
    except socket.timeout:
        print("Timeout khi yêu cầu danh sách file.")
    finally:
        client_socket.close()

def get_file_size(file_name):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.settimeout(TIMEOUT)
    try:
        client_socket.sendto(f"SIZE {file_name}".encode(), (SERVER_IP, SERVER_PORT))
        response, _ = client_socket.recvfrom(1024)
        if response.startswith(b"ERROR"):
            print(f"Lỗi: {response.decode()}")
            return None
        return int(response)
    except socket.timeout:
        print("Timeout khi yêu cầu kích thước file.")
        return None
    finally:
        client_socket.close()

def download_chunk(file_name, offset, output_path, total_chunks):
    with thread_limiter:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        retries = MAX_RETRIES
        seq_num = offset // CHUNK_SIZE

        try:
            while retries > 0:
                client_socket.sendto(f"DOWNLOAD {file_name} {offset}".encode(), (SERVER_IP, SERVER_PORT))
                client_socket.settimeout(TIMEOUT)
                packet, _ = client_socket.recvfrom(CHUNK_SIZE + 128)

                if packet == b"END":
                    print(f"Chunk {seq_num}: Kết thúc file.")
                    return True

                header, data = packet.split(b"|", 1)
                recv_seq, checksum = header.decode().split()

                if int(recv_seq) == seq_num and calculate_checksum(data) == checksum:
                    with open(output_path, "r+b") as f:
                        f.seek(offset)
                        f.write(data)
                    client_socket.sendto(f"ACK {recv_seq}".encode(), (SERVER_IP, SERVER_PORT))
                    print_progress(total_chunks, offset // CHUNK_SIZE + 1)
                    return True
                else:
                    print(f"Chunk {seq_num}: Checksum hoặc thứ tự sai, thử lại...")

        except socket.timeout:
            print(f"Chunk {seq_num}: Timeout, thử lại...")
        finally:
            client_socket.close()

        retries -= 1
        print(f"Chunk {seq_num} thất bại sau {MAX_RETRIES} lần thử.")
        return False

def print_progress(total_chunks, downloaded_chunks):
    """In phần trăm tiến độ tải lên màn hình"""
    percent = (downloaded_chunks / total_chunks) * 100
    print(f"\rĐang tải: {downloaded_chunks}/{total_chunks} chunks - {percent:.2f}% hoàn thành", end="")

def download_file(file_name):
    """Download toàn bộ file"""
    file_size = get_file_size(file_name)
    if not file_size:
        print(f"Không thể lấy kích thước file {file_name}.")
        return

    output_path = os.path.join(OUTPUT_FOLDER, file_name)

    with open(output_path, "wb") as f:
        f.truncate(file_size)

    total_chunks = (file_size + CHUNK_SIZE - 1) // CHUNK_SIZE
    threads = []

    for offset in range(0, file_size, CHUNK_SIZE):
        thread = Thread(target=download_chunk, args=(file_name, offset, output_path, total_chunks))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    if os.path.getsize(output_path) == file_size:
        print(f"\nFile '{file_name}' đã tải thành công.")
    else:
        print(f"\nFile '{file_name}' tải không hoàn tất.")

def main():
    """Quét file input.txt và tải file mới"""
    global SERVER_IP
    SERVER_IP = input("Nhập địa chỉ IP của Server: ").strip()

    processed_files = set()
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)

    list_files()
    time.sleep(5)

    try:
        while True:
            with open(INPUT_FILE, "r") as f:
                files_to_download = [line.strip() for line in f if line.strip()]

            for file_name in files_to_download:
                if file_name not in processed_files:
                    print(f"\nĐang tải file '{file_name}'...")
                    download_file(file_name)
                    processed_files.add(file_name)

            time.sleep(CHECK_INTERVAL)
    except KeyboardInterrupt:
        print("\nĐã dừng chương trình.")

if __name__ == "__main__":
    main()
