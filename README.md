# modelviews — diagrams as views of UML/SysML models

**modelviews** renders diagrams as views of real models: each emitter
returns a graphviz graph *and* — for SysML v2 — the equivalent textual
notation. It began as a fork of Ray Madachy's PyML (MIT, license terms
unchanged); the name is new because the scope grew past "Python
Modeling Language diagrams" into metamodel-driven diagramming.

## Scope

UML 2.5.1 and SysML first (v1 profiles and the v2 textual + graphical
notation). Later: UAF/UPDM (their rich color/symbol vocabularies) and
BPMN (pools, lanes, participant stick figures).

Copyright (c) 2022 Ray Madachy
Copyright (c) 2025 Jon R. Fox

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

## SysML v2 emitters (`sysml2.py`) and metamodel-backed diagrams (`model.py`)

Two new modules (2026-09, work in progress):

- **`sysml2.py`** — the PyML vocabulary re-expressed as SysML v2
  (per the OMG SysML v2.0 Language Specification, September 2025).
  Each function returns a graphviz graph drawn in SysML v2 graphical
  notation (sharp-corner definitions vs rounded usages, guillemet
  keywords, composition diamonds at the owner, hollow-triangle
  specializations, square port stubs, av/stv node shapes) **and** the
  equivalent SysML v2 textual notation, validated by the sysmlpy
  ANTLR parser when available:
  `part_tree` (General View), `interconnection` (Interconnection
  View), `action_flow` (Action Flow View), `state_machine` (State
  Transition View), `use_case`, `context_diagram`.
  Run `python example_sysml2.py` — 6/6 textual models parse.

- **`model.py`** — diagrams as views over *actual* UML 2.5.1 / SysML
  metamodel objects from [uml2py](https://github.com/mycr0ft/uml2py)
  (`gen.uml25` classes, `gen.sysml` Block/ValueType stereotypes).
  Edges exist only where the metamodel says so: Generalization ->
  hollow triangle, composite aggregation -> filled diamond at the
  owner (E3 `derived` semantics), typed attributes -> association
  lines with spec-derived multiplicities. `class_diagram` and
  `block_diagram` take a real Package root; `from_xmi` loads XMI 2.1
  corpora. Run `python example_model.py` — includes a class diagram
  over the OMG-published DoDAF Library.
