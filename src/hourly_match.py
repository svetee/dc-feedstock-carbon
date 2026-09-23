"""Pilot for research question 1: do hourly-matching rules change the emissions of
data-centre load, or only how they are reported?

Method
  Take EIA-930 hourly net generation by fuel for a balancing authority (BA). Build an
  hourly grid carbon intensity CI_h from generation shares and fuel emission factors.
  Place a flat load L (MW) in that BA and compare three accounting treatments of the
  same physical load over the same six months:

    location-based   E_loc  = sum_h L * CI_h
    annual-matched   E_ann  = 0 when a solar PPA is sized so that sum_h S_h = sum_h L
                              (GHG Protocol Scope 2 market-based method, 2015 guidance;
                              certificates matched over the year)
    hourly-matched   E_hr   = sum_h max(0, L - S_h) * CI_h
                              (proposed Scope 2 revision: certificate must match the
                              hour of consumption; unmatched hours carry the grid factor)

  where S_h is the BA's own solar generation shape scaled so the PPA covers 100 % of the
  load's energy over the period. The gap E_hr - E_ann is what annual matching lets a
  buyer leave unreported; E_loc is what the grid physically emitted to serve the load.
  This pilot does not model the marginal (consequential) effect of adding load, which is
  the next step and needs a dispatch model.

Data
  EIA Form 930, Hourly and Daily Balance for a Balancing Authority, six-month file
  July-December 2025 (data/EIA930_BALANCE_2025_Jul_Dec.csv). Public; no key needed.
  Fuel emission factors (kgCO2 per MWh generated), combustion only, illustrative
  fleet-average values with source:
    coal 1000  (EIA average US coal fleet ~1.0 t/MWh, 2023)
    gas   400  (EIA average US gas fleet ~0.4 t/MWh, 2023; CCGT ~0.37, peakers higher)
    petroleum 900 (EIA)
    other/unknown 500 (assumption; small share)
    nuclear, hydro, wind, solar, geothermal, storage 0 at the point of generation

Run: python src/hourly_match.py  -> prints table, writes figures/hourly_match.csv and .png
"""
from __future__ import annotations
import pandas as pd, numpy as np, os

CSV = "data/EIA930_BALANCE_2025_Jul_Dec.csv"
BAS = ["PJM", "ERCO", "MISO", "CISO", "SWPP", "SOCO"]
LOAD_MW = 100.0

FUEL_COLS = {
    "Net Generation (MW) from Coal": 1000.0,
    "Net Generation (MW) from Natural Gas": 400.0,
    "Net Generation (MW) from All Petroleum Products": 900.0,
    "Net Generation (MW) from Other Fuel Sources": 500.0,
    "Net Generation (MW) from Unknown Fuel Sources": 500.0,
    "Net Generation (MW) from Nuclear": 0.0,
    "Net Generation (MW) from Hydropower Excluding Pumped Storage": 0.0,
    "Net Generation (MW) from Pumped Storage": 0.0,
    "Net Generation (MW) from Solar without Integrated Battery Storage": 0.0,
    "Net Generation (MW) from Solar with Integrated Battery Storage": 0.0,
    "Net Generation (MW) from Wind without Integrated Battery Storage": 0.0,
    "Net Generation (MW) from Wind with Integrated Battery Storage": 0.0,
    "Net Generation (MW) from Battery Storage": 0.0,
    "Net Generation (MW) from Other Energy Storage": 0.0,
    "Net Generation (MW) from Unknown Energy Storage": 0.0,
    "Net Generation (MW) from Geothermal": 0.0,
}
SOLAR_COLS = ["Net Generation (MW) from Solar without Integrated Battery Storage",
              "Net Generation (MW) from Solar with Integrated Battery Storage"]


def load(ba: str) -> pd.DataFrame:
    usecols = ["Balancing Authority", "UTC Time at End of Hour"] + list(FUEL_COLS)
    df = pd.read_csv(CSV, usecols=usecols, thousands=",", low_memory=False)
    df = df[df["Balancing Authority"] == ba].copy()
    for c in FUEL_COLS:
        df[c] = pd.to_numeric(df[c], errors="coerce").clip(lower=0).fillna(0.0)
    df["gen"] = df[list(FUEL_COLS)].sum(axis=1)
    df = df[df["gen"] > 0]
    df["emis_kg"] = sum(df[c] * f for c, f in FUEL_COLS.items())
    df["ci"] = df["emis_kg"] / df["gen"]                    # kgCO2/MWh, hourly
    df["solar"] = df[SOLAR_COLS].sum(axis=1)
    return df


def run(ba: str) -> dict:
    df = load(ba)
    H = len(df); L = LOAD_MW
    e_loc = (L * df["ci"]).sum()
    solar_shape = df["solar"] / df["solar"].sum()            # shape sums to 1
    S = solar_shape * L * H                                  # scaled so sum_h S_h = L*H
    e_hr = (np.maximum(0.0, L - S) * df["ci"]).sum()
    matched_share = 1 - np.maximum(0.0, L - S).sum() / (L * H)
    return dict(ba=ba, hours=H, avg_ci=df["ci"].mean(), location_t=e_loc / 1000, annual_matched_t=0.0,
                hourly_matched_t=e_hr / 1000, hourly_matched_share=matched_share,
                ci_when_unmatched=(np.maximum(0.0, L - S) * df["ci"]).sum() / max(np.maximum(0.0, L - S).sum(), 1))


def main():
    rows = [run(b) for b in BAS]
    out = pd.DataFrame(rows)
    pd.set_option("display.width", 160)
    print(out.round({"avg_ci": 0, "location_t": 0, "hourly_matched_t": 0, "hourly_matched_share": 2, "ci_when_unmatched": 0}))
    os.makedirs("figures", exist_ok=True)
    out.to_csv("figures/hourly_match.csv", index=False)
    try:
        import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt, matplotlib.ticker
        plt.rcParams["font.family"] = "Helvetica"
        fig, ax = plt.subplots(figsize=(8, 4.2))
        x = np.arange(len(out)); w = 0.36
        ax.bar(x - w/2, out["location_t"], w, label="Location-based (what the grid emitted)", color="#5A3A28")
        ax.bar(x + w/2, out["hourly_matched_t"], w, label="Hourly-matched residual (proposed Scope 2); annual-matched = 0", color="#B5451B")
        names = {"PJM": "PJM", "ERCO": "ERCOT", "MISO": "MISO", "CISO": "CAISO", "SWPP": "SPP", "SOCO": "Southern"}
        ax.set_xticks(x); ax.set_xticklabels([names.get(b, b) for b in out["ba"]]); ax.set_ylabel("tCO$_2$, Jul–Dec 2025, 100 MW flat load", fontsize=9)
        ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v/1000:.0f}k")); ax.tick_params(labelsize=9)
        for sp in ("top", "right", "left"): ax.spines[sp].set_visible(False)
        ax.grid(axis="y", color="#D9CDBD", linewidth=0.5); ax.set_axisbelow(True)
        ax.legend(fontsize=8, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2)
        fig.tight_layout(); fig.savefig("figures/hourly_match.png", dpi=160)
        print("wrote figures/hourly_match.png")
    except ImportError:
        print("matplotlib not installed; csv written only")


if __name__ == "__main__":
    main()
