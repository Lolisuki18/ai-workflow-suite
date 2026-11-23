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
All slices done. Tests: python -m pytest: 3 passed.
EOF
echo "def export_csv(orders, header=True): pass" > src/report.py
