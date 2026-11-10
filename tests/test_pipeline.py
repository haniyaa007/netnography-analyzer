import subprocess, sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def test_end_to_end(tmp_path):
    subprocess.run([sys.executable, "sample_data/make_sample.py"], cwd=ROOT, check=True)
    out = tmp_path / "out.xlsx"
    subprocess.run([sys.executable, "main.py", "run", "--name", "Acme", "--website", "https://acme.com",
                    "--only", "manual", "--import-csv", "sample_data/sample_reviews.csv", "--out", str(out)],
                   cwd=ROOT, check=True)
    sheets = pd.read_excel(out, sheet_name=None)
    for s in ["Executive_Summary", "Platform_Profile", "Themes", "Field_Notes", "Raw_Data", "Authenticity"]:
        assert s in sheets and len(sheets[s]) > 0
    assert sheets["Raw_Data"]["platform"].nunique() >= 4
