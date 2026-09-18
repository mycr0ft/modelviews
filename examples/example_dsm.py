"""Design structure matrix — Madachy's PyML lineage, demonstrated.

The DSM (N² matrix of element dependencies) comes from Ray Madachy's
PyML. It is a systems-engineering integration/sequencing analysis
with tuple inputs — not a UML/SysML metamodel view — kept here as
lineage.

Input format:
  elements             : row/column heading names
  element_dependencies : ("input element", "output element"[, mark])

Run:  .venv/bin/python examples/example_dsm.py
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pyml

elements = ["Requirements", "Architecture", "Detailed design",
            "Implementation", "Verification"]
deps = [("Requirements", "Architecture"),
        ("Architecture", "Detailed design"),
        ("Detailed design", "Implementation"),
        ("Implementation", "Verification"),
        ("Verification", "Requirements")]  # the classic feedback loop

g = pyml.design_structure_matrix(elements, deps,
                                 filename="examples/vmodel_dsm")
src = g.source.upper()
print("dsm: html table / X marks =",
      "<TABLE" in src.upper(),
      src.count(">X<"))
assert src.count(">X<") == len(deps), src.count(">X<")
print("ok")