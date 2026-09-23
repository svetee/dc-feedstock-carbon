# Who pays for the electrons? Carbon, custody and the missing measurement layer under AI infrastructure

*Svenja Telle · September 2026 · Working paper. Code and data in this repository.*

## Summary

Frontier AI is being built on power that does not yet exist. Data centres arrive in two to three years; the generation and transmission to serve them take five to ten. In the gap, the load is served by whatever the grid already has, and the bill for upgrades lands on a rate base that did not ask for them. The largest AI developers have responded with pledges: to pay for grid upgrades, to bring new generation online, to cover the price effects their load causes, to run on clean power. None of the pledges I have read names a methodology, a data source or an auditor. That is not a criticism of the pledges. It is the gap this paper is about.

I make three arguments, drawn from two years of building carbon-accounting and certification systems for hydrogen, fuels and, most recently, on-site power for data centres in Asia.

1. **At the site, the carbon intensity of "low-carbon" power is a contract term, not a property of the technology.** A worked case with a methanol-to-power unit and CO₂ capture shows the same plant producing electricity at 250 or 700 kgCO₂e/MWh depending on three clauses: where the carbon came from, where the captured CO₂ goes, and who holds the claim on it.
2. **Across a portfolio, the accounting problem is a chain-of-custody problem.** Fuel, electricity and CO₂ attributes cross borders, registries and standards. The chain breaks at the handovers, and the fix is one record from meter to claim, not a better spreadsheet.
3. **The rules that will decide who pays are being written now, without the measurement to apply them.** A pilot on public hourly grid data shows that a solar PPA sized to 100 % of a data centre's annual energy leaves 55 to 65 % of its location-based emissions unmatched hour by hour. Under the current standard that load reports zero. Under the standard expected in 2027 it does not. The difference is the size of the policy question.

The paper ends with the research I propose to do next: measuring the societal cost of compute load, and testing which market mechanisms make AI infrastructure fund grid resilience rather than draw on it.

---

## 1. Load before generation

Three facts frame the problem.

**Large loads have become a rate class.** By May 2026, 23 US states had approved at least one large-load tariff and seven more were pending. Several now carry statutory cost-bearing terms: minimum contract lengths of 12 to 14 years, take-or-pay on 60 to 85 % of contracted demand, collateral of the order of US$1.5 million per MW. In June 2026 FERC issued show-cause orders to six regional grid operators on how loads above 50 MW interconnect and who pays for the network upgrades they trigger. Who pays is being decided docket by docket.

**The carbon accounting standard is changing underneath the pledges.** The GHG Protocol's Scope 2 revision, expected to be final in 2027, proposes that a certificate can only back a market-based claim if it matches the hour of consumption and comes from a deliverable region. Hourly certificates already exist (PJM-GATS since 2023, M-RETS). The Protocol's own consultation text says the hourly-matched inventory will usually be higher than the annually matched one unless clean attributes are procured for every hour. Every AI data centre being financed today will report under the new rule for most of its life.

**The pledges have no measurement layer.** "Cover the price effects our load causes" requires an attribution of wholesale and retail price movements to a specific load, using interconnection cost studies, PUC dockets and market data. "Match our needs with new generation" requires a definition of match: annual, capacity or hourly. "Pay for the upgrades" requires an allocation of shared network costs. None of this exists as a method, which means each pledge will be honoured in the currency the pledging party chooses.

## 2. At the site: carbon intensity is a contract term

Consider a data centre that wants firm, on-site, low-carbon power and chooses a liquid fuel: methanol, reformed on site, with the CO₂ captured before combustion and the hydrogen run through a fuel cell. Several such units are in development in Asia, including one I have advised on the accounting for. The technology is three known pieces: a reformer that traps CO₂ in solution, a fuel cell, and a heat loop. The engineering question is capture rate and parasitic load. The accounting question is harder.

The electricity's carbon intensity, in kilograms of CO₂e per MWh from well to plug, depends on:

- **Origin of the carbon.** Fossil methanol carries a well-to-tank footprint of roughly 650 kg per tonne and fossil carbon in the molecule. Bio-methanol carries a smaller footprint and biogenic carbon. E-methanol in a closed loop carries only the energy of making it.
- **Fate of the captured CO₂.** Only durable fates keep the tonne out of the air: geological storage, mineralisation into concrete. Sale to a beverage bottler, sale as e-fuel feedstock, or venting all return the carbon within months. In accounting terms those three are the same as not capturing.
- **Who holds the claim.** A captured tonne can be claimed once. If the CO₂ buyer takes the claim (as a removal credit, say), the electricity is accounted as if the CO₂ had been released.

Four rules follow, and I have found each of them contested in practice:

| Rule | Statement | Where it is usually broken |
|---|---|---|
| A. Exclusivity | The captured tonne is claimed by the power *or* the CO₂ buyer, by contract, never both | Power contract promises "decarbonised" MWh while the CO₂ offtake contract sells credits |
| B. Fate follows the tonne | Credit only for durable fates | Merchant CO₂ sales counted as abatement |
| C. Biogenic separate | Biogenic CO₂ reported outside the scopes; a removal is a separate product, never netted into the buyer's Scope 2 | "Negative" electricity figures offered to the buyer |
| D. Measure, do not assume | Capture rate and parasitics are measured inputs | 100 % capture in the model; engineering reviews expect 95–99 % |

`src/feedstock_ci.py` implements these rules on stoichiometry (1.374 t CO₂ per t methanol on full oxidation), a stated conversion efficiency, capture rate and parasitic share, with each fuel factor sourced and marked illustrative. The output for one plant configuration:

| Feedstock | CO₂ fate | Claim held by | Electricity, kgCO₂e/MWh | Removal, separate | 
|---|---|---|---|---|
| Fossil methanol | sold (merchant) | power | **708** | 0 |
| Fossil methanol | stored | power | **251** | 0 |
| Fossil methanol | stored | CO₂ buyer | **708** | 0 |
| Bio-methanol | vented | power | **105** | 0 |
| Bio-methanol | stored | power | **105** | 457 |
| E-methanol, closed loop | returns as fuel | power | **37** | 0 |

For reference, Singapore's published grid factor is 417 and a gas combined-cycle plant is about 500 well-to-plug. The point of the table is not the numbers, which move with the plant's efficiency and the fuel factors. It is that rows one and three are the same physical plant. What separates 251 from 708 is a clause in the CO₂ offtake agreement. A buyer signing a PPA for "low-carbon" power from such a unit is signing for a range until the fate and the claim are fixed in writing.

The same logic applies to every low-carbon feedstock now being offered to data centres: certified natural gas, renewable natural gas under book-and-claim, gas with post-combustion capture, hydrogen blends. In each case the carbon intensity the buyer may report depends on custody rules and claim rules more than on the molecule.

## 3. Across the portfolio: custody

Now follow the molecule across a border. In the Asian case the bio-methanol is made from waste biomass in one country, shipped to another, converted to power, and the renewable attribute is turned into a certificate the data-centre buyer retires. There are at least two readings of that chain, with two or three handovers each, and the rule at every handover is the same: cancel the incoming certificate, issue the outgoing one with the incoming serial on it. The place chains break is the first handover, where a producer keeps the sustainability proof and sells it to a second buyer while the same molecule is certified again downstream.

A US hyperscale portfolio has the same structure at larger scale. Its inputs are electricity (with certificates, soon hourly), fuel (gas, RNG, certified gas, hydrogen, each with its own registry and custody model), captured CO₂ (with its own registries), and water (with state reporting from 2027 in Virginia). Its claims are of four kinds: a ratepayer-protection claim, an electricity-carbon claim, a fuel-carbon claim and a water claim. The standard that decides whether book-and-claim fuel attributes may enter Scope 1 and 3 (the GHG Protocol's Actions and Market Instruments work) is due in draft in 2027 and final in 2028.

The infrastructure this needs is not complicated to describe. Each unit of input carries a serial, an emission or water factor, a custody model (mass balance or book-and-claim) and a claims flag, from the meter to the retired certificate. It is complicated to build, because the registries do not talk to each other and the standards are moving. But without it, every one of the pledges above is unauditable, and the owners' own net-zero mandates, which require a measured inventory within about two years of acquisition, cannot be met.

## 4. The pilot: reporting or emissions?

The most consequential of the moving standards is hourly matching, because it changes what a data centre's clean-power procurement is worth. I ran a first test on public data.

**Method.** EIA Form 930 gives hourly net generation by fuel for each US balancing authority. I built an hourly grid carbon intensity from fuel shares and fleet-average combustion factors (coal 1,000, gas 400, petroleum 900 kgCO₂/MWh; zero for nuclear, hydro, wind, solar, storage at the point of generation). I placed a flat 100 MW load in six balancing authorities for July to December 2025 and gave it a solar PPA sized so that solar energy over the period equals load energy, using each region's own solar shape. Then I computed the load's emissions three ways: location-based (load times hourly grid factor), annual-matched market-based (zero, since certificates cover the year), and hourly-matched (unmatched hours at the grid factor). The code is `src/hourly_match.py`; nothing is fitted.

**Result.**

| Balancing authority | Avg grid CI, kg/MWh | Location-based, tCO₂ | Hourly-matched residual, tCO₂ | Share of load matched by the hour | Annual-matched |
|---|---|---|---|---|---|
| PJM | 348 | 152,800 | 88,900 | 43 % | 0 |
| ERCOT | 303 | 132,400 | 82,100 | 44 % | 0 |
| MISO | 443 | 194,500 | 114,500 | 43 % | 0 |
| CAISO | 212 | 93,100 | 62,600 | 44 % | 0 |
| SPP | 421 | 185,900 | 90,800 | 48 % | 0 |
| Southern | 374 | 165,200 | 99,300 | 42 % | 0 |

![Same load, same PPA, three accounting answers](../figures/hourly_match.png)

A solar PPA that covers 100 % of annual energy covers 42 to 48 % of the hours. The residual, 55 to 65 % of the location-based figure, is what the current standard lets a buyer leave unreported and the proposed standard does not. In MISO that is 114,000 tCO₂ over six months for a single 100 MW site.

**What this does and does not show.** It shows that hourly matching changes reporting by a large, region-dependent amount, and that the residual is served by gas and coal in the hours solar is absent. It does not yet show the consequential effect: whether the load caused those plants to run, what it did to prices, or whether an hourly-matched procurement rule would change what gets built. That needs a dispatch model and the interconnection-queue data, and it is the research I am proposing.

## 5. Proposed research: the societal cost of compute, and who pays

Frame the question as one of societal resilience rather than corporate accounting. Compute load is arriving faster than generation. The costs land on three parties: ratepayers (price effects and upgrade costs), the grid (adequacy and reliability in the hours renewables are absent), and the climate (the residual above). The pledges say the developer will carry these costs. The regulatory system is deciding, tariff by tariff, how much of them it will be made to carry. Neither side has a measurement.

Three questions, in order:

**1. Measure the residual.** Extend the pilot from a flat load in six regions to the actual interconnection queue (LBNL's Queued Up dataset gives location, size and status of proposed large loads and generation) and to a dispatch-aware estimate of what serves the unmatched hours. Output: a public, reproducible estimate of the hourly-matched residual and the price-effect exposure of announced AI capacity, by region.

**2. Compare the mechanisms.** Large-load tariffs, clean transition tariffs, hourly-matched procurement mandates, developer-funded upgrade programmes and "pay the price effect" pledges are all attempts to make the load internalise its cost. They allocate it differently. Using the PUC docket record (the 23 states) and the FERC show-cause filings, classify the mechanisms by who bears what, and test them against the measured residual from question 1. Output: an evidence-based typology that a policymaker or a developer can use to say which mechanism buys resilience and which only moves cost.

**3. Specify the measurement layer.** For the mechanism that performs best, write the minimum data and custody specification that would let a pledge be audited: what is metered, what is matched, what is retired, who verifies. This is where the site-level and portfolio-level work above becomes a public good instead of a consulting deliverable.

The data are public. The methods are standard: panel and event-study designs on hourly and docket data, with the accounting rules implemented as code so that the choices are inspectable. What I bring is fourteen years of building exactly these accounting rules for regulators and buyers, and access to the developers, utilities and certification bodies whose behaviour the research is about.

---

*Author's note.* The site-level case draws on advisory work for a methanol-to-power developer and its data-centre counterparty in Singapore, and on proposal work for a US data-centre platform. Counterparties are not named; all site numbers are illustrative and are generated by the code in this repository from stated inputs. Standards cited: ISO 14067:2018; GHG Protocol Scope 2 Guidance (2015) and the 2025–26 revision consultation; GHG Protocol Corporate Standard, Appendix B; EIA Form 930; EEI large-load tariff tracker (May 2026); FERC show-cause orders of 18 June 2026.
