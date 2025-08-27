import csv
import datetime as dt
import os
from typing import List, Dict
import matplotlib.pyplot as plt
import streamlit as st
from dotenv import load_dotenv

# Load API keys
load_dotenv()
GOOGLE_API_KEY = os.getenv("GEMINI_API_KEY")

# LangChain + Gemini
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_chroma import Chroma

# LLM
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=GOOGLE_API_KEY)

# Embeddings + Chroma (auto-persist)
embeddings = GoogleGenerativeAIEmbeddings(
    model="models/embedding-001",
    google_api_key=GOOGLE_API_KEY
)
try:
    vectordb = Chroma(
        collection_name="habit_logs",
        embedding_function=embeddings,
        persist_directory="./chroma_db"
    )
except Exception as e:
    st.warning(f"⚠️ ChromaDB could not start: {e}")
    vectordb = None

# Habit definitions
HABITS = {
    "sleep": {"target": 9, "type": float, "label": "Sleep (hours)"},
    "steps": {"target": 8000, "type": int, "label": "Steps"},
    "water": {"target": 8, "type": int, "label": "Water (glasses)"},
}

LOG_FILE = "habit_logs.csv"
FIELDNAMES = ["date"] + list(HABITS.keys())

# ---------------- CSV Helpers ----------------
def ensure_csv():
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()

def log_habits(habit_values: Dict[str, float]):
    ensure_csv()
    today = dt.date.today().isoformat()
    row = {"date": today}
    row.update(habit_values)

    # Save to CSV
    with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writerow(row)

    # Save to Chroma
    vectordb.add_texts(
        texts=[f"On {today}, habits logged: {habit_values}"],
        ids=[today]
    )

def load_rows() -> List[Dict[str, str]]:
    ensure_csv()
    with open(LOG_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    rows.sort(key=lambda r: r["date"])
    return rows

# ---------------- Feedback ----------------
def simple_feedback():
    rows = load_rows()
    if not rows:
        st.info("No data yet. Log at least one day.")
        return
    last7 = rows[-7:]
    n = len(last7)
    st.subheader(f"Feedback (last {n} entries):")
    for key, meta in HABITS.items():
        values = []
        for r in last7:
            try:
                values.append(float(r[key]))
            except Exception:
                pass
        if not values:
            st.write(f"- {meta['label']}: no data")
            continue
        avg = sum(values)/len(values)
        target = meta["target"]
        status = "Good job!!!" if avg >= target else f"Try adding {target - avg:.1f} more per day."
        st.write(f"- {meta['label']}: avg {avg:.1f} (target {target}) -> {status}")

def plot_progress():
    rows = load_rows()
    if not rows:
        st.info("No data to plot yet.")
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
        st.pyplot(plt)

def ai_feedback():
    rows = load_rows()
    if not rows:
        st.info("No data yet. Log at least one day.")
        return
    
    last7 = rows[-7:]
    habits_text = "\n".join([str(r) for r in last7])

    prompt = ChatPromptTemplate.from_template(
        """
        You are a supportive personal habit coach. 
        Here are my last 7 days of habit logs:

        {habits_text}

        Based on this data:
        1. Summarize my performance.
        2. Highlight one strong area.
        3. Suggest one small challenge for tomorrow.
        Keep it motivating and short.
        """
    )

    chain = prompt | llm
    result = chain.invoke({"habits_text": habits_text})
    st.subheader("🤖 AI Coach Feedback")
    st.write(result.content)

# ---------------- View Stored Data ----------------
def view_chroma_data():
    results = vectordb.get()
    if not results["documents"]:
        st.info("No data stored yet in ChromaDB.")
        return
    
    st.subheader("📂 Data Stored in ChromaDB")
    for i, text in enumerate(results["documents"]):
        st.write(f"**{i+1}.** {text}  _(ID: {results['ids'][i]})_")

# ---------------- Streamlit App ----------------
st.title("📝 Personal Habit Coach ")

st.sidebar.header("Actions")
action = st.sidebar.radio(
    "Choose an action",
    ["Log Habits", "Simple Feedback", "Plot Progress", "AI Feedback", "View Stored Data"]
)

if action == "Log Habits":
    st.subheader("Log today's habits")
    habit_values = {}
    with st.form(key="habit_form"): 
        for key, meta in HABITS.items():
            if key == "steps":
                habit_values[key] = st.number_input(meta["label"], min_value=0, step=1000)  # increments of 1000
            elif key in ["sleep", "water"]:
                habit_values[key] = st.number_input(meta["label"], min_value=0, step=1)  # increments of 1
            else:
                habit_values[key] = st.number_input(meta["label"], min_value=0.0, step=0.1)
        submit = st.form_submit_button("Save")
        if submit:
            log_habits(habit_values)
            st.success("Habit logged successfully!")

elif action == "Simple Feedback":
    simple_feedback()

elif action == "Plot Progress":
    plot_progress()

elif action == "AI Feedback":
    ai_feedback()

elif action == "View Stored Data":
    view_chroma_data()

