import streamlit as st
import google.generativeai as genai
import os
import json
from snowflake.snowpark import Session

# ==================================================
# CONFIG
# ==================================================
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
llm = genai.GenerativeModel("gemini-2.5-flash")

# ==================================================
# PAGE CONFIG
# ==================================================
st.set_page_config(
    page_title="Digital Employee",
    page_icon="🤖",
    layout="wide"
)

# ==================================================
# SESSION STATE
# ==================================================
if "question" not in st.session_state:
    st.session_state.question = ""

if "followups" not in st.session_state:
    st.session_state.followups = []

if "responses" not in st.session_state:
    st.session_state.responses = []

# ==================================================
# SIDEBAR
# ==================================================
with st.sidebar:
    st.markdown("## 🤖 Digital Employee")
    st.caption("Intent-aware Assistant")
    st.markdown("""
• NLP → SQL  
• Follow-up suggestions   
• Model independent (Gemini / Snowflake)  
""")

# ==================================================
# HEADER
# ==================================================
st.markdown("<h1 style='text-align:center;'>🤖 Digital Employee</h1>", unsafe_allow_html=True)
st.divider()

# ==================================================
# CORE HANDLER
# ==================================================
def handle_submit(user_input: str):
    st.session_state.followups = []
    st.session_state.responses = []

    with st.spinner("Digital Employee is thinking..."):

        # --------------------------------------------------
        # 1️⃣ INTENT CLASSIFICATION
        # --------------------------------------------------
        intent_prompt = f"""
Classify the user's intent into ONE category:

DATA – analytics, SQL, reporting, learning SQL  
REPLY – drafting or responding to a message (thank you, okay, acknowledgement)

Return ONLY one word: DATA or REPLY.

User input:
{user_input}
"""
        intent = llm.generate_content(intent_prompt).text.strip().upper()

        # ==================================================
        # REPLY MODE (LINKEDIN-STYLE REPLY COMPOSER)
        # ==================================================
        if intent == "REPLY":
            response_prompt = f"""
The user received this message and wants to reply.

Generate EXACTLY 3 short, professional reply drafts
that the user can send to another person.

Rules:
- One sentence max
- Professional tone
- No emojis

Return ONLY a JSON array.

Message received:
{user_input}
"""
            try:
                st.session_state.responses = json.loads(
                    llm.generate_content(response_prompt).text
                )
            except Exception:
                st.session_state.responses = [
                    "You’re welcome.",
                    "Happy to help.",
                    "Anytime."
                ]

            st.success("Reply drafts ready")
            return

        # ==================================================
        # DATA MODE (NLP → SQL)
        # ==================================================
        sql_prompt = f"""
You are an expert Snowflake analyst.

Generate ONLY a valid Snowflake SELECT query.
No explanation. No markdown.

Question:
{user_input}
"""
        generated_sql = llm.generate_content(sql_prompt).text.strip()

        # Try executing SQL (infra may or may not exist)
        try:
            session = Session.builder.configs({
                "account": os.getenv("SNOWFLAKE_ACCOUNT"),
                "user": os.getenv("SNOWFLAKE_USER"),
                "password": os.getenv("SNOWFLAKE_PASSWORD"),
                "role": os.getenv("SNOWFLAKE_ROLE"),
                "warehouse": "DEMO_WH",
                "database": "DEMO_DB",
                "schema": "PUBLIC"
            }).create()

            df = session.sql(generated_sql).to_pandas()
            session.close()

            st.success("Answer generated")

            with st.expander("Generated SQL"):
                st.code(generated_sql, language="sql")

            st.dataframe(df, use_container_width=True)

        except Exception:
            st.warning("Data execution unavailable. Showing Digital Employee suggestions.")

        # --------------------------------------------------
        # FOLLOW-UP QUESTIONS (ROBUST + FALLBACK)
        # --------------------------------------------------
        followup_prompt = f"""
Generate EXACTLY 3 relevant follow-up questions
the user might ask next.

Return ONLY a JSON array of strings.

User question:
{user_input}
"""
        raw_followups = llm.generate_content(followup_prompt).text.strip()

        try:
            st.session_state.followups = json.loads(raw_followups)
        except Exception:
            # Enterprise-safe fallback so demo never looks broken
            st.session_state.followups = [
                "Can you break this down further?",
                "Can you compare this with last month?",
                "What trends should I look at next?"
            ]

# ==================================================
# INTENT STARTERS (AUTO-SUBMIT)
# ==================================================
st.markdown("## What would you like help with today?")

c1, c2, c3, c4 = st.columns(4)

if c1.button("📊 Analyze data"):
    st.session_state.question = "Analyze my business data and highlight key insights."
    handle_submit(st.session_state.question)

if c2.button("⚙️ Automate work"):
    st.session_state.question = "Help me automate my daily tasks."
    handle_submit(st.session_state.question)

if c3.button("📅 Prepare meetings"):
    st.session_state.question = "What meetings do I have today and tomorrow?"
    handle_submit(st.session_state.question)

if c4.button("📘 Learn SQL"):
    st.session_state.question = "Teach me SQL using business examples."
    handle_submit(st.session_state.question)

st.divider()

# ==================================================
# SQL LEARNING (AUTO-SUBMIT)
# ==================================================
st.markdown("## 📘 Learn SQL using natural language")

sql_learning = {
    "Basic Queries": [
        "List all customers",
        "List all orders",
        "Show all orders with customer names"
    ],
    "Aggregations": [
        "What is the total sales amount?",
        "What is the average order value?"
    ]
}

for category, questions in sql_learning.items():
    with st.expander(f"📌 {category}"):
        for q in questions:
            if st.button(q):
                st.session_state.question = q
                handle_submit(q)

st.divider()

# ==================================================
# TEXT INPUT (MANUAL SUBMIT)
# ==================================================
question = st.text_input(
    "Ask Digital Employee",
    value=st.session_state.question,
    placeholder="Type here and click Ask"
)

if st.button("Ask 🤔", use_container_width=True):
    if len(question.strip()) < 2:
        st.error("Please enter a message")
    else:
        handle_submit(question)

# ==================================================
# FOLLOW-UPS UI (ALWAYS SHOW FOR DATA)
# ==================================================
if st.session_state.followups:
    st.divider()
    st.markdown("### 🔁 Suggested Follow-up Questions")
    for fq in st.session_state.followups:
        if st.button(fq):
            st.session_state.question = fq
            handle_submit(fq)

# ==================================================
# REPLY DRAFTS UI (LINKEDIN-STYLE)
# ==================================================
if st.session_state.responses:
    st.divider()
    st.markdown("### 💬 Draft replies you can send")
    st.caption("Click to copy and send externally")

    for r in st.session_state.responses:
        if st.button(r):
            st.code(r)
