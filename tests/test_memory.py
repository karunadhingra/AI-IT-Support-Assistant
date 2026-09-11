from unittest.mock import patch

from app.diagnostics.memory import check_memory


def test_check_memory():
    mock_memory = type(
        "Memory",
        (),
        {
            "total": 16 * 1024**3,
            "available": 6 * 1024**3,
            "percent": 62.5
        }
    )()

    with patch(
        "app.diagnostics.memory.psutil.virtual_memory",
        return_value=mock_memory
    ):
        result = check_memory()

    assert result["total_gb"] == 16
    assert result["available_gb"] == 6
    assert result["used_percent"] == 62.5