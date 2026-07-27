#!/usr/bin/env bash
# scripts/generate-remediation-tasks.sh <remediation-map.json>
# Parses audits/CTO_<N>_remediation_map.json and appends each remediation to
# the named target stage's task doc as an acceptance-criteria line.

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

if [ "${#}" -lt 1 ]; then
  echo "Usage: $0 <remediation-map.json>"
  exit 2
fi

MAP="$1"
if [ ! -f "$MAP" ]; then
  echo "ERROR: $MAP not found."
  exit 2
fi

python - "$MAP" <<'PYEOF'
import json, sys, os, glob, re

map_path = sys.argv[1]
data = json.load(open(map_path, encoding="utf-8"))
remediations = data.get("remediations", [])

if not remediations:
    print("No remediations in map.")
    sys.exit(0)

routed = 0
for r in remediations:
    target = str(r.get("target_stage", "")).strip()
    desc = r.get("description", "").strip()
    if not target or not desc:
        continue
    # Resolve the target task doc by its EXACT frontmatter `stage:` value — NOT a filename-prefix glob.
    # (G-015 fix: glob "STAGE_11_*" wrongly matches STAGE_11_5_* (= stage 11.5), and sorted-first picked the
    #  half-stage doc — the live mis-route observed at CTO #2. Matching the `stage:` field is unambiguous.)
    t = target.replace(".", "_")
    intpart = t.split("_")[0]
    if intpart.isdigit() and len(intpart) == 1:
        intpart = "0" + intpart
    try:
        target_val = float(target.replace("_", "."))   # "11"->11.0, "13_5"->13.5
    except ValueError:
        target_val = None
    candidates = []
    for path in sorted(glob.glob(f"tasks/STAGE_{intpart}*.md")):
        try:
            head = open(path, "r", encoding="utf-8").read(400)
        except Exception:
            continue
        m = re.search(r"(?m)^stage:\s*([0-9]+(?:\.[0-9]+)?)\s*$", head)
        if m and target_val is not None and abs(float(m.group(1)) - target_val) < 1e-9:
            candidates.append(path)
    if not candidates:
        print(f"  (skip) no task doc with frontmatter stage:{target.replace('_','.')} yet: {desc[:60]}")
        continue
    task = candidates[0]
    with open(task, "r", encoding="utf-8") as f:
        body = f.read()
    if desc in body:
        continue  # already added
    if "## Acceptance criteria" in body:
        body = body.replace(
            "## Acceptance criteria",
            f"## Acceptance criteria\n\n- [ ] (CTO remediation) {desc}",
            1,
        )
    else:
        body += f"\n\n## Acceptance criteria\n\n- [ ] (CTO remediation) {desc}\n"
    with open(task, "w", encoding="utf-8") as f:
        f.write(body)
    print(f"  -> appended remediation to {task}")
    routed += 1

print(f"Routed {routed} remediation(s).")
PYEOF
