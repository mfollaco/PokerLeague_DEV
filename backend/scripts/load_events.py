import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "data"

def load_all_events():
    files = sorted(DATA_DIR.glob("*.csv"))
    if not files:
        raise RuntimeError("No CSV files found in data folder")

    frames = []
    for f in files:
        df = pd.read_csv(f)
        df["SourceFile"] = f.name
        frames.append(df)

    return pd.concat(frames, ignore_index=True)

if __name__ == "__main__":
    df = load_all_events()
    print(df.head())
    print(f"Rows loaded: {len(df)}")

