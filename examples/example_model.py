"""Diagrams from actual UML/SysML metamodel objects (uml2py).

Run:  .venv/bin/python examples/example_model.py
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import model

from gen import sysml as S
from gen import uml25 as U

# ── build a real block model (no strings) ───────────────────────────
root = U.Package(name="VehicleModel")

veh = S.Block(name="Vehicle"); veh.isAbstract = True
car = S.Block(name="Car")
truck = S.Block(name="Truck")
engine = S.Block(name="Engine")
wheel = S.Block(name="Wheel")
battery = S.Block(name="Battery")
mass = S.ValueType(name="MassValue")
rpm = S.ValueType(name="RPM")

for b in (veh, car, truck, engine, wheel, battery, mass, rpm):
    root.packagedElement.append(b)

car.generalization.append(_ := U.Generalization(general=veh))
truck.generalization.append(_ := U.Generalization(general=veh))

car.ownedAttribute.append(
    U.Property(name="mass", type=mass))
car.ownedAttribute.append(
    U.Property(name="engine", type=engine, aggregation="composite"))
car.ownedAttribute.append(
    U.Property(name="wheels", type=wheel, aggregation="composite",
               lowerValue=U.LiteralInteger(value=4),
               upperValue=U.LiteralUnlimitedNatural(value=4)))
car.ownedAttribute.append(
    U.Property(name="battery", type=battery,
               aggregation="composite"))
truck.ownedAttribute.append(
    U.Property(name="axles", type=int))
engine.ownedAttribute.append(
    U.Property(name="ratedRPM", type=rpm))
engine.ownedOperation.append(U.Operation(name="start"))
engine.ownedOperation.append(U.Operation(name="stop"))
battery.ownedAttribute.append(
    U.Port(name="power", type=S.Block(name="PowerPort")))

import query
print("walk finds:", len(list(query.walk(root))), "elements;",
      len([e for e in query.walk(root)
           if isinstance(e, U.Classifier)]), "classifiers")
print("stereotypes:", model._stereo_of(veh), model._stereo_of(mass))
import derived
print("parents(car):", [p.name for p in derived.parents(car)])

class_diagram = model.class_diagram(root, filename="vehicle_class_diagram")
block_diagram = model.block_diagram(root, filename="vehicle_block_diagram")
print("class diagram nodes:",
      class_diagram.source.count("shape=plain"))
print("block diagram nodes:",
      block_diagram.source.count("shape=plain"))

# ── behavioral views from real objects ──────────────────────────────
sm = U.StateMachine(name="PowerMachine")
reg = U.Region(); sm.region.append(reg)
off, on = U.State(name="Off"), U.State(name="On")
run = U.State(name="Running")
rsub = U.Region(); run.region.append(rsub)
cruise = U.State(name="Cruise")
rini = U.Pseudostate(kind=U.PseudostateKind.initial)
rfin = U.FinalState()
rsub.subvertex.extend([rini, cruise, rfin])
rsub.transition.extend([
    U.Transition(source=rini, target=cruise),
    U.Transition(source=cruise, target=rfin),
])
ini = U.Pseudostate(kind=U.PseudostateKind.initial)
fin = U.FinalState()
reg.subvertex.extend([ini, off, on, fin, run])
pow = U.Signal(name="powerOn")
t1 = U.Transition(source=ini, target=off)
t1.trigger.append(U.Trigger(event=U.SignalEvent(signal=pow)))
t2 = U.Transition(source=off, target=on)
t2.trigger.append(U.Trigger(event=U.SignalEvent(signal=pow)))
t2.guard = U.Constraint(specification=U.OpaqueExpression(body=["v > 0"]))
t3 = U.Transition(source=on, target=run)
reg.transition.extend([t1, t2, t3])
smv = model.state_machine_view(sm, filename="vehicle_state_machine")
print("sm: bullseye/rounded/guard =",
      smv.source.count("doublecircle"),
      smv.source.count("rounded"),
      "[v > 0]" in smv.source,
      smv.source.count("cluster_"))

ucpkg = U.Package(name="RideSharing")
uc1 = U.UseCase(name="RequestRide")
uc2 = U.UseCase(name="Authenticate")
uc1.include.append(U.Include(addition=uc2))
rider = U.Actor(name="Rider")
e1 = U.Property(name="e1", type=rider)
e2 = U.Property(name="e2", type=uc1)
a = U.Association(name="uses")
a.memberEnd.extend([e1, e2])
ucpkg.packagedElement.extend([uc1, uc2, rider, a])
ucv = model.use_case_view(ucpkg, filename="vehicle_use_cases")
print("uc: ellipse/actor/include =",
      ucv.source.count("shape=ellipse"),
      ucv.source.count("actor"),
      ucv.source.count("include"))

act = U.Activity(name="Drive")
n0 = U.InitialNode()
step = U.OpaqueAction(name="accelerate")
dec = U.DecisionNode(name="atSpeed?")
fk = U.ForkNode()
fin = U.ActivityFinalNode()
act.node.extend([n0, step, dec, fk, fin])
act.edge.extend([
    U.ControlFlow(source=n0, target=step),
    U.ControlFlow(source=step, target=dec),
    U.ObjectFlow(source=dec, target=fk),
    U.ControlFlow(source=fk, target=fin),
])
avv = model.activity_view(act, filename="vehicle_activity")
print("act: diamond/bar/bullseye =",
      avv.source.count("shape=diamond"),
      avv.source.count("fixedsize"),
      avv.source.count("doublecircle"))

pk = U.Package(name="Systems")
sub = U.Package(name="Power")
comp = U.Class(name="Controller")
pk.packagedElement.extend([sub, comp])
sub.packagedElement.append(U.Class(name="Controller"))
comp2 = sub.packagedElement[0]
pk.packagedElement.append(U.Dependency(name="d1", client=[comp],
                                       supplier=[comp2]))
pkv = model.package_view(pk, filename="vehicle_packages")
print("pkg: folder/use-dep =",
      pkv.source.count("«package»"),
      pkv.source.count("«use»"))

car2 = U.Class(name="CarIBD")
eng2 = U.Class(name="Engine2")
pout = U.Port(name="pout"); pin = U.Port(name="pin")
eng2.ownedAttribute.extend([pout, pin])
part = U.Property(name="eng", type=eng2, aggregation="composite")
car2.ownedAttribute.append(part)
conn = U.Connector(name="c1")
conn.end.extend([U.ConnectorEnd(role=pout),
                 U.ConnectorEnd(role=pin)])
car2.ownedConnector.append(conn)
ibdv = model.internal_block_view(car2, filename="vehicle_ibd")
print("ibd: port stubs/anchors =",
      ibdv.source.count("FIXEDSIZE"),
      "eng:pout" in ibdv.source and "eng:pin" in ibdv.source)

# ── the same machinery over an OMG-published corpus ─────────────────
import os
dodaf = "/mnt/TBFox/DoDAFLibrary.xmi"
if os.path.exists(dodaf):
    m = model.from_xmi(dodaf)
    r = m.roots[0]
    print("DoDAF root:", r.name if hasattr(r, "name") else r)
    import xmi21
    g = model.class_diagram(r, name="DoDAF", max_nodes=22,
                            filename="dodaf_class_diagram")
    print("DoDAF diagram source lines:", len(g.source.splitlines()))