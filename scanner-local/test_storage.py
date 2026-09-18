import tempfile
import unittest
from pathlib import Path

from storage import get_scan, list_scans, save_report


REPORT = {
    "target": "127.0.0.1",
    "resolved_target": "127.0.0.1",
    "scanned_ports": 1,
    "timeout_seconds": 0.1,
    "started_at_utc": "2026-09-18T00:00:00+00:00",
    "results": [
        {"port": 8000, "state": "open", "service": "irdmi", "latency_ms": 1.2, "error": None}
    ],
}


class StorageTests(unittest.TestCase):
    def test_save_and_read_normalized_report(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "scanner.db"
            scan_id = save_report(database, REPORT)
            self.assertEqual(len(list_scans(database)), 1)
            self.assertEqual(get_scan(database, scan_id)["results"][0]["port"], 8000)


if __name__ == "__main__":
    unittest.main()
