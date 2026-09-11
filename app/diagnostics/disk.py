import shutil


def check_disk_space(path="."):
    total, used, free = shutil.disk_usage(path)

    free_gb = round(free / (1024 ** 3), 2)
    total_gb = round(total / (1024 ** 3), 2)
    used_gb = round(used / (1024 ** 3), 2)

    return {
        "path": path,
        "total_gb": total_gb,
        "used_gb": used_gb,
        "free_gb": free_gb
    }