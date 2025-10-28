#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
import sys

import matplotlib.pyplot as plt  # type: ignore
import matplotlib.dates as mdates  # type: ignore

# Ensure project root on path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # type: ignore
from src.intelligence.lowcap_portfolio_manager.spiral.persist import SpiralPersist


def main() -> None:
    load_dotenv()
    ap = argparse.ArgumentParser(description="Plot TA snapshot for a token (price, EMAs, RSI, OBV, VO_z)")
    ap.add_argument("--contract", required=True)
    ap.add_argument("--chain", required=True)
    ap.add_argument("--hours", type=int, default=72)
    ap.add_argument("--mode", choices=["e1", "e2"], default="e1", help="E1: 1h reversal view; E2: 15m momentum view")
    ap.add_argument("--start", type=str, default=None, help="ISO start (e.g., 2025-10-10T00:00:00Z)")
    ap.add_argument("--end", type=str, default=None, help="ISO end (default now)")
    ap.add_argument("--overlay-geometry", action="store_true", help="Overlay geometry diagonals/SR on price panel")
    ap.add_argument("--tight", action="store_true", help="Tight y-zoom around price (±5%)")
    args = ap.parse_args()

    sp = SpiralPersist()
    now = datetime.now(timezone.utc)
    if args.start:
        try:
            start_dt = datetime.fromisoformat(args.start.replace('Z', '+00:00'))
        except Exception:
            start_dt = now - timedelta(hours=args.hours)
    else:
        start_dt = now - timedelta(hours=args.hours)
    if args.end:
        try:
            end_dt = datetime.fromisoformat(args.end.replace('Z', '+00:00'))
        except Exception:
            end_dt = now
    else:
        end_dt = now
    since_1m = start_dt.isoformat()

    # 1m closes for price and EMA_long
    rows_1m = (
        sp.sb.table('lowcap_price_data_ohlc')
        .select('timestamp, close_native')
        .eq('token_contract', args.contract)
        .eq('chain', args.chain)
        .eq('timeframe', '1m')
        .gte('timestamp', since_1m)
        .order('timestamp', desc=False)
        .execute()
        .data or []
    )
    t1 = [datetime.fromisoformat(str(r['timestamp']).replace('Z','+00:00')) for r in rows_1m]
    p1 = [float(r.get('close_native') or 0.0) for r in rows_1m]

    def ema(vals, span):
        if not vals:
            return []
        a = 2.0/(span+1)
        out = [vals[0]]
        for v in vals[1:]:
            out.append(a*v + (1-a)*out[-1])
        return out

    ema_long = ema(p1[-120:], 60)

    # 15m closes/volume for RSI/VO_z/OBV
    rows_15m = (
        sp.sb.table('lowcap_price_data_ohlc')
        .select('timestamp, open_native, high_native, low_native, close_native, volume')
        .eq('token_contract', args.contract)
        .eq('chain', args.chain)
        .eq('timeframe', '15m')
        .gte('timestamp', start_dt.isoformat())
        .lte('timestamp', end_dt.isoformat())
        .order('timestamp', desc=False)
        .execute()
        .data or []
    )
    t15 = [datetime.fromisoformat(str(r['timestamp']).replace('Z','+00:00')) for r in rows_15m]
    c15 = [float(r.get('close_native') or 0.0) for r in rows_15m]
    v15 = [float(r.get('volume') or 0.0) for r in rows_15m]

    # 15m ATR(14) for support band sizing
    def atr_15m_from(rows):
        if not rows:
            return 0.0
        trs = []
        prev_c = float(rows[0].get('close_native') or 0.0)
        for b in rows[1:]:
            h = float(b.get('high_native') or prev_c)
            l = float(b.get('low_native') or prev_c)
            c = float(b.get('close_native') or prev_c)
            tr = max(h - l, abs(h - prev_c), abs(prev_c - l))
            trs.append(tr)
            prev_c = c
        if not trs:
            return 0.0
        n = 14
        atr = sum(trs[:n]) / max(1, min(n, len(trs)))
        for tr in trs[n:]:
            atr = (atr * (n - 1) + tr) / n
        return atr
    atr15 = atr_15m_from(rows_15m)

    # Fallback: derive 15m from 1m if no rows
    if len(rows_15m) < 10 and t1:
        # group 15 samples per bucket
        c15 = []
        v15 = []
        t15 = []
        bucket_c = []
        bucket_v = []
        bucket_t0 = None
        # Pull 1m volume too
        rows_1m_full = (
            sp.sb.table('lowcap_price_data_ohlc')
            .select('timestamp, close_native, volume')
            .eq('token_contract', args.contract)
            .eq('chain', args.chain)
            .eq('timeframe', '1m')
            .gte('timestamp', start_dt.isoformat())
            .lte('timestamp', end_dt.isoformat())
            .order('timestamp', desc=False)
            .execute()
            .data or []
        )
        t1f = [datetime.fromisoformat(str(r['timestamp']).replace('Z','+00:00')) for r in rows_1m_full]
        p1f = [float(r.get('close_native') or 0.0) for r in rows_1m_full]
        v1f = [float(r.get('volume') or 0.0) for r in rows_1m_full]
        for i, px in enumerate(p1f):
            ts = t1f[i]
            if bucket_t0 is None:
                bucket_t0 = ts
            bucket_c.append(px)
            bucket_v.append(v1f[i])
            if len(bucket_c) == 15:
                c15.append(bucket_c[-1])
                v15.append(sum(bucket_v))
                t15.append(bucket_t0)
                bucket_c = []
                bucket_v = []
                bucket_t0 = None

    def rsi(vals, period=14):
        if len(vals) <= period:
            return [50.0]*len(vals)
        out = [50.0]*len(vals)
        for k in range(period, len(vals)):
            gains = []
            losses = []
            for i in range(k-period+1, k+1):
                ch = vals[i] - vals[i-1]
                gains.append(max(0.0, ch))
                losses.append(max(0.0, -ch))
            avg_gain = sum(gains)/period
            avg_loss = sum(losses)/period or 1e-9
            rs = avg_gain/avg_loss
            out[k] = 100.0 - (100.0/(1.0+rs))
        return out

    def zscore_window(w, val):
        import statistics
        if len(w) < 5:
            return 0.0
        mu = statistics.fmean(w)
        sd = statistics.pstdev(w) or 1.0
        return (val-mu)/sd

    rsi15 = rsi(c15, 14)
    vo_z_series = []
    for k in range(len(v15)):
        win = v15[max(0,k-29):k+1]
        vo_z_series.append(zscore_window(win, v15[k]))

    # OBV series (15m)
    obv = []
    acc = 0.0
    for i in range(len(c15)):
        if i == 0:
            obv.append(0.0)
            continue
        if c15[i] > c15[i-1]:
            acc += v15[i]
        elif c15[i] < c15[i-1]:
            acc -= v15[i]
        obv.append(acc)

    # Prepare optional 1h series for E1 view by resampling 15m → 1h (4 bars)
    t1h, c1h, v1h = [], [], []
    if len(c15) >= 4:
        acc_c, acc_v, acc_t0 = [], [], None
        for i, px in enumerate(c15):
            ts = t15[i]
            if acc_t0 is None:
                acc_t0 = ts
            acc_c.append(px)
            acc_v.append(v15[i])
            if len(acc_c) == 4:
                t1h.append(acc_t0)
                c1h.append(acc_c[-1])
                v1h.append(sum(acc_v))
                acc_c, acc_v, acc_t0 = [], [], None

    # Build indicator series per mode
    if args.mode == "e1" and t1h:
        rsi_for_plot = rsi(c1h, 14)
        # 1h VO_z
        vo_for_plot = []
        for k in range(len(v1h)):
            win = v1h[max(0, k-29):k+1]
            vo_for_plot.append(zscore_window(win, v1h[k]))
        # 1h OBV
        obv_for_plot = []
        acc = 0.0
        for i in range(len(c1h)):
            if i == 0:
                obv_for_plot.append(0.0)
                continue
            if c1h[i] > c1h[i-1]:
                acc += v1h[i]
            elif c1h[i] < c1h[i-1]:
                acc -= v1h[i]
            obv_for_plot.append(acc)
        t_for_ind = t1h
        ind_frame_label = "1h"
    else:
        t_for_ind = t15
        rsi_for_plot = rsi15
        vo_for_plot = vo_z_series
        obv_for_plot = obv
        ind_frame_label = "15m"

    # Plot
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(16, 12), gridspec_kw={'height_ratios':[3,1,1]})

    # Price panel
    if args.mode == "e1" and t1h:
        ax1.plot(t1h, c1h, 'b-', label='Price 1h')
    else:
        ax1.plot(t1, p1, 'b-', label='Price 1m')
        if ema_long:
            ax1.plot(t1[-len(ema_long):], ema_long, 'orange', label='EMA_long 1m (60)')
    # Fetch token ticker for title if available
    try:
        row = (
            sp.sb.table('lowcap_positions')
            .select('token_ticker')
            .eq('token_contract', args.contract)
            .eq('token_chain', args.chain)
            .limit(1)
            .execute()
            .data or []
        )
        tname = (row[0].get('token_ticker') if row else None) or args.contract[:6]
    except Exception:
        tname = args.contract[:6]
    ax1.set_title(f'TA Snapshot {tname} ({args.chain})')
    ax1.legend(); ax1.grid(True, alpha=0.3)

    # RSI + VO_z
    ax2.plot(t_for_ind, rsi_for_plot, 'purple', label=f'RSI(14) {ind_frame_label}')
    ax2.axhline(70, color='red', ls='--', alpha=0.4)
    ax2.axhline(30, color='green', ls='--', alpha=0.4)
    ax2.set_ylabel('RSI')
    ax2b = ax2.twinx()
    ax2b.plot(t_for_ind, vo_for_plot, 'gray', alpha=0.6, label=f'VO_z {ind_frame_label}')
    ax2b.axhline(0.3, color='gray', ls=':', alpha=0.6)
    ax2b.set_ylabel('VO_z')
    ax2.legend(loc='upper left'); ax2b.legend(loc='upper right'); ax2.grid(True, alpha=0.3)

    # OBV
    ax3.plot(t_for_ind, obv_for_plot, 'brown', label=f'OBV {ind_frame_label}')
    ax3.set_ylabel('OBV'); ax3.set_xlabel('Time')
    ax3.legend(); ax3.grid(True, alpha=0.3)

    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
    ax3.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
    # Optional tight y zoom
    if args.mode == "e1" and t1h and args.tight and c1h:
        pmin, pmax = min(c1h), max(c1h)
        pad = 0.05 * (pmax - pmin or 1.0)
        ax1.set_ylim(pmin - pad, pmax + pad)
    plt.tight_layout()

    # --- Overlay pivot markers and divergence guide ---
    def pivots(vals):
        highs, lows = [], []
        for i in range(2, len(vals)-2):
            v = vals[i]
            if v > vals[i-1] and v > vals[i-2] and v > vals[i+1] and v > vals[i+2]:
                highs.append(i)
            if v < vals[i-1] and v < vals[i-2] and v < vals[i+1] and v < vals[i+2]:
                lows.append(i)
        return highs, lows

    if args.mode == "e1" and t1h:
        # Use 1h pivots for divergence inspection
        pH, pL = pivots(c1h)
        rH, rL_all = pivots(rsi_for_plot)
        # Oversold filter for bullish divergence candidates
        rL = [i for i in rL_all if rsi_for_plot[i] < 35]
        # Bullish divergence (3‑pivot): price LL..LL and RSI HL..HL, time-aligned by nearest RSI low to each price low (±1 idx)
        def nearest(lst, idx):
            cand = [i for i in lst if abs(i - idx) <= 1]
            return cand[0] if cand else None
        if len(pL) >= 3 and len(rL) >= 3:
            # take last three price lows and find matching RSI lows
            p_idxs = pL[-3:]
            r_idxs = []
            ok = True
            for pi in p_idxs:
                ri = nearest(rL, pi)
                if ri is None:
                    ok = False
                    break
                r_idxs.append(ri)
            if ok:
                price_seq = [c1h[i] for i in p_idxs]
                rsi_seq = [rsi_for_plot[i] for i in r_idxs]
                if price_seq[0] > price_seq[1] > price_seq[2] and rsi_seq[0] < rsi_seq[1] < rsi_seq[2]:
                    # Mark on price panel
                    ax1.plot([t1h[i] for i in p_idxs], [c1h[i] for i in p_idxs], color='green', lw=2, alpha=0.7)
                    ax1.scatter([t1h[i] for i in p_idxs], [c1h[i] for i in p_idxs], c='green', s=50, marker='v', zorder=6)
                    # Mark on RSI panel
                    ax2.plot([t1h[i] for i in r_idxs], [rsi_for_plot[i] for i in r_idxs], color='green', lw=2, alpha=0.7)
                    ax2.scatter([t1h[i] for i in r_idxs], [rsi_for_plot[i] for i in r_idxs], c='green', s=40, marker='v', zorder=6)
        # Optional geometry overlay
        if args.overlay_geometry:
            try:
                row = (
                    sp.sb.table('lowcap_positions')
                    .select('features')
                    .eq('token_contract', args.contract)
                    .eq('token_chain', args.chain)
                    .limit(1)
                    .execute()
                    .data or []
                )
                features = (row[0].get('features') if row else {}) or {}
                geometry = features.get('geometry') or {}
                diags = geometry.get('diagonals') or {}
                if diags:
                    from datetime import datetime as _dt
                    def proj_line(diag: dict, times: list[datetime]) -> list[float]:
                        try:
                            m = float(diag.get('slope', 0.0))
                            b = float(diag.get('intercept', 0.0))
                            anchor = str(diag.get('anchor_time_iso') or '')
                            if not anchor:
                                return []
                            t0 = _dt.fromisoformat(anchor.replace('Z', '+00:00'))
                            out: list[float] = []
                            for t in times:
                                h = (t - t0).total_seconds() / 3600.0
                                out.append(m * h + b)
                            return out
                        except Exception:
                            return []
                    def diag_color(name: str) -> str:
                        s = name.lower()
                        if 'downtrend' in s and 'highs' in s:
                            return 'red'
                        if 'uptrend' in s and 'lows' in s:
                            return 'green'
                        if 'uptrend' in s and 'highs' in s:
                            return 'purple'
                        if 'downtrend' in s and 'lows' in s:
                            return 'orange'
                        return 'blue'
                    for k, diag in diags.items():
                        y = proj_line(diag, t1h)
                        if y and len(y) == len(t1h):
                            ax1.plot(t1h, y, color=diag_color(k), lw=2, alpha=0.8, label=k)
                # Draw horizontal S/R levels from geometry levels.sr_levels (if any)
                levels = ((geometry.get('levels') or {}).get('sr_levels') or [])
                if levels and t1h and c1h:
                    for lvl in levels:
                        try:
                            yv = float(lvl.get('price', 0.0))
                            lbl_src = str(lvl.get('fib_level') or lvl.get('source') or 'SR')
                            ax1.axhline(y=yv, color='steelblue', ls='--', lw=1.0, alpha=0.6)
                            ax1.text(t1h[0], yv, f"{lbl_src}: {yv:.6f}", fontsize=8, color='steelblue', alpha=0.9, va='bottom')
                        except Exception:
                            pass
            except Exception:
                pass
        # E1 readiness highlights (Agg=green, Norm=orange, Patient=purple)
        try:
            # --- Build 1h components already prepared ---
            # OBV delta over last 3 hours and acceleration
            obv_delta = [0.0]*len(c1h)
            obv_accel = [0.0]*len(c1h)
            for i in range(len(c1h)):
                if i >= 3:
                    obv_delta[i] = obv_for_plot[i] - obv_for_plot[i-3]
                if i >= 2:
                    obv_accel[i] = (obv_for_plot[i] - obv_for_plot[i-1]) - (obv_for_plot[i-1] - obv_for_plot[i-2])
            vo_ok = [ (vo_for_plot[i] >= 0.3) for i in range(len(vo_for_plot)) ]
            # RSI baseline: explicit oversold cross up through 30
            rsi_cross = [ False for _ in rsi_for_plot ]
            for i in range(1, len(rsi_for_plot)):
                prev = rsi_for_plot[i-1]
                cur = rsi_for_plot[i]
                rsi_cross[i] = (prev < 30.0 and cur >= 30.0)
            obv_ok = [ (obv_delta[i] > 0.0 and obv_accel[i] >= 0.0) for i in range(len(obv_delta)) ]
            # 1h ATR from 15m OHLC (grouped)
            def atr_1h_from(rows):
                if not rows:
                    return 0.0
                # group fours
                bars = []
                acc = []
                for i,b in enumerate(rows):
                    acc.append(b)
                    if len(acc) == 4:
                        o = float(acc[0].get('open_native') or 0.0)
                        h = max(float(x.get('high_native') or 0.0) for x in acc)
                        l = min(float(x.get('low_native') or 0.0) for x in acc)
                        c = float(acc[-1].get('close_native') or 0.0)
                        bars.append((o,h,l,c))
                        acc = []
                if len(bars) < 2:
                    return 0.0
                trs = []
                prev_c = bars[0][3]
                for (_,h,l,c) in bars[1:]:
                    tr = max(h-l, abs(h - prev_c), abs(prev_c - l))
                    trs.append(tr)
                    prev_c = c
                n = 14
                atr = sum(trs[:n]) / max(1, min(n, len(trs)))
                for tr in trs[n:]:
                    atr = (atr*(n-1)+tr)/n
                return atr
            atr1h = atr_1h_from(rows_15m)
            # Support proximity using geometry SR levels (non-Fib, strength>=8)
            row = (
                sp.sb.table('lowcap_positions')
                .select('features')
                .eq('token_contract', args.contract)
                .eq('token_chain', args.chain)
                .limit(1)
                .execute()
                .data or []
            )
            features = (row[0].get('features') if row else {}) or {}
            levels = ((features.get('geometry') or {}).get('levels') or {}).get('sr_levels') or []
            def near_support(px: float) -> bool:
                if not levels:
                    return False
                band = 0.5 * (atr1h or atr15 or (0.01 * px))
                for lvl in levels:
                    try:
                        src = str(lvl.get('source') or '')
                        strength = int(lvl.get('strength') or 0)
                        if src == 'fib_retracement' or strength < 8:
                            continue
                        yv = float(lvl.get('price', 0.0))
                        if abs(px - yv) <= band:
                            return True
                    except Exception:
                        pass
                return False
            at_sup = [near_support(c1h[i]) for i in range(len(c1h))]
            # Baseline: RSI 30-cross (visual), and Baseline_full: 30-cross at support (no persistence)
            base_rsi_only = [ rsi_cross[i] for i in range(len(c1h)) ]
            base_ready = [ (rsi_cross[i] and at_sup[i]) for i in range(len(c1h)) ]
            # Visualize RSI 30-cross (very light blue), and full baseline (slightly darker)
            for i in range(len(c1h)):
                t0 = t1h[i]
                t1s = t1h[i+1] if i+1 < len(t1h) else t1h[i]
                if base_rsi_only[i]:
                    ax1.axvspan(t0, t1s, color='#99ccff', alpha=0.06)
                if base_ready[i]:
                    ax1.axvspan(t0, t1s, color='#66b3ff', alpha=0.10)
            # Mode gates
            for i in range(len(c1h)):
                if not base_ready[i]:
                    continue
                extras = int(obv_ok[i]) + int(vo_ok[i])
                t0 = t1h[i]
                t1s = t1h[i+1] if i+1 < len(t1h) else t1h[i]
                if extras >= 2:
                    ax1.axvspan(t0, t1s, color='purple', alpha=0.14)  # Patient
                elif extras == 1:
                    ax1.axvspan(t0, t1s, color='orange', alpha=0.14)  # Normal
                else:
                    ax1.axvspan(t0, t1s, color='green', alpha=0.14)   # Aggressive
        except Exception:
            pass
    else:
        # Mark recent 15m pivots for context
        ph, pl = pivots(c15)
        rh, rl = pivots(rsi15)
        for idx in ph[-3:]:
            ax1.scatter([t15[idx]], [c15[idx]], c='red', s=40, marker='^', zorder=5)
        for idx in pl[-3:]:
            ax1.scatter([t15[idx]], [c15[idx]], c='green', s=40, marker='v', zorder=5)
        for idx in rh[-3:]:
            ax2.scatter([t15[idx]], [rsi15[idx]], c='red', s=30, marker='^', zorder=5)
        for idx in rl[-3:]:
            ax2.scatter([t15[idx]], [rsi15[idx]], c='green', s=30, marker='v', zorder=5)

    out = f"ta_snapshot_{args.contract[:6]}_{args.chain}_{now.strftime('%Y%m%d%H%M')}.png"
    plt.savefig(out, dpi=200, bbox_inches='tight')
    print(out)


if __name__ == '__main__':
    main()
