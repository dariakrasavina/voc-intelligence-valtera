"""
generate_synthetic_voc.py
-------------------------
Synthetic Voice-of-Customer data for **Valtera Motors** (a fictional automaker).
No real customer data is used anywhere in this project.

Produces JSON-lines files that land in a Unity Catalog volume, exactly the way a
contact-center / survey export would arrive:

  landing/dealers/dealers.json
  landing/customers/customers_<batch>.json     (change records -> AUTO CDC SCD1)
  landing/vehicles/vehicles.json
  landing/interactions/interactions_<yyyymmdd>.json   (one file per day)
  landing/_ground_truth/labels.json             (evaluation only, never used by models)

Story seeded in the data (what the app + Genie should surface):
  * OTA software update 4.2 shipped 2026-10-28 to Aurora EV MY2026.
    After it, "charge port door stuck" and "phantom braking" complaints spike
    for that model/year only -> a safety signal the business wants caught in days,
    not at the end-of-month vendor report.
  * One dealer (Lakeshore Valtera, Midwest) has a cluster of poor-experience calls.

Pure Python (no Spark) so it runs locally, in tests, and as a Databricks job task.
Deterministic for a given --seed.

Usage:
  python generate_synthetic_voc.py --out /Volumes/<cat>/<schema>/landing --mode backfill
  python generate_synthetic_voc.py --out ... --mode daily --day 2026-11-20
"""
import argparse
import datetime as dt
import json
import os
import random

OTA_42_DATE = dt.date(2026, 10, 28)
BACKFILL_START = dt.date(2026, 8, 22)
BACKFILL_END = dt.date(2026, 11, 19)

FIRST = ["Avery", "Jordan", "Taylor", "Morgan", "Riley", "Casey", "Jamie", "Quinn", "Reese",
         "Skyler", "Rowan", "Emerson", "Dakota", "Hayden", "Parker", "Sage", "Elliot", "Kai",
         "Logan", "Peyton", "Cameron", "Drew", "Alexis", "Blake", "Harper", "Marley", "Remy"]
LAST = ["Okafor", "Lindqvist", "Moreau", "Tanaka", "Castillo", "Novak", "Haddad", "Brennan",
        "Ivanova", "Mensah", "Sato", "Kowalski", "Delgado", "Fischer", "Nguyen", "Ortega",
        "Petrov", "Abara", "Holm", "Rossi", "Varga", "Achebe", "Lund", "Sharma", "Quintero"]
STATES = {"Midwest": ["MI", "OH", "IL", "IN", "WI", "MN"], "Northeast": ["NY", "MA", "PA", "NJ"],
          "South": ["TX", "GA", "FL", "NC", "TN"], "West": ["CA", "WA", "OR", "AZ", "CO"]}
MODELS = [  # model, powertrain, weight
    ("Aurora EV", "EV", 0.30), ("Strata EV", "EV", 0.20), ("Ridgeback", "ICE", 0.22),
    ("Ridgeback Hybrid", "HYBRID", 0.13), ("Cove", "ICE", 0.15)]
DEALER_NAMES = ["Lakeshore", "Summit", "Harbor", "Prairie", "Redwood", "Granite", "Bayview",
                "Riverbend", "Cedar Ridge", "Northgate", "Sunset", "Pinecrest", "Ironwood",
                "Blue Mesa", "Meadowbrook", "Stonebridge", "Westfield", "Copper Hill",
                "Silver Lake", "Oakmont"]
CALL_REASONS = {"chg_public_charger": "Charging", "chg_home_charger": "Charging",
                "chg_charge_port": "Vehicle Issue", "bat_range_loss": "Vehicle Issue",
                "saf_unexpected_braking": "Safety Concern", "saf_driver_assist": "Safety Concern",
                "saf_warning_lights": "Vehicle Issue", "sw_ota_failure": "Software",
                "sw_infotainment": "Software", "svc_repair_delay": "Service",
                "svc_warranty_denied": "Warranty", "svc_recall": "Recall",
                "dlr_poor_experience": "Dealer Complaint", "bil_payment_issue": "Billing",
                "pos_praise": "Feedback"}

# --------------------------------------------------------------------------
# Sentence banks per topic.  "rule" variants use the vocabulary the rule
# engine knows; "nuance" variants are paraphrases a keyword rule misses but a
# human (or an LLM) would label the same way.  That gap is the point of the
# rules-vs-AI bake-off.
# --------------------------------------------------------------------------
T = {
 "chg_public_charger": {
  "rule": ["The fast charger at the {place} failed three times before I gave up.",
           "I tried two different charging stations on the highway and neither would work.",
           "The public charger kept stopping at about {pct} percent.",
           "Every DC charger on my route was slow, it took over an hour.",
           "The charging network app said the station was available but it was not working."],
  "nuance": ["I sat at the plug-in spot by the {place} for forty minutes and got almost nothing.",
             "On my road trip I could not get a single top-up on the interstate."]},
 "chg_home_charger": {
  "rule": ["My home charger trips the breaker every night.",
           "The wall charger shows a fault light and will not start.",
           "Charging at home keeps stopping around midnight.",
           "The level 2 unit in my garage is not working since last week."],
  "nuance": ["I plug it in at the house and wake up to the same battery as when I went to bed."]},
 "chg_charge_port": {
  "rule": ["The charge port door is stuck and will not open.",
           "My charging port door won't close, so the car will not lock.",
           "The charge flap is jammed shut again this morning.",
           "The charge port door stays open after I unplug."],
  "nuance": ["That little door where you plug in will not budge, I had to pry it with my fingers.",
             "I cannot even get the cable in because the cover on the side refuses to pop."]},
 "bat_range_loss": {
  "rule": ["My range dropped from {r1} to about {r2} miles.",
           "I am losing range much faster than when I bought it.",
           "The battery drains about {pct} percent overnight while parked.",
           "I only get around {r2} miles of range in the cold."],
  "nuance": ["It used to get me to my sister's place and back, now I have to stop on the way."]},
 "saf_unexpected_braking": {
  "rule": ["The car slammed on the brakes on the highway with nothing in front of me.",
           "It braked by itself at {speed} miles an hour and the truck behind me almost hit me.",
           "I had phantom braking twice this week on the same road.",
           "Automatic braking kicked in under an overpass for no reason."],
  "nuance": ["It just stopped dead in the middle of the freeway like it saw a ghost.",
             "The car decided to stop hard on its own and my kids were thrown forward."]},
 "saf_driver_assist": {
  "rule": ["Lane keep assist pulled me toward the shoulder.",
           "Adaptive cruise control cut out without any warning.",
           "Valtera Pilot disengaged in the middle of a curve.",
           "The blind spot monitor is not working on the passenger side."],
  "nuance": ["The steering wheel yanked itself to the right when I was in the middle lane."]},
 "saf_warning_lights": {
  "rule": ["The airbag light came on and it will not go off.",
           "I keep getting a service vehicle soon warning message.",
           "A brake warning light showed up on the dash this morning.",
           "The check engine light is on again."],
  "nuance": ["There is a little red symbol of a person with a ball on the dash that will not go away."]},
 "sw_ota_failure": {
  "rule": ["The software update failed and now the screen is stuck on the logo.",
           "Since the update 4.2 the car has been acting strange.",
           "The over the air update would not install, it keeps saying error.",
           "After the update my settings were gone and it keeps rebooting."],
  "nuance": ["Ever since it downloaded that new version the whole car feels like a different car."]},
 "sw_infotainment": {
  "rule": ["The center screen freezes every time I start the car.",
           "CarPlay keeps disconnecting on every drive.",
           "The Valtera app will not connect to the car.",
           "Navigation crashes and the touchscreen goes black."],
  "nuance": ["My phone does not work as a key half the time and I am stuck in the parking lot."]},
 "svc_repair_delay": {
  "rule": ["My car has been in the shop for {weeks} weeks waiting on parts.",
           "The part is on back order and nobody can give me a date.",
           "They have no loaner and I am paying for a rental car myself.",
           "I cannot get a service appointment for another month."],
  "nuance": ["It has been sitting at the service center since the beginning of the month."]},
 "svc_warranty_denied": {
  "rule": ["They denied my warranty claim for the {part}.",
           "The dealer said the {part} is not covered under warranty.",
           "I have to pay out of pocket even though it is under warranty."],
  "nuance": ["They told me the repair is on me even though the car is barely a year old."]},
 "svc_recall": {
  "rule": ["I got a recall notice in the mail and want to know what to do.",
           "Is there a recall for the {part} on my car?",
           "The safety recall repair has not been done yet."],
  "nuance": ["I got a letter saying something on my car might be defective and needs to be fixed for free."]},
 "dlr_poor_experience": {
  "rule": ["The service advisor at the dealership was rude to me.",
           "The dealer never called me back after three messages.",
           "The salesman was pushy and lied about the price.",
           "Nobody at the service department returns my calls, they hung up on me."],
  "nuance": ["I felt completely brushed off at the store, like my problem was not worth their time."]},
 "bil_payment_issue": {
  "rule": ["I was charged twice for my monthly payment.",
           "My lease statement has a fee I do not recognize.",
           "Autopay took the wrong amount this month.",
           "Valtera Financial billed me a late fee even though I paid on time."],
  "nuance": ["The money came out of my account two times on the same day."]},
 "pos_praise": {
  "rule": ["I love this car, it is the best car I have owned.",
           "The technician did a great job, I am very happy.",
           "Honestly the car is amazing on long trips.",
           "Thank you so much, I am really impressed with the service."],
  "nuance": []},
}
FILLER_CUSTOMER = ["Hi, yes, thanks for picking up.", "Okay.", "Um, let me think.", "Yes, that is right.",
                   "It is a {my} {model}.", "I bought it about a year ago.", "Sure, one second.",
                   "I already tried turning it off and on.", "Can you help me with that?", "Got it."]
AGENT_OPEN = ["Thank you for calling Valtera Motors customer care, this is {agent}, how can I help?",
              "Valtera Motors, my name is {agent}, who do I have the pleasure of speaking with?"]
AGENT_MID = ["I am sorry to hear that, can I get the VIN of the vehicle?",
             "Thank you, let me pull up your vehicle.", "I understand, that sounds frustrating.",
             "Let me check our records for that.", "Can you tell me when this started?"]
AGENT_CLOSE = ["I have opened a case and a specialist will follow up within 48 hours.",
               "I have scheduled a service appointment and sent the details by text.",
               "I have escalated this to our technical team.", "Is there anything else I can help with?"]
CUSTOMER_CLOSE = ["Okay, thank you.", "Please call me back as soon as you can.", "Alright, bye.",
                  "I really need this fixed soon."]
SURVEY_OPEN = ["", "Overall: ", "Comments: "]
PLACES = ["mall", "grocery store", "rest stop", "hotel", "airport"]
PARTS = ["battery", "drive unit", "charge port", "infotainment screen", "brake sensor", "camera"]


def _fill(rng, s, ctx):
    return s.format(place=rng.choice(PLACES), pct=rng.choice([40, 55, 62, 70, 80]),
                    r1=rng.choice([290, 310, 320]), r2=rng.choice([180, 200, 210, 220]),
                    speed=rng.choice([45, 55, 65, 70]), weeks=rng.choice([2, 3, 4, 6]),
                    part=rng.choice(PARTS), my=ctx["year"], model=ctx["model"],
                    agent=ctx.get("agent", "Sam"))


def topic_weights(day, vehicle, dealer):
    """Base complaint mix, plus the seeded stories."""
    ev = vehicle["powertrain"] == "EV"
    w = {"chg_public_charger": 6 if ev else 0, "chg_home_charger": 4 if ev else 0,
         "chg_charge_port": 1.2 if ev else 0, "bat_range_loss": 5 if ev else 0,
         "saf_unexpected_braking": 0.8, "saf_driver_assist": 2, "saf_warning_lights": 3,
         "sw_ota_failure": 2, "sw_infotainment": 6, "svc_repair_delay": 6,
         "svc_warranty_denied": 3, "svc_recall": 2, "dlr_poor_experience": 4,
         "bil_payment_issue": 4, "pos_praise": 5}
    if vehicle["powertrain"] == "HYBRID":
        w["bat_range_loss"] = 1
    hit = vehicle["model"] == "Aurora EV" and vehicle["model_year"] == 2026 and day >= OTA_42_DATE
    if hit:
        ramp = min(1.0, (day - OTA_42_DATE).days / 7.0 + 0.3)
        w["chg_charge_port"] += 22 * ramp
        w["saf_unexpected_braking"] += 12 * ramp
        w["sw_ota_failure"] += 10 * ramp
    if dealer["dealer_name"].startswith("Lakeshore"):
        w["dlr_poor_experience"] += 14
        w["svc_repair_delay"] += 6
    return w


def pick_topics(rng, w):
    keys = [k for k in w if w[k] > 0]
    n = 1 if rng.random() < 0.72 else 2
    out = []
    while len(out) < n:
        k = rng.choices(keys, weights=[w[x] for x in keys])[0]
        if k not in out:
            out.append(k)
    return out


def topic_sentence(rng, topic, ctx):
    bank = T[topic]
    use_nuance = bank["nuance"] and rng.random() < 0.22
    s = rng.choice(bank["nuance"] if use_nuance else bank["rule"])
    return _fill(rng, s, ctx), ("nuance" if use_nuance else "rule")


def build_reference(rng):
    dealers = []
    i = 0
    for region, states in STATES.items():
        for _ in range(5):
            name = DEALER_NAMES[i]
            dealers.append({"dealer_id": "D%03d" % (i + 1), "dealer_name": "%s Valtera" % name,
                            "region": region, "state": rng.choice(states)})
            i += 1
    customers, vehicles = [], []
    for c in range(1, 3201):
        fn, ln = rng.choice(FIRST), rng.choice(LAST)
        region = rng.choice(list(STATES))
        customers.append({
            "customer_id": "C%05d" % c, "first_name": fn, "last_name": ln,
            "email": "%s.%s%d@example.com" % (fn.lower(), ln.lower(), c),
            "phone": "+1-555-%03d-%04d" % (rng.randint(100, 999), rng.randint(0, 9999)),
            "state": rng.choice(STATES[region]), "region": region,
            "loyalty_tier": rng.choices(["Standard", "Silver", "Gold"], [0.6, 0.3, 0.1])[0],
            "updated_at": "2026-08-01T00:00:00Z", "op": "UPSERT"})
        model, pt, _ = rng.choices(MODELS, weights=[m[2] for m in MODELS])[0]
        vehicles.append({
            "vin": "7VAL%s%06d" % (model[:2].upper(), c), "customer_id": "C%05d" % c,
            "model": model, "powertrain": pt, "model_year": rng.choice([2024, 2025, 2026, 2026]),
            "dealer_id": rng.choice([d["dealer_id"] for d in dealers if d["region"] == region]),
            "sold_date": "2025-%02d-%02d" % (rng.randint(1, 12), rng.randint(1, 28))})
    return dealers, customers, vehicles


def make_interaction(rng, seq, day, veh, dealer, cust):
    ctx = {"model": veh["model"], "year": veh["model_year"], "agent": rng.choice(["Sam", "Lee", "Ana", "Raj", "Mia"])}
    topics = pick_topics(rng, topic_weights(day, veh, dealer))
    labels = []
    channel = "call" if rng.random() < 0.7 else "survey"
    ts = dt.datetime.combine(day, dt.time(rng.randint(8, 19), rng.randint(0, 59), rng.randint(0, 59)))
    iid = "I%s%05d" % (day.strftime("%Y%m%d"), seq)
    if channel == "call":
        turns = [{"speaker": "agent", "text": _fill(rng, rng.choice(AGENT_OPEN), ctx)},
                 {"speaker": "customer", "text": _fill(rng, rng.choice(FILLER_CUSTOMER[:1] + FILLER_CUSTOMER[4:6]), ctx)}]
        for t in topics:
            s, kind = topic_sentence(rng, t, ctx)
            extra = _fill(rng, rng.choice(FILLER_CUSTOMER), ctx)
            turns.append({"speaker": "customer", "text": s + " " + extra if rng.random() < 0.4 else s})
            labels.append({"interaction_id": iid, "topic_id": t, "sentence": s, "variant": kind})
            turns.append({"speaker": "agent", "text": rng.choice(AGENT_MID)})
        turns.append({"speaker": "agent", "text": rng.choice(AGENT_CLOSE)})
        turns.append({"speaker": "customer", "text": rng.choice(CUSTOMER_CLOSE)})
        nps = None
        duration = rng.randint(180, 1500)
    else:
        parts = []
        for t in topics:
            s, kind = topic_sentence(rng, t, ctx)
            parts.append(s)
            labels.append({"interaction_id": iid, "topic_id": t, "sentence": s, "variant": kind})
        turns = [{"speaker": "customer", "text": rng.choice(SURVEY_OPEN) + " ".join(parts)}]
        nps = rng.randint(8, 10) if topics == ["pos_praise"] else rng.randint(0, 6)
        duration = None
    return {"interaction_id": iid, "channel": channel, "created_at": ts.isoformat() + "Z",
            "customer_id": cust["customer_id"], "vin": veh["vin"], "dealer_id": dealer["dealer_id"],
            "language": "english", "call_reason": CALL_REASONS[topics[0]],
            "duration_sec": duration, "nps_score": nps, "turns": turns}, labels


def write_jsonl(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


def generate_days(rng, days, dealers, customers, vehicles, out, per_day=(55, 80)):
    dmap = {d["dealer_id"]: d for d in dealers}
    cmap = {c["customer_id"]: c for c in customers}
    hot = [v for v in vehicles if v["model"] == "Aurora EV" and v["model_year"] == 2026]
    all_labels, total = [], 0
    for day in days:
        rows = []
        n = rng.randint(*per_day)
        for seq in range(n):
            # after OTA 4.2, affected owners call more often
            if day >= OTA_42_DATE and rng.random() < 0.22:
                veh = rng.choice(hot)
            else:
                veh = rng.choice(vehicles)
            row, labels = make_interaction(rng, seq, day, veh, dmap[veh["dealer_id"]], cmap[veh["customer_id"]])
            rows.append(row)
            all_labels.extend(labels)
        write_jsonl(os.path.join(out, "interactions", "interactions_%s.json" % day.strftime("%Y%m%d")), rows)
        total += n
    return total, all_labels


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--mode", choices=["backfill", "daily"], default="backfill")
    ap.add_argument("--day", default=None, help="YYYY-MM-DD for --mode daily")
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args(argv)
    rng = random.Random(a.seed)
    dealers, customers, vehicles = build_reference(rng)
    if a.mode == "backfill":
        write_jsonl(os.path.join(a.out, "dealers", "dealers.json"), dealers)
        write_jsonl(os.path.join(a.out, "vehicles", "vehicles.json"), vehicles)
        write_jsonl(os.path.join(a.out, "customers", "customers_0001_initial.json"), customers)
        # A later change batch: tier upgrades + email changes -> exercised by AUTO CDC.
        crng = random.Random(a.seed + 1)
        changes = []
        for c in crng.sample(customers, 150):
            c2 = dict(c, updated_at="2026-10-15T00:00:00Z")
            if crng.random() < 0.6:
                c2["loyalty_tier"] = {"Standard": "Silver", "Silver": "Gold", "Gold": "Gold"}[c["loyalty_tier"]]
            else:
                c2["email"] = c["email"].replace("@example.com", ".new@example.com")
            changes.append(c2)
        write_jsonl(os.path.join(a.out, "customers", "customers_0002_changes.json"), changes)
        days = [BACKFILL_START + dt.timedelta(d) for d in range((BACKFILL_END - BACKFILL_START).days + 1)]
        total, labels = generate_days(rng, days, dealers, customers, vehicles, a.out)
        write_jsonl(os.path.join(a.out, "_ground_truth", "labels.json"), labels)
    else:
        day = dt.date.fromisoformat(a.day) if a.day else dt.date.today()
        drng = random.Random(a.seed * 1000 + day.toordinal())
        total, labels = generate_days(drng, [day], dealers, customers, vehicles, a.out)
        write_jsonl(os.path.join(a.out, "_ground_truth", "labels_%s.json" % day.strftime("%Y%m%d")), labels)
    summary = {"mode": a.mode, "interactions_written": total, "labels": len(labels),
               "dealers": len(dealers), "customers": len(customers), "vehicles": len(vehicles)}
    print(json.dumps(summary))
    return summary


if __name__ == "__main__":
    main()
