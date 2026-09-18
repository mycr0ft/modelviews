"""Direction 2 — modelviews re-imagined over the uml2py metamodel.

Diagrams here are views over *actual* UML 2.5.1 / SysML v1 objects
(gen.uml25 classes, gen.sysml stereotype classes such as Block and
ValueType) — not strings. Traversal uses the spec-derived semantics:

  - query.walk            : containment walk over derived unions
  - derived.parents       : Generalization parents of a Classifier
  - derived.lower/upper   : MultiplicityElement::lowerBound/upperBound
  - query.stereotypes     : «stereotype» labels from applied profiles

so a diagram edge only exists where the metamodel says the
relationship exists.

Run under .venv (graphviz) with ~/uml2py importable; for XMI corpora
add lxml (pip install lxml into .venv).
"""
import os
import sys

UML2PY = os.path.expanduser("~/uml2py")
if UML2PY not in sys.path:
    sys.path.insert(0, UML2PY)

import graphviz  # noqa: E402
from gen import sysml as S  # noqa: E402
from gen import uml25 as U  # noqa: E402
import derived  # noqa: E402
import query  # noqa: E402

PRIMS = (str, bool, int, float)


# ── helpers ──────────────────────────────────────────────────────────
def _name(e):
    return getattr(e, "name", None) or "?"


def _literal_name(v):
    return getattr(v, "name", v)


def _type_of(f):
    t = getattr(f, "type", None)
    return t


def _type_label(f):
    t = _type_of(f)
    if t is None:
        return ""
    if isinstance(t, type):
        return t.__name__
    return _name(t)


def _mult(f):
    lo, hi = derived.lower_bound(f), derived.upper_bound(f)
    if (lo, hi) in ((1, 1), (None, None), (1, None)):
        return ""
    if lo == hi:
        return f"[{lo}]"
    return f"[{lo}..{hi}]"


def _vis(f):
    return {"public": "+", "private": "-", "protected": "#",
            "package": "~"}.get(_literal_name(getattr(f, "visibility",
                                                       None))),


def _vis_prefix(f):
    v = getattr(f, "visibility", None)
    v = _literal_name(v) if v is not None else "public"
    return {"public": "+", "private": "-", "protected": "#",
            "package": "~"}.get(v, "+")


def _stereo_of(el):
    """Applied-stereotype labels, including the stereotype-as-metaclass
    pattern (a gen.sysml.Block INSTANCE carries _STEREO on its class;
    reader-applied applications live in _applied_stereotypes)."""
    labs = list(query.stereotypes(el))
    s = getattr(type(el), "_STEREO", None)
    if s and s not in labs:
        labs.append(s)
    return labs


def _kind(el):
    """Header keyword for a classifier (notation: guillemet keyword)."""
    if isinstance(el, U.Interface):
        return "«interface»"
    if isinstance(el, U.Enumeration):
        return "«enumeration»"
    if isinstance(el, (U.DataType,)) or isinstance(el, S.ValueType):
        return "«valueType»"
    stereos = _stereo_of(el)
    if stereos:
        return "«" + stereos[-1].split("::")[-1].lower() + "»"
    if isinstance(el, U.Signal):
        return "«signal»"
    return "«class»"


def _abstract(el):
    return bool(getattr(el, "isAbstract", False))


def _classifiers_in_scope(root, max_nodes):
    els = []
    for e in query.walk(root):
        if isinstance(e, U.Classifier) and not isinstance(e, (U.Association,
                                                              U.Behavior)):
            els.append(e)
        if len(els) >= max_nodes:
            break
    return els


def _classifier_label(el, compartments):
    """HTML label: guillemet header + italic-if-abstract + compartments
    (attribute/operation rows as `<TD ALIGN=LEFT>`)."""
    kw = _kind(el)
    ital = ("<I>" if _abstract(el) else "")
    ital_end = ("</I>" if _abstract(el) else "")
    rows = [f"<TR><TD><B>{kw}</B><BR/><FONT POINT-SIZE='13'>{ital}"
            f"{_name(el)}{ital_end}</FONT></TD></TR>"]
    for title, lines in compartments:
        if not lines:
            continue
        rows.append("<HR/>")
        body = "<BR ALIGN='LEFT'/>".join(f"  {ln}" for ln in lines)
        rows.append(f"<TR><TD ALIGN='LEFT'><FONT POINT-SIZE='11'>"
                    f"{title}<BR ALIGN='LEFT'/>{body}"
                    f"<BR ALIGN='LEFT'/></FONT></TD></TR>")
    return ("<<TABLE BORDER='0' CELLBORDER='0' CELLSPACING='0'"
            " CELLPADDING='4'>" + "".join(rows) + "</TABLE>>")


def _attr_lines(el, filt=None, kind_names=None):
    lines = []
    for a in el.ownedAttribute:
        if filt and not filt(a):
            continue
        mark = ""
        if kind_names and isinstance(a, kind_names):
            mark = "«port» "
        lines.append(f"{_vis_prefix(a)} {mark}{a.name}"
                     f" : {_type_label(a)} {_mult(a)}".rstrip())
    return lines


def _op_lines(el):
    return [f"{_vis_prefix(o)} {o.name}()".rstrip()
            for o in el.ownedOperation]


def _compositions(el, scope):
    out = []
    for a in el.ownedAttribute:
        if _literal_name(getattr(a, "aggregation", None)) != "composite":
            continue
        t = _type_of(a)
        if t is not None and id(t) in scope:
            out.append((a, t))
    return out


def _associations(el, scope):
    out = []
    for a in el.ownedAttribute:
        if _literal_name(getattr(a, "aggregation", None)) == "composite":
            continue
        t = _type_of(a)
        if t is None or isinstance(t, type) or t not in (U.Property,):
            pass
        if (t is not None and not isinstance(t, type)
                and id(t) in scope):
            out.append((a, t))
    return out


def _parents(el, scope):
    out = []
    try:
        for p in derived.parents(el):
            if id(p) in scope:
                out.append(p)
    except Exception:
        pass
    return out


def class_diagram(root, name=None, filename=None, format="svg",
                  max_nodes=40):
    """Class diagram from a real package/classifier object graph.

    Edges exist only where the metamodel objects say so:
    Generalization -> hollow triangle; composite aggregation -> filled
    diamond at the owner; typed attributes -> association line with
    name+multiplicity (E3 lower/upper bound semantics)."""
    els = _classifiers_in_scope(root, max_nodes)
    scope = {id(e) for e in els}
    by_name = {}
    for e in els:
        by_name.setdefault(_name(e), e)

    g = graphviz.Digraph(name or _name(root), format=format, engine="dot",
                         node_attr={"fontname": "Helvetica"})
    g.attr(rankdir="TB", splines="ortho", nodesep="0.4", ranksep="0.7")
    g.attr(label=f"  class diagram [{_name(root)}]", labelloc="t",
           labeljust="l", fontname="Courier", fontsize="13")

    for e in els:
        attrs = _attr_lines(e, kind_names=(U.Port,))
        ops = _op_lines(e)
        comps = [("attributes", attrs)]
        if isinstance(e, U.Enumeration):
            comps.append(("literals", [_name(l) for l in
                                       getattr(e, "ownedLiteral", [])]))
        comps.append(("operations", ops))
        g.node(_name(e), label=_classifier_label(e, comps), shape="plain")

    seen = set()
    for e in els:
        for p in _parents(e, scope):
            g.edge(_name(e), _name(p), arrowhead="onormal",
                   arrowtail="none")
        for a, t in _compositions(e, scope):
            g.edge(_name(e), _name(t), arrowtail="diamond", dir="back",
                   arrowhead="none",
                   xlabel=f"{a.name} {_mult(a)}".strip(),
                   fontname="Helvetica", fontsize="10")
        for a, t in _associations(e, scope):
            key = tuple(sorted((_name(e), _name(t), a.name)))
            if key in seen:
                continue
            seen.add(key)
            g.edge(_name(e), _name(t), arrowhead="none",
                   arrowtail="none",
                   xlabel=f"{a.name} {_mult(a)}".strip(),
                   fontname="Helvetica", fontsize="10",
                   style="dashed")

    if filename:
        g.render(filename=filename, format=format, cleanup=True)
    return g


def block_diagram(root, name=None, filename=None, format="svg",
                  max_nodes=40):
    """SysML v1-style block definition diagram over gen.sysml.Block
    objects: «block» headers (stereotypes from query.stereotypes) and
    parts / values / references compartments."""
    def _is_blockish(e):
        if isinstance(e, S.Block):
            return True
        for lab in _stereo_of(e):
            seg = lab.split("::")[-1].lower()
            if seg.endswith("block"):
                return True
        return False

    els = [e for e in _classifiers_in_scope(root, max_nodes)
           if _is_blockish(e)]
    scope = {id(e) for e in els}

    g = graphviz.Digraph(name or _name(root), format=format, engine="dot",
                         node_attr={"fontname": "Helvetica"})
    g.attr(rankdir="TB", splines="ortho", nodesep="0.4", ranksep="0.7")
    g.attr(label=f"  block definition diagram [{_name(root)}]",
           labelloc="t", labeljust="l", fontname="Courier", fontsize="13")

    for e in els:
        parts, values, refs = [], [], []
        for a in e.ownedAttribute:
            t = _type_of(a)
            line = (f"«port» {a.name} : {_type_label(a)} {_mult(a)}"
                    if isinstance(a, U.Port) else
                    f"{_vis_prefix(a)} {a.name} : {_type_label(a)} "
                    f"{_mult(a)}").rstrip()
            if _literal_name(getattr(a, "aggregation", None)) == "composite":
                parts.append(line)
            elif isinstance(t, (S.ValueType, U.DataType)) or (
                    t is not None and getattr(t, "name", "") == ""):
                values.append(line)
            else:
                refs.append(line)
        g.node(_name(e), label=_classifier_label(
            e, [("parts", parts), ("values", values),
                ("references", refs)]), shape="plain")

    seen = set()
    for e in els:
        for p in _parents(e, scope):
            g.edge(_name(e), _name(p), arrowhead="onormal",
                   arrowtail="none")
        for a, t in _compositions(e, scope):
            key = (_name(e), _name(t), a.name)
            if key in seen:
                continue
            seen.add(key)
            g.edge(_name(e), _name(t), arrowtail="diamond", dir="back",
                   arrowhead="none",
                   xlabel=f"{a.name} {_mult(a)}".strip(),
                   fontname="Helvetica", fontsize="10")

    if filename:
        g.render(filename=filename, format=format, cleanup=True)
    return g


# ── behavioral & SysML v1 views (model objects → graphviz) ───────────
def _id(n):
    return f"n{id(n)}"


def state_machine_view(sm, filename=None, format="svg"):
    """State machine diagram from real StateMachine/Region/State/
    Transition objects. UML notation: initial pseudostate = filled
    circle, FinalState = bullseye, state = rounded box (composite
    states become nested clusters), choice = diamond; transition
    labels are the UML anatomy "[guard] trigger / effect" with
    SignalEvent/CallEvent resolution."""
    g = graphviz.Digraph(_name(sm), format=format, engine="dot",
                         node_attr={"fontname": "Helvetica"})
    g.attr(rankdir="TB", nodesep="0.4", ranksep="0.6")
    g.attr(label=f"  state machine [{_name(sm)}]", labelloc="t",
           labeljust="l", fontname="Courier", fontsize="13")

    def _triggers(t):
        out = []
        for trg in t.trigger:
            ev = trg.event
            if ev is None:
                continue
            sig = getattr(ev, "signal", None)
            op = getattr(ev, "operation", None)
            if sig is not None:
                out.append(sig.name or "?")
            elif op is not None:
                out.append(op.name or "?")
            elif isinstance(ev, U.AnyReceiveEvent):
                out.append("all")
            else:
                out.append(type(ev).__name__)
        return " ".join(out)

    def _tlabel(t):
        parts = []
        gd = getattr(t, "guard", None)
        body = getattr(getattr(gd, "specification", None), "body", None)
        if body:
            parts.append("[" + body[0] + "]")
        sig = _triggers(t)
        if sig:
            parts.append(sig)
        eff = getattr(t, "effect", None)
        if eff is not None and getattr(eff, "name", None):
            parts.append("/ " + eff.name)
        return " ".join(parts)

    def _region(r, sub):
        for v in r.subvertex:
            if isinstance(v, U.FinalState):
                sub.node(_id(v), shape="doublecircle", style="filled",
                         fillcolor="black", width=".18", height=".18",
                         label="")
            elif isinstance(v, U.Pseudostate):
                k = getattr(v.kind, "name", None) if v.kind else None
                if k == "choice":
                    sub.node(_id(v), shape="diamond",
                             label=_name(v) or "", height=".5",
                             width=".9")
                elif k == "junction":
                    sub.node(_id(v), shape="diamond", label="",
                             width=".25", height=".25", fixedsize="true")
                elif k == "initial":
                    sub.node(_id(v), shape="circle", style="filled",
                             fillcolor="black", width=".14", height=".14",
                             label="")
                else:
                    sub.node(_id(v), shape="circle", style="filled",
                             fillcolor="black", width=".12", height=".12",
                             label="")
            elif isinstance(v, U.State):
                if v.region:
                    with sub.subgraph(name=f"cluster_s{id(v)}") as c:
                        c.attr(label=_name(v), labeljust="l",
                               style="rounded", color="gray40",
                               fontname="Helvetica", fontsize="11")
                        for sr in v.region:
                            _region(sr, c)
                else:
                    lines = []
                    for tag, b in (("entry", v.entry),
                                   ("do", getattr(v, "do", None)),
                                   ("exit", v.exit)):
                        if b is not None and getattr(b, "name", None):
                            lines.append(f"{tag} / {b.name}")
                    lbl = _name(v)
                    if lines:
                        lbl += "\\n" + "\\n".join(lines)
                    sub.node(_id(v), shape="box", style="rounded",
                             label=lbl)
        for t in r.transition:
            if t.source is None or t.target is None:
                continue
            sub.edge(_id(t.source), _id(t.target),
                     label=_tlabel(t) or None, fontname="Helvetica",
                     fontsize="10")

    for r in list(sm.region):
        _region(r, g)
    if filename:
        g.render(filename=filename, format=format, cleanup=True)
    return g


def use_case_view(pkg, filename=None, format="svg"):
    """Use-case diagram from real UseCase/Actor/Association/Include/
    Extend objects in a Package. UML notation: use case = ellipse,
    actor = «actor» rectangle (the spec-legal alternative to the
    stick figure), association = plain solid line, include/extend =
    dashed open arrow with guillemet keyword; use cases sit inside
    the system-boundary cluster, actors outside it."""
    g = graphviz.Digraph(_name(pkg), format=format, engine="dot",
                         node_attr={"fontname": "Helvetica"})
    g.attr(rankdir="LR", nodesep="0.4", ranksep="1.0")
    g.attr(label=f"  use case diagram [{_name(pkg)}]", labelloc="t",
           labeljust="l", fontname="Courier", fontsize="13")

    ucs, actors = [], []
    for e in query.walk(pkg):
        if isinstance(e, U.UseCase):
            ucs.append(e)
        elif isinstance(e, U.Actor):
            actors.append(e)
    scope = {id(e) for e in ucs + actors}

    with g.subgraph(name="cluster_boundary") as b:
        b.attr(label=f"«system» {_name(pkg)}", labeljust="l",
               style="rounded", color="black", fontname="Helvetica",
               fontsize="11")
        for uc in ucs:
            b.node(_id(uc), shape="ellipse", label=_name(uc))
    for a in actors:
        g.node(_id(a), label=f"«actor»\n{_name(a)}", shape="box",
               style="rounded")

    for e in query.walk(pkg):
        if isinstance(e, U.Association):
            ends = list(e.memberEnd) or list(e.ownedEnd)
            tps = [getattr(x, "type", None) for x in ends]
            if len(tps) == 2 and all(id(t) in scope for t in tps):
                g.edge(_id(tps[0]), _id(tps[1]), arrowhead="none",
                       arrowtail="none")
        elif isinstance(e, U.Include):
            if e.addition is not None and id(e.addition) in scope:
                g.edge(_id(derived.owner(e) or e), _id(e.addition),
                       style="dashed", arrowhead="vee",
                       label="«include»", fontname="Helvetica",
                       fontsize="10")
        elif isinstance(e, U.Extend):
            base = getattr(e, "extendedCase", None)
            ext = getattr(e, "extension", None)
            if base is not None and ext is not None and id(ext) in scope:
                g.edge(_id(ext), _id(base), style="dashed",
                       arrowhead="vee", label="«extend»",
                       fontname="Helvetica", fontsize="10")

    if filename:
        g.render(filename=filename, format=format, cleanup=True)
    return g


def activity_view(act, filename=None, format="svg"):
    """Activity diagram from a real Activity: InitialNode = filled
    circle, ActivityFinalNode = bullseye, Decision/Merge = diamond,
    Fork/Join = filled bar, actions = rounded boxes; ControlFlow and
    ObjectFlow both render as edges (object flows label themselves
    from their target object node)."""
    g = graphviz.Digraph(_name(act), format=format, engine="dot",
                         node_attr={"fontname": "Helvetica"})
    g.attr(rankdir="TB", nodesep="0.4", ranksep="0.6")
    g.attr(label=f"  activity diagram [{_name(act)}]", labelloc="t",
           labeljust="l", fontname="Courier", fontsize="13")

    def _node(n):
        if isinstance(n, U.InitialNode):
            g.node(_id(n), shape="circle", style="filled",
                   fillcolor="black", width=".14", height=".14",
                   label="")
        elif isinstance(n, (U.ActivityFinalNode, U.FlowFinalNode)):
            g.node(_id(n), shape="doublecircle", style="filled",
                   fillcolor="black", width=".18", height=".18",
                   label="")
        elif isinstance(n, (U.DecisionNode, U.MergeNode)):
            g.node(_id(n), shape="diamond", label=_name(n) or "",
                   height=".6", width="1.1")
        elif isinstance(n, (U.ForkNode, U.JoinNode)):
            g.node(_id(n), shape="box", style="filled",
                   fillcolor="black", fixedsize="true", width="1.4",
                   height=".08", label="")
        elif isinstance(n, (U.OpaqueAction, U.CallBehaviorAction,
                            U.Action)):
            lbl = _name(n) or _name(getattr(n, "behavior", None)) \
                or type(n).__name__
            g.node(_id(n), shape="box", style="rounded", label=lbl)
        elif isinstance(n, (U.StructuredActivityNode,)):
            g.node(_id(n), shape="box", style="rounded", label=_name(n))
        else:
            g.node(_id(n), shape="box", label=_name(n) or
                   type(n).__name__)

    for n in act.node:
        _node(n)
    for e in act.edge:
        if e.source is None or e.target is None:
            continue
        lbl = None
        body = getattr(getattr(e, "guard", None), "body", None)
        if body:
            lbl = "[" + body[0] + "]"
        g.edge(_id(e.source), _id(e.target),
               style="dashed" if isinstance(e, U.ObjectFlow) else None,
               label=lbl, fontname="Helvetica", fontsize="10")
    if filename:
        g.render(filename=filename, format=format, cleanup=True)
    return g


def package_view(root, filename=None, format="svg", max_nodes=60):
    """Package diagram from a real Package tree: folders with guillemet
    keywords nested as graphviz clusters, owned types as boxes, UML
    Dependency as dashed open arrow «use», PackageImport as dashed
    open arrow «import» (importing -> imported)."""
    g = graphviz.Digraph(_name(root), format=format, engine="dot",
                         node_attr={"fontname": "Helvetica"})
    g.attr(rankdir="TB", compound="true", nodesep="0.4",
           ranksep="0.7")
    g.attr(label=f"  package diagram [{_name(root)}]", labelloc="t",
           labeljust="l", fontname="Courier", fontsize="13")
    counter = [0]

    def _types_in(p):
        return [e for e in getattr(p, "packagedElement", [])
                if isinstance(e, U.Classifier)]

    def _pkgs_in(p):
        return [e for e in getattr(p, "packagedElement", [])
                if isinstance(e, U.Package)]

    def _pkg_node(p, parent):
        counter[0] += 1
        cname = f"cluster_{counter[0]}"
        with parent.subgraph(name=cname) as c:
            c.attr(label=f"«package» {_name(p)}", labeljust="l",
                   style="rounded", color="black", fontname="Helvetica",
                   fontsize="11")
            for t in _types_in(p):
                c.node(_id(t), label=f"{_kind(t)}\\n{_name(t)}",
                       shape="box", fontsize="10")
            for sp in _pkgs_in(p):
                _pkg_node(sp, c)
        return cname

    _pkg_node(root, g)
    for e in query.walk(root):
        if isinstance(e, U.Dependency):
            for cl in e.client:
                for sup in e.supplier:
                    g.edge(_id(cl), _id(sup), style="dashed",
                           arrowhead="vee", label="«use»",
                           fontname="Helvetica", fontsize="10")
        elif isinstance(e, U.PackageImport):
            imp = e.importedPackage
            owner = derived.owner(e)
            if imp is not None and owner is not None:
                g.edge(_id(owner), _id(imp), style="dashed",
                       arrowhead="vee", label="«import»",
                       fontname="Helvetica", fontsize="10")
    if filename:
        g.render(filename=filename, format=format, cleanup=True)
    return g


def internal_block_view(block, filename=None, format="svg"):
    """SysML v1 internal block diagram from a real Block: parts
    (composite-typed properties) as HTML-table boxes with their type's
    Ports as TD-PORT stubs, ownedConnectors as plain lines anchored at
    part:port (flat partWithPort connectors only)."""
    parts = [a for a in block.ownedAttribute
             if isinstance(a, U.Property) and not isinstance(a, U.Port)
             and isinstance(getattr(a, "type", None), U.Classifier)]
    scope = {id(a) for a in parts}

    g = graphviz.Digraph(_name(block), format=format, engine="dot",
                         node_attr={"fontname": "Helvetica"})
    g.attr(rankdir="LR", nodesep="0.5", ranksep="1.2", splines="ortho")
    g.attr(label=f"  internal block diagram [{_name(block)}]",
           labelloc="t", labeljust="l", fontname="Courier", fontsize="13")

    port_owner = {}   # id(port) -> part
    for a in parts:
        stubs = "".join(
            f"<TD PORT='{p.name}' WIDTH='9' HEIGHT='9' "
            f"FIXEDSIZE='true' BGCOLOR='black'></TD>"
            for p in a.type.ownedAttribute if isinstance(p, U.Port))
        for p in a.type.ownedAttribute:
            if isinstance(p, U.Port):
                port_owner[id(p)] = a
        label = (f"<<TABLE BORDER='0' CELLBORDER='1' CELLSPACING='0' "
                 f"CELLPADDING='4' STYLE='ROUNDED'>"
                 f"<TR><TD>{a.name} : {_type_label(a)}</TD></TR>"
                 f"<TR>{stubs}</TR></TABLE>>") if stubs else \
            (f"<<TABLE BORDER='0' CELLBORDER='1' CELLSPACING='0' "
             f"CELLPADDING='4' STYLE='ROUNDED'>"
             f"<TR><TD>{a.name} : {_type_label(a)}</TD></TR>"
             f"</TABLE>>")
        g.node(_name(a), label=label, shape="plain")

    for c in block.ownedConnector:
        roles = [e.role for e in c.end if e.role is not None]
        anchors = []
        for r in roles:
            if isinstance(r, U.Port) and id(r) in port_owner:
                anchors.append(f"{_name(port_owner[id(r)])}:{r.name}")
            elif isinstance(r, U.Property) and id(r) in scope:
                anchors.append(_name(r))
        if len(anchors) == 2:
            g.edge(anchors[0], anchors[1], arrowhead="none",
                   arrowtail="none")
    if filename:
        g.render(filename=filename, format=format, cleanup=True)
    return g


def from_xmi(path, **kw):
    """Load an XMI 2.1 file with uml2py's reader and return the model
    (roots, objects). Requires lxml in this venv."""
    import xmi21
    return xmi21.read_xmi21(path)