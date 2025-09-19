from langchain_community.utilities import SQLDatabase
from dotenv import load_dotenv
import os
import streamlit as st

# load_dotenv()

# DB_HOST = os.getenv("MYSQL_HOST")
# DB_PORT = int(os.getenv("DB_PORT", 3306))
# DB_USER = os.getenv("DB_USER")
# DB_PASSWORD = os.getenv("DB_PASSWORD")
# DB_NAME = os.getenv("DB_NAME")



# DB_HOST = st.secrets["MYSQL_HOST"]
# DB_PORT = int(st.secrets.get("DB_PORT", 3306))
# DB_USER = st.secrets["DB_USER"]
# DB_PASSWORD = st.secrets["DB_PASSWORD"]
# DB_NAME = st.secrets["DB_NAME"]

if os.path.exists(".env"):
    load_dotenv()

DB_HOST = st.secrets.get("MYSQL_HOST", os.getenv("MYSQL_HOST"))
DB_PORT = int(st.secrets.get("DB_PORT", os.getenv("DB_PORT", 3306)))
DB_USER = st.secrets.get("DB_USER", os.getenv("DB_USER"))
DB_PASSWORD = st.secrets.get("DB_PASSWORD", os.getenv("DB_PASSWORD"))
DB_NAME = st.secrets.get("DB_NAME", os.getenv("DB_NAME"))

def get_sqlalchemy_database():
    """
    Returns a LangChain SQLDatabase object connected to MySQL via SQLAlchemy.
    """
    # SQLAlchemy connection string
    connection_string = f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    
    # Return SQLDatabase object compatible with LangChain
    return SQLDatabase.from_uri(connection_string)

