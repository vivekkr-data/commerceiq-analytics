"""Raw Olist data loading."""

from pathlib import Path

import pandas as pd

from src.config import RAW_DIR, RAW_FILES


def verify_raw_files(raw_dir: Path = RAW_DIR) -> dict[str, Path]:
    paths = {name: raw_dir / filename for name, filename in RAW_FILES.items()}
    missing = [str(path) for path in paths.values() if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing raw data files:\n" + "\n".join(missing))
    return paths


def load_raw_data(raw_dir: Path = RAW_DIR) -> dict[str, pd.DataFrame]:
    """Load all nine CSVs without changing source column names."""
    paths = verify_raw_files(raw_dir)
    return {
        name: pd.read_csv(path, low_memory=False)
        for name, path in paths.items()
    }
