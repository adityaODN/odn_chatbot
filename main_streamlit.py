import os
import ast
import time
import streamlit as st
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import text   # 🔧 needed for manual query execution
from langchain_openai import ChatOpenAI
from langchain_experimental.sql import SQLDatabaseChain
from db_utils import get_sqlalchemy_database

# ---------------- Load API Keys ----------------
# load_dotenv()

# OPENAI_API_KEY = os.getenv("OPEN_AI_KEY")
OPENAI_API_KEY = st.secrets["OPEN_AI_KEY"]
if not OPENAI_API_KEY:
    st.error("OPENAI_API_KEY environment variable not set. Please set it in your .env file or system environment.")
    st.stop()

# ---------------- Initialize LLM ----------------
# llm = ChatOpenAI(temperature=0, openai_api_key=OPENAI_API_KEY)
llm = ChatOpenAI(api_key=OPENAI_API_KEY, model="gpt-4o-mini")
# ---------------- MySQL Connection ----------------
db = get_sqlalchemy_database()
db_chain = SQLDatabaseChain.from_llm(llm, db, verbose=True)

# ---------------- Streamlit Config ----------------
st.set_page_config(page_title="Chitti Babu", page_icon="🤖", layout="wide")
st.title("Chitti Babu 🤖")

# ---------------- Session State ----------------
if "messages" not in st.session_state:
    st.session_state.messages = []

def add_message(msg, sender="user"):
    st.session_state.messages.append({"message": msg, "sender": sender})

# ---------------- INR Formatter ----------------
def format_inr(value):
    try:
        value = float(value)
        return f"₹{value:,.2f}"
    except:
        return value

def format_money_columns(data):
    if isinstance(data, pd.DataFrame):
        money_cols = [col for col in data.columns if any(
            kw in col.lower() for kw in ["cost", "expense", "salary"]
        )]
        for col in money_cols:
            data[col] = data[col].apply(format_inr)
    return data

# ---------------- Schema Context ----------------
SCHEMA_CONTEXT = """
You are connected to a database with the following schema:

Table 1: ohs_oes (Overheads and Other Expenses)
Columns:
- S_No
- Month
- Year
- Location
- Expense Segment
- Department
- Expense Type
- Cost

Table 2: salary_expense
Columns:
- S_No
- Month
- Year
- Expense Segment
- Department
- Location
- Employee Code
- Employee Name
- Salary

Table 3: variable_expense
Columns:
- Month
- Year
- Location
- Expense Segment
- Department
- Expense Type
- Modelling Agency Name/Freelancer Name
- Expense
"""

# ---------------- Intent Classification ----------------
def classify_intent(msg: str) -> str:
    intent_prompt = f"""
    {SCHEMA_CONTEXT}

    Classify the following user request into one of three categories:
    1. db_query - direct request for data
    2. prediction - forecasting, trend analysis, estimation, classification
    3. smalltalk - greeting, farewell, thanking, or chit-chat

    User request: "{msg}"

    Answer with only one word: db_query, prediction, or smalltalk.
    """
    return llm.predict(intent_prompt).strip().lower()

# ---------------- Typing Effect ----------------
def typing_effect(message, speed=0.02):
    placeholder = st.empty()
    text = ""
    for char in message:
        text += char
        placeholder.markdown(
            f"<div class='chat-bubble bot-bubble'>Chitti Babu: {text}</div>",
            unsafe_allow_html=True
        )
        time.sleep(speed)
    return text

# ---------------- SQL Query Generator ----------------
def build_sql_prompt(user_input: str, forced_table: str = None) -> str:
    sql_prompt = f"""
    {SCHEMA_CONTEXT}

    The user request is: "{user_input}".

    Rules:
    - Always generate valid MySQL SQL queries.
    - If the request contains the word "by" (e.g. "month and department by cost"),
      interpret it as a GROUP BY request.
    - Extract mentioned columns (like Month, Department, Location) and group by them.
    - Always SUM numeric fields like Cost, Expense, Salary and alias them clearly.
    - Also ORDER BY the grouped columns in the same order as requested.
    - Use correct column names only from schema.
    {"Force the query to use this table: " + forced_table if forced_table else ""}
    Only return the SQL query.
    """
    return sql_prompt

# ---------------- Main Handler ----------------
def handle_message(user_input):
    if not user_input.strip():
        return

    add_message(user_input, sender="user")

    try:
        # Force table selection based on keywords
        forced_table = None
        if any(word in user_input.lower() for word in ["cost", "overhead", "fee", "compliance", "maintenance"]):
            forced_table = "ohs_oes"
        elif any(word in user_input.lower() for word in ["expense", "freelancer", "agency", "marketing"]):
            forced_table = "variable_expense"
        elif any(word in user_input.lower() for word in ["salary", "payroll", "employee"]):
            forced_table = "salary_expense"

        intent = classify_intent(user_input)

        if intent in ["prediction", "db_query"]:
            sql_prompt = build_sql_prompt(user_input, forced_table)
            sql_query = llm.predict(sql_prompt).strip()

            if not sql_query.lower().startswith("select"):
                add_message("Sorry, I could not create a valid SQL query. Please rephrase.", sender="bot")
                return

            try:
                # 🔧 FIX: Run query with SQLAlchemy and get real headers
                with db._engine.connect() as connection:
                    result = connection.execute(text(sql_query))
                    columns = result.keys()
                    rows = result.fetchall()
                    history = pd.DataFrame(rows, columns=columns)

                history = format_money_columns(history)

            except Exception as e:
                add_message(f"I tried to run a query but got an error: {e}.", sender="bot")
                return

            if intent == "prediction":
                prediction_prompt = f"""
                User asked: "{user_input}".

                Historical data:
                {history}

                Based on this data, make a prediction or forecast.
                Show results clearly in a table (if possible).
                Format monetary values (Cost, Expense, Salary) in INR (₹).
                Provide a short explanation of the trend.
                """
                response = llm.predict(prediction_prompt)
                add_message(response, sender="bot")
            else:
                add_message(history, sender="bot")
        else:
            response = llm.predict(
                f"The user said: '{user_input}'. Respond naturally, conversationally. No databases or predictions."
            )
            add_message(response, sender="bot")

    except Exception as e:
        add_message(f"Unexpected error: {e}", sender="bot")

# ---------------- CSS for ChatGPT-like Style ----------------
st.markdown(
    """
    <style>
    .chat-bubble {
        display: inline-block;
        padding: 10px 15px;
        border-radius: 15px;
        margin: 5px 0;
        word-wrap: break-word;
        color: black;
        max-width: 80%;
    }
    .user-bubble {
        background-color: #DCF8C6;
        margin-left: auto;
        text-align: right;
    }
    .bot-bubble {
        background-color: #F1F0F0;
        margin-right: auto;
        text-align: left;
    }
    .chat-input {
        position: fixed;
        bottom: 20px;
        left: 5%;
        width: 90%;
        background-color: white;
        padding: 10px;
        border-top: 1px solid #ddd;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ---------------- Display Chat History ----------------
st.markdown("<div class='chat-container'>", unsafe_allow_html=True)
for msg in st.session_state.messages:
    if msg["sender"] == "user":
        st.markdown(
            f"<div class='chat-bubble user-bubble'>You: {msg['message']}</div>",
            unsafe_allow_html=True
        )
    else:
        message = msg["message"]

        if isinstance(message, pd.DataFrame):
            st.markdown("<div class='chat-bubble bot-bubble'>Chitti Babu:</div>", unsafe_allow_html=True)
            st.dataframe(message)

        elif isinstance(message, list) and all(isinstance(x, tuple) for x in message):
            st.markdown("<div class='chat-bubble bot-bubble'>Chitti Babu:</div>", unsafe_allow_html=True)
            df = pd.DataFrame(message)
            st.dataframe(df)

        elif isinstance(message, str) and message.strip().startswith("[("):
            try:
                parsed = ast.literal_eval(message)
                if isinstance(parsed, list) and all(isinstance(x, tuple) for x in parsed):
                    st.markdown("<div class='chat-bubble bot-bubble'>Chitti Babu:</div>", unsafe_allow_html=True)
                    df = pd.DataFrame(parsed)
                    st.dataframe(df)
                    continue
            except Exception:
                pass
            st.markdown(f"<div class='chat-bubble bot-bubble'>Chitti Babu: {message}</div>", unsafe_allow_html=True)

        else:
            if msg == st.session_state.messages[-1]:
                typing_effect(str(message), speed=0.02)
            else:
                st.markdown(f"<div class='chat-bubble bot-bubble'>Chitti Babu: {message}</div>", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

# ---------------- CSS for Sticky Bottom Chat Input ----------------
st.markdown(
    """
    <style>
    /* Force body padding to avoid overlap with chat bar */
    .block-container {
        padding-bottom: 80px !important;
    }

    /* Sticky container */
    .chat-input-container {
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        display: flex;
        align-items: center;
        padding: 10px 15px;
        background-color: #2a2a2a;
        box-shadow: 0px -2px 6px rgba(0,0,0,0.3);
        z-index: 9999;
    }

    /* Stretch input field */
    div[data-testid="stTextInput"] {
        flex: 1;
    }

    /* Style input box */
    div[data-testid="stTextInput"] input {
        border: none !important;
        outline: none !important;
        font-size: 16px;
        background-color: #1e1e1e !important;
        color: #f8f8f8 !important;
    }

    /* Style send button */
    div[data-testid="stFormSubmitButton"] button {
        border: none !important;
        background-color: #25D366 !important;
        color: white !important;
        font-size: 18px !important;
        font-weight: bold !important;
        border-radius: 50% !important;
        width: 45px !important;
        height: 45px !important;
        margin-left: 10px;
        cursor: pointer;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ---------------- Sticky Input Form ----------------
st.markdown('<div class="chat-input-container">', unsafe_allow_html=True)

with st.form(key="chat_form", clear_on_submit=True):
    col1, col2 = st.columns([10, 1])
    with col1:
        user_input = st.text_input("", placeholder="Hi, I'm Chitti the Chatbot.", label_visibility="collapsed")
    with col2:
        send = st.form_submit_button("➤")

    if send and user_input.strip():
        handle_message(user_input)
        st.rerun()

st.markdown('</div>', unsafe_allow_html=True)


