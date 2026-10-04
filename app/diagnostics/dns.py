
import socket


def dns_lookup(host):
    try:
        address = socket.gethostbyname(host)

        return {
            "host": host,
            "success": True,
            "address": address,
            "error": None,
        }

    except socket.gaierror as exc:
        return {
            "host": host,
            "success": False,
            "address": None,
            "error": str(exc),
        }

    except OSError as exc:
        return {
            "host": host,
            "success": False,
            "address": None,
            "error": str(exc),
        }