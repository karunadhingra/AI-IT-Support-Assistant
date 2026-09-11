import psutil


def check_memory():
    memory = psutil.virtual_memory()

    total_gb = round(memory.total / (1024 ** 3), 2)
    available_gb = round(memory.available / (1024 ** 3), 2)
    used_percent = memory.percent

    return {
        "total_gb": total_gb,
        "available_gb": available_gb,
        "used_percent": used_percent
    }