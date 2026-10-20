import json
from collections import defaultdict
from statistics import median

import numpy as np
import torch
import torch.nn as nn
from sklearn.ensemble import HistGradientBoostingRegressor

SEED = 0
torch.manual_seed(SEED)
np.random.seed(SEED)

B = json.load(open("data/built.json"))
records = B["records"]


def in_scope(r):
    return (not r["multi_permit"]) and r["parcel_in_opa"]


scope = [r for r in records if in_scope(r)]
clean = [r for r in scope if r["clean"]]
CATS = ("SINGLE FAMILY", "MULTI FAMILY")

ISSUE_FLOOR = "2019"
ISSUE_CUT = "2022"
SALE_CUT = "2025"

sale_pool = [r for r in clean
             if r["cat"] in CATS and r["co_date"][:4] <= SALE_CUT
             and r["issue_date"] and ISSUE_FLOOR <= r["issue_date"][:4] <= ISSUE_CUT]

build_pool = [r for r in scope
              if r["cat"] in CATS and r["issue_date"]
              and ISSUE_FLOOR <= r["issue_date"][:4] <= ISSUE_CUT
              and r["permit_to_co_days"] is not None]

EXPECTED = {"build_pool": 3112, "sale_pool": 1177}
actual = {"build_pool": len(build_pool), "sale_pool": len(sale_pool)}
if actual != EXPECTED:
    raise SystemExit(
        f"population drift: {actual} != {EXPECTED}. model.py and this file no "
        f"longer describe the same records, so the comparison is meaningless. "
        f"Reconcile the pool definitions before trusting any number below.")

NUM = ["units", "area", "stories", "approx_gfa_per_unit",
       "zip_price", "zip_land", "zip_spread", "zip_activity"]
CAT = ["cat", "zip5"]
FEATURES = NUM + CAT
CAT_MASK = [f in CAT for f in FEATURES]
MIN_OBS = 5


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


def usable(Xtr):
    return [j for j in range(Xtr.shape[1])
            if len(np.unique(Xtr[:, j][~np.isnan(Xtr[:, j])])) >= 2]


def hgb(Xtr, ytr, mask):
    m = HistGradientBoostingRegressor(
        loss="quantile", quantile=0.5,
        max_iter=300, learning_rate=0.06, min_samples_leaf=20,
        l2_regularization=1.0, categorical_features=mask, random_state=SEED)
    m.fit(Xtr, ytr)
    return m


def onehot(col, n):
    out = np.zeros((len(col), n), dtype=np.float32)
    for i, v in enumerate(col):
        if not np.isnan(v):
            out[i, int(v)] = 1.0
    return out


def prepare(Xtr, Xte, keep, maps):
    num_idx = [j for j in keep if not CAT_MASK[j]]
    cat_idx = [j for j in keep if CAT_MASK[j]]

    tr_num = Xtr[:, num_idx].astype(np.float32)
    te_num = Xte[:, num_idx].astype(np.float32)

    tr_missing = np.isnan(tr_num).astype(np.float32)
    te_missing = np.isnan(te_num).astype(np.float32)

    fill = np.nanmedian(tr_num, axis=0)
    fill = np.where(np.isnan(fill), 0.0, fill)
    tr_num = np.where(np.isnan(tr_num), fill, tr_num)
    te_num = np.where(np.isnan(te_num), fill, te_num)

    mu = tr_num.mean(axis=0)
    sd = tr_num.std(axis=0)
    sd = np.where(sd < 1e-8, 1.0, sd)
    tr_num = (tr_num - mu) / sd
    te_num = (te_num - mu) / sd

    tr_parts, te_parts = [tr_num, tr_missing], [te_num, te_missing]
    for j in cat_idx:
        n = len(maps[FEATURES[j]])
        tr_parts.append(onehot(Xtr[:, j], n))
        te_parts.append(onehot(Xte[:, j], n))

    return np.hstack(tr_parts), np.hstack(te_parts)


class MLP(nn.Module):
    def __init__(self, d):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(d, 128), nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(128, 64), nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(64, 1))

    def forward(self, x):
        return self.net(x).squeeze(-1)


def pinball(pred, y, q=0.5):
    d = y - pred
    return torch.maximum(q * d, (q - 1) * d).mean()


def train_mlp(Xtr, ytr, epochs=400, patience=40):
    n = len(Xtr)
    idx = np.random.RandomState(SEED).permutation(n)
    cut = int(n * 0.85)
    tr, va = idx[:cut], idx[cut:]

    y_mu, y_sd = ytr[tr].mean(), ytr[tr].std()
    y_sd = y_sd if y_sd > 1e-8 else 1.0

    Xt = torch.tensor(Xtr[tr], dtype=torch.float32)
    yt = torch.tensor((ytr[tr] - y_mu) / y_sd, dtype=torch.float32)
    Xv = torch.tensor(Xtr[va], dtype=torch.float32)
    yv = torch.tensor((ytr[va] - y_mu) / y_sd, dtype=torch.float32)

    model = MLP(Xtr.shape[1])
    opt = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)

    best, best_state, since = float("inf"), None, 0
    for _ in range(epochs):
        model.train()
        opt.zero_grad()
        pinball(model(Xt), yt).backward()
        opt.step()

        model.eval()
        with torch.no_grad():
            v = float(pinball(model(Xv), yv))
        if v < best - 1e-5:
            best, best_state, since = v, {k: t.clone() for k, t in model.state_dict().items()}, 0
        else:
            since += 1
            if since >= patience:
                break

    if best_state is not None:
        model.load_state_dict(best_state)
    model.eval()
    return model, y_mu, y_sd


def predict_mlp(model, X, y_mu, y_sd):
    with torch.no_grad():
        p = model(torch.tensor(X, dtype=torch.float32)).numpy()
    return p * y_sd + y_mu


def run(pool, target, label, cutoffs=("2019", "2020", "2021")):
    print(f"\n{'=' * 78}\n{label}   n={len(pool):,}\n{'=' * 78}")
    maps = {c: codes(pool, c) for c in CAT}
    print(f"{'fold':<22}{'n':>6}{'median':>11}{'  via':<8}"
          f"{'HGB':>10}{'MLP':>10}{'  winner':<10}")

    wins = {"median": 0, "HGB": 0, "MLP": 0}
    for cutoff in cutoffs:
        nxt = str(int(cutoff) + 1)
        train = [r for r in pool if r["issue_date"][:4] <= cutoff]
        test = [r for r in pool if r["issue_date"][:4] == nxt]
        if len(train) < 100 or len(test) < 30:
            continue

        Xtr, ytr = matrix(train, maps), np.array([r[target] for r in train], float)
        Xte, yte = matrix(test, maps), np.array([r[target] for r in test], float)

        keep = usable(Xtr)
        mask = [CAT_MASK[j] for j in keep]

        base, which = group_baseline(train, test, target)

        g = hgb(Xtr[:, keep], ytr, mask)
        e_hgb = float(np.median(np.abs(yte - g.predict(Xte[:, keep]))))

        Ptr, Pte = prepare(Xtr, Xte, keep, maps)
        m, y_mu, y_sd = train_mlp(Ptr, ytr)
        e_mlp = float(np.median(np.abs(yte - predict_mlp(m, Pte, y_mu, y_sd))))

        scores = {"median": base, "HGB": e_hgb, "MLP": e_mlp}
        winner = min(scores, key=scores.get)
        wins[winner] += 1

        print(f"train<={cutoff} test {nxt:<8}{len(test):>6}{base:>11,.0f}"
              f"  {which:<8}{e_hgb:>10,.0f}{e_mlp:>10,.0f}  {winner:<10}")

    total = sum(wins.values())
    print(f"\n  folds won   median {wins['median']}/{total}   "
          f"HGB {wins['HGB']}/{total}   MLP {wins['MLP']}/{total}")
    return wins


if __name__ == "__main__":
    print(f"build_pool {len(build_pool):,}   sale_pool {len(sale_pool):,}")
    results = {
        "BUILD DAYS   permit -> certificate of occupancy":
            run(build_pool, "permit_to_co_days", "BUILD DAYS   permit -> certificate of occupancy"),
        "SELL DAYS    C of O -> first recorded sale":
            run(sale_pool, "days", "SELL DAYS    C of O -> first recorded sale"),
        "PRICE ($)":
            run(sale_pool, "price", "PRICE ($)"),
    }

    print(f"\n{'=' * 78}\nVERDICT\n{'=' * 78}")
    for label, w in results.items():
        t = sum(w.values())
        print(f"  {label:<52}median {w['median']}/{t}  HGB {w['HGB']}/{t}  MLP {w['MLP']}/{t}")
