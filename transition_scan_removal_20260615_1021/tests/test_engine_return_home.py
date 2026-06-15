"""Sanity tests for engine_return_home.py. Exits non-zero on any failure.

These are TINY correctness checks (L<=32, T<=40), not model simulations / sweeps.

1. delta=0 reproduces the dissuasion-only model BIT-FOR-BIT. We compare against the
   in-folder `engine_removal.py` with kappa=delta=0, which is itself bit-identical to
   the frozen `engine.py`. (The frozen folder is not always mounted, so we anchor on
   the local reference.)
2. chi=0 => exp(-chi M)=1 => A_tilde = A0 + B (no deterrence effect).
3. Daily mass balance closes: balance_error == 0 with delta>0.
4. sum(M) == M_tot conserved; no NaN; B>=0; A_tilde>=A0.
5. exit fractions (crime+home) sum to 1 on days with removals.
6. delta>0 reduces the criminal population vs delta=0 (the blow-up fix).
7. event log: residence == day - entry_day; residences are non-negative; crime+home
   event counts match the daily aggregates.
8. sequential vs competing differ only at O(dt^2) (sanity, not equality).
"""
import os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from engine_return_home import run_return_home_sim          # noqa: E402
from engine_removal import run_removal_sim                  # noqa: E402  (obsolete ref)

FAILS = []
def check(name, cond, detail=""):
    print(("PASS" if cond else "FAIL"), name, detail)
    if not cond:
        FAILS.append(name)

cfg = dict(L=32, T_max=40, M_tot=125.0, seed=0)

# 1. delta=0 bit-identity vs the dissuasion-only reference (kappa=delta=0)
for chi in [0.0, 30.0]:
    _, _, fo = run_removal_sim(chi=chi, kappa=0.0, delta=0.0, **cfg)
    _, _, fn, _ev = run_return_home_sim(chi=chi, delta=0.0, **cfg)
    check("bit-identical B (chi=%g)" % chi, np.array_equal(fo["B"], fn["B"]))
    check("bit-identical M (chi=%g)" % chi, np.array_equal(fo["M"], fn["M"]))
    bx = len(fo["x"]) == len(fn["x"])
    check("identical #criminals (chi=%g)" % chi, bx, "%d vs %d" % (len(fo["x"]), len(fn["x"])))
    check("identical positions (chi=%g)" % chi,
          bx and np.array_equal(np.sort(fo["x"]), np.sort(fn["x"])))

# 2. chi=0 => no deterrence: A_tilde == A0 + B at every snapshot
df0, snaps0, fin0, _ = run_return_home_sim(chi=0.0, delta=1/15, snapshot_days=[40], **cfg)
sn = snaps0[40]
check("chi=0 no deterrence (deter==1)", np.allclose(sn["deter"], 1.0))
check("chi=0 A_tilde == A0 + B", np.allclose(sn["A_tilde"], 1/30 + sn["B"]))

# 3-5. mass balance, conservation, guards, fractions (delta>0, chi>0)
df, _, fin, ev = run_return_home_sim(chi=30.0, delta=0.1, event_log=True, **cfg)
check("daily mass balance closes", bool((df.balance_error == 0).all()),
      "max|err|=%d" % int(df.balance_error.abs().max()))
check("M conserved", abs(fin["M"].sum() - cfg["M_tot"]) < 1e-6 * cfg["M_tot"],
      "sum(M)=%.6f" % fin["M"].sum())
check("no negative criminals", bool((df.n_criminals >= 0).all()))
check("no NaN/inf", bool(np.isfinite(df.select_dtypes("number").values).all()))
check("B >= 0", bool(fin["B"].min() >= -1e-9))
check("A_tilde >= A0", bool((1/30 + fin["B"] * np.exp(-30.0 * fin["M"])).min() >= 1/30 - 1e-9))
tot = df.crimes_that_day + df.home_exits_that_day
check("exit fractions sum ~1", bool(np.allclose(
    (df.frac_exit_crime + df.frac_exit_home)[tot > 0], 1.0)))

# 6. delta>0 fixes the blow-up: in the strong-dissuasion regime (chi=30, g~3.7) the
#    dissuasion-only population inflates; the home channel must cut it substantially.
def tail_N(delta, seeds=(0, 1, 2)):
    return float(np.mean([run_return_home_sim(L=32, T_max=80, M_tot=125.0, chi=30.0,
                                              delta=delta, seed=s)[0].n_criminals.tail(20).mean()
                          for s in seeds]))
N0 = tail_N(0.0); Nd = tail_N(1/15)
check("delta>0 fixes blow-up (reduces N at chi=30)", Nd < N0, "%.1f < %.1f" % (Nd, N0))

# 7. event log consistency
check("residence == day - entry_day", bool(np.allclose(ev.residence, ev.day - ev.entry_day)))
check("residence non-negative", bool((ev.residence >= -1e-12).all()))
n_crime_ev = int((ev.type == "crime").sum())
n_home_ev = int((ev.type == "home_exit").sum())
check("logged crimes == daily sum", n_crime_ev == int(df.crimes_that_day.sum()),
      "%d vs %d" % (n_crime_ev, int(df.crimes_that_day.sum())))
check("logged home == daily sum", n_home_ev == int(df.home_exits_that_day.sum()),
      "%d vs %d" % (n_home_ev, int(df.home_exits_that_day.sum())))

# 8. competing vs sequential: same engine, ~equal but not identical
ds, _, _, _ = run_return_home_sim(chi=10.0, delta=0.1, event_order="sequential", **cfg)
dc, _, _, _ = run_return_home_sim(chi=10.0, delta=0.1, event_order="competing", **cfg)
rel = abs(ds.n_criminals.tail(20).mean() - dc.n_criminals.tail(20).mean()) / max(
    ds.n_criminals.tail(20).mean(), 1)
check("sequential ~ competing (small diff)", rel < 0.5, "rel diff=%.3f" % rel)

print("\n%d check(s) failed" % len(FAILS))
sys.exit(1 if FAILS else 0)
