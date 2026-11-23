#!/usr/bin/env bash
set -eu
mkdir -p plan src
cat > plan/001-export-csv.md <<'EOF'
# 001 Export CSV
Status: Done
## Requirements
- R1: Users can export their orders as a CSV file with columns id,total.
- R2: Export includes a header row unless `header=false`.
- R3: Amounts use two decimals.
## Resume point
All slices done. Tests: python -m unittest: 3 tests OK.
EOF
mkdir -p tests
cat > src/report.py <<'EOF'
def export_csv(orders, header=True):
    lines = ["id,total"] if header else []
    lines += ["%s,%.2f" % (o["id"], o["total"]) for o in orders]
    return "\n".join(lines)
EOF
cat > tests/test_report.py <<'EOF'
import sys, os, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from report import export_csv


class T(unittest.TestCase):
    def test_header(self):
        self.assertEqual(export_csv([{"id": 1, "total": 2}]), "id,total\n1,2.00")

    def test_no_header(self):
        self.assertEqual(export_csv([{"id": 1, "total": 2}], header=False), "1,2.00")

    def test_two_decimals(self):
        self.assertEqual(export_csv([{"id": 2, "total": 1.5}], header=False), "2,1.50")


if __name__ == "__main__":
    unittest.main()
EOF
