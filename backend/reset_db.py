"""Reset the working DB: copy data/campus_customs.db over data/campus_customs_new.db.

Run before every full ticket run:  .venv/bin/python -m backend.reset_db
"""

import shutil
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"

if __name__ == "__main__":
    shutil.copyfile(DATA / "campus_customs.db", DATA / "campus_customs_new.db")
    print("Reset data/campus_customs_new.db from data/campus_customs.db")
