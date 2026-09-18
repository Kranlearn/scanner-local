"""TCP connect scanner for one explicitly authorized host.

This project is educational. Scan only systems you own or have permission to test.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import ipaddress
import json
import socket
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from storage import save_report

DEFAULT_TIMEOUT = 0.5
MAX_WORKERS = 32


@dataclass(frozen=True)
class PortResult:
    port: int
    state: str
    service: str
    latency_ms: float | None
    error: str | None = None


def parse_ports(value: str) -> list[int]:
    """Parse comma-separated ports and inclusive ranges."""
    ports: set[int] = set()

    for part in value.split(","):
        token = part.strip()
        if not token:
            continue

        if "-" in token:
            start_text, end_text = token.split("-", maxsplit=1)
            try:
                start, end = int(start_text), int(end_text)
            except ValueError as exc:
                raise ValueError(f"Invalid port range: {token}") from exc
            if start > end:
                raise ValueError(f"Port range must be ascending: {token}")
            ports.update(range(start, end + 1))
        else:
            try:
                ports.add(int(token))
            except ValueError as exc:
                raise ValueError(f"Invalid port: {token}") from exc

    if not ports or any(port < 1 or port > 65535 for port in ports):
        raise ValueError("Ports must be between 1 and 65535")

    return sorted(ports)


def validate_target(target: str) -> str:
    """Accept one hostname or IP address, never a network range."""
    if "/" in target:
        raise ValueError("Network ranges are not supported; provide one host")

    try:
        ipaddress.ip_address(target)
        return target
    except ValueError:
        pass

    if not target or len(target) > 253 or target.startswith("."):
        raise ValueError("Target must be one valid hostname or IP address")

    try:
        socket.getaddrinfo(target, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ValueError(f"Unable to resolve target: {target}") from exc

    return target


def service_name(port: int) -> str:
    try:
        return socket.getservbyport(port, "tcp")
    except OSError:
        return "unknown"


def scan_port(target: str, port: int, timeout: float) -> PortResult:
    started = datetime.now(timezone.utc)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)

    try:
        error_code = sock.connect_ex((target, port))
        latency_ms = round(
            (datetime.now(timezone.utc) - started).total_seconds() * 1000, 2
        )
        if error_code == 0:
            return PortResult(port, "open", service_name(port), latency_ms)
        return PortResult(port, "closed_or_filtered", service_name(port), latency_ms)
    except socket.gaierror as exc:
        return PortResult(port, "error", service_name(port), None, str(exc))
    except OSError as exc:
        return PortResult(port, "error", service_name(port), None, str(exc))
    finally:
        sock.close()


def scan(target: str, ports: list[int], timeout: float) -> dict:
    """Scan the requested ports concurrently and return serializable results."""
    resolved_target = socket.gethostbyname(target)
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(ports))) as pool:
        results = list(pool.map(lambda port: scan_port(resolved_target, port, timeout), ports))

    return {
        "target": target,
        "resolved_target": resolved_target,
        "scanned_ports": len(ports),
        "timeout_seconds": timeout,
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "results": [asdict(result) for result in sorted(results, key=lambda item: item.port)],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Educational TCP scanner for one host")
    parser.add_argument("target", help="One authorized hostname or IPv4 address")
    parser.add_argument(
        "--ports",
        default="22,80,443",
        help="Ports such as 22,80,443 or ranges such as 1-1024",
    )
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--output", type=Path, help="Write JSON results to this file")
    parser.add_argument("--database", default="scanner.db", help="SQLite database path")
    parser.add_argument("--no-save", action="store_true", help="Do not save this report")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        target = validate_target(args.target)
        ports = parse_ports(args.ports)
        if args.timeout <= 0 or args.timeout > 10:
            raise ValueError("Timeout must be greater than 0 and no more than 10 seconds")
        report = scan(target, ports, args.timeout)
        scan_id = None if args.no_save else save_report(args.database, report)
    except ValueError as exc:
        print(f"Input error: {exc}", file=sys.stderr)
        return 2

    serialized = json.dumps(report, indent=2)
    if scan_id is not None:
        print(f"Saved scan #{scan_id} to {args.database}")
    if args.output:
        args.output.write_text(serialized + "\n", encoding="utf-8")
        print(f"Report written to {args.output}")
    else:
        print(serialized)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
