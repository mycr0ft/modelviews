"""Critical path method — Madachy's PyML lineage, demonstrated.

The CPM scheduler embedded in PyML is CKS's 2013 `criticalpath`
implementation (forward/backward pass, slack, critical-path
highlighting) wrapped by Ray Madachy with a graphviz renderer.
Like the FTA toolkit it is a systems-engineering analysis with tuple
inputs — not a UML/SysML metamodel view — kept here as lineage.

Input format:
  tasks       : (task name, {"Duration": number})
  dependencies: (predecessor task, successor task)

Run:  .venv/bin/python examples/example_cpm.py
"""
import io
import contextlib
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pyml

tasks = [("Design", {"Duration": 5}), ("Build", {"Duration": 8}),
         ("Test", {"Duration": 3}), ("Document", {"Duration": 2}),
         ("Ship", {"Duration": 1})]
deps = [("Design", "Build"), ("Build", "Test"), ("Build", "Document"),
        ("Test", "Ship"), ("Document", "Ship")]

buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    g = pyml.critical_path_diagram(tasks, deps,
                                   filename="examples/skate_cpm")
line = buf.getvalue().strip()
print("cpm says:", line)
assert "critical path" in line and "Design" in line
assert all(t in g.source for t, _ in tasks)
print("ok")