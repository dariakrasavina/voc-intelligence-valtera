"""
tagger.py
---------
Shared, dependency-free tagging core used by BOTH the local runner
(tests, local preview) and the Databricks job (src/classification/rule_tagging.py).

Keeping this in one place guarantees the local validation and the production
Spark run apply byte-identical rule logic. No pyspark import here.

Public API:
    load_rules(path)                    -> dict (parsed category_model.json)
    build_tagger(rules)                 -> Tagger
    Tagger.in_scope(text, attrs)        -> (bool, list[reason_terms])
    Tagger.tag(text, attrs)             -> dict {topic_id: {matched, terms}}
    ATTR_FIELDS                         -> metadata/sentence fields the rules read
"""
import json
import os

from rule_engine import CompiledNode, Context, compile_nodes

# Attribute fields referenced by the rule set (sentence + joined metadata).
# The Spark job must supply these into the per-row attrs dict.
ATTR_FIELDS = [
    "channel",          # 'call' / 'survey'
    "speaker",          # 'customer' / 'agent'
    "language",         # 'english' ...
    "powertrain",       # vehicle: 'EV' / 'HYBRID' / 'ICE'
]


def find_category_model(filename=None):
    """Locate a category-model JSON regardless of folder layout.

    `filename` may be:
      * None / ""  -> the default 'category_model.json' (v1);
      * a basename -> resolved against the known layout dirs, so a job can pass
                      'category_model_v2.json' and have executors find the copy
                      the bundle synced into shared/ (the driver's absolute path
                      won't exist on an executor, so we fall back to the basename);
      * an existing path (absolute or relative) -> used as-is.

    Files live in a track folder (classification_rule_engine/ or classification_ai/)
    while the model lives in shared/. On Databricks the bundle co-locates modules +
    shared/. Search order covers both the local repo layout and a flat cluster upload.
    """
    filename = (filename or "").strip()
    if filename and os.path.exists(filename):
        return filename                                          # explicit, present path
    base = os.path.basename(filename) if filename else "category_model.json"
    here = os.path.dirname(os.path.abspath(__file__))
    repo = os.path.dirname(here)
    candidates = [
        os.path.join(here, base),                                # flat / co-located (cluster)
        os.path.join(repo, "shared", base),                      # repo layout, sibling folder
        os.path.join(here, "shared", base),                      # shared under cwd
        os.path.join(os.getcwd(), base),
        os.path.join(os.getcwd(), "shared", base),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    raise FileNotFoundError(
        "%s not found; looked in: %s" % (base, ", ".join(candidates)))


def load_rules(path=None):
    path = find_category_model(path)
    with open(path) as f:
        return json.load(f)


def build_ancestor_map(rules):
    """category_id -> [ancestor category_ids ...] (nearest parent first).

    Node paths in the model are stored as category *names*; map those to ids so
    a leaf match can roll up to its parents, e.g. Charging - Public Charger Failure -> Battery & Charging.
    """
    name_to_id = {n["name"]: n["id"] for n in rules["nodes"]}
    ancestors = {}
    for n in rules["nodes"]:
        chain = []
        for ancestor_name in reversed(n.get("path", [])):  # nearest parent first
            aid = name_to_id.get(ancestor_name)
            if aid:
                chain.append(aid)
        ancestors[n["id"]] = chain
    return ancestors


def rule_gates(rules):
    """category_id -> [rule-bearing ancestor ids] whose own rules must ALSO match.

    A parent category's rules act as a filter on its children (vendor-compatible
    semantics). Rule-free ancestors impose no condition.
    """
    # Same test as Tagger._evaluatable: a node with no keywords lane can never match.
    has_rules = {n["id"] for n in rules["nodes"]
                 if ((n.get("lanes") or {}).get("keywords") or "").strip()}
    return {cid: [a for a in chain if a in has_rules]
            for cid, chain in build_ancestor_map(rules).items()}


class Tagger(object):
    """Applies the global scope filter and assigns categories (with roll-up)."""

    def __init__(self, rules):
        self.rules = rules
        gf = rules.get("global_filter")
        self.global_node = CompiledNode({
            "id": "global_filter", "name": gf["name"], "lanes": gf["lanes"],
        }) if gf else None

        # Compile every category node. Only rule-bearing nodes are evaluated
        # directly; rule-free parents (e.g. Battery & Charging) are populated only
        # by roll-up from a matching descendant.
        all_nodes = compile_nodes(rules["nodes"])
        self._by_id = {n.id: n for n in all_nodes}
        self._evaluatable = [n for n in all_nodes if n.keywords is not None]
        self._ancestors = build_ancestor_map(rules)
        # Parent rules filter their children : a category can
        # only match when every RULE-BEARING ancestor's own rules also match. Rule-free
        # parents (e.g. Battery & Charging) are pass-through. Set
        # "parent_rules_filter_children": false in the model to evaluate leaves alone.
        self._gates = rule_gates(rules) \
            if rules.get("parent_rules_filter_children", True) else {}

        # Category output order: all categories, so parents get their own columns
        # and counts roll up like a real category model.
        self._all_ids = [n["id"] for n in rules["nodes"]]
        self._meta = {n["id"]: {"name": n["name"], "path": n.get("path", []),
                                "is_target": n.get("comparison_target", False)}
                      for n in rules["nodes"]}

    def in_scope(self, text, attrs):
        """Global scope filter: English, customer-side sentences only."""
        if self.global_node is None:
            return True, []
        matched, terms = self.global_node.evaluate(Context(text, attrs))
        return matched, terms

    def tag(self, text, attrs):
        """Return {category_id: {terms, name, path, via}} for in-scope rows.

        Multi-label: a sentence may match several categories. Roll-up: when a
        category matches, its ancestor categories are also assigned (marked
        via='rollup') so parent counts include their children.
        Out-of-scope rows return {} (only English customer-side text is tagged).
        """
        ctx = Context(text, attrs)
        in_scope, _ = self.in_scope(text, attrs)
        if not in_scope:
            return {}

        results = {}
        # 1. Own-rule matches of every rule-bearing category, then keep only those
        #    whose rule-bearing ancestors also matched (parent rules filter children).
        own = {}
        for node in self._evaluatable:
            matched, terms = node.evaluate(ctx)
            if matched:
                own[node.id] = (node, terms)
        for cid, (node, terms) in own.items():
            if all(g in own for g in self._gates.get(cid, [])):
                results[cid] = {"terms": terms, "name": node.name,
                                "path": node.path, "via": "direct"}
        # 2. Roll up to ancestors of every directly matched category.
        for matched_id in list(results.keys()):
            for aid in self._ancestors.get(matched_id, []):
                if aid not in results:  # keep a direct match if the parent also matched
                    m = self._meta.get(aid, {})
                    results[aid] = {"terms": [], "name": m.get("name", aid),
                                    "path": m.get("path", []),
                                    "via": "rollup:%s" % matched_id}
        return results

    def topic_ids(self):
        # All categories (leaves + parents) so roll-up has columns to land in.
        return list(self._all_ids)

    def topic_meta(self):
        return {cid: dict(self._meta[cid]) for cid in self._all_ids}


def build_tagger(rules):
    return Tagger(rules)
