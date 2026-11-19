"""Unit tests for the rule engine + Valtera category model.

Run:  python -m pytest tests -q      (no Spark, no cluster)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src", "classification"))

from rule_engine import CompiledNode, Context  # noqa: E402
from tagger import build_tagger, load_rules  # noqa: E402

CUST = {"speaker": "customer", "language": "english", "channel": "call"}


def lane(keywords, text, and_="", not_="", attrs=None):
    node = CompiledNode({"id": "t", "name": "t",
                         "lanes": {"keywords": keywords, "and": and_, "and2": "", "not": not_}})
    return node.evaluate(Context(text, attrs or {}))[0]


# ---- rule language ---------------------------------------------------------
def test_implicit_or_and_phrase():
    assert lane('charger, "charge port"', "the charge port is stuck")
    assert not lane('"charge port"', "the port charge is stuck")


def test_wildcard_and_and_lane():
    assert lane("fast charg*", "the fast charging failed", and_="fail*")
    assert not lane("fast charg*", "fast charging was fine", and_="fail*")


def test_not_lane_excludes():
    assert not lane("love", "I would love to know why", not_='"would love"')
    assert lane("love", "I love it", not_='"would love"')


def test_proximity():
    assert lane('"charging station"~2', "the charging public station was down")
    assert not lane('"charging station"~1', "charging at the far away station")


def test_attribute_predicate():
    assert lane("*", "anything", and_="speaker:customer", attrs={"speaker": "customer"})
    assert not lane("*", "anything", and_="speaker:customer", attrs={"speaker": "agent"})


# ---- Valtera taxonomy --------------------------------------------------------
TAGGER = build_tagger(load_rules(os.path.join(HERE, "..", "src", "classification", "category_model.json")))


def direct(text, attrs=CUST):
    return {k for k, v in TAGGER.tag(text, attrs).items() if v["via"] == "direct"}


def test_safety_braking():
    assert "saf_unexpected_braking" in direct("The car slammed on the brakes with nothing in front of me.")


def test_charge_port():
    assert "chg_charge_port" in direct("The charge port door is stuck and will not open.")


def test_rollup_to_parent():
    tags = TAGGER.tag("The charge port door is stuck and will not open.", CUST)
    assert tags["battery_charging"]["via"].startswith("rollup:")


def test_agent_side_out_of_scope():
    assert direct("The fast charger failed.", dict(CUST, speaker="agent")) == set()


def test_multilabel():
    assert {"sw_ota_failure", "sw_infotainment"} <= direct("Since the update 4.2 the screen keeps freezing.")


def test_filler_matches_nothing():
    for s in ["Okay.", "Um, let me think.", "Yes, that is right.", "I would love to know why."]:
        assert direct(s) == set(), s


def test_every_leaf_has_ai_description_and_weight():
    for n in load_rules(os.path.join(HERE, "..", "src", "classification", "category_model.json"))["nodes"]:
        if n["is_leaf"]:
            assert n["ai_description"] and "escalation_weight" in n
