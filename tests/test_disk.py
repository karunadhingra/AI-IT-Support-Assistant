from unittest.mock import patch

from app.diagnostics.disk import check_disk_space


def test_check_disk_space():
    with patch(
        "app.diagnostics.disk.shutil.disk_usage",
        return_value=(100 * 1024**3, 60 * 1024**3, 40 * 1024**3)
    ):
        result = check_disk_space(".")

    assert result["path"] == "."
    assert result["total_gb"] == 100
    assert result["used_gb"] == 60
    assert result["free_gb"] == 40
def test_check_disk_space_handles_os_error():

    with patch(
        "app.diagnostics.disk.shutil.disk_usage",
        side_effect=OSError("Disk access failed")
    ):
        result = check_disk_space(".")

    assert result["path"] == "."
    assert result["success"] is False
    assert "Disk access failed" in result["error"]