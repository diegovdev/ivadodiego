"""Read Locust CSV stats and enforce p95/p99/error-rate thresholds (V35).

Usage: python check_locust_thresholds.py <locust_stats.csv>
Exit 1 if any threshold is breached.
"""

import csv
import sys

_P95_THRESHOLD_MS = 500
_P99_THRESHOLD_MS = 1000
_ERROR_RATE_THRESHOLD_PCT = 1.0


def main(csv_path: str) -> int:
    failures: list[str] = []
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("Name", "")
            if name == "Aggregated":
                continue
            p95 = float(row.get("95%", 0) or 0)
            p99 = float(row.get("99%", 0) or 0)
            requests = int(row.get("Request Count", 0) or 0)
            failures_count = int(row.get("Failure Count", 0) or 0)
            error_rate = (failures_count / requests * 100) if requests else 0.0

            if p95 > _P95_THRESHOLD_MS:
                failures.append(
                    f"{name}: p95={p95:.0f}ms > threshold {_P95_THRESHOLD_MS}ms"
                )
            if p99 > _P99_THRESHOLD_MS:
                failures.append(
                    f"{name}: p99={p99:.0f}ms > threshold {_P99_THRESHOLD_MS}ms"
                )
            if error_rate > _ERROR_RATE_THRESHOLD_PCT:
                failures.append(
                    f"{name}: error_rate={error_rate:.1f}% > threshold "
                    f"{_ERROR_RATE_THRESHOLD_PCT}%"
                )

    if failures:
        print("THRESHOLD BREACHES:")
        for msg in failures:
            print(f"  {msg}")
        return 1

    print("All thresholds passed.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <locust_stats.csv>", file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
