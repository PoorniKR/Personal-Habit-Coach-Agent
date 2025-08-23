import csv
import datetime as dt
import os
from typing import List, Dict
import matplotlib.pyplot as plt

HABITS = {
    "sleep": {"target": 9, "type": float, "label": "Sleep (hours)"},
    "steps": {"target": 8000, "type": int, "label": "Steps"},
    "water": {"target": 8, "type": int, "label": "Water (glasses)"},
}

LOG_FILE = "habit_logs.csv"
FIELDNAMES = ["date"] + list(HABITS.keys())

def ensure_csv():
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
    
def parse_input(prompt: str, cast):
    while True:
        raw = input(prompt).strip()
        try:
            return cast(raw)
        except Exception:
            print("Enter valid number")
        
def log_today():
    ensure_csv()
    today = dt.date.today().isoformat()
    print(f"\nLogging today's habits:\n")
    row = {"date": today}
    for key, meta in HABITS.items():
        nice = meta["label"]
        val = parse_input(f"    {nice}:", meta["type"])
        row[key] = val
    with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writerow(row)
    print("\nLOG SAVED!\n")

def load_rows() -> List[Dict[str, str]]:
    ensure_csv()
    with open(LOG_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    rows.sort(key=lambda r: r["date"])
    return rows

def feedback():
    rows = load_rows()
    if not rows:
        print("No data yet. Log atleast one day")
        return
    last7 = rows[-7:]
    n = len(last7)
    print("Feedback (last {} entries):\n".format(n))
    for key, meta in HABITS.items():
        values = []
        for r in last7:
            try:
                values.append(float(r[key]))
            except Exception:
                pass
        if not values:
            print(f"- {meta['label']}: no data")
            continue
        avg = sum(values)/len(values)
        target = meta["target"]
        status = "Good job!!!" if avg >= target else f"Try adding {target - avg:.1f} more per day."
        print(f"- {meta['label']}: avg {avg:.1f} (target {target}) -> {status}")
    print()

def plot_progress(save_path="progress.png"):
    rows = load_rows()
    if not rows:
        print("No data to plot yet.")
        return
    dates = [r["date"] for r in rows]
    for key, meta in HABITS.items():
        values = []
        for r in rows:
            try:
                values.append(float(r[key]))
            except Exception:
                values.append(None)

        plt.figure()
        xs, ys = [], []
        for d, v in zip(dates, values):
            if v is None:
                if xs and ys:
                    plt.plot(xs, ys, marker="o")
                xs, ys = [], []
            else:
                xs.append(d)
                ys.append(v)
        if xs and ys:
            plt.plot(xs, ys, marker="o")

        plt.axhline(meta["target"], linestyle="--", label=f"Target {meta['target']}")
        plt.title(f"{meta['label']} Over Time")
        plt.xlabel("Date")
        plt.ylabel(meta["label"])
        plt.xticks(rotation=45, ha="right")
        plt.legend()
        plt.tight_layout()

        if save_path:
            base, ext = os.path.splitext(save_path)
            out = f"{base}_{key}{ext or '.png'}"
            plt.savefig(out, dpi=150)
        else:
            plt.show()

def main():
    print("=== Personal Habit Coach (MVP) ===")
    print("1) Log today's habits")
    print("2) Show feedback (last 7)")
    print("3) Plot progress")
    print("4) Log + Feedback + Plot")
    choice = input("Select 1/2/3/4: ").strip()

    if choice == "1":
        log_today()
    elif choice == "2":
        feedback()
    elif choice == "3":
        plot_progress()
    elif choice == "4":
        log_today()
        feedback()
        plot_progress()
    else:
        print("Invalid choice. Exiting.")

if __name__ == "__main__":
    main()