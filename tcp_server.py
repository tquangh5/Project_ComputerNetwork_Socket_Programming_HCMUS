
import socket
import threading
import os

SERVER_PORT = 65000
FORMAT = "utf8"

def read_file_list():
    files = {}
    if os.path.exists("file_list.txt"):
        with open("file_list.txt", "r") as f:
            for line in f:
                name, size_str = line.strip().split()
                # Lấy kích thước thực tế từ hệ thống
                actual_size = os.path.getsize(name)
                files[name] = actual_size
    return files

def handle_client(client_socket, files):
    print("New client connected.")
    try:
        while True:
            request = client_socket.recv(1024).decode("utf-8")
            if not request:
                break

            parts = request.split()
            if parts[0] == "LIST":
                if not files:
                    client_socket.sendall(b"ERROR: No files available.")
                else:
                    file_list = "\n".join([f"{name} - {size}B" for name, size in files.items()])
                    client_socket.sendall(file_list.encode("utf-8"))
            elif parts[0] == "SIZE":
                file_name = parts[1]
                if file_name in files:
                    client_socket.sendall(str(files[file_name]).encode("utf-8"))
                else:
                    client_socket.sendall(b"ERROR: File not found")
            elif parts[0] == "DOWNLOAD":
                file_name, offset, chunk_size = parts[1], int(parts[2]), int(parts[3])
                if file_name in files:
                    try:
                        with open(file_name, "rb") as f:
                            f.seek(offset)
                            data = f.read(chunk_size)
                            client_socket.sendall(data)
                    except Exception as e:
                        client_socket.sendall(f"ERROR: {str(e)}".encode("utf-8"))
                else:
                    client_socket.sendall(b"ERROR: File not found")
            else:
                client_socket.sendall(b"ERROR: Invalid command")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client_socket.close()
        print("Client disconnected.")
        
def main():
    files = read_file_list()

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    SERVER = socket.gethostname()
    s.bind((SERVER, SERVER_PORT))
    s.listen()

    SERVER_HOST = socket.gethostname()
    SERVER_IP = socket.gethostbyname(SERVER_HOST)
    print(f"Server hostname: {SERVER_HOST}")
    print(f"Server IP address: {SERVER_IP}")
    print(f"Server port: {SERVER_PORT}")
    print("Waiting for client.")

    while True:
        try:
            client_socket, addr = s.accept()
            print(f"Accepted connection from {addr}")
            threading.Thread(target=handle_client, args=(client_socket, files)).start()
        except KeyboardInterrupt:
            print("\nServer is shutting down.")
            break

if __name__ == "__main__":
    main()
