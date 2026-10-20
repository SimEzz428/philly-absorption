# Findings ledger

**Oct 17, 2026.** Every number here came off a real run, with where it prints.
This is the source the README gets assembled from at the end — not the README.

Rule for this file: **a claim with no reproduction path does not belong in it.**
Section 6 holds the ones that currently fail that test.

---

# 1 — The answer

Single-family new construction, 15% annualised hurdle, 9% construction loan,
$300,000 per dwelling. `model.py`, DEAL ARITHMETIC and MAXIMUM BUILD BUDGET.

⚠️ **Re-run Oct 20, 2026 and the numbers moved.** The previous version of this
table named 19147 first at 21.9%. It is now third at 19.2%, and 19128 leads at
19.9%. Both tables came off real runs; the earlier one is simply older, and the
ordering inside the top tier was never statistically separable anyway (see the
bootstrap below). The figures here are the current run.

**Annualised return at $300k/dwelling** — `DEAL ARITHMETIC`:

| ZIP | | n | days | land $ | basis $ | price $ | profit $ | ROC | ann |
|---|---|---|---|---|---|---|---|---|---|
| 19128 | Roxborough | 30 | 666 | 146,250 | 496,657 | 676,562 | 179,904 | 36.2% | **19.9%** ✅ |
| 19119 | Mt Airy | 21 | 695 | 45,750 | 381,626 | 524,792 | 143,167 | **37.5%** | **19.7%** ✅ |
| 19147 | Queen Village | 48 | 665 | 287,500 | 662,067 | 894,125 | **232,058** | 35.1% | **19.2%** ✅ |
| 19123 | Northern Liberties | 23 | 986 | 200,000 | 588,317 | 793,357 | 205,039 | 34.9% | 12.9% |
| 19133 | Fairhill | 43 | 468 | 30,500 | 353,497 | 406,238 | 52,741 | 14.9% | 11.6% |
| 19125 | Fishtown | 105 | 613 | 83,812 | 420,891 | 492,512 | 71,621 | 17.0% | 10.1% |
| 19121 | Brewerytown | 103 | 577 | 40,625 | 368,856 | 421,939 | 53,083 | 14.4% | 9.1% |
| 19104 | West Philadelphia | 18 | 722 | 23,500 | 357,714 | 415,849 | 58,136 | 16.3% | 8.2% |
| 19122 | Olde Kensington | 106 | 495 | 51,000 | 376,606 | 416,949 | 40,343 | 10.7% | 7.9% |
| 19134 | Kensington | 58 | 604 | 25,000 | 353,063 | 397,823 | 44,759 | 12.7% | 7.7% |
| 19145 | Girard Estate | 43 | 592 | 84,750 | 419,691 | 459,735 | 40,044 | 9.5% | 5.9% |
| 19148 | Pennsport | 73 | 536 | 70,070 | 400,920 | 429,811 | 28,890 | 7.2% | 4.9% |
| 19146 | Point Breeze | 213 | 568 | 75,000 | 407,946 | 434,776 | 26,831 | 6.6% | 4.2% |
| 19143 | Kingsessing | 20 | 792 | 36,125 | 376,250 | 364,063 | **−12,187** | −3.2% | **−1.5%** ✗ |

**Three submarkets clear the 15% hurdle. 19143 loses money outright.**

## 1.1 The clock you choose changes the winner

`MAXIMUM BUILD BUDGET` prices the same cells two ways — over the development
period, and over the whole capital commitment including hold time:

| ZIP | dev days | all-in days | max build (dev) | max build (all-in) | delta |
|---|---|---|---|---|---|
| 19147 | 665 | 942 | **336,787** | 265,994 | −70,793 |
| 19128 | 666 | 902 | 331,807 | **289,261** | −42,546 |
| 19119 | 695 | 1,218 | 324,306 | 265,487 | −58,819 |
| 19133 | 468 | 644 | 287,937 | 268,402 | −19,535 |

On the development clock Queen Village allows the largest budget. On the all-in
clock **Roxborough wins and Queen Village falls to third**, because its capital
sits idle 277 days beyond the build. Reporting only the development clock names
the wrong submarket.

## 1.2 ⚠️ The constraint that inverts the recommendation

`CAN I BUY IN?` — allowable budget against observed site turnover:

| ZIP | top-3 share | sites/yr | years per site |
|---|---|---|---|
| 19147 Queen Village | 65% | 4.4 | 0.2 |
| 19128 Roxborough | **75%** | **2.4** | **0.4** |
| 19119 Mt Airy | 67% | 2.2 | 0.5 |
| 19133 Fairhill | 23% | 13.8 | 0.1 |
| 19121 Brewerytown | 2% | 20.5 | 0.0 |

**The top tier turns over 2.4 sites a year; everywhere else turns over 12.1.**
The submarkets that clear the hurdle are the ones where a site is hardest to
source, which is not a coincidence — it is what scarcity does to price.

So the answer is not "build in the top tier." It is: build there if a site can
be sourced, expect ~0.4 years of searching per site, and treat 19133 (11.6%, but
13.8 sites a year) as the cell where capital can actually be deployed on
schedule.

## 1.3 The order is not defensible

2,000 bootstrap resamples per cell: **7 of 14 submarkets reach the top three in
more than 10% of resamples**, and the top three have overlapping p10–p90 bands
(19128 252,184–403,953; 19119 197,615–340,589; 19147 228,982–407,842). Any two
overlapping cells are not distinguishable with this many projects. Report tiers,
not ranks.

Resampling is within each cell, so it measures sampling noise given the project
counts actually present. It does **not** capture model error, the land proxy's
bias, or the 2019–2022 window being unrepresentative.

Multi-family (2–4 units) has three cells with enough projects — 19122 (51),
19121 (31), 19146 (17, thin) — and **no budget figure**, because one recorded
deed is not known to equal one project's total revenue.

---

# 2 — The population, every drop with a mechanism

`build.py` and `analyze.py` print all of this.

```
937,512   permits downloaded
582,164   deeds (486,326 carry a parcel id)
583,713   property assessments

  8,868   residential + certificate of occupancy + parcel id
  6,774   new construction only              − 2,094  additions/alterations (23.6%)
  5,441   single parcel, identifier extant   − 1,170  multi-permit parcels
                                             −   163  parcel retired from OPA
  2,013   matched to a recorded sale                  37.0%
  1,829   arms-length, single-parcel         −   143  nominal (<$10k)
                                             −    86  bulk (multi-parcel deed)
                                             +    45  overlap
```

Plus **99 unobservable** — certificate of occupancy postdates the deed extract
(2026-09-02), so no data covers them. Flagged, not pooled with unsold buildings.

**Counter families, each summing to 6,774:**

```
build_counts  {ok: 6774}
gfa_counts    {ok: 4319, no_area_or_stories: 2420, no_units: 35}
obs_counts    {ok: 6675, unobservable: 99}
land_counts   {observed: 1872, outside_window: 355, bulk_only: 826,
               nominal_only: 953, no_prior_deed: 2768}
```

`build_counts` having a single key is itself a result: **zero missing issue
dates and zero ordering violations in 6,774 records** — permit issue always
precedes the certificate of occupancy.

---

# 3 — The capital clock

## 3.1 The chain, and which parts were ever measured

```
land purchase → [369 d] → permit → [602 d] → C of O → [39 d] → sale
                  NEW                NEW               known
```

| | median | n | source |
|---|---|---|---|
| acquisition → permit issue | **369 d** | 2,227 | `build.py` LAND ACQUISITION |
| permit → certificate of occupancy | **602 d** | 6,774 | p10 285, p90 1,313, max 3,440 |
| C of O → first sale | **39 d** SF / 109 MF | 1,829 | `analyze.py` ABSORPTION |
| **land → final sale** | **1,080 d (3.0 y)** | 809 | ⚠ narrowest subset, shakiest figure |

Build share of the permit-to-sale clock: **92% single family, 84% multi family,
62% apartments.** Absorption — the quantity this literature measures — is 8% of
the single-family clock.

Holding periods vary **135 → 656 days** across cells, so the single 369-day
median hides a 4.8× spread.

## 3.2 What the time costs

`model.py`, WHAT THE TIME COSTS. Needs only the two observed durations and the
rate — no cost assumption, no floor-area estimate.

| | total days | interest per $100k @ 9% |
|---|---|---|
| 19133 | 468 | $11,552 |
| 19123 | 986 | $24,325 |
| difference | 518 | **$12,773** |

Counting the land holding period costs **$11,335 to $72,674 of build budget**
per dwelling depending on the cell (MAXIMUM BUILD BUDGET, `delta` column).

## 3.3 Two clocks, two questions

| | answers |
|---|---|
| `max (dev)` | *"I already own the land — is building worth it?"* |
| `max (all-in)` | *"was buying **and** building worth it?"* |

Land carries the whole period including entitlement; construction does not, so
the holding period cannot be added to build days. **Both are legitimate.**

Under the all-in clock the ranking reorders again: **19123 falls six places**
(360-day hold), 19104 falls on 656 days, 19128 takes the top from 19147.

**The clearest single example — 19145:**

| ranked by | position |
|---|---|
| sell carry alone | **1st of 10** |
| spread | 3rd |
| total carry | **8th** |

A seven-place swing. 19145 sells in **38 days**, the fastest in the city, and
takes **576** to build. Judge it on absorption and it is the best market in
Philadelphia. Judge it on committed capital and it is eighth of ten.

> The project's spine: ranking by spread misranks markets → correcting for
> absorption alone still misranks them → counting the land clock reorders them
> a third time. Each time you count more of the capital clock, the answer moves.

---

# 4 — What the model can and cannot do

`model.py`. Walk-forward, split on **permit issue date** — the moment the
prediction would be made — against the best of global/tract/ZIP/category
medians.

| target | fold 1 | fold 2 | fold 3 | verdict |
|---|---|---|---|---|
| **price** | **+2.0%** | **+5.3%** | **+18.7%** | model wins 3/3 |
| build days | −32.0% | +2.7% | −31.7% | **baseline wins** |
| sell days | −34.7% | −93.5% | −39.7% | **baseline wins** |

So the tool uses the model for price and **observed distributions for
duration** — shipping a model on a target where it lost would contradict the
validation that was run to catch exactly that.

## 4.1 ⚠️ And the raw location lift, corrected

I quoted *"location predicts price 15–41% better than citywide"* and later
*"27–33%, 3/3 folds."* **Both were measured on a contaminated window.** On the
aligned 2019–2022 pools:

| price, best group median vs global | fold 1 | fold 2 | fold 3 |
|---|---|---|---|
| lift over citywide | 7.7% | 17.6% | 26.2% |
| which grouping won | **product type** | ZIP | ZIP |

**Location beats citywide on price in 2 of 3 folds, by 17.6% and 26.2%** — and
in 2020 both tract and ZIP were *worse* than a single citywide median, with
product type winning instead. The honest claim is "7.7–26.2%, location in two
of three periods", not a flat 27–33%.

Build time went the same way and the corrected figure is cleaner:

| build days, best vs global | fold 1 | fold 2 | fold 3 |
|---|---|---|---|
| lift over citywide | −0.2% | 0.0% | 8.6% |

**Location beats citywide on build time in 1 of 3 folds.** The earlier
8.1/7.7/20.2 came from folds trained on left-truncated pre-2019 cohorts and
tested on censored 2023–24 data. With the honest window, location predicts
build duration essentially not at all — which agrees with rho 0.22 and with the
model losing.

**Interval calibration: 50–67% coverage against a nominal 80%.** Every model
here is overconfident, price included. Duration intervals in the output are
therefore empirical p10–p90, which cannot be miscalibrated.

**Permutation importance, held-out:**

```
PRICE   stories        22,956 +/- 6,936     strongest single predictor
        zip5            8,956 +/- 1,335     tightest estimate in the run
SELL    gfa_per_unit      10.6 +/-   5.7
BUILD   cat                9.5 +/-   1.4
```

Only `stories` and `zip5` on price, and `cat` on build, have error bars small
enough to assert without hedging. `stories` is also the one input on that list
a developer fully controls.

---

# 5 — Data findings

## 5.1 The ZIP-median land proxy is biased, and now measured

`model.py`, OBSERVED LAND PRICE vs THE ZIP-MEDIAN PROXY.

```
median proxy error: −$21,257      12 of 13 cells understated
worst: 19146 MULTI FAMILY   observed $167,500   proxy $47,500   −$120,000
```

**Mechanism:** the proxy samples parcels *currently* classified `VACANT LAND`.
A lot that was bought and built on is no longer vacant, so it leaves the sample
— leaving only land nobody developed, which is cheaper by definition. **The
proxy was pricing the land developers didn't buy.**

## 5.2 And it was excluding submarkets entirely

```
13 cells  →  17 cells
new: 19147 Queen Village, 19128 Roxborough, 19119 Mt Airy, 19123 N Liberties
```

Those four had **no vacant-land comps at all**, which is what built-out
desirable neighbourhoods look like. **All three submarkets that clear a 15%
hurdle are among them.** Before observed acquisitions, the answer was "nothing
in Philadelphia pencils" — and that was an artifact of the proxy, not a fact
about the city.

## 5.3 17.3% of permits are structurally unmatchable

Multi-permit parcels: a lot built out as many dwellings files permits against
the parent, but sales record against child parcels created at subdivision. One
case has **60 permits issued on a single day**.

| | multi-permit | singleton |
|---|---|---|
| match rate | **14.9%** | 37.0% |
| absent from the OPA roll | **20.2%** | 2.9% |
| still assessed `VACANT LAND` | see `verify.sql` §7 | — |

Not migration artifacts (0 cross-system `permitnumber` collisions) and not bulk
transfers ($440k vs $450k median). No address matcher recovers these — the link
does not exist in the data.

**Large multifamily** is unmeasurable for the same *kind* of reason and a
different mechanism: single-parcel rental buildings, so no unit deeds exist.

## 5.4 23.6% of permits with a C of O are renovations

`Addition and/or Alteration`, not new supply. Excluding them moved single-family
absorption **41 → 39 days**: conceptually necessary, numerically irrelevant.
Both halves worth stating.

## 5.5 The data is biased at both ends, by opposite mechanisms

Build time by permit issue year:

```
2016   n=24      median 2,184 d      left-truncated
2019   n=1,054          594          usable
2021   n=1,512          665          usable
2025   n=319            292          right-censored
```

Before 2019, C of O recording had barely started, so an early permit only
appears if it built *slowly* enough to still be open. After 2022, slow builds
haven't finished. **Modelling window: issue years 2019–2022.**

## 5.6 A feature can be valid for ordering and invalid as a quantity

`approx_gfa_per_unit` (footprint × storeys ÷ units) **leads the sell-days
importance table**, so it carries real tier signal. As an absolute square
footage it fails:

```
19147   3,038 sqft   $305 / claimed sqft    plausible
19133   1,650        $246                   plausible
19128   3,900        $173
19119   4,725        $110                   implausible
19145   4,266        $108                   implausible
```

**Above roughly 3,500 claimed sqft the figure breaks down**; below it the range
is a believable $173–$305. Not a general inverse relationship — 19147 has the
largest plausible area *and* the highest $/sqft. So the feature stays in the
model, where only ordering matters, and out of the arithmetic, where magnitude
matters: cost is an input **per dwelling**, never per square foot.

## 5.7 Approval friction: the queue, not the rejection

The fourth factor of the original question, measured at last — and the first
measurement was pointed at the wrong permit type.

```
10,726  residential new-construction BUILDING applications  ->      4 refused (0.04%)
39,192  ZONING applications, eCLIPSE only                   ->  2,490 refused (6.35%)
```

**Philadelphia refuses at the zoning stage.** By the time you file for a
building permit you have already cleared zoning, so refusal is invisible there.
You only find this by knowing how the process works rather than what the
columns are named.

⚠️ **The eCLIPSE restriction is load-bearing, and it caught me out.** Counting
all 125,443 zoning permits gives 1.98% — because HANSEN's ~86,000 `ZP_*` rows
use a different status vocabulary (`COMPLETED`, `EXPIRED`, in capitals) and
**never record `Denied` or `Refused` in title case.** They add denominator with
no numerator. A zip-validation filter happened to exclude them too, so the right
number appeared for the wrong reason; the system filter is now explicit in
`build.py`. The two-systems trap, for the fourth time in this project.

The entitlement *lag* is still counted across both systems, because a zoning
issue date is a real date whatever the status vocabulary.

Priced against each other, across the 14 submarkets in the answer:

| | worst case |
|---|---|
| refusal risk, as expected sunk filing cost | **$2,015** |
| entitlement **queue**, as land carry | **$13,824** |

19147 waits **244 days** from zoning approval to building permit; 19145 waits
**49**. That 195-day gap on 19147's $287,500 of land at 9% is $13,824 of pure
carry — about 7× the worst refusal risk. `rank move` is **+0 for every cell**:
pricing refusal risk does not change where to build.

> **The friction that matters is the queue, not the rejection.** And the
> entitlement queue is **189 days median** — roughly half the 369-day
> acquisition-to-permit gap, so it explains that wait rather than adding to it.
> In 19147, 244 of 277 holding days are the city. In 19133, 60 of 176 are. One
> is a process a by-right design can attack; the other is your own timing.

⚠️ `entitle` and `hold` are medians over different subsets (one needs a zoning
match, the other an acquisition), so the ratio is indicative, not exact.

⚠️ Also worth noting without claiming: the highest zoning-refusal ZIPs — 19120
(15.6%), 19126 (14.5%), 19141 (12.4%) — are **absent from the buildable table
entirely**. That is either a barrier to entry or a selection effect in weak
markets, and this data cannot separate them.

## 5.8 `numberofunits` means units in scope of THIS permit — resolved

Roadmap Part 6 open question #4, and it was load-bearing: every per-unit figure
in the project assumes this reading.

Apartment-classified parcels, permits with a unit count:

| | permits | median | p90 | max |
|---|---|---|---|---|
| addition / alteration | 1,386 | **1** | 17 | 1,017 |
| new construction | 1,153 | **6** | 55 | 1,111 |

**Alterations show a median of 1.** If the field meant building size, an
alteration on an apartment building would carry the whole building's count and
the median would be large. It doesn't. So the field is units *in scope of this
permit*.

The nuance: alteration p90 is 17 and max is 1,017, so a building-wide job does
carry the building's count — the field means "units this permit touches", which
is 1 for a unit renovation and the whole building for a facade job. Internally
consistent, but it means an alteration's unit count is not comparable to a new
construction's.

**Why the project is safe:** the population filters to `New Construction`, where
units-touched and units-created are the same thing. Fourth instance of the same
pattern — *the filter that defines the population also determines which data
defects can reach it.*

⚠️ My second test did not discriminate. I claimed `distinct_unit_values = 1`
across a parcel would prove "building size". It doesn't: 885989560 has 47
permits all carrying 2 units and summing to 94, which is equally consistent
with **47 identical duplexes**. A uniform development gives one distinct value.
Test 1 settled it; test 2 was badly designed.

## 5.9 The `numberofunits` coverage collapse never reached the analysis

Roadmap Part 6 open question #6.

```
ALL new-construction permits        INSIDE the population
2007-2014      0.0%                 2015-2026      100.0%  every year
2015           4.4%
2021          26.3%
2022          10.3%
2024          12.5%
```

**Erratic 10–26% in the raw feed, 100% in every single year of the
population.** Requiring a certificate of occupancy selects for
completely-filled records, so the defect could not reach the analysis. That is
an answer, not a dodge.

⚠️ And it corrects something: `build.py` reports `gfa_counts["no_units"] = 35`,
which reads like 35 missing values. It isn't — **all 6,774 records have a
non-null unit count, and 35 of them declare ZERO.** The counter fires on `not
units`, which is true for both. A new-construction permit declaring zero
dwelling units is a real thing to look at (shell-only filings, or the
non-residential leg of a mixed-use project), and it is exactly the distinction
`unit_bucket` preserves and `test_none_and_zero_are_different_facts` asserts.

## 5.10 `areaofdisturbance` is footprint, not floor area

Per-unit area collapses 800 → 273 sq ft as unit count rises, which is what
land-per-unit does and floor-area-per-unit does not. Using it directly would
have **inverted** the product-tier signal.

## 5.11 The completion date is sound

`permitcompleteddate` vs `certificateofoccupancydate`: **median gap 0 days over
6,767 records**; 176 disagree by more than a year and **all 176 in the same
direction**. Two independently-recorded fields with consistent ordering.

## 5.12 OPA classification is stale for new construction

`building_code_description` reads `VACANT LAND` on **68%** of completed
new-construction parcels, and disagrees with `category_code_description` on the
same row. So that field says nothing about matchability — a hypothesis I held
and the data reversed.

## 5.13 Other raw-data traps

| | |
|---|---|
| two permitting systems | HANSEN ends 2020-03-12; natural key is `(systemofrecord, permittype, permitnumber)`. **This trap bit four separate times**: the natural key, the C of O floor that makes the population eCLIPSE-only, the `ZP_*` vs `Zoning` permit-type names, and the status vocabulary (`COMPLETED` vs `Completed`, no `Refused` in HANSEN at all) |
| `commercialorresidential` | means building **code** — a 50-unit apartment building files as "Commercial" |
| `occupancytype` | pipe-delimited, so equality tests drop every mixed-use project |
| `RTT_SUMMARY` | not sales — the largest document type is MORTGAGE |
| five columns | carry duplicate spellings for the same value |

---

# 6 — ⚠️ Claims that do NOT yet reproduce

These were measured during exploration against data that was then filtered, or
on an earlier population. **Re-derive, attribute with a date, or cut.**

**Reconciled against `verify.sql` on Oct 17.** Results:

| claim | outcome |
|---|---|
| 224 duplicate `permitnumber` values | ✅ **CONFIRMED** — `verify.sql` §3 returns exactly 224, and 0 for the three-column natural key. I was wrong to doubt it |
| "82 of 93 still assessed vacant" | ❌ → **89 of 138 = 64.5%**. The old figure was the top-15 rows, not a count |
| match 37.0% vs 14.9% | ⚠️ those **exclude retired parcels**. Including them: **36.0% vs 11.4%**. Both correct, different denominators — always say which |
| absent from OPA 20.2% | ⚠️ that is **per parcel**. Per permit it is **23.6%**. Say the unit |
| unobservable 99 | ⚠️ SQL said 93 with `>`, now `>=` and agrees at 99. A zero-day window *is* unobservable |
| 21,910 vs 10,158 clustered missingness | ❌ **not reproducible** — computed over all 1.1M deeds; only 486,326 are stored. Cut it, or attribute to a live query dated 2026-10-12 |
| 2.76 permits per address | ❌ live API query, not in the database. Cut or attribute |

## The `parentjobid` correction

I excluded multi-permit parcels rather than grouping them, and claimed grouping
might be impossible. **`verify.sql` §11 disproves that:**

```
population 6,774   with_parent 1,877   distinct_parents 437
888001944   60 permits   60 with_parent   1 distinct parent
885989560   47           47               1
```

Sixty permits sharing one parent job — they **are** one project, and roadmap
Stage 4's instruction to group them was right. Exclusion was defensible but
grouping is better: it would fix the unit counts. **The unmatchability
conclusion survives either way**, because sales still record against child
parcels regardless of how the permits are grouped.

---

# 7 — What cannot be known from public data

The second half of the question, and the half that decides how far to trust
section 1.

| | |
|---|---|
| **construction cost** | by design — it is the user's input, which is why the answer is a *budget* to check against their own number |
| **large multifamily economics** | single-parcel rentals, no unit deeds exist |
| **multi-unit parcel outcomes** | 1,170 permits, link destroyed at subdivision |
| **rents** | absent from all three sources, so build-to-rent cannot be screened. Largest blind spot by dollar volume |
| **acquisitions before 2010** | the deed ingest floor. `no_prior_deed` (2,768) conflates "parcel didn't exist" with "bought before 2010" |
| **slow and failed sales** | 63% of in-scope projects have no recorded sale; absorption is optimistic by an unmeasured amount |
| **abandoned projects** | only permits issued *and* built are observed |
| **anything before 2020** | C of O recording floor, so the window is post-pandemic and includes a rate shock |
| **census-tract resolution** | 1,829 clean records ÷ ~380 tracts ≈ **4.8 per tract**. ZIP is the finest geography this data supports, and that arithmetic is the finding |
| **duration, predictively** | a neighbourhood median beats the model on build and sell time across three held-out years |

---

# 8 — Ranking confidence, and what is still open

## The ranking is a tier, not an order

2,000 bootstrap resamples per cell, drawn at each cell's real size, so the
noise measured is the noise the project counts actually carry.

| | max build | bootstrap p10–p90 | top-3 share |
|---|---|---|---|
| **19128** | $331,780 | 250,548 – 403,864 | **75%** |
| **19147** | $359,707 | 252,831 – 431,665 | **74%** |
| **19119** | $321,075 | 195,409 – 338,721 | **65%** |
| 19133 | $288,075 | 272,337 – 293,602 | 22% |
| 19123 | $277,709 | 243,414 – 308,689 | 22% |
| 19145 | $255,067 | 246,208 – 364,857 | 19% |
| 19146 | $249,322 | 242,929 – 263,682 | **0%** |

**Six of fourteen reach the top three in more than 10% of resamples, so the
1-to-14 order is not defensible.** But three submarkets take 214% of the 300%
available top-three slots: **membership in the top tier is solid, the order
within it is noise.** Those three are exactly the three that clear a 15%
hurdle.

Two bands worth reading: 19146 (n=213) is tight and never reaches the top, so
you can say confidently it is mid-table. 19145's band is $119k wide — high
price, high land, few projects — so it could be anywhere.

⚠️ This captures sampling noise only. It does not capture model error, the
land proxy's residual bias, or the 2019–2022 window being unrepresentative.

## And the ranking does not persist

| target | zips | rho 2019-20 → 2021-22 | |
|---|---|---|---|
| **price** | 13 | **0.88** | stable |
| build days | 19 | 0.22 | **not persistent** |
| sell days | 13 | −0.13 | **not persistent** |

Three independent methods now agree on the same split: **price is predictable
(location beats citywide 7.7–26.2%, winning in two of three periods), the model
beats its baseline 3/3, and the ranking holds across periods. Duration fails all
three.**

⚠️ This line said "27–33%" until Oct 18 — the figure §4.1 above retires. The
ledger contradicted itself for a day, which is the argument for §4.1 existing as
a numbered correction rather than a quiet edit.

> So the price side of the answer transfers forward. The time side describes
> history. A duration ranking built on 2019–20 would not have predicted
> 2021–22, and that caps what the tool can claim however good the within-period
> fit looks.

## Still open

| | hours | why |
|---|---|---|
| **zoning envelope** | 2 | `zoning` is on all 583,713 parcels, unused. The only "cannot be known" item you actually have. Product type is constrained, not chosen |
| group by `parentjobid` | 2 | §6 shows it is possible; it would fix the unit counts |
| sharpen 5.6 in the code footnote | 15m | still says "falls as claimed area rises" — it breaks down above ~3,500 sqft, below that $173–$305 is believable |
| README | last | assembled from this file |

---

# 9 — Decisions that used to live only in the code

Rule 8 says reasoning belongs here, not in comments. These were extracted from
`build.py`, `analyze.py`, `model.py` and `test_pipeline.py` on Oct 18 before the
comments were removed. Nothing below is new; it is relocated.

## 9.1 The leakage guard, and why it is a function rather than three lines

`trailing_window(issue_year, n=2)` is anchored on the permit **issue** year and
closes **strictly before** it. It used to be inlined off `co_date`, which handed
the model roughly **600 days of future information** — the median permit-to-C-of-O
interval. A market feature computed from the year a building *finished* is not
knowable on the day its permit is pulled, so a model trained on it scores well
and cannot be run.

Three properties make the guard real rather than decorative:

| | |
|---|---|
| it is a **function in `lib.py`** | so the test and the pipeline cannot drift apart |
| `test_pipeline.py` asserts it over **2015–2026** | every year, not a spot check |
| `build.py` **calls** it | a tested function the pipeline reimplements protects nothing |

That last row is the whole point. A test that checks `lib` while the pipeline
computes its own copy is theatre, and the failure is silent.

```python
def test_window_closes_strictly_before_the_issue_year(self):
    for year in range(2015, 2027):
        for y in trailing_window(year):
            assert int(y) < year
```

## 9.2 Two constants that deliberately exclude nothing

**`TOO_LONG_DAYS = 3650`.** The maximum observed permit-to-C-of-O interval is
**3,440 days**, so this threshold drops zero rows and `build_counts["too_long"]`
stays at 0. Kept anyway, because every reported duration is a **median** — already
robust to the tail — and any tighter number invites *"why that one and not
another?"* with no defensible answer. A knob set where it bites nothing is
visible; deleting it makes the same decision invisibly.

**`LAND_LOOKBACK_YEARS = 3`.** A 1998 deed on a parcel permitted in 2022 *is*
what they paid, but it is a 1998 price and says nothing about what land costs
now. The build data shows acquire-entitle-build runs one to three years, which
is where the 3 comes from. The acquisition price is stored **regardless of age**
along with `land_lag_days`; the constant only sets the `land_in_window` flag. So
changing it loses nothing and the coverage histogram shows what each choice
would cost.

## 9.3 What `permit → C of O` actually measures

The 602-day figure is **entitlement-to-occupancy, not construction duration.** It
includes financing and scheduling delay before ground was broken. Every claim
resting on it — including "build is 92% of the single-family clock" — inherits
that. The direction of the error is known: it makes construction look slower than
it is, and the 92% is an upper bound on the build share.

No public field separates ground-breaking from permit issue, so this cannot be
corrected, only stated.

## 9.4 Three bounds that must agree across two files

```
SALE_CUT    = "2025"    C of O year; 2026 is only 8 months observed
ISSUE_FLOOR = "2019"    below it, C of O recording had barely started — left truncation
ISSUE_CUT   = "2022"    above it, slow builds have not finished — right censoring
```

⚠️ **These drifted for a while.** `analyze.py` and `model.py` carried different
values, so the baselines printed in one file described a different population
from the one the model was validated on — **`build_pool` read 4,123 in `analyze.py`
and 3,112 in `model.py`.** Two files, two populations, one set of conclusions
quoted as if they came from the same place.

The lesson is not "be careful." It is that a shared constant duplicated across
files is a bug waiting on a schedule, and the only reason it was caught is that
both files print their pool sizes.

## 9.5 The median of predictions, not a prediction at the median

For each cell the model predicts **every real project in it** and the **median of
those predictions** is taken. Predicting once at the median of the features is a
different quantity for any non-linear model, and gradient boosting is non-linear.
They coincide only for a linear model, which this is not.

## 9.6 Why `issue_year` is not a feature

In walk-forward the test year is always one the model has never seen, and a tree
can only split on values present in training — so the feature cannot transfer by
construction. Permutation importance measured it at exactly **0.0**, which is the
confirmation rather than the reason.

## 9.7 Sign conventions kept on purpose

| | |
|---|---|
| **observation window** | a C of O dated after the deed snapshot gives a *negative* window. The sign says how far past the snapshot completion falls, so it is kept rather than clamped. These are the 99 unobservable records — missing for coverage reasons, not market ones |
| **build intervals** | a negative interval is a data finding, not something to `abs()` away. Asserted signed in the tests |
| **unit counts** | `None` (never declared, 35 permits) and `0` (declared as zero) are different facts. Merging them loses information |

## 9.8 Why the filing cost is a cost of the submarket

`COST_PER_FILING = 25_000` covers design, drawings, fees and consultants for
**one** attempt. A refusal spends it and leaves you holding no asset — so it is a
property of where you chose to file, not an overhead to spread across a year.
Priced that way it comes to **$2,015** worst-case expected sunk cost, against
**$13,824** for the entitlement queue in the same cell: see §5.7.

## 9.9 Site supply is counted from purchases, not from the vacant-land roll

The three submarkets that clear the hurdle only surfaced once observed
acquisitions replaced the ZIP-median proxy, and the reason they had no proxy is
that they have **almost no vacant-land market**. Counting supply from parcels
*currently classified* vacant would undercount exactly where development
happened, because that classification is stale on **68%** of built parcels
(§5.12). The missing measurement was the signal.

---

# 10 — Reasoning relocated from docstrings

Rule 8 covers docstrings as well as `#` comments: **no explanation of any kind
lives in a source file.** These were lifted out of `build.py`, `lib.py`,
`analyze.py`, `model.py`, `test_pipeline.py` and `torch_compare.py` on Oct 19
before the strip. Items already recorded in §9 are not repeated.

## 10.1 Two populations, deliberately

`is_qualifying` requires a certificate of occupancy **and** a parcel id.
`is_application` requires neither, because **a refused permit never receives a
certificate of occupancy** — screening refusals through the completion filter
would find a refusal rate of zero by construction. The looser population exists
only for the approval-friction work in §5.7.

## 10.2 Three small decisions that look arbitrary and are not

| | |
|---|---|
| **`zip5` truncates to five characters** | Philadelphia carries both `19146` and `19146-1234`. Grouping on the raw field silently splits one submarket into two |
| **`days_between` returns `None`, never raises** | Missing dates are a measurable quantity here. Every caller counts its `None` cases into a counter family that must sum to the population — crashing would make the missingness invisible |
| **`codes()` is built over the whole pool, not per fold** | It is an identity map from label to integer and carries no target information. Building it per fold would mean a ZIP seen only in test has no code, which is a different bug |

## 10.3 NaN is not missing data to delete

`approx_gfa_per_unit` covers roughly 55% of rows.
`HistGradientBoostingRegressor` learns a split direction for NaN, so
**missingness becomes a feature** rather than a reason to discard 45% of the
sample. This is also why `torch_compare.py` has to impute and add a
was-missing flag: a network cannot accept NaN at all, so the comparison hands
the network strictly more columns and still makes it earn the result.

## 10.4 Why `usable()` exists

sklearn's binner computes midpoints between consecutive distinct values, so a
column that is constant or all-NaN **inside a particular training fold** crashes
the fit outright. The check is per fold, not per pool, because a column can be
usable in 2021 and constant in 2019.

## 10.5 The test suite is two suites

| | Runs when | Why |
|---|---|---|
| **Logic tests** | always, on every push | they need no data, so CI can execute them |
| **Invariant tests** | only when `data/built.json` exists | 2.1M records do not belong in a repository |

The invariants each encode a decision that could silently regress:

- **The leakage guard** — the regression test for a bug that was in this pipeline for real, asserted over every year 2015–2026
- **Land carries the whole period, construction does not** — moving a day from the build phase to the sell phase must cost *more*, because construction is half-drawn during the build and fully drawn after the C of O
- **Round-trip** — spending exactly `max_build_budget` must land on the hurdle rate, or the inversion in §9 is wrong
- **Unobservable records can never match** — `deed_snapshot` is the maximum `display_date`, so a C of O after it cannot be followed by any deed. Matching one would mean the join compares dates wrongly. ⚠️ `days_observed >= 0` is *not* an invariant; negative is the signal
- **Flags are `None` on unmatched rows, not `False`** — an unmatched permit has no price, so calling it "not nominal" asserts something unknown

## 10.6 `spearman()` correlates shared keys only

Early and late periods do not contain the same submarkets. Ranking the union
would rank absences against observations, so the function intersects the keys
first — which is also why the n differs per target in §8 (13 ZIPs for price, 19
for build days).

---

# 11 — Comparables: the tract beats everything, and the embedding is dead

`tract_comps.py`. Predicting each census tract's 2022 median sale price from
training data through 2021 only, across 42 test tracts.

## 11.1 The answer a developer uses

| method | median abs error | vs own tract |
|---|---|---|
| **the tract's own sales history** | **$113,498** | — |
| learned embedding comps, zip5 in features | $140,000 | +23% |
| **same-ZIP comps** | **$175,005** | **+54%** |
| learned embedding comps, zip5 removed | $176,125 | +55% |
| one citywide median | $179,125 | +58% |

**Use the tract. Do not widen.** The instinct when comps look thin is to widen
the search to the neighbourhood or the ZIP. That instinct is wrong here and the
cost is measurable: widening from tract to ZIP adds **$61,507 of median error**,
or 54%.

⚠️ This holds at roughly **6 priced sales per tract** across 176 tracts. It is
not a claim about one or two sales, and §11.3 is the boundary.

## 11.2 ⚠️ The embedding did not work, and the hypothesis I started from was wrong

The premise was that ~5 sales per tract is too thin to model directly, so a
learned 8-dimensional profile per tract would let thin tracts borrow strength
from tracts that behave like them. Both halves failed.

**It never beat ZIP reliably.** With zip5 in the features the median seed
scored $140,000 against ZIP's $175,005 — but the spread across 5 seeds was
**$100,375 to $219,250**, straddling the comparison. One or two seeds in five
were worse than simply using the ZIP. A median that good with a spread that
wide is the same shape as the win streak that inflated the Kalshi t-statistics
to 13.17–18.72.

**Two hypotheses, one eliminated.** Either the embedding had nothing to add
beyond zip5, or it was undertrained. Removing zip5 from the features
distinguishes them: if the profiles carried independent location signal,
dropping a redundant feature should have let them learn *more*. Instead the
error rose to **$176,125**, a dead tie with ZIP. Redundancy is ruled out.

**What is left is the long-tail problem.** An embedding is learned from
gradient updates, and a tract with two records receives almost none — its
vector stays near its random initialisation. So the tracts that most need to
borrow strength are exactly the ones whose profile is least trustworthy. The
thin tail confirms it in both configurations:

| tracts with ≤5 training sales | embedding | same zip |
|---|---|---|
| zip5 in features | $248,500 | $192,505 |
| zip5 removed | $255,005 | $192,505 |

Worse than ZIP by ~30% in the exact place the method was supposed to help.

**It is not a data-coverage artifact.** Neighbour pools were empty for **0 of
42** tracts, so the comps are defined and simply wrong — tract 003200 at $412k
draws 016702 at $160k and 037600 at $770k as two of its five nearest.

## 11.3 Still open

- **Shrinkage.** The principled fix for a rare category is to pull its embedding toward a global prior in proportion to how little data it has, exactly as a thin-file credit score is shrunk toward the population mean. Untested here.
- **The boundary.** §11.1 holds at ~6 sales per tract. Where own-tract stops beating ZIP — 3 sales? 2? — is not measured, and that crossover is the number a developer would actually want.

---

# 14 — Orchestration: why Airflow, why the gate, and what is still unproven

The pipeline ran as seven scripts invoked by hand in the right order. That works
exactly as long as the person running it remembers the order, which is not a
property a pipeline should depend on.

## 14.1 Airflow rather than dbt

dbt was the first choice and was wrong for this project. dbt models SQL
transformations; the transformations here are in pandas and plain Python, and
the SQL files (`schema.sql`, `units.sql`, `approval.sql`, `verify.sql`) are DDL
and ad-hoc investigation rather than a modelling layer. Wrapping seven Python
stages in dbt would have meant inventing a SQL layer for the sake of using the
tool.

A second reason, which should be stated because it influenced the decision:
**dbt could not be installed in the environment this was written in** — its
build step fetches a wheel from GitHub and the network refused it. Shipping dbt
configuration that had never been executed would have violated the rule that a
claim has to reproduce. Airflow installed, so Airflow could be verified.

## 14.2 Every stage shells out instead of importing

`build.py`, `model.py`, `analyze.py` and the three ingest scripts all execute at
module level — there is no `main()` and no `argparse`. An Airflow task that
imported them would run the whole pipeline at DAG-parse time, every thirty
seconds, forever, because the scheduler reparses DAG files continuously.

So every stage is a `BashOperator` running `python3 <script>`. This is normally
the lazy choice and here it is the only correct one. The project's own CI file
had already discovered the same constraint from the other direction, which is
why it uses `py_compile` rather than importing those modules.

## 14.3 The invariant test is a gate, not a report

The DAG's shape is the point:

```
start → logic_tests → [3 ingests in parallel] → load_postgres
      → build_population → invariant_gate → [analyze, model, tract_comps] → done
```

Two test stages, placed deliberately:

- **`logic_tests` runs before any ingestion.** The pure-logic tests need no data
  and no network and finish in under a second. Running them first means a broken
  leakage guard costs one second instead of discovering it after a 2.1M-record
  download.
- **`invariant_gate` sits between the build and every modelling stage**, and
  nothing can reach a model without passing through it. If the population
  invariants or the leakage guard fail, `analyze`, `model` and `tract_comps`
  never start. A failed invariant that merely *logged* a warning would produce a
  submarket ranking computed on a population that does not satisfy its own
  definition, which is worse than producing nothing.

Both gates have `retries=0`. Retrying a failed assertion is meaningless — the
data does not change between attempts — and a retry would only delay the
failure and muddy the logs. The ingest tasks retry 3 times with exponential
backoff to a 30-minute ceiling, because *those* failures are rate limits and
transient network errors, which do resolve on their own. Four of the thirteen
tests exist to pin exactly this asymmetry.

## 14.4 Two settings that prevent a specific kind of corruption

- **`max_active_runs=1`.** Every stage writes to fixed paths (`data/raw/*`,
  `data/built.json`). Two concurrent runs would interleave writes to the same
  files, and the resulting `built.json` would be a mix of two populations with
  nothing in it to indicate that.
- **`catchup=False`.** With a weekly schedule and a January start date, enabling
  catchup would queue dozens of historical runs on first deploy, each
  re-downloading the full dataset. The source APIs serve current data anyway, so
  a "2026-03-01" run would download exactly what a today run downloads — the
  backfill would be meaningless as well as expensive.

The project directory comes from an Airflow Variable rather than a literal path,
and a test asserts no task contains `/Users/`, so the DAG does not carry one
machine's filesystem layout into the repository.

## 14.5 ⚠️ What the 13 tests prove, and what they do not

Proven: the DAG file imports with zero errors, every expected stage exists, the
dependency graph is exactly as described above, no modelling stage can bypass
the gate, the retry asymmetry holds, there are no cycles, and no path is
hardcoded. These run with no Airflow database — they read the in-memory
`DagBag`, so they work in CI.

Not proven: **the DAG has never been executed.** No scheduler has run it, no
task has invoked a real script, Postgres was never connected, and the Airflow
Variable `philly_project_dir` does not exist yet. The structure is verified; the
execution is not. The first real run needs `airflow variables set
philly_project_dir <path>` and a live Postgres, and should be run one task at a
time with `airflow tasks test` before the DAG is ever unpaused.

---

# 18 — CI: reasoning relocated from the workflow file, and the second job

`.github/workflows/ci.yml` carried its reasoning in comments. Under the
no-comments rule that reasoning has to live here instead, and it is worth
keeping, because three of the steps look redundant and are not.

## 18.1 Why the Python version is pinned to 3.14

`requirements.txt` was frozen against 3.14. On 3.12 several of those pinned
versions have no wheels, so `pip install` either compiles from source or fails
outright — and CI would then be testing a different environment than the one the
work is done in. A green build on the wrong interpreter is worse than a red one.

## 18.2 Why modules are compiled rather than imported

`build.py`, `model.py`, `analyze.py` and the three ingest scripts execute at
module level. A test that imported them would download 2.1M records. `py_compile`
parses without executing, which catches a syntax error in seconds instead of
twenty minutes into a run. This is the same constraint the Airflow DAG hits from
the other direction (§14.2), and it is why every stage there is a
`BashOperator`.

## 18.3 Why pyflakes runs even though py_compile passed

⚠️ `py_compile` checks **syntax**, not **names**. It will happily compile
`Counter()` with no `from collections import Counter`, and the `NameError`
surfaces mid-run. That bug shipped once. pyflakes resolves names without
executing anything, so it works on exactly the modules that cannot be imported.

The two steps are not redundant: one catches malformed code, the other catches
code that is well-formed and wrong.

## 18.4 Why the DAG tests are a separate job

`test_dag.py` needs Apache Airflow, which is a large install, and Airflow 2.10.5
pins SQLAlchemy 1.4 while this project does not. Putting it in the pipeline job
would slow every run and risk a dependency conflict for no benefit.

So there are two jobs. `pipeline` runs on 3.14 (the version `requirements.txt`
was frozen against, per §18.1) with `pytest --ignore=test_dag.py`; `dags` runs on
3.11, installs Airflow separately and runs only `test_dag.py`, with
`AIRFLOW_HOME` pointed at `/tmp` so no state persists. Airflow 2.10.5 does not
support 3.14, which is the second reason the jobs cannot share an interpreter.

This mirrors a conflict hit while building: installing Airflow in a shared
environment downgraded SQLAlchemy to 1.4 and broke an unrelated project's
imports until the two were separated into their own environments. The two-job
split is that lesson applied to CI rather than discovered again in it.

## 18.5 Repository cleanup

- `ci.yml` existed twice — once at the repo root, once at
  `.github/workflows/ci.yml` — byte-identical. The root copy does nothing;
  GitHub only reads workflows from `.github/workflows/`. Removed.
- `test_pipeline.py` was empty (0 bytes) and the real 39-test suite was in
  `test_piprline.py`. pytest collected it anyway, since `test_*.py` matches the
  typo, so the tests ran and the misspelling was invisible in the output.
  Renamed over the empty file; **52 tests** now collect from
  `test_pipeline.py` and `test_dag.py` together.
