
import socket
import os
import time
import threading

SERVER_IP = ""
SERVER_PORT = 65000
CHUNK_SIZE = 1024 * 1024  # 1MB
OUTPUT_FOLDER = "output"
INPUT_FILE = "input.txt"

if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)

def fetch_file_list():
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((SERVER_IP, SERVER_PORT))
        client.send("LIST".encode("utf-8"))

        file_list = client.recv(4096).decode("utf-8")
        client.close()
        print("\nDanh sách file trên server:")
        print(file_list)
    except Exception as e:
        print(f"Error: {e}")

def print_progress(file_name, progress):
    progress_line = f"Downloading {file_name} progress: "
    for i, p in enumerate(progress):
        progress_line += f"Part {i+1}: {p:.2f}%  "
    print(progress_line, end="\r")

def download_file(file_name, file_size):
    # Chia file thành đúng 4 phần
    part_size = file_size // 4
    remainder = file_size % 4

    parts = [b""] * 4
    progress = [0] * 4
    threads = []

    def download_part(part_id, start_offset, size):
        nonlocal progress
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((SERVER_IP, SERVER_PORT))
        client.send(f"DOWNLOAD {file_name} {start_offset} {size}".encode("utf-8"))

        received_data = b""
        while len(received_data) < size:
            chunk = client.recv(min(CHUNK_SIZE, size - len(received_data)))
            if not chunk:
                break
            received_data += chunk
            progress[part_id] = (len(received_data) / size) * 100
            print_progress(file_name, progress)
        client.close()
        parts[part_id] = received_data

    # Tải từng phần
    for i in range(4):
        start_offset = i * part_size
        size = part_size + (remainder if i == 3 else 0)  # Phần dư được cộng vào phần cuối
        thread = threading.Thread(target=download_part, args=(i, start_offset, size))
        threads.append(thread)
        thread.start()

    # Chờ tất cả các thread hoàn thành
    for thread in threads:
        thread.join()

    # Ghi dữ liệu các phần vào file
    output_path = os.path.join(OUTPUT_FOLDER, file_name)
    with open(output_path, "wb") as f:
        for part in parts:
            f.write(part)
    print(f"\nFile {file_name} đã tải xong và lưu vào '{OUTPUT_FOLDER}'")

def get_file_size(file_name):
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((SERVER_IP, SERVER_PORT))
        client.send(f"SIZE {file_name}".encode("utf-8"))
        response = client.recv(1024).decode("utf-8")
        client.close()
        if response.startswith("ERROR"):
            print(response)
            return None
        return int(response)
    except Exception as e:
        print(f"Error: {e}")
        return None

def main():
    global SERVER_IP
    SERVER_IP = input("Nhập địa chỉ IP của Server: ").strip()
    processed_files = set()
    
    try:
        fetch_file_list()

        while True:
            if os.path.exists(INPUT_FILE):
                with open(INPUT_FILE, "r") as file:
                    lines = file.readlines()
                    for file_name in lines:
                        file_name = file_name.strip()
                        if file_name and file_name not in processed_files:
                            print(f"\nĐang tải {file_name}...")
                            file_size = get_file_size(file_name)
                            if file_size:
                                download_file(file_name, file_size)
                                processed_files.add(file_name)
                            else:
                                print(f"Không thể lấy kích thước của file '{file_name}'")
            else:
                print(f"{INPUT_FILE} không tồn tại!")
            
            time.sleep(5)
    except KeyboardInterrupt:
        print("\nChương trình đã dừng lại.")

if __name__ == "__main__":
    main()
