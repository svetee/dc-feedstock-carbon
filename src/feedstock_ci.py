"""Carbon intensity of data-centre power from a low-carbon liquid feedstock.

Worked case: methanol is reformed on site, the CO2 is captured before combustion,
the hydrogen runs a fuel cell. The electricity's carbon intensity (kgCO2e per MWh,
well-to-plug) depends on three things the power contract has to state:

  1. where the methanol's carbon came from (fossil, biogenic, or a closed loop),
  2. where the captured CO2 goes (its "fate"),
  3. who holds the claim on the captured tonne (the power buyer or the CO2 buyer).

Rules implemented
  A  Exclusivity: a captured tonne is claimed once. The electricity keeps the claim
     only if the CO2 buyer has not taken it in contract.
  B  Fate follows the tonne: only durable fates (geological storage, mineralisation)
     keep carbon out of the air. Merchant use, fuel synthesis and venting do not.
  C  Biogenic CO2 is reported separately. A removal is a separate product; it is never
     netted into the buyer's Scope 2 figure (no negative electricity).
  D  Capture rate and parasitic load are inputs to be measured, never assumed at 100 %.

Method and standards
  Product carbon footprint boundary per ISO 14067:2018 (cradle-to-gate for the fuel,
  gate-to-plug for the conversion). Buyer's electricity figure per GHG Protocol Scope 2
  Guidance (2015), market-based method. Biogenic CO2 treatment per GHG Protocol
  Corporate Standard, Appendix B (report outside the scopes). Well-to-tank fuel factors
  are illustrative defaults with the source named next to each; replace them with
  measured or certified values for a real site.

All inputs are parameters. Run `python src/feedstock_ci.py` to print the table and
write figures/feedstock_ci.csv. Nothing here is a real site's number.
"""
from __future__ import annotations
from dataclasses import dataclass
import csv, os

# ----------------------------------------------------------------------------
# Physical constants (stoichiometry and heating value)
# ----------------------------------------------------------------------------
CO2_PER_T_MEOH_T = 44.01 / 32.04          # t CO2 per t methanol on full oxidation = 1.374
MEOH_LHV_MWH_PER_T = 19.9 / 3.6           # 19.9 GJ/t LHV (IEA / Methanol Institute) = 5.53 MWh_th/t


@dataclass
class Plant:
    """Conversion plant parameters. Defaults are engineering ranges, not a vendor's numbers."""
    electrical_efficiency_lhv: float = 0.55   # net electric output / fuel LHV. Reforming + SOFC systems: ~0.50-0.60 net.
    capture_rate: float = 0.95                # share of reformed CO2 captured. Independent technical reviews expect 0.95-0.99, never 1.0.
    parasitic_share: float = 0.06             # share of gross output consumed by capture, compression, liquefaction.

    @property
    def mwh_per_t_meoh(self) -> float:
        return MEOH_LHV_MWH_PER_T * self.electrical_efficiency_lhv * (1 - self.parasitic_share)


@dataclass
class Feedstock:
    name: str
    wtt_kg_per_t_meoh: float   # well-to-tank footprint of producing and delivering 1 t methanol, kgCO2e
    biogenic: bool             # carbon in the molecule is biogenic (or looped)
    source: str


FEEDSTOCKS = [
    Feedstock("Grey methanol (natural gas)", 650.0, False,
              "IEA Innovation Outlook: Renewable Methanol (2021), fossil methanol ~0.6-0.7 tCO2e/t WtT excl. combustion"),
    Feedstock("Bio-methanol (waste biomass)", 300.0, True,
              "IEA (2021) range for biomass-based methanol; RED III Annex VI default-type value, illustrative"),
    Feedstock("E-methanol (renewable H2 + captured CO2, closed loop)", 100.0, True,
              "IEA (2021) low end for renewable e-methanol; loop losses ~5 % per pass added below"),
]

# Fate: (durable, description)
FATES = {
    "vented":     (False, "released to air"),
    "merchant":   (False, "sold for food, greenhouse, dry ice (short cycle)"),
    "efuel":      (False, "sold as e-fuel feedstock, burned later elsewhere"),
    "mineralised":(True,  "locked into concrete or aggregates"),
    "stored":     (True,  "geological storage"),
}


def electricity_ci(fs: Feedstock, plant: Plant, fate: str, power_holds_claim: bool, loop: bool = False):
    """Return dict with kgCO2e/MWh for the buyer's electricity and the separate removal line.

    Formula (per tonne of methanol, then divided by MWh produced):
      combustion_equivalent = CO2_PER_T_MEOH_T * 1000                      [kg, what full oxidation releases]
      captured   = combustion_equivalent * capture_rate
      escaped    = combustion_equivalent * (1 - capture_rate)
      fossil case:
        electricity_kg = WtT + escaped + (captured if not (durable and power_holds_claim) else 0)
        removal_kg     = 0
      biogenic case (Rule C):
        electricity_kg = WtT + 0 (biogenic escaped CO2 reported outside scopes)
        removal_kg     = captured if durable and power_holds_claim else 0   [separate product]
      loop case: WtT already includes capture energy; add 5 % make-up per pass on the WtT.
    """
    durable, _ = FATES[fate]
    comb = CO2_PER_T_MEOH_T * 1000.0
    captured = comb * plant.capture_rate
    escaped = comb * (1 - plant.capture_rate)
    wtt = fs.wtt_kg_per_t_meoh * (1.05 if loop else 1.0)
    if fs.biogenic:
        elec_kg = wtt
        removal_kg = captured if (durable and power_holds_claim) else 0.0
        biogenic_reported = escaped + (0.0 if (durable and power_holds_claim) else captured)
    else:
        credit = captured if (durable and power_holds_claim) else 0.0
        elec_kg = wtt + escaped + captured - credit
        removal_kg = 0.0
        biogenic_reported = 0.0
    mwh = plant.mwh_per_t_meoh
    return dict(electricity=elec_kg / mwh, removal=removal_kg / mwh, biogenic_outside_scopes=biogenic_reported / mwh, mwh_per_t=mwh)


# ----------------------------------------------------------------------------
# The captured tonne as a product: value per MWh of electricity by fate.
# Prices are illustrative ranges with the source next to each; a real site uses its
# offtake contract. Value and claim are separate: Rule A decides who holds the claim.
# ----------------------------------------------------------------------------
COPRODUCT = {
    # fate: (low, high USD per t CO2 received by the plant; negative = plant pays), durable, source
    "merchant":     (100.0, 250.0, False, "Merchant liquid CO2, food/industrial grade, Asian and US spot ranges; IEA 'Putting CO2 to Use' (2019) for market size"),
    "efuel":        (50.0, 150.0, False, "Biogenic or point-source CO2 offered to e-fuel producers; developer term sheets 2024-26, illustrative"),
    "mineralised":  (0.0, 60.0, True, "Carbonated aggregate and concrete curing: CO2 taken at or near zero; value comes from the durable-removal claim if biogenic (see below)"),
    "stored":       (-50.0, -20.0, True, "Geological storage is a cost: transport and injection fee, US Gulf Coast and North Sea ranges"),
}
REMOVAL_CREDIT = (100.0, 300.0)   # USD per t, durable removal (mineralisation) with biogenic carbon; 2025 CDR offtake ranges, illustrative


def coproduct_value(plant: Plant, fs: Feedstock):
    """USD per MWh of electricity from selling the captured CO2 by fate, plus the separate
    removal-credit value where the fate is durable and the carbon biogenic.
        t_per_mwh = CO2_PER_T_MEOH_T * capture_rate / mwh_per_t_meoh
        value_per_mwh = price_per_t * t_per_mwh
    """
    t_per_mwh = CO2_PER_T_MEOH_T * plant.capture_rate / plant.mwh_per_t_meoh
    rows = []
    for fate, (lo, hi, durable, src) in COPRODUCT.items():
        credit = (REMOVAL_CREDIT[0] * t_per_mwh, REMOVAL_CREDIT[1] * t_per_mwh) if (durable and fs.biogenic) else (0.0, 0.0)
        rows.append(dict(fate=fate, t_co2_per_mwh=t_per_mwh, product_usd_per_mwh=(lo * t_per_mwh, hi * t_per_mwh), removal_usd_per_mwh=credit,
                         durable=durable, power_claim_if_sold=(not durable) or False, source=src))
    return rows


REFERENCE = {
    "Singapore grid, operating margin (EMA 2023 GEF, direct)": 417.0,   # EMA published grid emission factor, kgCO2/MWh
    "Gas CCGT, well-to-plug (illustrative)": 500.0,                       # ~370 direct + upstream gas at ~2 % methane loss
}


def main():
    plant = Plant()
    rows = []
    cases = [
        (FEEDSTOCKS[0], "merchant", True,  False),
        (FEEDSTOCKS[0], "stored",   True,  False),
        (FEEDSTOCKS[0], "stored",   False, False),
        (FEEDSTOCKS[0], "mineralised", True, False),
        (FEEDSTOCKS[1], "vented",   True,  False),
        (FEEDSTOCKS[1], "stored",   True,  False),
        (FEEDSTOCKS[1], "stored",   False, False),
        (FEEDSTOCKS[2], "efuel",    True,  True),
    ]
    print(f"{'Feedstock':52} {'CO2 fate':12} {'Claim':8} {'Elec kg/MWh':>12} {'Removal':>9} {'Biogenic*':>10}")
    for fs, fate, claim, loop in cases:
        r = electricity_ci(fs, plant, fate, claim, loop)
        who = "power" if claim else "CO2 buyer"
        print(f"{fs.name:52} {fate:12} {who:8} {r['electricity']:12.0f} {r['removal']:9.0f} {r['biogenic_outside_scopes']:10.0f}")
        rows.append(dict(feedstock=fs.name, fate=fate, claim_holder=who, electricity_kg_per_mwh=round(r['electricity']),
                         removal_kg_per_mwh=round(r['removal']), biogenic_outside_scopes=round(r['biogenic_outside_scopes'])))
    print("* biogenic CO2 reported outside the scopes (GHGP Corporate Standard, App. B); not netted into the electricity figure.")
    print(f"\nPlant: {plant.mwh_per_t_meoh:.2f} MWh/t methanol at {plant.electrical_efficiency_lhv:.0%} LHV, "
          f"{plant.capture_rate:.0%} capture, {plant.parasitic_share:.0%} parasitic.")
    for k, v in REFERENCE.items():
        print(f"Reference  {k}: {v:.0f}")
    os.makedirs("figures", exist_ok=True)
    with open("figures/feedstock_ci.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
    print("\nCaptured CO2 as a product, USD per MWh of electricity (illustrative price ranges):")
    for fs in (FEEDSTOCKS[0], FEEDSTOCKS[1]):
        print(f"  {fs.name}:  {CO2_PER_T_MEOH_T * plant.capture_rate / plant.mwh_per_t_meoh:.2f} t CO2 per MWh")
        for r in coproduct_value(plant, fs):
            lo, hi = r["product_usd_per_mwh"]; clo, chi = r["removal_usd_per_mwh"]
            print(f"    {r['fate']:12} product {lo:6.0f} to {hi:5.0f} $/MWh   removal credit {clo:4.0f} to {chi:4.0f} $/MWh   durable={r['durable']}")


if __name__ == "__main__":
    main()
