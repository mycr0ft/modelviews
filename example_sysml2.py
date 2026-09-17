"""Exercise the SysML v2 emitters with the skateboard example content.

Run:  .venv/bin/python example_sysml2.py
"""
import sys

import sysml2

results = []


def report(label, r):
    results.append((label, r))
    print(f"[{'VALID' if r['valid'] else 'INVALID'}] {label}  "
          f"-> {r['message'][:120]}")


# ── context (was pyml.context_diagram) ──────────────────────────────
r = sysml2.context_diagram("Skateboard", ["Skateboarder"],
                           filename="sysml2_skateboard_context", format="png")
report("context_diagram", r)

# ── part tree (was wbs_diagram / tree) ──────────────────────────────
r = sysml2.part_tree(
    "SkateboardModel",
    decompositions=[
        ("Skateboard", "Deck"),
        ("Skateboard", "TruckSet"),
        ("TruckSet", "Truck"),
        ("Skateboard", "WheelSet"),
        ("WheelSet", "Wheel"),
        ("Skateboard", "Bearing"),
    ],
    attributes={
        "Wheel": [("diameter", "LengthValue")],
        "Deck": [("length", "LengthValue"), ("width", "LengthValue")],
        "Skateboard": [("mass", "MassValue")],
    },
    multiplicities={("Skateboard", "WheelSet"): None,
                    ("TruckSet", "Truck"): "2",
                    ("WheelSet", "Wheel"): "4",
                    ("Skateboard", "Bearing"): "8"},
    abstract=("Deck",),
    specializations=[("Deck", "KicktailDeck")],
    filename="sysml2_skateboard_part_tree", format="png")
report("part_tree", r)

# ── interconnection (was not in PyML; ports + connections) ─────────
r = sysml2.interconnection(
    "SkateboardWiring",
    outer="ElectricSkateboard",
    parts=[("battery", "Battery"), ("motor", "MotorController"),
           ("wheelMotor", "HubMotor")],
    ports=[("motor", "throttleOut", "ThrottleSignal", "out"),
           ("wheelMotor", "driveIn", "DriveCommand", "in"),
           ("battery", "powerOut", "Power", "out"),
           ("motor", "powerIn", "Power", "in")],
    connections=[("battery", "powerOut", "motor", "powerIn")],
    flows=[("motor", "throttleOut", "wheelMotor", "driveIn",
            "DriveCommand")],
    filename="sysml2_electric_skateboard_wiring", format="png")
report("interconnection", r)

# ── action flow (was activity_diagram) ──────────────────────────────
r = sysml2.action_flow("RideBoard",
                       ["Mount", "Push", "Steer", "Brake"],
                       [("_start", "Mount"), ("Mount", "Push"),
                        ("Push", "Steer"), ("Steer", "Brake"),
                        ("Brake", "_done")],
                       filename="sysml2_skateboard_action_flow", format="png")
report("action_flow", r)

# ── state machine ───────────────────────────────────────────────────
r = sysml2.state_machine("RideStates",
                         ["coasting", "pushing", "braking"],
                         [("coasting", "pushing", "PushEvent",
                           "speed < maxSpeed", None),
                          ("pushing", "coasting", None, "footOnDeck",
                           None),
                          ("coasting", "braking", "BrakeCmd", None,
                           "applyBrake"),
                          ("braking", "coasting", None, "released",
                           None)],
                         filename="sysml2_skateboard_states", format="png")
report("state_machine", r)

# ── use case (was pyml.use_case_diagram) ────────────────────────────
r = sysml2.use_case("SkateboardUseCases", "Skateboard",
                    ["Skateboarder"],
                    ["RideBoard", "MaintainBoard"],
                    [("Skateboarder", "RideBoard"),
                     ("Skateboarder", "MaintainBoard")],
                    includes=[("RideBoard", "MaintainBoard")],
                    filename="sysml2_skateboard_use_case", format="png")
report("use_case", r)

print()
print(f"{sum(r["valid"] for _, r in results)}/"
      f"{len(results)} textual models accepted by sysmlpy.loads")