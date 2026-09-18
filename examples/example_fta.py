"""Fault tree analysis — Madachy's PyML lineage, demonstrated.

The FTA toolkit (fault_tree_diagram, fault_tree_cutsets, the MOCUS
minimal-cut-set algorithm, and quantitative probability propagation)
comes from Ray Madachy's PyML. It is a systems-safety analysis with
tuple inputs — NOT a UML/SysML metamodel view — kept here as an
example of the assortment of diagram ideas riding along in the fork.

Input format:
  gates  : (name, "And"|"Or", [branch names])
  basics : (name, "Basic", [])            # for the plain diagram
  quantitative variant: gates as (name, type, "", [branches]) and
  basics as (name, "Basic", probability).

Known inherited quirk (documented, not fixed — lineage code):
draw_fault_tree_diagram_quantitative mutates the caller's branch
lists through aliasing when renaming nodes with probabilities, so
this example passes it fresh copies.

Run:  .venv/bin/python examples/example_fta.py
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pyml

ft = [
    ("Motor overheats", "Or",
     ["No cooling", "Overload"]),
    ("No cooling", "And",
     ["Fan failure", "Thermal cutoff fail"]),
    ("Fan failure", "Basic", []),
    ("Thermal cutoff fail", "Basic", []),
    ("Overload", "Basic", []),
]

# NOTE: the lineage FTA writes its gate images (OR_node.svg,
# AND_node.svg, ...) into the CWD and references them by bare name,
# so the rendered file must land beside them — i.e. in the CWD, not
# examples/.
g = pyml.fault_tree_diagram(ft, filename="motor_fta")
print("fta diagram: top-event mentions =", g.source.count("Motor overheat"))

cutsets = pyml.mocus(ft)
print("mocus minimal cut sets:", cutsets)
# MOCUS reduces intermediate gates to basic events: the "No cooling"
# AND gate becomes the two-event cut set {fan, cutoff}; "Overload"
# is already basic.
assert sorted(map(sorted, cutsets)) == sorted(
    [["Fan failure", "Thermal cutoff fail"], ["Overload"]]), cutsets

# quantitative pass on fresh input (see aliasing quirk above)
ftq = [(ft[0][0], "Or", "", ft[0][2]),
       (ft[1][0], "And", "", ft[1][2]),
       ("Fan failure", "Basic", 0.02),
       ("Thermal cutoff fail", "Basic", 0.001),
       ("Overload", "Basic", 0.05)]
gq = pyml.draw_fault_tree_diagram_quantitative(ftq,
                                               filename="motor_fta_quant")
print("fta quantitative: probability labels =",
      gq.source.count("p="))
assert "p=" in gq.source
print("ok")