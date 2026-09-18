"""Skateboard project — Madachy's demo, recast over real metamodel classes.

Ray Madachy's original PyML demo (skateboard_project_example.py at the
repo root) built every diagram from parallel lists of strings. This
recast builds ONE real model — Actor, UseCase, Association,
OpaqueActions, ControlFlows, an Interaction — and renders multiple
views from the same objects:

- use_case_view  : «system» context + use cases from one model (the
                   original context_diagram and use_case_diagram
                   sections were tuple-driven duplicates)
- activity_view  : Make Board / Acquire Wheels -> Assemble, plus the
                   Assemble <-> Test feedback cycle
- sequence_view  : the Ride Board scenario as messages, exercising
                   the asynchCall open-vee arrow style
- DSM (lineage)  : fed from the real ControlFlow edges, so the cycle
                   Madachy's DSM exists to expose lands as an X below
                   the diagonal — one model, two complementary views

The original's parameter DSM (Requirements -> Board Size -> Cost) is
NOT recast: "parameter influences parameter" has no UML-asserted edge
(the honesty rule), so that analysis stays tuple-level lineage.

Run:  .venv/bin/python examples/example_skateboard.py
"""
import os
import re
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pyml
import model  # bootstraps ~/uml2py onto sys.path
import gen.uml25 as U

# ── one real model: the Skateboard system ───────────────────────────
skatepkg = U.Package(name="Skateboard Project")

uc = U.UseCase(name="Ride Board")
actor = U.Actor(name="Skateboarder")
a = U.Association(name="rides")
a.memberEnd.extend([U.Property(name="skateboarder", type=actor),
                    U.Property(name="rideBoard", type=uc)])
skatepkg.packagedElement.extend([uc, actor, a])

# Build Skateboard: two parallel tasks converge on Assemble, and the
# Test <-> Assemble loop is the feedback Madachy's DSM exists to show.
act = U.Activity(name="Build Skateboard")
make = U.OpaqueAction(name="Make Board")
acquire = U.OpaqueAction(name="Acquire Wheels")
assemble = U.OpaqueAction(name="Assemble")
test = U.OpaqueAction(name="Test")
act.node.extend([U.InitialNode(), make, acquire, assemble, test,
                 U.ActivityFinalNode()])
act.edge.extend([
    U.ControlFlow(source=act.node[0], target=make),
    U.ControlFlow(source=make, target=assemble),
    U.ControlFlow(source=acquire, target=assemble),
    U.ControlFlow(source=assemble, target=test),
    U.ControlFlow(source=test, target=assemble),          # feedback
    U.ControlFlow(source=test, target=act.node[-1]),
])

# Ride Board scenario: mount, push (async), and the board's reply.
inter = U.Interaction(name="RideBoard")
boardc = U.Class(name="Skateboard")
ll_r = U.Lifeline(name="rider",
                  represents=U.Property(name="rider", type=actor))
ll_b = U.Lifeline(name="board",
                  represents=U.Property(name="board", type=boardc))
inter.lifeline.extend([ll_r, ll_b])


def _msg(name, send_ll, recv_ll, sort=None):
    m = U.Message(name=name)
    if sort is not None:
        m.messageSort = sort
    m.sendEvent = U.MessageOccurrenceSpecification(covered=send_ll)
    m.receiveEvent = U.MessageOccurrenceSpecification(covered=recv_ll)
    inter.message.append(m)
    inter.fragment.extend([m.sendEvent, m.receiveEvent])


_msg("mount", ll_r, ll_b)                                  # synchCall
_msg("push", ll_r, ll_b, U.MessageSort.asynchCall)         # open vee
_msg("rolling", ll_b, ll_r, U.MessageSort.reply)           # dashed vee

# ── views of the same model ─────────────────────────────────────────
ucv = model.use_case_view(skatepkg, filename="examples/skateboard_use_case")
print("uc: ellipse/actor/assoc =",
      ucv.source.count("ellipse"),
      ucv.source.count("«actor»"),
      "Ride Board" in ucv.source)

avv = model.activity_view(act, filename="examples/skateboard_activity")
label_id = {(q or b): nid for nid, q, b in re.findall(
    r'(n\d+) \[label=(?:"([^"]*)"|(\S+))', avv.source)}
print("activity: edges/cycle =",
      avv.source.count("->"),
      f"{label_id.get('Test')} -> {label_id.get('Assemble')}"
      in avv.source)

seqv = model.sequence_view(inter, filename="examples/skateboard_sequence")
print("sequence: actor/async-vee/sync-filled/reply/lifelines =",
      seqv.source.count("«actor»"),
      seqv.source.count("arrowhead=vee"),
      seqv.source.count("arrowhead=normal"),
      seqv.source.count("style=dashed"),
      seqv.source.count("shape=point"))

# ── DSM (lineage) derived from the real ControlFlow edges ───────────
tasks = [n.name for n in act.node if isinstance(n, U.OpaqueAction)]
deps = [(f.source.name, f.target.name) for f in act.edge
        if isinstance(f.source, U.OpaqueAction)
        and isinstance(f.target, U.OpaqueAction)]
dsm = pyml.design_structure_matrix(tasks, deps,
                                   filename="examples/skateboard_task_dsm")
src = dsm.source
rows = re.findall(r"<TR[^>]*>(.*?)</TR>", src, flags=re.S | re.I)
test_marks = None
for row in rows:
    cells = re.findall(r"<td[^>]*>(.*?)</td>", row, flags=re.S | re.I)
    if cells and cells[0].strip() == "Test":
        test_marks = cells[1:1 + len(tasks)]      # marks after the heading
        break
assert test_marks is not None, rows
xcols = [i for i, c in enumerate(test_marks) if c.strip() == "X"]
print("dsm: tasks/edges/X marks/Test-row feedback =",
      tasks, len(deps), src.count(">X<"),
      [tasks[i] for i in xcols])
assert src.count(">X<") == len(deps) == 4
assert tasks[xcols[0]] == "Assemble", test_marks   # below the diagonal
print("ok")