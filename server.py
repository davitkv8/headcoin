"""Server module, intermediate for newly created nodes, helping them to know each other."""

import socket

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('0.0.0.0', 55555))

peers = set()

print("Rendezvous server started on port 55555...")

while True:
    data, address = sock.recvfrom(128)
    print("connection from:", address)

    peers.add(address)

    peer_list = list(peers)
    msg = "PEERS " + " ".join([f"{ip}:{port}" for ip, port in peer_list])

    for peer in peer_list:
        sock.sendto(msg.encode(), peer)
