"""Direction 2 — PyMLDiagram re-imagined over the uml2py metamodel.

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


def from_xmi(path, **kw):
    """Load an XMI 2.1 file with uml2py's reader and return the model
    (roots, objects). Requires lxml in this venv."""
    import xmi21
    return xmi21.read_xmi21(path)