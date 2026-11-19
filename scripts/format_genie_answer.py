"""Format one Genie start-conversation JSON response (stdin) as Markdown."""
import json
import sys

q = sys.argv[1]
raw = sys.stdin.read()
print("\n## Q: %s\n" % q)
try:
    m = json.loads(raw)
except ValueError:
    print("ERROR: " + raw[:400])
    sys.exit(0)
print("status: %s" % m.get("status"))
for a in m.get("attachments") or []:
    if a.get("text"):
        print("\n**Answer:** " + (a["text"].get("content") or "").strip())
    if a.get("query"):
        qq = a["query"]
        print("\n**Generated SQL** (%s):\n```sql\n%s\n```" % (qq.get("description") or "", (qq.get("query") or "").strip()))
        meta = qq.get("query_result_metadata") or {}
        print("result rows: %s" % meta.get("row_count"))
