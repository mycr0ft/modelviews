"""Diagrams from actual UML/SysML metamodel objects (uml2py).

Run:  .venv/bin/python example_model.py
"""
import sys

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