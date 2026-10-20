# Philadelphia development screener

Which Philadelphia neighborhoods are actually worth building a house in?

This links 2.1M city records — building permits, property deeds, and tax
assessments — and answers that question with a number instead of a hunch.

## The answer

Single-family new construction, $300,000 per dwelling, 9% loan, 15% annualised
hurdle. **Of 14 submarkets, 3 clear it:**

| ZIP | | annualised | return on basis | land | days | profit |
|---|---|---|---|---|---|---|
| **19128** | Roxborough | **19.9%** | 36.2% | $146,250 | 666 | $179,904 |
| **19119** | Mt Airy | **19.7%** | 37.5% | $45,750 | 695 | $143,167 |
| **19147** | Queen Village | **19.2%** | 35.1% | $287,500 | 665 | $232,058 |

Pick by what you are short of:

- **Least capital** — Mt Airy. Land is $45,750, a sixth of Queen Village, and it
  returns the most per dollar at risk (37.5%).
- **Most profit per deal** — Queen Village, $232,058. But you need $287,500 of
  land first.
- **Most reliable** — Roxborough. It lands in the top three in 75% of 2,000
  bootstrap resamples, the highest of any submarket.

**Avoid 19143 Kingsessing.** At the same cost it loses $12,187 per house, −1.5%
annualised. It is not a thin margin; it does not pencil.

## The catch, which is the real finding

**The top tier turns over 2.4 sites a year. Everywhere else turns over 12.1.**

The submarkets that clear the hurdle are exactly the ones where a site is
hardest to buy, and that is not bad luck — it is what scarcity does to price. At
observed turnover, expect roughly **five months of searching per site** in
Roxborough.

So the recommendation is not "build in the top tier." It is: build there *if you
can source a site*, and keep Fairhill (19133, 11.6% but 13.8 sites a year) as
the place you can actually deploy capital on schedule.

## And the order is not real

7 of 14 submarkets reach the top three in more than 10% of resamples. Any two
whose confidence bands overlap are not distinguishable with this much data. So
this reports **tiers, not a 1-to-14 ranking** — the three above are a tier, and
saying so is part of the result.

## How it works

```
permits + deeds + assessments  ->  Postgres  ->  link on parcel  ->  rank
     (3 city APIs)                            (join + validate)
```

Five stages, each a plain Python script:

| | |
|---|---|
| `ingest_*.py` | pull from the three city APIs, resumable |
| `load_pg.py` | load into Postgres |
| `build.py` | link records into projects, write `data/built.json` |
| `analyze.py` | rank the submarkets |
| `model.py` | predict build time, sale time, and price |

`dags/philly_absorption.py` runs all of it on a schedule.

## Run it

```sh
pip install -r requirements.txt
psql -f schema.sql
python3 ingest_permits.py && python3 ingest_rtt.py && python3 ingest_opa.py
python3 load_pg.py
python3 build.py
python3 analyze.py
```

Tests need no data and no network:

```sh
pytest -q --ignore=test_dag.py
```

## Things worth knowing

**The ranking does not hold up over time.** Price rankings transfer between
two-year periods (rho 0.88), but build-duration rankings do not (rho −0.13). So
this tells you where to build now; it does not predict next year.

**Which clock you use changes the winner.** Priced over the development period
alone, Queen Village allows the biggest build budget ($336,787). Priced over the
whole capital commitment including hold time, Roxborough wins ($289,261 against
Queen Village's $265,994) — because Queen Village's money sits idle for 277 days
on top of the build. Reporting only the development clock would have named the
wrong submarket.

**The model is honest about not knowing.** Its 80% prediction intervals only
contain the true answer 50–67% of the time, so the tool ships the measured
intervals rather than the ones the model claims.

**A tract's own sale history beats its neighbors by 35%.** Widening the comp
search to nearby tracts makes estimates worse, not better. So don't widen it.

**The obvious join key was wrong.** Joining permits on their ID returned 224
duplicates. The real key is (system, type, number), which also made queries
3,516x faster.




