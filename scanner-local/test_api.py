import json
import tempfile
import unittest
from http.client import HTTPConnection
from threading import Thread
from http.server import ThreadingHTTPServer
from pathlib import Path

from api import ApiHandler


class ApiTests(unittest.TestCase):
    def test_dashboard_is_served(self):
        ApiHandler.database = ":memory:"
        server = ThreadingHTTPServer(("127.0.0.1", 0), ApiHandler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            connection = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
            connection.request("GET", "/")
            response = connection.getresponse()
            body = response.read().decode("utf-8")
            self.assertEqual(response.status, 200)
            self.assertIn("LocalScope", body)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_health_and_empty_scan_list(self):
        with tempfile.TemporaryDirectory() as directory:
            ApiHandler.database = str(Path(directory) / "scanner.db")
            server = ThreadingHTTPServer(("127.0.0.1", 0), ApiHandler)
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                connection = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
                connection.request("GET", "/health")
                response = connection.getresponse()
                self.assertEqual(response.status, 200)
                self.assertEqual(json.loads(response.read()), {"status": "ok"})

                connection.request("GET", "/scans")
                response = connection.getresponse()
                self.assertEqual(response.status, 200)
                self.assertEqual(json.loads(response.read()), {"scans": []})
            finally:
                server.shutdown()
                server.server_close()
                thread.join()


if __name__ == "__main__":
    unittest.main()
