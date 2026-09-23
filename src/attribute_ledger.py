"""A minimal attribute ledger: one record from the meter to the claim.

The portfolio problem in section 3 of the paper. Every unit of input to a data-centre
portfolio (a MWh of electricity, a tonne of fuel, a tonne of captured CO2, a cubic metre
of water) carries an attribute: an emission or water factor, an origin, and a custody
model. Attributes change hands at every handover. The rule that keeps a chain honest is
the same at every step:

    cancel the incoming certificate; issue the outgoing one carrying the incoming serial.

This module implements that rule and the four claim types a hyperscale portfolio makes,
and refuses the two things that break chains in practice: a serial claimed twice, and a
claim asserted on an attribute whose end use does not support it.

Custody models
  mass_balance   attribute travels with the physical unit through certified sites; books
                 reconciled at each site (ISCC-type schemes)
  book_and_claim attribute travels separately from the unit through a registry; allowed
                 where physical tracking is impossible (pipeline gas, grid electricity)

Claim types (section 3 of the paper)
  ratepayer      cost of grid upgrades and price effects borne by the developer
  electricity    Scope 2 market-based claim on a MWh (hourly-matched under the 2027 rule)
  fuel           Scope 1/3 claim on a fuel attribute (RNG, certified gas, low-carbon methanol)
  water          consumptive-use claim, state reporting (Virginia from 2027)

Run `python src/attribute_ledger.py` for a worked chain: bio-methanol certified in one
country, converted to power in another, retired as a renewable-electricity claim by the
buyer, with one attempted double claim rejected.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal, Optional
import hashlib, itertools

Custody = Literal["mass_balance", "book_and_claim"]
EndUse = Literal["stored", "mineralised", "merchant", "efuel", "vented", "consumed"]
Claim = Literal["ratepayer", "electricity", "fuel", "water", "removal"]

DURABLE = {"stored", "mineralised"}
_seq = itertools.count(1)


@dataclass
class Attribute:
    serial: str
    unit: str                    # "MWh", "t_fuel", "t_CO2", "m3_water"
    quantity: float
    factor: float                # kgCO2e per unit (or litres per unit for water)
    origin: str                  # "biogenic", "fossil", "renewable", "grid", ...
    custody: Custody
    holder: str
    parent: Optional[str] = None # serial cancelled to create this one
    end_use: Optional[EndUse] = None
    hour: Optional[str] = None   # ISO hour for electricity (hourly matching)
    region: Optional[str] = None # deliverability region
    cancelled: bool = False
    claimed_as: Optional[Claim] = None


class DoubleClaim(Exception): ...
class BrokenChain(Exception): ...
class UnsupportedClaim(Exception): ...


class Ledger:
    def __init__(self):
        self.records: dict[str, Attribute] = {}

    def _serial(self, prefix: str) -> str:
        return f"{prefix}-{next(_seq):05d}-{hashlib.sha1(str(len(self.records)).encode()).hexdigest()[:6]}"

    def issue(self, prefix: str, **kw) -> Attribute:
        a = Attribute(serial=self._serial(prefix), **kw); self.records[a.serial] = a; return a

    def handover(self, serial: str, to: str, new_unit: str | None = None, new_quantity: float | None = None,
                 new_factor: float | None = None, custody: Custody | None = None, prefix: str = "X") -> Attribute:
        """Cancel `serial`, issue a successor carrying it as parent. Conversion (fuel -> MWh)
        changes unit, quantity and factor; a plain transfer keeps them."""
        p = self.records[serial]
        if p.cancelled: raise BrokenChain(f"{serial} already cancelled; cannot hand over twice")
        if p.claimed_as: raise DoubleClaim(f"{serial} already retired as a {p.claimed_as} claim")
        p.cancelled = True
        return self.issue(prefix, unit=new_unit or p.unit, quantity=new_quantity if new_quantity is not None else p.quantity,
                          factor=new_factor if new_factor is not None else p.factor, origin=p.origin,
                          custody=custody or p.custody, holder=to, parent=p.serial, hour=p.hour, region=p.region)

    def set_end_use(self, serial: str, end_use: EndUse):
        self.records[serial].end_use = end_use

    def claim(self, serial: str, kind: Claim, hour: str | None = None, region: str | None = None) -> Attribute:
        a = self.records[serial]
        if a.cancelled: raise DoubleClaim(f"{serial} was cancelled on handover; the claim lives on its successor")
        if a.claimed_as: raise DoubleClaim(f"{serial} already retired as a {a.claimed_as} claim")
        if kind == "removal" and (a.origin != "biogenic" or a.end_use not in DURABLE):
            raise UnsupportedClaim("removal needs biogenic carbon and a durable end use")
        if kind == "electricity" and a.custody == "book_and_claim":
            if hour and a.hour and hour != a.hour: raise UnsupportedClaim(f"hourly rule: certificate hour {a.hour} != consumption hour {hour}")
            if region and a.region and region != a.region: raise UnsupportedClaim(f"deliverability: {a.region} != {region}")
        a.claimed_as = kind; return a

    def chain(self, serial: str) -> list[Attribute]:
        out = []; a = self.records[serial]
        while a:
            out.append(a); a = self.records.get(a.parent) if a.parent else None
        return list(reversed(out))

    def audit(self, serial: str) -> str:
        return "\n".join(f"  {'[cancelled]' if a.cancelled else '[live]     '} {a.serial:26} {a.holder:22} {a.quantity:9.1f} {a.unit:7} factor {a.factor:7.1f}  {a.origin:9} {a.custody:14}"
                         f"{(' end_use=' + a.end_use) if a.end_use else ''}{(' CLAIMED:' + a.claimed_as) if a.claimed_as else ''}" for a in self.chain(serial))


if __name__ == "__main__":
    L = Ledger()
    # 1. Producer in country A certifies a batch of bio-methanol (sustainability proof, mass balance).
    batch = L.issue("SP", unit="t_fuel", quantity=100.0, factor=300.0, origin="biogenic", custody="mass_balance", holder="Producer (country A)")
    # 2. Shipped to the converter in country B: proof cancelled, successor issued with the parent serial.
    at_plant = L.handover(batch.serial, to="Methanol-to-power plant (country B)", prefix="SP")
    # 3. Converted to electricity: 100 t -> 286 MWh at the plant's yield; the fuel footprint is carried per MWh.
    mwh = 100.0 * 2.86; power = L.handover(at_plant.serial, to="Certificate issuer (country B)", new_unit="MWh", new_quantity=mwh,
                                            new_factor=300.0 * 100.0 / mwh, custody="book_and_claim", prefix="REC")
    power.hour = "2026-03-01T14:00"; power.region = "SG"
    # 4. Buyer retires the certificate against consumption in the same hour and region.
    L.claim(power.serial, "electricity", hour="2026-03-01T14:00", region="SG")
    print("Chain, bio-methanol to retired electricity claim:"); print(L.audit(power.serial))
    # 5. The producer tries to sell the original proof a second time.
    try:
        L.handover(batch.serial, to="Second buyer")
    except BrokenChain as e:
        print("\nRejected:", e)
    # 6. Captured CO2 from fossil methanol offered as a removal credit.
    co2 = L.issue("CO2", unit="t_CO2", quantity=130.0, factor=1000.0, origin="fossil", custody="mass_balance", holder="Plant"); L.set_end_use(co2.serial, "stored")
    try:
        L.claim(co2.serial, "removal")
    except UnsupportedClaim as e:
        print("Rejected:", e)
    # 7. Hourly rule: a certificate from a different hour cannot back the claim.
    off = L.issue("REC", unit="MWh", quantity=1.0, factor=0.0, origin="renewable", custody="book_and_claim", holder="Buyer", hour="2026-03-01T02:00", region="PJM")
    try:
        L.claim(off.serial, "electricity", hour="2026-03-01T14:00", region="PJM")
    except UnsupportedClaim as e:
        print("Rejected:", e)
