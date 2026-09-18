import unittest

from scanner import parse_ports, validate_target


class ScannerInputTests(unittest.TestCase):
    def test_parse_ports_deduplicates_and_sorts(self):
        self.assertEqual(parse_ports("443,80,80,8000-8002"), [80, 443, 8000, 8001, 8002])

    def test_parse_ports_rejects_invalid_port(self):
        with self.assertRaises(ValueError):
            parse_ports("0,70000")

    def test_validate_target_rejects_network_range(self):
        with self.assertRaises(ValueError):
            validate_target("192.168.1.0/24")

    def test_validate_target_accepts_loopback(self):
        self.assertEqual(validate_target("127.0.0.1"), "127.0.0.1")


if __name__ == "__main__":
    unittest.main()
