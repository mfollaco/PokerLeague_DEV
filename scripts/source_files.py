from __future__ import annotations

from pathlib import Path
from typing import List, Optional


def list_log_files(data_dir: Path) -> List[Path]:
    """
    Return log CSVs only (e.g. '02.10.26 log.csv'). Excludes roster.csv and anything else.
    """
    if data_dir is None:
        return []
    if not data_dir.exists():
        return []

    # Only files that end with ' log.csv' (space matters)
    log_files = [p for p in data_dir.glob("*.csv") if p.name.lower().endswith(" log.csv")]
    return sorted(log_files)


def find_latest_log_file(data_dir: Path) -> Optional[Path]:
    """
    Latest log file by modified time (mtime). Returns None if none found.
    """
    log_files = list_log_files(data_dir)
    if not log_files:
        return None

    # newest by modified time
    return max(log_files, key=lambda p: p.stat().st_mtime)


def latest_log_filename(data_dir: Path, default: str = "N/A") -> str:
    """
    Convenience for display: returns the filename string.
    """
    latest = find_latest_log_file(data_dir)
    return latest.name if latest else default