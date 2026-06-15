"""Sanity tests for engine_removal.py. Exits non-zero on any failure.

1. kappa=delta=0 reproduces frozen engine.py BIT-FOR-BIT (RNG sequence preserved).
2. Mass balance: daily balance_error == 0 with arrest+home active.
3. sum(M) == M_tot conserved.
4. No negative criminals / NaN; removal fractions sum to 1.
5. Arrest-only and home-only each reduce the criminal population vs baseline.
"""
import os, sys, importlib.util
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
FROZEN = os.path.join(HERE, "..", "transition_scan_20260615_0330")
sys.path.insert(0, HERE)
from engine_removal import run_removal_sim
spec = importlib.util.spec_from_file_location("ef", os.path.join(FROZEN, "engine.py"))
ef = importlib.util.module_from_spec(spec); spec.loader.exec_module(ef)

FAILS = []
def check(name, cond, detail=""):
    print(("PASS" if cond else "FAIL"), name, detail)
    if not cond: FAILS.append(name)

cfg = dict(L=32, T_max=40, M_tot=125.0, seed=0)

for chi in [0.0, 30.0]:
    _, _, fo = ef.run_police_sim(chi=chi, **cfg)
    _, _, fn = run_removal_sim(chi=chi, kappa=0.0, delta=0.0, **cfg)
    check("bit-identical B (chi=%g)" % chi, np.array_equal(fo["B"], fn["B"]))
    check("bit-identical M (chi=%g)" % chi, np.array_equal(fo["M"], fn["M"]))
    bx = len(fo["x"]) == len(fn["x"])
    check("identical #criminals (chi=%g)" % chi, bx, "%d vs %d" % (len(fo["x"]), len(fn["x"])))
    check("identical positions (chi=%g)" % chi,
          bx and np.array_equal(np.sort(fo["x"]), np.sort(fn["x"])))

df, _, fin = run_removal_sim(chi=30.0, kappa=30.0, delta=0.1, **cfg)
check("daily mass balance closes", bool((df.balance_error == 0).all()),
      "max|err|=%d" % int(df.balance_error.abs().max()))
check("M conserved", abs(fin["M"].sum() - cfg["M_tot"]) < 1e-6 * cfg["M_tot"],
      "sum(M)=%.6f" % fin["M"].sum())
check("no negative criminals", bool((df.n_criminals >= 0).all()))
check("no NaN/inf", bool(np.isfinite(df.select_dtypes("number").values).all()))
tot = df.crimes_that_day + df.arrests_that_day + df.home_exits_that_day
check("fractions sum ~1", bool(np.allclose(
    (df.frac_removed_crime + df.frac_removed_arrest + df.frac_removed_home)[tot > 0], 1.0)))

big = dict(L=48, T_max=120, M_tot=125.0 * (48 ** 2) / (64 ** 2))
def tail_mean(**kw):
    return float(np.mean([run_removal_sim(seed=s, **big, **kw)[0].n_criminals.tail(40).mean()
                          for s in (0, 1, 2)]))
base = tail_mean(chi=0.0, kappa=0.0, delta=0.0)
arr  = tail_mean(chi=0.0, kappa=80.0, delta=0.0)
hom  = tail_mean(chi=0.0, kappa=0.0, delta=1.0)
check("arrest-only reduces criminals", arr < base, "%.1f < %.1f" % (arr, base))
check("home-only reduces criminals", hom < base, "%.1f < %.1f" % (hom, base))

print("\n%d check(s) failed" % len(FAILS))
sys.exit(1 if FAILS else 0)
