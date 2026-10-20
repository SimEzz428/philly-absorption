import json
from collections import defaultdict, Counter
from statistics import median

import numpy as np
import torch
import torch.nn as nn

SEED = 0
SEEDS = (0, 1, 2, 3, 4)
EMB_DIM = 8
USE_ZIP = False
K = 5
TRAIN_CUT = "2021"
TEST_YEAR = "2022"
ISSUE_FLOOR = "2019"
SALE_CUT = "2025"
CATS = ("SINGLE FAMILY", "MULTI FAMILY")
NUM = ["units", "area", "stories", "approx_gfa_per_unit",
       "zip_price", "zip_land", "zip_spread", "zip_activity"]

torch.manual_seed(SEED)
np.random.seed(SEED)

B = json.load(open("data/built.json"))
records = B["records"]


def in_scope(r):
    return (not r["multi_permit"]) and r["parcel_in_opa"]


def has_price(r):
    return bool(r["clean"]) and r["co_date"] and r["co_date"][:4] <= SALE_CUT \
        and r["price"] is not None


def has_build(r):
    return r["permit_to_co_days"] is not None


pool = [r for r in records
        if in_scope(r) and r["cat"] in CATS and r["issue_date"] and r["tract"]
        and ISSUE_FLOOR <= r["issue_date"][:4] <= TEST_YEAR
        and (has_price(r) or has_build(r))]

train = [r for r in pool if r["issue_date"][:4] <= TRAIN_CUT]
test = [r for r in pool if r["issue_date"][:4] == TEST_YEAR]

tracts = sorted({r["tract"] for r in train})
tract_ix = {t: i for i, t in enumerate(tracts)}
zips = sorted({r["zip5"] for r in train if r["zip5"]})
zip_ix = {z: i for i, z in enumerate(zips)}
cats = sorted({r["cat"] for r in train})
cat_ix = {c: i for i, c in enumerate(cats)}

print(f"pool {len(pool):,}   train(<={TRAIN_CUT}) {len(train):,}   "
      f"test({TEST_YEAR}) {len(test):,}")
print(f"tracts in train {len(tracts)}   records per tract "
      f"{len(train) / len(tracts):.1f}")
n_price = sum(1 for r in train if has_price(r))
n_build = sum(1 for r in train if has_build(r))
print(f"train rows with a price {n_price:,}   with a build duration {n_build:,}")


def numeric(rows, fill=None, mu=None, sd=None):
    X = np.full((len(rows), len(NUM)), np.nan, dtype=np.float32)
    for i, r in enumerate(rows):
        for j, f in enumerate(NUM):
            if r[f] is not None:
                X[i, j] = float(r[f])
    miss = np.isnan(X).astype(np.float32)
    if fill is None:
        fill = np.nanmedian(X, axis=0)
        fill = np.where(np.isnan(fill), 0.0, fill)
    X = np.where(np.isnan(X), fill, X)
    if mu is None:
        mu, sd = X.mean(axis=0), X.std(axis=0)
        sd = np.where(sd < 1e-8, 1.0, sd)
    X = (X - mu) / sd
    return np.hstack([X, miss]), fill, mu, sd


def onehot(rows, key, ix):
    out = np.zeros((len(rows), len(ix)), dtype=np.float32)
    for i, r in enumerate(rows):
        j = ix.get(r[key])
        if j is not None:
            out[i, j] = 1.0
    return out


def tract_codes(rows):
    return np.array([tract_ix.get(r["tract"], -1) for r in rows], dtype=np.int64)


def targets(rows):
    p = np.array([r["price"] if has_price(r) else 0.0 for r in rows], dtype=np.float32)
    pm = np.array([1.0 if has_price(r) else 0.0 for r in rows], dtype=np.float32)
    d = np.array([r["permit_to_co_days"] if has_build(r) else 0.0 for r in rows],
                 dtype=np.float32)
    dm = np.array([1.0 if has_build(r) else 0.0 for r in rows], dtype=np.float32)
    return p, pm, d, dm


class TractNet(nn.Module):
    def __init__(self, n_tracts, d_dense, emb_dim=EMB_DIM):
        super().__init__()
        self.emb = nn.Embedding(n_tracts + 1, emb_dim)
        nn.init.normal_(self.emb.weight, std=0.1)
        self.trunk = nn.Sequential(
            nn.Linear(d_dense + emb_dim, 128), nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(128, 64), nn.ReLU(), nn.Dropout(0.2))
        self.price_head = nn.Linear(64, 1)
        self.days_head = nn.Linear(64, 1)

    def forward(self, dense, tix):
        e = self.emb(tix + 1)
        h = self.trunk(torch.cat([dense, e], dim=1))
        return self.price_head(h).squeeze(-1), self.days_head(h).squeeze(-1)


def masked_l1(pred, y, mask):
    if mask.sum() < 1:
        return torch.tensor(0.0)
    return (torch.abs(pred - y) * mask).sum() / mask.sum()


def fit(seed):
    torch.manual_seed(seed)
    rng = np.random.RandomState(seed)

    Dtr, fill, mu, sd = numeric(train)
    parts = [Dtr]
    if USE_ZIP:
        parts.append(onehot(train, "zip5", zip_ix))
    parts.append(onehot(train, "cat", cat_ix))
    Dtr = np.hstack(parts)
    Ttr = tract_codes(train)
    p, pm, d, dm = targets(train)

    p_mu, p_sd = p[pm > 0].mean(), p[pm > 0].std()
    d_mu, d_sd = d[dm > 0].mean(), d[dm > 0].std()
    pn = np.where(pm > 0, (p - p_mu) / p_sd, 0.0).astype(np.float32)
    dn = np.where(dm > 0, (d - d_mu) / d_sd, 0.0).astype(np.float32)

    idx = rng.permutation(len(train))
    cut = int(len(train) * 0.85)
    tr, va = idx[:cut], idx[cut:]

    t = lambda a, i: torch.tensor(a[i])
    model = TractNet(len(tracts), Dtr.shape[1])
    opt = torch.optim.AdamW(model.parameters(), lr=2e-3, weight_decay=1e-4)

    best, best_state, since = float("inf"), None, 0
    for _ in range(600):
        model.train()
        opt.zero_grad()
        ph, dh = model(t(Dtr, tr), t(Ttr, tr))
        loss = masked_l1(ph, t(pn, tr), t(pm, tr)) + masked_l1(dh, t(dn, tr), t(dm, tr))
        loss.backward()
        opt.step()

        model.eval()
        with torch.no_grad():
            ph, dh = model(t(Dtr, va), t(Ttr, va))
            v = float(masked_l1(ph, t(pn, va), t(pm, va))
                      + masked_l1(dh, t(dn, va), t(dm, va)))
        if v < best - 1e-5:
            best, since = v, 0
            best_state = {k: x.clone() for k, x in model.state_dict().items()}
        else:
            since += 1
            if since >= 60:
                break

    if best_state is not None:
        model.load_state_dict(best_state)
    model.eval()
    with torch.no_grad():
        E = model.emb.weight[1:].numpy().copy()
    return E


def neighbours(E, k=K):
    norm = E / (np.linalg.norm(E, axis=1, keepdims=True) + 1e-9)
    sim = norm @ norm.T
    np.fill_diagonal(sim, -np.inf)
    return np.argsort(-sim, axis=1)[:, :k]


train_price_by_tract = defaultdict(list)
train_price_by_zip = defaultdict(list)
for r in train:
    if has_price(r):
        train_price_by_tract[r["tract"]].append(r["price"])
        if r["zip5"]:
            train_price_by_zip[r["zip5"]].append(r["price"])

global_median = median([r["price"] for r in train if has_price(r)])

test_by_tract = defaultdict(list)
for r in test:
    if has_price(r) and r["tract"] in tract_ix:
        test_by_tract[r["tract"]].append(r)

cold = sum(1 for r in test if has_price(r) and r["tract"] not in tract_ix)
print(f"test tracts seen in train {len(test_by_tract)}   "
      f"cold-start test sales {cold}")


def score(nbrs):
    errs = {"embedding": [], "same zip": [], "own tract": [], "citywide": []}
    thin = {"embedding": [], "same zip": []}
    empty = 0
    for t, rows in test_by_tract.items():
        truth = median(r["price"] for r in rows)
        i = tract_ix[t]

        pool_e = [v for j in nbrs[i] for v in train_price_by_tract.get(tracts[j], [])]
        if not pool_e:
            empty += 1
        pred_e = median(pool_e) if pool_e else global_median

        z = rows[0]["zip5"]
        pool_z = train_price_by_zip.get(z, [])
        pred_z = median(pool_z) if pool_z else global_median

        own = train_price_by_tract.get(t, [])
        pred_o = median(own) if own else global_median

        errs["embedding"].append(abs(truth - pred_e))
        errs["same zip"].append(abs(truth - pred_z))
        errs["own tract"].append(abs(truth - pred_o))
        errs["citywide"].append(abs(truth - global_median))

        if len(own) <= 5:
            thin["embedding"].append(abs(truth - pred_e))
            thin["same zip"].append(abs(truth - pred_z))
    return errs, thin, empty


print(f"\n{'=' * 78}\nDO LEARNED COMPS BEAT 'SAME ZIP' COMPS?   "
      f"zip5 as a feature: {'yes' if USE_ZIP else 'no'}\n{'=' * 78}")
print(f"predicting each tract's {TEST_YEAR} median sale price from "
      f"training data only\n")

agg = defaultdict(list)
agg_thin = defaultdict(list)
empties = []
for sd in SEEDS:
    E = fit(sd)
    errs, thin, empty = score(neighbours(E))
    empties.append(empty)
    for k, v in errs.items():
        agg[k].append(median(v))
    for k, v in thin.items():
        agg_thin[k].append(median(v) if v else float("nan"))

n_t = len(test_by_tract)
print(f"{'method':<16}{'median abs error':>20}{'  spread over seeds':<24}{'n tracts':>9}")
for k in ("embedding", "same zip", "own tract", "citywide"):
    vals = agg[k]
    spread = f"{min(vals):,.0f} - {max(vals):,.0f}" if len(set(vals)) > 1 else "fixed"
    print(f"{k:<16}{median(vals):>20,.0f}  {spread:<24}{n_t:>9}")

print("\n  tracts with <=5 training sales only")
for k in ("embedding", "same zip"):
    vals = [v for v in agg_thin[k] if v == v]
    if vals:
        print(f"    {k:<14}{median(vals):>18,.0f}")

print(f"\n  tracts whose 5 neighbours had no sales at all between them: "
      f"{median(empties):.0f} of {n_t}")

E = fit(SEED)
nb = neighbours(E)
counts = Counter(r["tract"] for r in train if has_price(r))
busiest = [t for t, _ in counts.most_common(6)]
print(f"\n{'=' * 78}\nCOMPARABLE SUBMARKETS   seed {SEED}, {K} nearest in embedding space"
      f"\n{'=' * 78}")
for t in busiest:
    i = tract_ix[t]
    own = train_price_by_tract.get(t, [])
    line = []
    for j in nb[i]:
        nt = tracts[j]
        v = train_price_by_tract.get(nt, [])
        line.append(f"{nt}" + (f" (${median(v) / 1000:,.0f}k)" if v else " (no sales)"))
    print(f"  {t}  ${median(own) / 1000:,.0f}k  n={len(own):<4} -> " + ", ".join(line))

print(f"\n{'=' * 78}\nREAD IT\n{'=' * 78}")
print("  If 'embedding' beats 'same zip', the learned comps carry information")
print("  ZIP does not, and the comparable-submarket table above is usable.")
print("  If it does not, the embedding is decoration and belongs in section 6")
print("  of FINDINGS.md with the other claims that did not reproduce.")