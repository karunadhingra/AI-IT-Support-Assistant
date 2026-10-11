import time
import psutil


def check_cpu_usage(interval=0.5):
    """
    Measure live CPU utilization percentage and core count.
    """
    try:
        cpu_percent = round(float(psutil.cpu_percent(interval=interval)), 1)
        logical_cores = psutil.cpu_count(logical=True) or 1

        return {
            "success": True,
            "cpu_percent": cpu_percent,
            "logical_cores": logical_cores,
            "high_load": cpu_percent >= 80.0,
        }
    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
        }


def check_system_uptime():
    """
    Check how long the system has been running since the last boot.
    Long uptime (> 72 hours) often causes memory leaks and slowdowns.
    """
    try:
        boot_timestamp = psutil.boot_time()
        uptime_seconds = max(0.0, time.time() - boot_timestamp)
        uptime_hours = round(uptime_seconds / 3600.0, 1)
        uptime_days = round(uptime_hours / 24.0, 1)

        return {
            "success": True,
            "uptime_hours": uptime_hours,
            "uptime_days": uptime_days,
            "needs_reboot": uptime_hours >= 72.0,
        }
    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
        }


def check_swap_memory():
    """
    Check swap / pagefile usage to see if the system is paging heavily to disk.
    """
    try:
        swap = psutil.swap_memory()
        total_gb = round(swap.total / (1024 ** 3), 2)
        used_gb = round(swap.used / (1024 ** 3), 2)
        used_percent = round(float(swap.percent), 1)

        return {
            "success": True,
            "total_gb": total_gb,
            "used_gb": used_gb,
            "used_percent": used_percent,
            "high_swap": used_percent >= 80.0,
        }
    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
        }