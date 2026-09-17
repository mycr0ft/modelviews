"""SysML v2 emitters for modelviews (direction 1).

Each function keeps PyML's ergonomics (lists of plain strings/tuples)
but emits SysML v2: a graphviz graph drawn in SysML v2 graphical
notation (per the OMG SysML v2.0 Language Specification, September
2025 — rules pinned from the notation reference under
~/sysml-v2-docs/language/11-graphical-notation.md) AND the equivalent
SysML v2 textual notation, validated by the sysmlpy ANTLR parser when
available.

Notation pins (reference doc, with the section):
  - corners encode def vs usage (1.1): sharp rectangle = definition,
    rounded rectangle = usage. Graphviz: shape=box vs style="rounded".
  - guillemet keyword labels are mandatory (1.5).
  - composition: filled diamond at owner (1.8) -> arrowtail=diamond,
    dir=back, arrowhead=none.
  - specializes (:>): hollow triangle at target (1.8) ->
    arrowhead=onormal.
  - connections: plain line, no arrowheads (1.8).
  - item flow direction: filled arrowhead (1.8) -> arrowhead=normal.
  - av nodes (4.1): start = filled circle, done = circle-in-ring,
    action = rounded rectangle; successions = solid arrows (4.2).
  - stv (5.1/5.2): initial = filled circle, states = rounded,
    transition label "[guard] trigger / effect".
  - use case def MUST carry subject and actors (7.1); actors connect
    with plain association lines (7.2).
  - port stubs: small squares on the part boundary (3.1) — drawn as
    HTML-table ports with square glyphs.
  - frame header "kind [ElementType] Name" (1.3) as the graph label.

The SysML v2 textual forms are the subset accepted by sysmlpy.loads
(package-wrapped): part/part def, port def, item def, connection
... connect a.p to b.q, flow ... from ... to ..., action def with
first a then b successions, state def with transition ... first ...
accept ... then ..., use case def with subject/actor.
"""
import os
import subprocess
import textwrap

import graphviz

# ── SysML v2 keyword labels (notation 1.5) ──────────────────────────
KW_PART_DEF = "«part def»"
KW_PART = "«part»"
KW_PORT = "«port»"
KW_PORT_DEF = "«port def»"
KW_ACTION = "«action»"
KW_ACTOR = "«actor»"
KW_ITEM = "«item»"
KW_USE_CASE_DEF = "«use case def»"

SYSMLPY_PYTHON = os.path.expanduser("~/sysmlpy/.venv/bin/python")


# ── validation ───────────────────────────────────────────────────────
def validate(sysml_text):
    """Parse *sysml_text* with sysmlpy (subprocess; sysmlpy venv).

    Returns (ok, message). (False, reason-for-skipping) if the venv is
    absent — never silently claims validity."""
    if not os.path.exists(SYSMLPY_PYTHON):
        return False, "sysmlpy venv not found; validation skipped"
    probe = (
        "import sysmlpy\n"
        f"text = {sysml_text!r}\n"
        "try:\n"
        "    sysmlpy.loads(text)\n"
        "    print('VALID')\n"
        "except Exception as e:\n"
        "    print('INVALID: %s: %s' % (type(e).__name__, str(e)[:400]))\n"
    )
    r = subprocess.run([SYSMLPY_PYTHON, "-c", probe],
                       capture_output=True, text=True, timeout=120)
    out = (r.stdout + r.stderr).strip()
    if "VALID" in out and "INVALID" not in out:
        return True, "parsed by sysmlpy.loads"
    return False, out[-400:]


# ── graph builders ───────────────────────────────────────────────────
def _frame(g, kind, element_type, name, label=None):
    """Diagram frame header (notation 1.3) as the graph label."""
    head = f"{kind} [{element_type}] {name}"
    if label:
        head += f" [{label}]"
    g.attr(label=f"  {head}", labelloc="t", labeljust="l",
           fontname="Courier", fontsize="13")


def _def_box(g, node_id, keyword, name, compartments=None, italic=False,
             fillcolor=None):
    """Definition: sharp-corner rectangle, guillemet + name, optional
    labeled compartments (notation 1.1, 1.5, 1.6)."""
    rows = [f"<TR><TD><B>{keyword}</B><BR/><FONT POINT-SIZE='13'>"
            + ("<I>" if italic else ""),
            name,
            ("</I>" if italic else "") + "</FONT></TD></TR>"]
    if compartments:
        for title, lines in compartments:
            rows.append("<HR/>")
            body = "<BR ALIGN='LEFT'/>".join(lines)
            rows.append(f"<TR><TD ALIGN='LEFT'><FONT POINT-SIZE='11'>"
                        f"{title}<BR ALIGN='LEFT'/>{body}"
                        f"<BR ALIGN='LEFT'/></FONT></TD></TR>")
    attrs = f' BGCOLOR="{fillcolor}"' if fillcolor else ""
    lbl = "<<TABLE BORDER='0' CELLBORDER='0' CELLSPACING='0'"
    lbl += f" CELLPADDING='4'{attrs}>" + "".join(rows) + "</TABLE>>"
    g.node(node_id, label=lbl, shape="box", style="filled",
           fillcolor="white", color="black")


def _usage_box(g, node_id, keyword, name, compartments=None):
    """Usage: rounded-corner rectangle (notation 1.1)."""
    lbl = f"{keyword}\\n{name}"
    if compartments:
        for title, lines in compartments:
            lbl += "\\n─────────────\\n" + title
            for ln in lines:
                lbl += "\\n  " + ln
    g.node(node_id, label=lbl, shape="box", style="rounded",
           fontname="Helvetica")


def _port_stub(g, pid, name, ptype, direction="inout"):
    """Port stub: small square glyph + `name : Type` label (3.1)."""
    arrow = {"in": "←", "out": "→", "inout": "↔", None: ""}[direction]
    g.node(pid, label=f"{arrow}", shape="rectangle", fixedsize="true",
           width="0.14", height="0.14", style="filled",
           fillcolor="black", fontsize="8",
           xlabel=f"{name} : {ptype}")


def _composition_edge(g, whole, part, label=None, xlabel=None):
    """Filled diamond at the OWNER end (notation 1.8)."""
    g.edge(whole, part, arrowtail="diamond", dir="back",
           arrowhead="none", xlabel=xlabel or label or "",
           fontname="Helvetica")


def _specialization_edge(g, base, derived):
    """Hollow triangle at the specializing target (notation 1.8)."""
    g.edge(derived, base, arrowhead="onormal", arrowtail="none")


def _connect(g, a, pa, b, pb, item=None, flow=False):
    """connect = plain line (1.8); flow = filled arrowhead toward the
    consuming port (3.3)."""
    g.edge(f"{a}:{pa}", f"{b}:{pb}", arrowhead="normal" if flow
           else "none", arrowtail="none", label=item or "",
           fontname="Helvetica", fontsize="10")


# ── textual builders ─────────────────────────────────────────────────
def _pkg(name, body_lines):
    ind = "\n  ".join(body_lines)
    return f"package {name} {{\n  {ind}\n}}"


# ── 1. General View: part definition tree (BDD analog) ──────────────
def part_tree(name, decompositions, parts=None, attributes=None,
              multiplicities=None, abstract=(), specializations=(),
              filename=None, format="svg"):
    """General View of a part definition hierarchy.

    decompositions : list of (whole, part) — composition (owned parts)
    specializations: list of (base, derived) — :> generalization
    attributes     : {part: [(attrname, type), ...]}
    multiplicities : {(whole, part): "4"} — rendered [n]
    abstract       : iterable of abstract part names
    """
    parts = dict(parts or {})          # name -> display type (optional)
    attributes = dict(attributes or {})
    multiplicities = dict(multiplicities or {})
    abstract = set(abstract)
    nodes = {w for w, p in decompositions} | {p for w, p in decompositions}
    nodes |= {d for b, d in specializations} | {b for b, d in specializations}
    nodes |= set(attributes)

    g = graphviz.Digraph(name, format=format, engine="dot",
                         node_attr={"fontname": "Helvetica"})
    g.attr(rankdir="TB", splines="ortho", nodesep="0.5", ranksep="0.8")
    _frame(g, "gv", "package", name, "Part Definitions")

    for n in sorted(nodes):
        comps = []
        if attributes.get(n):
            comps.append(("attributes",
                          [f"{a} : {t}" for a, t in attributes[n]]))
        _def_box(g, n, KW_PART_DEF, n, comps or None, italic=n in abstract)

    for whole, part in decompositions:
        mult = multiplicities.get((whole, part))
        _composition_edge(g, whole, part,
                          xlabel=f"[{mult}]" if mult else None)
    for base, derived in specializations:
        _specialization_edge(g, base, derived)

    # ── SysML v2 text ──
    body = []
    for n in sorted(nodes):
        pre = "abstract " if n in abstract else ""
        feats = []
        for a, t in attributes.get(n, []):
            feats.append(f"attribute {a} : {t};")
        for whole, part in decompositions:
            if whole != n:
                continue
            mult = multiplicities.get((whole, part))
            suff = f"[{mult}]" if mult else ""
            feats.append(f"part {part} : {part}{suff};")
        if feats:
            body.append(f"{pre}part def {n} {{ "
                        + " ".join(feats) + " }")
        else:
            body.append(f"{pre}part def {n};")
    for base, derived in specializations:
        body.append(f"part def {derived} :> {base};")
    text = _pkg(name, body)

    ok, msg = validate(text)
    if filename:
        g.render(filename=filename, format=format, cleanup=True)
        with open(os.path.splitext(filename)[0] + ".sysml", "w") as f:
            f.write(text + "\n")
    return {"graph": g, "sysml": text, "valid": ok, "message": msg}


# ── 2. Interconnection View (IBD analog) ─────────────────────────────
def interconnection(name, outer, parts, ports, connections, flows=(),
                    filename=None, format="svg"):
    """Interconnection View: parts wired through ports (Part 3).

    outer      : the part def being opened («part def» frame anchor)
    parts      : list of (name, type) — internal part usages
    ports      : list of (part, port, porttype, direction)
                 direction in {'in','out','inout',None}
    connections: list of (partA, portA, partB, portB) — plain connect
    flows      : list of (partA, portA, partB, portB, itemType) —
                 item flow (filled arrowhead + item label)
    """
    g = graphviz.Digraph(name, format=format, engine="dot",
                         node_attr={"fontname": "Helvetica"})
    g.attr(rankdir="LR", splines="spline", nodesep="0.6", ranksep="1.0")
    _frame(g, "iv", "part def", outer, "Internal Wiring")

    by_part = {}
    for part, port, ptype, direction in ports:
        by_part.setdefault(part, []).append((port, ptype, direction))

    for pname, ptype in parts:
        ports_here = by_part.get(pname, [])
        if ports_here:
            # port stubs: small squares on the boundary (notation 3.1),
            # as HTML-table ports so edges can anchor at the stub
            stubs = "".join(
                f"<TD PORT='{port}' WIDTH='9' HEIGHT='9' FIXEDSIZE='true'"
                f" BGCOLOR='black'></TD>"
                for port, _, _ in ports_here)
            plabels = "<BR ALIGN='LEFT'/>".join(
                f"  {port} : {ptype_}" for port, ptype_, _ in ports_here)
            lbl = ("<<TABLE STYLE='ROUNDED' BORDER='1' CELLBORDER='0' CELLSPACING='0'"
                   " CELLPADDING='4'>"
                   "<TR><TD><B>«part»</B><BR/>"
                   f"{pname} : {ptype}</TD></TR>"
                   "<HR/>"
                   "<TR><TD ALIGN='LEFT'><FONT POINT-SIZE='11'>ports"
                   f"<BR ALIGN='LEFT'/>{plabels}"
                   "<BR ALIGN='LEFT'/></FONT></TD></TR>"
                   "<TR><TD><TABLE BORDER='0' CELLBORDER='0'>"
                   f"<TR>{stubs}</TR></TABLE></TD></TR>"
                   "</TABLE>>")
            g.node(pname, label=lbl, shape="plain")
        else:
            _usage_box(g, pname, KW_PART, f"{pname} : {ptype}")

    for a, pa, b, pb in connections:
        g.edge(f"{a}:{pa}", f"{b}:{pb}", arrowhead="none",
               arrowtail="none")
    for a, pa, b, pb, item in flows:
        g.edge(f"{a}:{pa}", f"{b}:{pb}", arrowhead="normal",
               arrowtail="none", label=item, fontname="Helvetica",
               fontsize="10")

    # ── SysML v2 text ──
    body = []
    ptypes = {p: t for (p, t) in parts}
    for pname, ptype in parts:
        feats = [f"port {port} : {ptype_};" for port, ptype_, _ in
                 by_part.get(pname, [])]
        if feats:
            body.append(f"part def {ptype} {{ "
                        + " ".join(feats) + " }")
        else:
            body.append(f"part def {ptype};")
    inner = [f"part {p} : {t};" for p, t in parts]
    for a, pa, b, pb in connections:
        inner.append(f"connection connect {a}.{pa} to {b}.{pb};")
    for a, pa, b, pb, item in flows:
        inner.append(f"flow {item.lower()} : {item} from {a}.{pa} "
                     f"to {b}.{pb};")
    body.append(f"part def {outer} {{ " + " ".join(inner) + " }")
    text = _pkg(name, body)

    ok, msg = validate(text)
    if filename:
        g.render(filename=filename, format=format, cleanup=True)
        with open(os.path.splitext(filename)[0] + ".sysml", "w") as f:
            f.write(text + "\n")
    return {"graph": g, "sysml": text, "valid": ok, "message": msg}


# ── 3. Action Flow View (activity analog) ────────────────────────────
def action_flow(name, actions, dependencies, filename=None, format="svg"):
    """Action Flow View: start ●, «action» usages, done ⊙, successions.

    dependencies: list of (src, dst) — succession control flow.
    Feedback edges (cycles) are drawn but omitted from the textual
    successions (a cycle needs decision/merge to be well-formed).
    """
    g = graphviz.Digraph(name, format=format, engine="dot",
                         node_attr={"fontname": "Helvetica"})
    g.attr(rankdir="LR", splines="ortho", nodesep="0.4", ranksep="0.7")
    _frame(g, "av", "action def", name, "Action Flow")

    g.node("_start", label="", shape="circle", style="filled",
           fillcolor="black", fixedsize="true", width="0.16")
    g.node("_done", label="", shape="doublecircle", style="filled",
           fillcolor="black", fixedsize="true", width="0.18",
           peripheries="2")
    for a in actions:
        _usage_box(g, a, KW_ACTION, a)

    succ, feedback = [], []
    for s, d in dependencies:
        if s in actions and d in actions:
            g.edge(s, d, arrowhead="normal")
            succ.append((s, d))
        elif s == "_start":
            g.edge("_start", d, arrowhead="normal")
        elif d == "_done":
            g.edge(s, "_done", arrowhead="normal")
    for s, d in succ:
        if (d, s) in succ:   # cycle pair: draw, but flag for decision/merge
            feedback.append((s, d))

    # ── SysML v2 text ──
    body = [f"action {a};" for a in actions]
    for s, d in succ:
        if (s, d) not in feedback:
            body.append(f"first {s} then {d};")
    for s, _d in feedback:
        body.append(f"// feedback edge {_d} -> {s} omitted "
                    "(needs decision/merge)")
    text = _pkg(name, [f"action def {name} {{ " + " ".join(body) + " }"])

    ok, msg = validate(text)
    if filename:
        g.render(filename=filename, format=format, cleanup=True)
        with open(os.path.splitext(filename)[0] + ".sysml", "w") as f:
            f.write(text + "\n")
    return {"graph": g, "sysml": text, "valid": ok, "message": msg}


# ── 4. State Transition View (state machine analog) ─────────────────
def state_machine(name, states, transitions, filename=None, format="svg"):
    """State Transition View.

    transitions: list of (src, dst, trigger, guard, effect); any of
    trigger/guard/effect may be None. Label anatomy per 5.2:
    "[guard] trigger / effect".
    """
    g = graphviz.Digraph(name, format=format, engine="dot",
                         node_attr={"fontname": "Helvetica"})
    g.attr(rankdir="LR", splines="spline", nodesep="0.5", ranksep="1.0")
    _frame(g, "stv", "state def", name, "State Transition View")

    initial = transitions[0][0] if transitions else None
    g.node("_init", label="", shape="circle", style="filled",
           fillcolor="black", fixedsize="true", width="0.16")
    for s in states:
        _usage_box(g, s, "«state»", s)
    if initial is not None:
        g.edge("_init", initial, arrowhead="normal")

    for src, dst, trigger, guard, effect in transitions:
        parts = []
        if guard:
            parts.append(f"[{guard}]")
        if trigger:
            parts.append(trigger)
        if effect:
            parts.append(f"/ {effect}")
        g.edge(src, dst, label=" ".join(parts), fontname="Helvetica")

    # ── SysML v2 text ──
    body = [f"state {s};" for s in states]
    for i, (src, dst, trigger, guard, effect) in enumerate(transitions):
        tn = f"t{i}"
        acc = f" accept {trigger}" if trigger else ""
        body.append(f"transition {tn} first {src}{acc} then {dst};")
    text = _pkg(name, [f"state def {name} {{ " + " ".join(body) + " }"])

    ok, msg = validate(text)
    if filename:
        g.render(filename=filename, format=format, cleanup=True)
        with open(os.path.splitext(filename)[0] + ".sysml", "w") as f:
            f.write(text + "\n")
    return {"graph": g, "sysml": text, "valid": ok, "message": msg}


# ── 5. Use cases (General View, 7.1–7.4) ─────────────────────────────
def use_case(name, system, actors, use_cases, interactions,
             includes=None, filename=None, format="svg"):
    """Use cases in the General View: «use case def» boxes with
    subject and actors compartments (subject REQUIRED per 7.1),
    «actor» boxes with plain association lines (7.2)."""
    includes = includes or []
    g = graphviz.Graph(name, format=format, engine="dot",
                       node_attr={"fontname": "Helvetica"})
    g.attr(rankdir="LR", splines="spline", nodesep="0.5", ranksep="1.0")
    _frame(g, "gv", "package", name, "Use Cases")

    g.node(system, label=f"{KW_PART_DEF}\\n{system}", shape="box")
    for a in actors:
        g.node(a, label=f"{KW_ACTOR}\\n{a}", shape="box")
    for uc in use_cases:
        comps = [("subject", [system]), ("actors", list(actors))]
        _def_box(g, uc, KW_USE_CASE_DEF, uc, comps)
    for a, uc in interactions:
        g.edge(a, uc, arrowhead="none", arrowtail="none")
    for src, dst in includes:
        g.edge(src, dst, style="dashed", arrowhead="open",
               label="«include»", fontname="Helvetica")

    # ── SysML v2 text ──
    body = [f"part def {system};"]
    body += [f"// actor {a} (actors are members of use case defs)"
             for a in actors]
    for uc in use_cases:
        inner = ([f"subject {system};"]
                 + [f"actor {a};" for a in actors])
        body.append(f"use case def {uc} {{ " + " ".join(inner) + " }")
    for src, dst in includes:
        body.append(f"// {src} includes {dst}")
    text = _pkg(name, body)

    ok, msg = validate(text)
    if filename:
        g.render(filename=filename, format=format, cleanup=True)
        with open(os.path.splitext(filename)[0] + ".sysml", "w") as f:
            f.write(text + "\n")
    return {"graph": g, "sysml": text, "valid": ok, "message": msg}


# ── 6. Context diagram, SysML v2 style ──────────────────────────────
def context_diagram(system, external_systems, filename=None, format="svg",
                    engine="neato"):
    """The PyML context diagram, re-expressed per SysML v2: the system
    as a «part» usage (rounded), external systems as «part» usages,
    human actors per notation 7.2, plain connection lines (1.8)."""
    human = {"User", "user", "Customer", "customer", "Operator",
             "operator", "Patient", "Doctor"}
    g = graphviz.Graph("context", format=format, engine=engine,
                       node_attr={"fontname": "Helvetica"})
    g.attr(overlap="false", splines="true")
    _frame(g, "iv", "part def", system, "Context")
    g.node(system, label=f"{KW_PART}\\n{system}", shape="box",
           style="rounded")
    for es in external_systems:
        kw = KW_ACTOR if es in human else KW_PART
        g.node(es, label=f"{kw}\\n{es}", shape="box",
               style="rounded" if es not in human else "")
        g.edge(system, es, arrowhead="none", arrowtail="none", len="1.4")

    # ── SysML v2 text ──
    body = [f"part def {system};"]
    body += [f"part def {es};" for es in external_systems
             if es not in human]
    body += [f"// {es} is a human actor (notation 7.2)" for es
             in external_systems if es in human]
    text = _pkg(f"{system}Context", body)

    ok, msg = validate(text)
    if filename:
        g.render(filename=filename, format=format, cleanup=True)
        with open(os.path.splitext(filename)[0] + ".sysml", "w") as f:
            f.write(text + "\n")
    return {"graph": g, "sysml": text, "valid": ok, "message": msg}