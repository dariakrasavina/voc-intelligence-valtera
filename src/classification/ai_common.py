"""
ai_common.py
------------
Shared, dependency-free helpers for the AI classification track (ai_classify_job.py):

  * find_category_model() / load_categories()  - locate + parse the SAME
    category_model.json the rule engine uses, so both classifiers work against
    identical categories. ai_classify reads each target category's
    `ai_description` (falling back to `description`) as its label definition.
  * labels_json() / definitions_fingerprint()  - the {label: definition} object
    passed to ai_classify, and a hash of everything ai_classify reads (used as
    part of the result-cache key, so editing a definition forces re-classification).

No pyspark import here, so it loads cleanly in DBSQL-batch jobs and locally.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def find_category_model(filename=None):
    """Locate a category-model JSON regardless of folder layout (repo vs. a flat
    cluster upload where the modules + json are co-located).

    `filename` may be None/"" (the default category_model.json / v1), a basename
    (e.g. category_model_v2.json, resolved against the known dirs so the bundle's
    shared/ copy is found), or an existing path (used as-is).
    """
    filename = (filename or "").strip()
    if filename and os.path.exists(filename):
        return filename
    base = os.path.basename(filename) if filename else "category_model.json"
    repo = os.path.dirname(HERE)
    for c in (os.path.join(HERE, base),
              os.path.join(repo, "shared", base),
              os.path.join(HERE, "shared", base),
              os.path.join(os.getcwd(), base),
              os.path.join(os.getcwd(), "shared", base)):
        if os.path.exists(c):
            return c
    raise FileNotFoundError("%s not found near %s" % (base, HERE))


def load_categories(rules_path=None):
    """Return category metadata from category_model.json.

    Returns:
      target_labels : {category_name: short description}  (leaf comparison targets)
      name_to_id    : {category_name: category_id}         (all categories)
      all_ids       : [category_id ...] in model order      (leaves + parents)
      ancestors     : {category_id: [ancestor_id ...]}      (nearest parent first)
      meta          : {category_id: {name, path, is_target}}
    """
    rules_path = find_category_model(rules_path)
    with open(rules_path) as f:
        rules = json.load(f)

    name_to_id = {n["name"]: n["id"] for n in rules["nodes"]}
    target_labels = {}
    for node in rules["nodes"]:
        if node.get("comparison_target"):
            # Prefer `ai_description` (the classifier-facing definition with full
            # include/exclude) when present; fall back to the customer-authored
            # `description`. This keeps the customer's `description` untouched while
            # letting the model file be the single source of truth for the AI track. 1000 = the ai_classify v2.1 label-description cap.
            desc = " ".join((node.get("ai_description")
                             or node.get("description") or node["name"]).split())
            target_labels[node["name"]] = desc[:1000]
    ancestors = {}
    for n in rules["nodes"]:
        ancestors[n["id"]] = [name_to_id[a] for a in reversed(n.get("path", []))
                              if a in name_to_id]
    meta = {n["id"]: {"name": n["name"], "path": n.get("path", []),
                      "is_target": n.get("comparison_target", False)}
            for n in rules["nodes"]}
    all_ids = [n["id"] for n in rules["nodes"]]
    return target_labels, name_to_id, all_ids, ancestors, meta


def labels_json(rules_path=None):
    """JSON object {category_name: definition} for the target (leaf) categories,
    in the ai_classify v2.1 labels-with-descriptions format (key 1-100 chars,
    value 0-1000 chars)."""
    target_labels = load_categories(rules_path)[0]
    return json.dumps({name: (desc or name)[:1000] for name, desc in target_labels.items()},
                      sort_keys=True)


def definitions_fingerprint(labels, instructions, version):
    """Stable hash of every input that changes ai_classify's answer for a sentence
    (label names + definitions, global instructions, function version). Part of the
    result-cache key: change any of them and cached results no longer match."""
    import hashlib
    blob = json.dumps({"labels": json.loads(labels), "instructions": instructions,
                       "version": version}, sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]
