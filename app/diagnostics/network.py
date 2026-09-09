import platform
import subprocess


def ping_host(host):
    if platform.system().lower() == "windows":
        command = ["ping", "-n", "1", host]
    else:
        command = ["ping", "-c", "1", host]

    try:
        result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=5
    )

        return {
            "host": host,
            "success": result.returncode == 0,
            "output": result.stdout.strip()
        }
    except subprocess.TimeoutExpired:
        return {
            "host": host,
            "success": False,
            "output": "Ping request timed out."
        }