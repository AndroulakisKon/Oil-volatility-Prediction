"""
01_get_data.py — Stage 1: download the raw data.
 
Downloads every raw series used in the project into data/raw/ exactly as the
source provides it (no cleaning here — that happens in 02_clean.ipynb), and
writes data/raw/sources.csv recording source, URL, licence and retrieval time.
 
Run from anywhere:
    python code/01_get_data.py            # skips files that already exist
    python code/01_get_data.py --force    # re-download everything
 
Runtime: under a minute. No API keys needed.
 
Written with Claude (Anthropic); reviewed and run by Konstantinos Androulakis.
"""
 
import csv
import gzip
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
 
# Paths relative to the repository root, so the script works from any folder
ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
 
FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={}"
FRED_LICENCE = "FRED / source terms (public data; cite FRED, Federal Reserve Bank of St. Louis)"
 
# (file name, url, description, source, licence)
SOURCES = [
    ("fred_dcoilwtico.csv", FRED_URL.format("DCOILWTICO"),
     "WTI crude oil spot price, Cushing OK, USD/bbl, daily", "FRED (EIA)", FRED_LICENCE),
    ("fred_dcoilbrenteu.csv", FRED_URL.format("DCOILBRENTEU"),
     "Brent crude oil spot price, USD/bbl, daily", "FRED (EIA)", FRED_LICENCE),
    ("fred_ovxcls.csv", FRED_URL.format("OVXCLS"),
     "CBOE Crude Oil Volatility Index (OVX), daily close", "FRED (CBOE)", FRED_LICENCE),
    ("fred_vixcls.csv", FRED_URL.format("VIXCLS"),
     "CBOE Volatility Index (VIX), daily close", "FRED (CBOE)", FRED_LICENCE),
    ("fred_dtwexbgs.csv", FRED_URL.format("DTWEXBGS"),
     "Nominal broad U.S. dollar index, daily", "FRED (Federal Reserve Board)", FRED_LICENCE),
    ("eia_wcestus1.xls", "https://www.eia.gov/dnav/pet/hist_xls/WCESTUS1w.xls",
     "Weekly U.S. ending stocks of crude oil excl. SPR, thousand barrels (sheet 'Data 1')",
     "U.S. Energy Information Administration", "U.S. government data, public domain (cite EIA)"),
    ("gpr_daily.xls", "https://www.matteoiacoviello.com/gpr_files/data_gpr_daily_recent.xls",
     "Daily Geopolitical Risk Index (Caldara & Iacoviello, 2022, AER)",
     "matteoiacoviello.com/gpr.htm", "CC BY (credit the authors and the website)"),
]
 
HEADERS = {"User-Agent": "Mozilla/5.0 (academic research; HEC Lausanne ADA project)"}
 
 
def download(url: str) -> bytes:
    """Fetch a URL and return its bytes (un-gzipped if needed)."""
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = resp.read()
    if data[:2] == b"\x1f\x8b":  # gzip magic number
        data = gzip.decompress(data)
    return data
 
 
def quick_check(path: Path) -> str:
    """Short human-readable summary so you can eyeball each file."""
    size_kb = path.stat().st_size / 1024
    if path.suffix == ".csv":
        lines = path.read_text(errors="replace").strip().splitlines()
        return f"{size_kb:7.1f} KB | {len(lines) - 1} rows | first: {lines[1]} | last: {lines[-1]}"
    return f"{size_kb:7.1f} KB | Excel file (parsed in 02_clean.ipynb)"
 
 
def main(force: bool = False) -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    manifest = []
    failed = []
 
    for fname, url, desc, source, licence in SOURCES:
        path = RAW / fname
        if path.exists() and not force:
            print(f"[skip] {fname} already exists (use --force to re-download)")
            retrieved = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        else:
            try:
                path.write_bytes(download(url))
                retrieved = datetime.now(timezone.utc)
                print(f"[ ok ] {fname}")
            except Exception as err:  # keep going; report at the end
                print(f"[FAIL] {fname}: {err}")
                failed.append((fname, url))
                continue
        print(f"       {quick_check(path)}")
        manifest.append({
            "file": fname, "description": desc, "source": source, "url": url,
            "licence": licence, "retrieved_utc": retrieved.strftime("%Y-%m-%d %H:%M"),
        })
 
    with open(RAW / "sources.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(manifest[0].keys()) if manifest else ["file"])
        writer.writeheader()
        writer.writerows(manifest)
    print(f"\nWrote {RAW / 'sources.csv'} ({len(manifest)} files).")
 
    if failed:
        print("\nSome downloads failed. Download these by hand into data/raw/ with the same name:")
        for fname, url in failed:
            print(f"  {fname}  <-  {url}")
        sys.exit(1)
 
 
if __name__ == "__main__":
    main(force="--force" in sys.argv)