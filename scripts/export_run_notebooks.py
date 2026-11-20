"""Export every notebook task of a job run as a Jupyter notebook WITH its cell outputs.

The outputs come from the real job run (not a separate interactive run): the run export contains the
executed notebook model, which is decoded into .ipynb files under evidence/notebooks/ (readable as text,
rendered by GitHub).

Usage: python3 scripts/export_run_notebooks.py <profile> <job_run_id>
"""
import base64
import html as htmllib
import json
import os
import re
import subprocess
import sys
import urllib.parse

PROFILE, RUN_ID = sys.argv[1], sys.argv[2]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "evidence", "notebooks")


def cli(*args):
    out = subprocess.run(["databricks", *args, "--profile", PROFILE, "-o", "json"], capture_output=True, text=True)
    if out.returncode:
        raise SystemExit(out.stderr)
    return json.loads(out.stdout)


def text_of(result):
    """Flatten a Databricks command result into plain text."""
    if not result:
        return ""
    rtype, data = result.get("type"), result.get("data")
    if rtype == "listResults":
        return "".join(text_of(item) for item in data or [])
    if rtype in ("ansi", "text"):
        return re.sub(r"\x1b\[[0-9;]*m", "", str(data or ""))
    if rtype == "table":
        cols = [c.get("name") for c in result.get("schema", [])]
        rows = data or []
        lines = [" | ".join(cols)] + [" | ".join(str(v) for v in r) for r in rows[:50]]
        return "\n".join(lines) + ("\n... (%d rows)" % len(rows) if len(rows) > 50 else "") + "\n"
    if rtype in ("html", "htmlSandbox"):
        return htmllib.unescape(re.sub(r"<[^>]+>", " ", str(data or ""))).strip() + "\n"
    if rtype == "error":
        return "ERROR: " + str(result.get("summary") or data)[:2000] + "\n"
    return str(data or "") if data else ""


def to_ipynb(model, title):
    cells = []
    for c in sorted(model["commands"], key=lambda c: c.get("position", 0)):
        src = c.get("command", "")
        if src.lstrip().startswith("%md"):
            cells.append({"cell_type": "markdown", "metadata": {}, "source": src.split("\n", 1)[1] if "\n" in src else ""})
            continue
        out = text_of(c.get("results"))
        outputs = [{"output_type": "stream", "name": "stdout", "text": out}] if out else []
        cells.append({"cell_type": "code", "execution_count": None, "metadata": {}, "source": src, "outputs": outputs})
    return {"nbformat": 4, "nbformat_minor": 5, "cells": cells,
            "metadata": {"title": title, "language_info": {"name": "python"},
                         "databricks_job_run": RUN_ID}}


def main():
    os.makedirs(OUT, exist_ok=True)
    run = cli("jobs", "get-run", RUN_ID)
    done = []
    for t in sorted(run["tasks"], key=lambda t: t.get("start_time", 0)):
        path = (t.get("notebook_task") or {}).get("notebook_path")
        if not path:
            continue
        name = os.path.basename(path).replace(".py", "")
        views = cli("jobs", "export-run", str(t["run_id"]), "--views-to-export", "CODE").get("views", [])
        m = re.search(r"__DATABRICKS_NOTEBOOK_MODEL = '([^']+)'", views[0]["content"]) if views else None
        if not m:
            print("skip %s: no notebook model in export" % name)
            continue
        model = json.loads(urllib.parse.unquote(base64.b64decode(m.group(1)).decode("utf-8")))
        nb = to_ipynb(model, "%s (job run %s, task %s, %s)" % (name, RUN_ID, t["task_key"], t["state"].get("result_state")))
        with open(os.path.join(OUT, name + ".ipynb"), "w") as f:
            json.dump(nb, f, indent=1)
        done.append((name, t["state"].get("result_state"), sum(1 for c in nb["cells"] if c.get("outputs"))))
    for name, state, n in done:
        print("%-22s %-8s %d cells with output" % (name, state, n))


if __name__ == "__main__":
    main()
