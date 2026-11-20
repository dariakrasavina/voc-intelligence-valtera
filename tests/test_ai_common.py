"""ai_classify labels + cache key (no cluster needed)."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src", "classification"))

from ai_common import definitions_fingerprint, labels_json  # noqa: E402

MODEL = os.path.join(HERE, "..", "src", "classification", "category_model.json")


def test_labels_come_from_ai_description():
    labels = json.loads(labels_json(MODEL))
    model = json.load(open(MODEL))
    leaves = [n for n in model["nodes"] if n["comparison_target"]]
    assert len(labels) == len(leaves) == 15
    for n in leaves:
        assert labels[n["name"]] == " ".join(n["ai_description"].split())


def test_fingerprint_is_stable():
    l = labels_json(MODEL)
    assert definitions_fingerprint(l, "ins", "2.1") == definitions_fingerprint(l, "ins", "2.1")


def test_editing_a_definition_changes_the_cache_key(tmp_path):
    model = json.load(open(MODEL))
    base = definitions_fingerprint(labels_json(MODEL), "ins", "2.1")
    for n in model["nodes"]:
        if n["id"] == "chg_charge_port":
            n["ai_description"] += " Includes a charge port that is stuck closed in freezing weather."
    edited = tmp_path / "category_model.json"
    edited.write_text(json.dumps(model))
    assert definitions_fingerprint(labels_json(str(edited)), "ins", "2.1") != base


def test_instructions_or_version_change_the_cache_key():
    l = labels_json(MODEL)
    base = definitions_fingerprint(l, "ins", "2.1")
    assert definitions_fingerprint(l, "other instructions", "2.1") != base
    assert definitions_fingerprint(l, "ins", "2.2") != base
