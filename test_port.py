import socket
import trio

async def simple_listener():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("0.0.0.0", 60005))
        s.listen()
        print("Test listener active on 60005. Waiting for connection...")
        s.setblocking(False)
        while True:
            conn, addr = await trio.lowlevel.checkpoint(), await trio.run_sync_in_worker_thread(s.accept)
            client_sock, client_addr = conn
            print(f"Connection from {client_addr}")
            data = await trio.run_sync_in_worker_thread(client_sock.recv, 1024)
            print(f"Received {len(data)} bytes")
            client_sock.close()

if __name__ == "__main__":
    trio.run(simple_listener)
