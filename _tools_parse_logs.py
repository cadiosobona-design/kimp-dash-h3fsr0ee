"""
Remote parse_logs for MMCCV PC.
Reads bot logs from C:\\Users\\MMCCV\\Desktop\\launcher_v25_11_01\\
Writes data.js/data.json into REPO_DIR for git push.
"""
from __future__ import annotations
import json
import re
import sys
from datetime import datetime
from pathlib import Path

LOG_DIR = Path(r"C:\Users\MMCCV\Desktop\launcher_v25_11_01")
REPO_DIR = Path(r"C:\Users\MMCCV\kimp_repo")
OUTPUT = REPO_DIR / "data.json"
OUTPUT_JS = REPO_DIR / "data.js"

LINE_RE = re.compile(
    r"^\[(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+\]\s*"
    r"업빗:(?P<krw>[\d,]+)원\s*/\s*"
    r"비트겟:(?P<usd>[\d.,]+)USD,\s*"
    r"환율:(?P<fx>[\d.]+),\s*"
    r"비트겟원화:(?P<krw_bg>[\d,]+)원\s*/\s*"
    r"\*\*총자산\*\*\s*:(?P<total>[\d,]+)원"
)


def num(s: str) -> float:
    return float(s.replace(",", ""))


def parse_file(path: Path) -> list[dict]:
    rows: list[dict] = []
    text = path.read_text(encoding="cp949", errors="replace")
    for line in text.splitlines():
        m = LINE_RE.match(line)
        if not m:
            continue
        ts = datetime.strptime(m.group("ts"), "%Y-%m-%d %H:%M:%S")
        krw_upbit = num(m.group("krw"))
        usd_bitget = num(m.group("usd"))
        fx = num(m.group("fx"))
        krw_bg = num(m.group("krw_bg"))
        total_krw = num(m.group("total"))
        total_usdt = total_krw / fx if fx > 0 else 0.0
        rows.append({
            "ts": ts.isoformat(),
            "date": ts.strftime("%Y-%m-%d"),
            "krw_upbit": krw_upbit,
            "usd_bitget": usd_bitget,
            "fx": fx,
            "krw_bitget": krw_bg,
            "total_krw": total_krw,
            "total_usdt": round(total_usdt, 2),
        })
    return rows


def build_daily(series: list[dict]) -> list[dict]:
    buckets: dict[str, list[dict]] = {}
    for r in series:
        buckets.setdefault(r["date"], []).append(r)
    days = sorted(buckets.keys())
    out: list[dict] = []
    prev_close = None
    for d in days:
        rows = buckets[d]
        rows.sort(key=lambda x: x["ts"])
        vals = [r["total_usdt"] for r in rows]
        open_v = vals[0]
        close_v = vals[-1]
        high_v = max(vals)
        low_v = min(vals)
        if prev_close is None or prev_close == 0:
            change_pct = 0.0
        else:
            change_pct = (close_v - prev_close) / prev_close * 100
        out.append({
            "date": d,
            "open": round(open_v, 2),
            "close": round(close_v, 2),
            "high": round(high_v, 2),
            "low": round(low_v, 2),
            "change_pct": round(change_pct, 3),
            "samples": len(rows),
            "fx_close": rows[-1]["fx"],
            "total_krw_close": rows[-1]["total_krw"],
            "krw_upbit_close": rows[-1]["krw_upbit"],
            "usd_bitget_close": rows[-1]["usd_bitget"],
        })
        prev_close = close_v
    return out


def main() -> int:
    if not LOG_DIR.exists():
        print(f"log dir missing: {LOG_DIR}", file=sys.stderr)
        return 1
    files = sorted(
        LOG_DIR.glob("Log_assets_upbit_bitget.txt*"),
        key=lambda p: (0, int(p.suffix[1:])) if p.suffix[1:].isdigit() else (1, 0),
        reverse=True,
    )
    if not files:
        print("no log files", file=sys.stderr)
        return 1
    all_rows: list[dict] = []
    for f in files:
        print(f"parsing {f.name}")
        rows = parse_file(f)
        print(f"  -> {len(rows)} rows")
        all_rows.extend(rows)
    all_rows.sort(key=lambda r: r["ts"])
    seen = set()
    dedup: list[dict] = []
    for r in all_rows:
        if r["ts"] in seen:
            continue
        seen.add(r["ts"])
        dedup.append(r)
    daily = build_daily(dedup)
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source": "upbit-bitget",
        "count_series": len(dedup),
        "count_days": len(daily),
        "series": dedup,
        "daily": daily,
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    OUTPUT_JS.write_text("window.DASHBOARD_DATA = " + json.dumps(payload, ensure_ascii=False) + ";\n", encoding="utf-8")
    print(f"wrote {OUTPUT} : series={len(dedup)} days={len(daily)}")
    if daily:
        print(f"  last: {daily[-1]['date']} USDT={daily[-1]['close']:,.2f} change={daily[-1]['change_pct']:+.3f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
