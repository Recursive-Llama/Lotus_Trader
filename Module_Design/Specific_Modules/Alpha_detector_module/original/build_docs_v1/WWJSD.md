Alright—let’s build the Simons-style Divergence Engine the way a Renaissance desk would: as residual factories + regime gates + micro-triggered execution. I’ll “spiral” from principles → concrete components → registries → training loop → live loop → governance. No drawings, just objects you can code.

0) North star

A “divergence” is a standardized innovation from a predictive state—value, flow, factor, carry, or network.
We don’t spot divergences; we manufacture them, score them, and trade only when a clean micro trigger cuts costs.

1) Data + lattice (foundation)

Universes: liquid perps/futures + index baskets; dq_status=ok, min samples per horizon.
Events: time bars (1m/5m/1h) + session landmarks (open/close/IB), + HTF touch (PDH/PDL, weekly VWAP bands).
Targets: forward returns at horizons 
𝜏
∈
{
1
𝑚
,
5
𝑚
,
30
𝑚
,
4
ℎ
,
1
𝑑
}
τ∈{1m,5m,30m,4h,1d}, both signed and raw.
Costs model: spread + fees + slippage 
=
𝛼
0
+
𝛼
1
⋅
vol
+
𝛼
2
⋅
MO_intensity
=α
0
	​

+α
1
	​

⋅vol+α
2
	​

⋅MO_intensity. Train this too.

2) Residual families (the eight divergence factories)

Each outputs:

z_residual (the divergence)

context (features used, regime)

horizon (τ list)

evidence (magnitudes to log/attribute)

(A) Factor-Residual (cross-sectional)

Model: daily or intraday cross-sectional ridge:

𝑟
𝑖
,
𝑡
+
𝜏
=
𝛽
⊤
𝐹
𝑖
,
𝑡
+
𝜖
𝑖
,
𝑡
r
i,t+τ
	​

=β
⊤
F
i,t
	​

+ϵ
i,t
	​


F: market, sector/index, size/liquidity, on-chain activity, funding/OI, value/growth proxies.
Divergence: 
𝑍
𝑖
,
𝑡
𝑖
𝑑
=
𝑧
(
𝜖
𝑖
,
𝑡
)
Z
i,t
id
	​

=z(ϵ
i,t
	​

).
Trade: mean-revert 
𝑍
Z toward 0, market/sector neutral, OI/funding gates for crypto.

(B) State-Space / Kalman (latent fair value)

State:

𝑚
𝑡
=
𝐴
𝑚
𝑡
−
1
+
𝐵
𝑋
𝑡
+
𝜂
𝑡
,
𝑃
𝑡
=
𝐶
𝑚
𝑡
+
𝜖
𝑡
m
t
	​

=Am
t−1
	​

+BX
t
	​

+η
t
	​

,P
t
	​

=Cm
t
	​

+ϵ
t
	​


Innovation:

𝜈
𝑡
=
𝑃
𝑡
−
𝑃
^
𝑡
ν
t
	​

=P
t
	​

−
P
^
t
	​


Divergence: 
𝑍
𝑡
𝑘
𝑎
𝑙
=
𝑧
(
𝜈
𝑡
)
Z
t
kal
	​

=z(ν
t
	​

) conditioned on 
𝑚
^
˙
𝑡
m
^
˙
t
	​

 sign & ATR regime.
Trade: revert if 
∣
𝑍
∣
>
𝑧
\*
∣Z∣>z
\*
 with flat slope; continue if large 
𝑍
Z and slope aligns (trend gate).

(C) Order-Flow / LOB (microstructure)

Features: queue imbalance, depth slope, spread, MO intensity, cumulative delta, VPIN-like toxicity.
Flow-fit: 
Δ
𝑃
^
𝑡
=
𝑓
(
flow
𝑡
)
ΔP
t
	​

=f(flow
t
	​

) → flow residual 
𝑍
𝑓
𝑙
𝑜
𝑤
=
𝑧
(
Δ
𝑃
𝑡
−
Δ
𝑃
^
𝑡
)
Z
flow
=z(ΔP
t
	​

−
ΔP
t
	​

).
Classic “delta divergence at highs” = price HH while 
𝑍
𝑓
𝑙
𝑜
𝑤
<
0
Z
flow
<0 and footprint shows absorption.
Trigger: failure test of high + VWAP reclaim; tight horizon (1–15m).

(D) Lead-Lag Network (peer prediction)

Build graph 
𝐺
G from rolling MI/TE or betas; predict 
𝑟
𝑖
r
i
	​

 from neighbors:

𝑟
^
𝑖
,
𝑡
+
𝜏
=
∑
𝑗
∈
𝑁
(
𝑖
)
𝑤
𝑖
𝑗
𝑟
𝑗
,
𝑡
r
i,t+τ
	​

=
j∈N(i)
∑
	​

w
ij
	​

r
j,t
	​


Divergence: 
𝑍
𝑖
,
𝑡
𝑛
𝑒
𝑡
=
𝑧
(
𝑟
𝑖
,
𝑡
−
𝑟
^
𝑖
,
𝑡
)
Z
i,t
net
	​

=z(r
i,t
	​

−
r
i,t
	​

).
Use: mean-revert idiosyncratic drift; cluster caps to avoid crowding.

(E) Term-Structure / Basis (carry)

Model expected basis from rates, vol, funding, inventory:

basis
^
𝑡
=
𝑔
(
funding
,
OI
,
RV
,
term
)
basis
t
	​

=g(funding,OI,RV,term)

Residual: 
𝑍
𝑐
𝑎
𝑟
𝑟
𝑦
=
𝑧
(
(
𝑃
𝑝
𝑒
𝑟
𝑝
−
𝑃
𝑠
𝑝
𝑜
𝑡
)
−
basis
^
)
Z
carry
=z((P
perp
−P
spot
)−
basis
).
Trade: revert residual with OI/funding gates; pairs with Kalman band on price.

(F) Breadth / Market-Mode (index)

Predict index returns from breadth composite (%, AD line, NH-NL) + credit/rates.
Residual: 
𝑍
𝑚
𝑜
𝑑
𝑒
=
𝑧
(
𝑟
𝑖
𝑑
𝑥
−
𝑟
^
𝑖
𝑑
𝑥
)
Z
mode
=z(r
idx
	​

−
r
idx
	​

).
Use: risk-tilt / tail-hedge, slow horizon (d/w).

(G) Vol-Surface (options)

Surface vs realized/forecast vol:

𝑍
𝑣
𝑜
𝑙
=
𝑧
(
𝜎
𝑘
,
𝑡
𝑖
𝑚
𝑝
−
𝜎
^
𝑘
,
𝑡
𝑟
𝑒
𝑎
𝑙
/
𝑓
𝑜
𝑟
𝑒
𝑐
𝑎
𝑠
𝑡
)
Z
vol
=z(σ
k,t
imp
	​

−
σ
k,t
real/forecast
	​

)

Trade: variance carry when residual + flows align (dealer positioning if you have it).

(H) Seasonality / Time-of-Day

Expected intraday path 
𝑟
^
𝑡
𝑜
𝑑
(
𝜙
)
r
tod
	​

(ϕ).
Residual: 
𝑍
𝑡
𝑜
𝑑
=
𝑧
(
𝑟
−
𝑟
^
𝑡
𝑜
𝑑
)
Z
tod
=z(r−
r
tod
	​

).
Trade: tiny, fast mean-revert with strict cost gates.

3) Regime control & de-leak (non-negotiables)

Purged K-fold CV + embargo for every model.

Multiple testing control: cluster features by correlation → FDR on cluster means.

Stationarity: difference/standardize; rolling re-fit with half-life; shrinkage priors.

Activation gates: ATR pctile 
[
20
,
90
]
[20,90], ADX bands by class, DQ=ok, min samples per τ.

Costs in training: optimize net IR after the cost model.

4) Scoring & ensemble (how signals meet capital)

For each class 
𝑘
k:

𝑆
𝑡
(
𝑘
)
=
𝑤
(
𝑘
)
⋅
𝑍
𝑡
(
𝑘
)
S
t
(k)
	​

=w
(k)
⋅Z
t
(k)
	​


Weights 
𝑤
(
𝑘
)
w
(k)
 from rolling OOS IR, whitened (PCA) to reduce double-counting.
Total score:

𝑆
𝑡
=
∑
𝑘
𝑤
~
𝑘
𝑆
𝑡
(
𝑘
)
with cluster caps
S
t
	​

=
k
∑
	​

w
~
k
	​

S
t
(k)
	​

with cluster caps

Size: Kelly-capped by live drawdown VaR; neutrality constraints (market/sector/funding).

5) Triggers & execution (where edge survives)

Trigger library: micro_pivot_break, VWAP_reclaim, inside_break, footprint_absorption, queue_flip.
Rules:

No trigger → no order.

Prefer liquidity-reducing fills (join/iceberg) when adverse selection high.

Model queue position; avoid child orders into toxic prints (VPIN up).

6) Registry (drop-in objects)
detectors.yaml
- detector_id: kalman_div_v1
  class: value
  horizons: [5m, 30m, 4h]
  features: [ema_slope_20, ema_slope_100, atr_14, rv_parkinson_20, funding_8h, oi_chg]
  model: kalman_linear
  output: z_innovation
  gates:
    atr_pctile: [20, 90]
    adx_range: [12, 35]
    dq_status: ok
    min_samples: 2000
  triggers: [micro_pivot_break, vwap_reclaim]
  cooldown: "15m"
  cost_guard: true

- detector_id: flow_div_hi_v2
  class: flow
  horizons: [1m, 5m, 15m]
  features: [lob_imbalance, depth_slope, spread_bps, mo_intensity, cum_delta, vpin_30]
  model: gbdt_small
  output: z_flow_residual
  context_level: "near_htf_high"
  gates:
    atr_pctile: [25, 85]
    session_phase: ["open", "lunch_end", "close"]
  triggers: [failure_test, vwap_reclaim]
  cooldown: "7m"
  cost_guard: true

- detector_id: basis_div_v1
  class: carry
  horizons: [30m, 4h]
  features: [funding_8h, oi_level, rv_20, perp_spot_spread, term_slope]
  model: ridge
  output: z_basis_residual
  gates:
    funding_z: [-2.5, 2.5]
    oi_min_usd: 50e6
  triggers: [micro_pivot_break]
  cooldown: "30m"

triggers.yaml
micro_pivot_break:
  lookback: 20
  def: "enter long if close > max(high[-n:]) since last swing; short symmetric"

vwap_reclaim:
  bands: [1,2]  # std bands
  def: "after |Z|>z*, wait for cross and hold above/below VWAP for k ticks"

failure_test:
  def: "wick through HTF level and close back inside range within m minutes"

ensemble.yaml
weights:
  value: auto  # learned from rolling net IR
  flow:  auto
  carry: auto
  network: auto
whiten: true
cluster_caps:
  flow_related: 0.35
  value_related: 0.35
  slow_modes: 0.25
position_limits:
  per_symbol_netr: 2.0
  per_cluster_var: 0.3

7) Training loop (purged CV, costs in the loss)
# pseudo-code
for detector in registry:
    X, y = build_features_targets(detector)
    folds = purged_kfold(X.index, embargo='2h', n_splits=8)
    preds, resid = [], []
    for tr, te in folds:
        model = fit_model(detector.model, X.iloc[tr], y.iloc[tr])
        yhat = model.predict(X.iloc[te])
        # residual defines the divergence:
        eps = (y.iloc[te] - yhat)
        z = standardize(eps, ref=tr)  # train-mean/std only
        preds.append(yhat); resid.append(z)
    Z = concat(resid)
    # learn trigger-conditional PnL after costs
    pnl = simulate_with_triggers(Z, costs_model, detector.triggers, gates=detector.gates)
    log_oos_metrics(detector.id, pnl)
    persist_model(detector, model, standardizer, meta=metrics)


FDR step: cluster detectors by correlation of Z; Benjamini–Hochberg on OOS IRs of cluster means; keep survivors.

8) Live loop (signal → gate → trigger → route)
while True:
    tick = ingest()
    update_features(tick)
    for det in active_detectors():
        z = score_residual(det)           # innovation today
        if not pass_gates(det, z): 
            continue
        trig = evaluate_triggers(det)     # micro-pivot, vwap, etc.
        if trig.fired:
            size = risk_engine.size(det, z, costs_now(), cluster_loads())
            route = execution_router.choose(det.class, toxicity=vpin(), spread=spread_bps())
            place_order(route, size, stop=atr_stop(), target=template_target(det))
            log_evidence(det, z, trig, size, costs_snapshot())
    rebalance_ensemble_weights()  # slow

9) Risk, attribution, governance

Risk:

Cluster VAR caps; per-symbol net-R cap; inventory decay; kill-switch on rolling net IR < 0 per class.

Drawdown VaR throttles Kelly fraction.

Attribution to learn:

For every fill: which detector(s) fired, their Z, regime, trigger type, expected vs realized costs, time-to-edge decay.

Compute decay curves (alpha half-life) per class; auto-adjust horizons/holding templates.

Dashboards (minimum):

Live IR by class & cluster (net of costs).

Trigger hit-rate & slippage by trigger type.

Cost decomposition by spread/impact/fees vs vol & MO intensity.

Detector survival table (FDR keep/kill) with last refit time.

10) Concrete “recipes” (ready to implement)
Hidden continuation via state innovations

Gate: ADX ∈ [20,40], ATR pctile ∈ [30,85].

Divergence: 
𝑍
𝑘
𝑎
𝑙
Z
kal
 negative at HL (bull) and 
𝑚
^
˙
𝑡
>
0
m
^
˙
t
	​

>0.

Trigger: break micro swing high OR VWAP reclaim with 2-bar hold.

Exit: prior extreme + trailing ATR; time-stop 
=
3
×
=3× median edge half-life.

Delta divergence at HTF level (intraday)

Context: within 0.25*ATR of PDH/PDL or weekly_VWAP_band.

Condition: price HH & z(cum_delta) lower than prior HH’s delta.

Trigger: failure test + footprint absorption (net negative delta at/after HH).

Exit: VWAP or value-area POC; hard stop: wick high + 0.3*ATR.

Basis/funding divergence (crypto)

Condition: price HH with basis/funding z extreme and spot lead stall (spot-lead residual < 0).

Trigger: micro-break + OI rollover.

Exit: basis normalization to prior pctile; price target = prior range mid.

11) Build order (one-week sprint)

Day 1–2:

Feature kit + targets; costs model; gates; HTF level detector.

Implement Kalman module (linear), innovation standardizer.

Day 3:

Flow model (GBDT small) and residual scorer; VWAP/trigger library.

Day 4:

Basis/carry model; OI/funding gates.

Purged CV wrapper; embargo utilities.

Day 5:

Ensemble (whitened weights); risk caps; attribution logging.

Backtest harness with trigger simulation; FDR cluster selection.

Day 6–7:

Walk-forward OOS on 6–12 months; cost-aware; decay curves.

Kill/keep list; deploy two classes (value+flow) first; shadow-trade for a session, then go small.

12) Why this survives reality

Residualization removes shared mode risk; you trade what shouldn’t be there.

Purged CV + FDR tames multiple testing.

Triggers & TCA turn paper alpha into fills.

Attribution & decay let you prune fast and refit before regime drift kills you.

If you want, I’ll turn the above YAML and pseudo-code into a minimal Python package skeleton (registry loader, purged-CV trainer, Kalman/GBDT models, trigger simulator, cost model, live router) you can drop into your event lattice.