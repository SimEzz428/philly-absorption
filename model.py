import json
from collections import defaultdict, Counter
from statistics import median
import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.inspection import permutation_importance
from lib import carry_cost, max_build_budget

B = json.load(open("data/built.json"))
records = B["records"]


def in_scope(r):
    return (not r["multi_permit"]) and r["parcel_in_opa"]


def pctl(sorted_vals, p):
    return sorted_vals[min(int(len(sorted_vals) * p), len(sorted_vals) - 1)]


scope = [r for r in records if in_scope(r)]
clean = [r for r in scope if r["clean"]]
CATS  = ("SINGLE FAMILY", "MULTI FAMILY")

ISSUE_FLOOR = "2019"
ISSUE_CUT   = "2022"
SALE_CUT    = "2025"

sale_pool = [r for r in clean
             if r["cat"] in CATS and r["co_date"][:4] <= SALE_CUT
             and r["issue_date"] and ISSUE_FLOOR <= r["issue_date"][:4] <= ISSUE_CUT]

build_pool = [r for r in scope
              if r["cat"] in CATS and r["issue_date"]
              and ISSUE_FLOOR <= r["issue_date"][:4] <= ISSUE_CUT
              and r["permit_to_co_days"] is not None]

print(f"build_pool {len(build_pool):,}   sale_pool {len(sale_pool):,}")

NUM = ["units", "area", "stories", "approx_gfa_per_unit",
       "zip_price", "zip_land", "zip_spread", "zip_activity"]
CAT = ["cat", "zip5"]
FEATURES = NUM + CAT
CAT_MASK = [f in CAT for f in FEATURES]


def codes(pool, col):
    return {v: i for i, v in enumerate(sorted({r[col] for r in pool
                                               if r[col] is not None}))}


def matrix(pool, maps):
    X = np.full((len(pool), len(FEATURES)), np.nan)
    for i, r in enumerate(pool):
        for j, f in enumerate(FEATURES):
            v = maps[f].get(r[f]) if f in CAT else r[f]
            if v is not None:
                X[i, j] = float(v)
    return X


def fit(X, y, q, mask):
    m = HistGradientBoostingRegressor(
        loss="quantile", quantile=q,
        max_iter=300, learning_rate=0.06, min_samples_leaf=20,
        l2_regularization=1.0, categorical_features=mask, random_state=0)
    m.fit(X, y)
    return m


def usable(Xtr):
    keep = []
    for j in range(Xtr.shape[1]):
        col = Xtr[:, j]
        if len(np.unique(col[~np.isnan(col)])) >= 2:
            keep.append(j)
    return keep


MIN_OBS = 5


def group_baseline(train, test, target):
    g = median(r[target] for r in train)
    best = median(abs(r[target] - g) for r in test)
    which = "global"
    for key in ("tract", "zip5", "cat"):
        d = defaultdict(list)
        for r in train:
            d[r[key]].append(r[target])
        pred = {k: median(v) for k, v in d.items() if len(v) >= MIN_OBS}
        e = median(abs(r[target] - pred.get(r[key], g)) for r in test)
        if e < best:
            best, which = e, key
    return best, which


def run(pool, target, label, cutoffs=("2019", "2020", "2021")):
    print(f"\n{'='*74}\n{label}   n={len(pool):,}\n{'='*74}")
    maps = {c: codes(pool, c) for c in CAT}
    print(f"{'fold':<22}{'n':>6}{'baseline':>11}{'  via':<8}"
          f"{'model':>10}{'lift':>8}{'cover':>8}")
    last = None
    for cutoff in cutoffs:
        nxt = str(int(cutoff) + 1)
        train = [r for r in pool if r["issue_date"][:4] <= cutoff]
        test  = [r for r in pool if r["issue_date"][:4] == nxt]
        if len(train) < 100 or len(test) < 30:
            continue
        Xtr, ytr = matrix(train, maps), np.array([r[target] for r in train], float)
        Xte, yte = matrix(test,  maps), np.array([r[target] for r in test],  float)

        keep = usable(Xtr)
        mask = [CAT_MASK[j] for j in keep]
        Xtr, Xte = Xtr[:, keep], Xte[:, keep]

        base, which = group_baseline(train, test, target)
        mid = fit(Xtr, ytr, 0.5, mask)
        err = float(np.median(np.abs(yte - mid.predict(Xte))))

        lo, hi = fit(Xtr, ytr, 0.1, mask), fit(Xtr, ytr, 0.9, mask)
        inside = np.mean((yte >= lo.predict(Xte)) & (yte <= hi.predict(Xte)))

        print(f"train<={cutoff} test {nxt:<8}{len(test):>6}{base:>11,.0f}"
              f"  {which:<8}{err:>10,.0f}{(base-err)/base:>8.1%}{inside:>8.0%}")
        last = (Xtr, ytr, Xte, yte, keep, mask)

    if last is None:
        return None
    Xtr, ytr, Xte, yte, keep, mask = last
    final = fit(Xtr, ytr, 0.5, mask)
    imp = permutation_importance(final, Xte, yte, n_repeats=10,
                                 random_state=0, scoring="neg_median_absolute_error")
    print("\n  permutation importance (last fold)")
    names = [FEATURES[j] for j in keep]
    for j in np.argsort(-imp.importances_mean)[:6]:
        print(f"    {names[j]:<22}{imp.importances_mean[j]:>10,.1f}"
              f"  +/-{imp.importances_std[j]:>8,.1f}")

    Xall = matrix(pool, maps)
    kall = usable(Xall)
    mall = [CAT_MASK[j] for j in kall]
    yall = np.array([r[target] for r in pool], float)
    models = {q: fit(Xall[:, kall], yall, q, mall) for q in (0.1, 0.5, 0.9)}
    return models, maps, kall


build_m = run(build_pool, "permit_to_co_days", "BUILD DAYS   permit -> certificate of occupancy")
sell_m  = run(sale_pool,  "days",              "SELL DAYS    C of O -> first recorded sale")
price_m = run(sale_pool,  "price",             "PRICE ($)")


MIN_CELL = 15

COST_PER_UNIT   = 300_000.0
LOAN_RATE       = 0.09
HURDLE          = 0.15
COST_PER_FILING =  25_000.0

acq_year = defaultdict(set)
acq_n    = Counter()
for r in scope:
    if r["land_date"] and r["zip5"]:
        acq_n[r["zip5"]] += 1
        acq_year[r["zip5"]].add(r["land_date"][:4])
site_velocity = {z: acq_n[z] / len(yrs) for z, yrs in acq_year.items() if yrs}

build_cells = defaultdict(list)
for r in build_pool:
    build_cells[(r["zip5"], r["cat"])].append(r)
sale_cells = defaultdict(list)
for r in sale_pool:
    sale_cells[(r["zip5"], r["cat"])].append(r)

(bm, bmaps, bk), (sm, smaps, sk), (pm, pmaps, pk) = build_m, sell_m, price_m

out = []
samples = {}
for key, rs in build_cells.items():
    srs = sale_cells.get(key, [])
    if len(rs) < MIN_CELL or len(srs) < MIN_CELL:
        continue
    z, cat = key

    bvals = sorted(r["permit_to_co_days"] for r in rs)
    svals = sorted(r["days"] for r in srs)
    build, b_lo, b_hi = median(bvals), pctl(bvals, .10), pctl(bvals, .90)
    sell = median(svals)

    Xp = matrix(srs, pmaps)[:, pk]
    price = float(np.median(pm[0.5].predict(Xp)))
    p_lo  = float(np.median(pm[0.1].predict(Xp)))
    p_hi  = float(np.median(pm[0.9].predict(Xp)))

    obs_land, px_land, land_vals = [], [], []
    for r in srs:
        if r["land_in_window"] and r["land_price"]:
            obs_land.append(r["land_price"])
            land_vals.append(r["land_price"])
        elif r["zip_land"]:
            px_land.append(r["zip_land"])
            land_vals.append(r["zip_land"])
    if not land_vals:
        continue
    land     = median(land_vals)
    land_obs = len(obs_land) / len(srs)

    lags = [r["land_lag_days"] for r in srs if r["land_lag_days"] is not None]
    hold = median(lags) if lags else None

    drs  = [r["zip_zoning_denial"] for r in srs
            if r["zip_zoning_denial"] is not None]
    ents = [r["entitlement_days"] for r in srs
            if r["entitlement_days"] is not None and r["entitlement_days"] >= 0]
    denial  = drs[0] if drs else None
    entitle = median(ents) if ents else None

    total = build + sell
    total_full = (hold + total) if hold is not None else None

    gfas  = [r["approx_gfa_per_unit"] for r in srs if r["approx_gfa_per_unit"]]
    unitv = [r["units"] for r in srs if r["units"]]
    gfa   = (median(gfas) * median(unitv)) if (gfas and unitv) else None
    hard  = median(unitv) * COST_PER_UNIT if unitv else None

    carry_per_100k = LOAN_RATE * total / 365.0 * 100_000

    carry = carry_cost(land, hard, build, sell, LOAN_RATE) if hard else None
    basis = (land + hard + carry) if hard else None
    one_unit = bool(unitv) and median(unitv) == 1
    profit = (price - basis) if (basis and one_unit) else None
    roc    = (profit / basis) if profit is not None else None
    ann    = (roc * 365.0 / max(total, 1)) if roc is not None else None

    samples[(z, cat)] = dict(b=bvals, s=svals, l=land_vals,
                             p=list(pm[0.5].predict(Xp)))

    out.append(dict(zip5=z, cat=cat, nb=len(rs), ns=len(srs),
                    build=build, b_lo=b_lo, b_hi=b_hi, sell=sell, total=total,
                    hold=hold, total_full=total_full,
                    denial=denial, entitle=entitle,
                    sites_per_year=site_velocity.get(z),
                    price=price, p_lo=p_lo, p_hi=p_hi, land=land,
                    land_obs=land_obs, n_obs=len(obs_land),
                    obs_median=median(obs_land) if obs_land else None,
                    px_median=median(px_land) if px_land else None,
                    gfa=gfa, price_per_claimed_sqft=(price / gfa) if gfa else None,
                    carry_per_100k=carry_per_100k,
                    hard=hard, carry=carry, basis=basis,
                    profit=profit, roc=roc, annualized=ann,
                    spread=price - land, per_day=(price - land) / max(total, 1)))

print(f"\n{'='*110}")
print("WHERE TO BUILD - ranked by spread per day of total capital carry")
print(f"{'='*110}")
print(f"{'zip':<7}{'product':<15}{'n':>5}{'build d':>9}{'(10-90)':>14}"
      f"{'sell d':>8}{'total':>7}{'price $':>11}{'land $':>10}{'$/day':>8}")
print("-" * 110)
for c in sorted(out, key=lambda c: -c["per_day"]):
    thin = "  thin" if min(c["nb"], c["ns"]) < 30 else ""
    band = "({:,.0f}-{:,.0f})".format(c["b_lo"], c["b_hi"])
    print(f"{c['zip5']:<7}{c['cat'][:14]:<15}{min(c['nb'],c['ns']):>5}"
          f"{c['build']:>9,.0f}{band:>14}"
          f"{c['sell']:>8,.0f}{c['total']:>7,.0f}{c['price']:>11,.0f}"
          f"{c['land']:>10,.0f}{c['per_day']:>8,.0f}{thin}")

print("""
build d, sell d   observed medians for this cell. Gradient boosting LOST to a
                  group median on both targets across held-out years, so the
                  model is not used here. (build 10-90) is the empirical range.
price $           model prediction. It beat its baseline on all three folds
                  (+2.0%, +5.3%, +18.7%), so it earned its place.
thin              fewer than 30 observed projects; treat the ranking as a hint.
land $            observed acquisition price where recoverable within
                  LAND_LOOKBACK_YEARS, zip-year median otherwise. The next
                  table reports which, and measures the gap between them.
$/day             revenue-minus-land per day. NOT a return: construction cost
                  is absent, so this is money available to cover cost and
                  profit. The hurdle tables below are the defensible version.""")


both = [c for c in out if c["obs_median"] and c["px_median"]]
if both:
    print(f"\n{'='*92}")
    print("OBSERVED LAND PRICE vs THE ZIP-MEDIAN PROXY")
    print(f"{'='*92}")
    print(f"{'zip':<7}{'product':<15}{'obs n':>7}{'obs %':>7}"
          f"{'observed $':>12}{'proxy $':>11}{'proxy error':>13}")
    print("-" * 92)
    for c in sorted(both, key=lambda c: -c["land_obs"]):
        err = c["px_median"] - c["obs_median"]
        print(f"{c['zip5']:<7}{c['cat'][:14]:<15}{c['n_obs']:>7}"
              f"{c['land_obs']:>7.0%}{c['obs_median']:>12,.0f}"
              f"{c['px_median']:>11,.0f}{err:>+13,.0f}")
    errs = [c["px_median"] - c["obs_median"] for c in both]
    print(f"\nmedian proxy error: {median(errs):+,.0f}  "
          f"({sum(1 for e in errs if e < 0)} of {len(errs)} cells understated)")
    print("Negative = the proxy is LOWER than what developers actually paid, so")
    print("spread and allowable budget were both overstated wherever it was used.")


print(f"\n{'='*92}")
print(f"WHAT THE TIME COSTS - interest per $100,000 of capital, at {LOAN_RATE:.0%}")
print(f"{'='*92}")
print(f"{'zip':<7}{'product':<15}{'n':>5}{'build d':>9}{'sell d':>8}{'total':>7}"
      f"{'carry / $100k':>15}")
print("-" * 92)
ranked = sorted(out, key=lambda c: c["carry_per_100k"])
for c in ranked:
    print(f"{c['zip5']:<7}{c['cat'][:14]:<15}{min(c['nb'],c['ns']):>5}"
          f"{c['build']:>9,.0f}{c['sell']:>8,.0f}{c['total']:>7,.0f}"
          f"{c['carry_per_100k']:>15,.0f}")

if len(ranked) >= 2:
    fast, slow = ranked[0], ranked[-1]
    gap = slow["carry_per_100k"] - fast["carry_per_100k"]
    print(f"\nTIME ALONE: {slow['zip5']} {slow['cat']} commits capital "
          f"{slow['total']-fast['total']:,.0f} days longer than "
          f"{fast['zip5']} {fast['cat']}")
    print(f"            ${gap:,.0f} of extra interest per $100,000 committed, "
          f"before anyone has")
    print(f"            argued about construction cost. On a "
          f"${COST_PER_UNIT:,.0f} basis that is ${gap * COST_PER_UNIT / 100_000:,.0f}.")

print("\nNo cost assumption, no floor-area estimate, nothing invented: this needs")
print("only the two observed durations and the rate, which is the user's input.")


print(f"\n{'='*92}")
print("WHY COST IS QUOTED PER DWELLING, NOT PER SQFT")
print(f"{'='*92}")
print(f"{'zip':<7}{'product':<15}{'claimed gfa':>13}{'price $':>11}{'$/claimed sqft':>16}")
for c in sorted((c for c in out if c["gfa"]), key=lambda c: -c["price_per_claimed_sqft"]):
    print(f"{c['zip5']:<7}{c['cat'][:14]:<15}{c['gfa']:>13,.0f}"
          f"{c['price']:>11,.0f}{c['price_per_claimed_sqft']:>16,.0f}")
print("""
approx_gfa_per_unit = areaofdisturbance x storeys / units. It ranks product tier
usefully - it leads the sell-days importance table - but as an ABSOLUTE square
footage it fails: $/claimed-sqft falls as claimed area rises, which is
measurement error, not market variation. A feature can be valid for ORDERING and
invalid as a QUANTITY. So cost is an input per dwelling, never per sqft.""")


deals = [c for c in out if c["annualized"] is not None]
if deals:
    print(f"\n{'='*96}")
    print(f"DEAL ARITHMETIC - single-dwelling cells, ${COST_PER_UNIT:,.0f}/dwelling, "
          f"loan {LOAN_RATE:.0%}")
    print(f"{'='*96}")
    print(f"{'zip':<7}{'n':>5}{'days':>6}{'land $':>10}{'hard $':>10}{'carry $':>10}"
          f"{'basis $':>11}{'price $':>11}{'profit $':>11}{'ROC':>7}{'ann':>7}")
    print("-" * 96)
    for c in sorted(deals, key=lambda c: -c["annualized"]):
        print(f"{c['zip5']:<7}{min(c['nb'],c['ns']):>5}{c['total']:>6,.0f}"
              f"{c['land']:>10,.0f}{c['hard']:>10,.0f}{c['carry']:>10,.0f}"
              f"{c['basis']:>11,.0f}{c['price']:>11,.0f}"
              f"{c['profit']:>11,.0f}{c['roc']:>7.1%}{c['annualized']:>7.1%}")
    print("\nhard $ is YOUR cost per dwelling, not the model's. ROC = profit/basis;")
    print("ann annualises it over total days, so it is comparable to a hurdle rate.")
    print("Single-dwelling cells only: for multi-unit parcels one deed is not known")
    print("to equal one project's revenue, so the margin would be unfounded.")


print(f"\n{'='*96}")
print(f"MAXIMUM BUILD BUDGET per dwelling to clear {HURDLE:.0%} annualised, "
      f"loan {LOAN_RATE:.0%}")
print(f"{'='*96}")
print(f"{'zip':<7}{'n':>5}{'hold':>6}{'dev d':>7}{'all d':>7}"
      f"{'price $':>11}{'land $':>10}{'max (dev)':>12}{'max (all-in)':>14}"
      f"{'delta':>11}")
print("-" * 96)
for c in deals:
    c["budget_dev"] = max_build_budget(
        c["price"], c["land"], c["build"], c["sell"], LOAN_RATE, HURDLE)
    c["budget_all"] = (max_build_budget(
        c["price"], c["land"], c["build"], c["sell"], LOAN_RATE, HURDLE,
        hold_days=c["hold"]) if c["hold"] is not None else None)

for c in sorted(deals, key=lambda c: -c["budget_dev"]):
    s_hold  = f"{c['hold']:,.0f}"       if c["hold"]       is not None else "-"
    s_all_d = f"{c['total_full']:,.0f}" if c["total_full"] is not None else "-"
    s_all   = f"{c['budget_all']:,.0f}" if c["budget_all"] is not None else "-"
    s_delta = (f"{c['budget_all'] - c['budget_dev']:+,.0f}"
               if c["budget_all"] is not None else "-")
    print(f"{c['zip5']:<7}{min(c['nb'],c['ns']):>5}{s_hold:>6}"
          f"{c['total']:>7,.0f}{s_all_d:>7}"
          f"{c['price']:>11,.0f}{c['land']:>10,.0f}"
          f"{c['budget_dev']:>12,.0f}{s_all:>14}{s_delta:>11}")

print(f"""
hold          median acquisition -> permit-issue gap for this cell
max (dev)     "I already own the land - is building worth it?"
max (all-in)  "was buying AND building worth it?"  Land carries the whole
              period including entitlement; construction does not, so the
              holding period cannot simply be added to build days.
delta         what counting the holding period costs you in build budget.
Both columns are legitimate and they answer different questions. Neither
assumes a construction cost: they ask what cost the market will support, which
is the question a developer can actually answer. Compare against
COST_PER_UNIT = ${COST_PER_UNIT:,.0f}.""")


priced = [c for c in deals if c["denial"] is not None]
if priced:
    print(f"\n{'='*100}")
    print(f"APPROVAL FRICTION PRICED - ${COST_PER_FILING:,.0f} per filing attempt")
    print(f"{'='*100}")
    print(f"{'zip':<7}{'n':>5}{'refusal':>9}{'entitle d':>11}{'exp. sunk $':>13}"
          f"{'max (dev)':>12}{'risk-adj':>12}{'rank move':>11}")
    print("-" * 100)
    for c in priced:
        p = 1.0 - c["denial"]
        c["sunk"] = ((1.0 / p) - 1.0) * COST_PER_FILING if p > 0 else None
        c["budget_risk"] = (c["budget_dev"] - c["sunk"]) if c["sunk"] is not None else None
    before = [c["zip5"] for c in sorted(priced, key=lambda c: -c["budget_dev"])]
    after  = [c["zip5"] for c in sorted(priced, key=lambda c: -(c["budget_risk"] or 0))]
    for c in sorted(priced, key=lambda c: -(c["budget_risk"] or 0)):
        mv = before.index(c["zip5"]) - after.index(c["zip5"])
        s_ent = f"{c['entitle']:,.0f}" if c["entitle"] is not None else "-"
        print(f"{c['zip5']:<7}{min(c['nb'],c['ns']):>5}{c['denial']:>9.1%}"
              f"{s_ent:>11}{c['sunk']:>13,.0f}{c['budget_dev']:>12,.0f}"
              f"{c['budget_risk']:>12,.0f}{mv:>+11}")

    with_ent = [c for c in priced if c["entitle"] is not None]
    if len(with_ent) >= 2:
        fast = min(with_ent, key=lambda c: c["entitle"])
        slow = max(with_ent, key=lambda c: c["entitle"])
        gap_d = slow["entitle"] - fast["entitle"]
        cost  = slow["land"] * gap_d / 365.0 * LOAN_RATE
        print("\nTHE QUEUE, NOT THE REJECTION:")
        print(f"  {slow['zip5']} waits {slow['entitle']:,.0f} days from zoning "
              f"approval to building permit; {fast['zip5']} waits "
              f"{fast['entitle']:,.0f}.")
        print(f"  That {gap_d:,.0f}-day gap, on {slow['zip5']}'s "
              f"${slow['land']:,.0f} of land at {LOAN_RATE:.0%}, is "
              f"${cost:,.0f} of pure carry")
        print(f"  - against ${max(c['sunk'] for c in priced):,.0f} for the worst "
              f"refusal risk in the table.")

    print(f"""
refusal       share of ZONING applications in this zip that were Denied or
              Refused. Measured on zoning, not building permits: only 4 of
              10,726 residential new-construction BUILDING applications were
              refused, because Philadelphia refuses at the zoning stage and
              you have already cleared it before filing to build.
entitle d     zoning permit -> building permit. Sits INSIDE the land holding
              period, so it explains the wait rather than extending it.
exp. sunk $   (1/(1-refusal) - 1) x ${COST_PER_FILING:,.0f}: what you expect to
              spend on filings that produce nothing, per successful project.
rank move     places gained by pricing refusal risk.""")


BOOT = 2000
rng = np.random.default_rng(0)


def boot_medians(vals, n_iter):
    a = np.asarray(vals, float)
    idx = rng.integers(0, len(a), size=(n_iter, len(a)))
    return np.median(a[idx], axis=1)


cells  = list(deals)
budget = np.zeros((BOOT, len(cells)))
for j, c in enumerate(cells):
    s = samples[(c["zip5"], c["cat"])]
    bb = boot_medians(s["b"], BOOT)
    ss = boot_medians(s["s"], BOOT)
    pp = boot_medians(s["p"], BOOT)
    ll = boot_medians(s["l"], BOOT)
    for i in range(BOOT):
        budget[i, j] = max_build_budget(pp[i], ll[i], bb[i], ss[i],
                                        LOAN_RATE, HURDLE)

top3 = np.zeros(len(cells))
for i in range(BOOT):
    for j in np.argsort(-budget[i])[:3]:
        top3[j] += 1
top3 /= BOOT

print(f"\n{'='*96}")
print(f"IS THE RANKING REAL? - {BOOT:,} bootstrap resamples per cell")
print(f"{'='*96}")
print(f"{'zip':<7}{'n':>5}{'max build $':>13}{'bootstrap p10-p90':>24}"
      f"{'top-3 share':>14}")
print("-" * 96)
order = np.argsort(-top3)
for j in order:
    c = cells[j]
    lo, hi = np.percentile(budget[:, j], [10, 90])
    band = f"{lo:,.0f} - {hi:,.0f}"
    print(f"{c['zip5']:<7}{min(c['nb'],c['ns']):>5}{c['budget_dev']:>13,.0f}"
          f"{band:>24}{top3[j]:>14.0%}")


contenders = int((top3 > 0.10).sum())
print(f"\n{contenders} of {len(cells)} submarkets reach the top three in more "
      f"than 10% of resamples.")
if contenders > 4:
    print("The 1-to-14 order is NOT defensible - report tiers, not ranks. Any")
    print("two cells whose p10-p90 bands overlap are not distinguishable with")
    print("this much data, and saying so is the finding.")
else:
    print("A small set of submarkets wins consistently, so the top of the")
    print("ranking is defensible. The tail still is not - check the bands.")
print("Resampling is WITHIN each cell, so this measures sampling noise given")
print("the project counts you actually have. It does NOT capture model error,")
print("the land proxy's bias, or the 2019-2022 window being unrepresentative.")


sup = [c for c in deals if c["sites_per_year"]]
if sup:
    idx = {cells[j]["zip5"]: top3[j] for j in range(len(cells))}
    print(f"\n{'='*92}")
    print("CAN I BUY IN? - allowable budget against observed site turnover")
    print(f"{'='*92}")
    print(f"{'zip':<7}{'n':>5}{'max build $':>13}{'top-3 %':>10}"
          f"{'sites/yr':>10}{'yrs per site':>14}")
    print("-" * 92)
    for c in sorted(sup, key=lambda c: -c["budget_dev"]):
        print(f"{c['zip5']:<7}{min(c['nb'],c['ns']):>5}{c['budget_dev']:>13,.0f}"
              f"{idx.get(c['zip5'], 0):>10.0%}{c['sites_per_year']:>10.1f}"
              f"{1.0/c['sites_per_year']:>14.1f}")

    top  = [c for c in sup if idx.get(c["zip5"], 0) > 0.50]
    rest = [c for c in sup if idx.get(c["zip5"], 0) <= 0.50]
    if top and rest:
        tv, rv = (median([c["sites_per_year"] for c in top]),
                  median([c["sites_per_year"] for c in rest]))
        print(f"""
THE TENSION: the top tier turns over {tv:.1f} sites a year. Everywhere else
             turns over {rv:.1f}. The submarkets that clear the hurdle are the
             ones where a site is hardest to find, and that is not a
             coincidence - it is what scarcity does to price.

             So the answer is not "build in the top tier". It is "build there
             IF you can source a site, and at observed turnover expect roughly
             {1/tv:.1f} years of searching per site."

sites/yr     observed developer acquisitions per year, from deeds preceding a
             permit. NOT from parcels currently assessed vacant, which is
             stale on 68% of built parcels and would undercount exactly where
             development happened.

⚠️ THIS IS A LOWER BOUND, AND THE BIAS IS NOT UNIFORM. Only 32.9% of permits
   have a recoverable acquisition, and per-cell coverage ranges 22% to 69%.
   So true turnover is roughly 1.5-4x these figures, and a cell with low
   coverage looks scarcer than it is. Treat the ordering as indicative and do
   not quote the absolute years-per-site without that caveat.""")

json.dump(out, open("data/recommendations.json", "w"), indent=1)
print(f"\nwrote data/recommendations.json - {len(out)} cells, {len(deals)} with deal arithmetic")