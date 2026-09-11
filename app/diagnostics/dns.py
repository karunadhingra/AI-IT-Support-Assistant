import socket


def dns_lookup(host):
    try:
        address = socket.gethostbyname(host)

        return {
            "host": host,
            "success": True,
            "address": address
        }

    except socket.gaierror:
        return {
            "host": host,
            "success": False,
            "address": None
        }