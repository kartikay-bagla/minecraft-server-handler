import socket
import struct
import json


def _unpack_varint(s):
    d = 0
    for i in range(5):
        b = ord(s.recv(1))
        d |= (b & 0x7F) << 7 * i
        if not b & 0x80:
            break
    return d


def _pack_varint(d):
    o = b""
    while True:
        b = d & 0x7F
        d >>= 7
        o += struct.pack("B", b | (0x80 if d > 0 else 0))
        if d == 0:
            break
    return o


def _pack_data(d):
    h = _pack_varint(len(d))
    if type(d) == str:
        d = bytes(d, "utf-8")
    return h + d


def _pack_port(i):
    return struct.pack(">H", i)


def get_info(host="localhost", port=25565):
    """Get info for minecraft server."""
    # Connect
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))

    # Send handshake + status request
    s.send(
        _pack_data(
            b"\x00\x00" + _pack_data(host.encode("utf8")) + _pack_port(port) + b"\x01"
        )
    )
    s.send(_pack_data("\x00"))

    # Read response
    _unpack_varint(s)  # Packet length
    _unpack_varint(s)  # Packet ID
    length = _unpack_varint(s)  # String length

    d = b""
    while len(d) < length:
        d += s.recv(1024)

    # Close our socket
    s.close()

    # Load json and return
    return json.loads(d.decode("utf8"))
