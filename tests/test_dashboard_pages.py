from pathlib import Path


def test_dashboard_pages_exist():
    root = Path(__file__).resolve().parents[1]
    required = [
        "src/dashboard.py",
        "src/dashboard_pages/__init__.py",
        "src/dashboard_pages/overview.py",
        "src/dashboard_pages/zones.py",
        "src/dashboard_pages/analytics.py",
        "src/dashboard_pages/forecast.py",
        "src/dashboard_pages/controls.py",
        "src/dashboard_pages/data_explorer.py",
    ]
    for rel in required:
        assert (root / rel).exists(), f"Missing dashboard page: {rel}"
