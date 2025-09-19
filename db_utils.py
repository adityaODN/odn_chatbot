from langchain_community.utilities import SQLDatabase
from dotenv import load_dotenv
import os

load_dotenv()

DB_HOST = os.getenv("MYSQL_HOST")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

def get_sqlalchemy_database():
    """
    Returns a LangChain SQLDatabase object connected to MySQL via SQLAlchemy.
    """
    # SQLAlchemy connection string
    connection_string = f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    
    # Return SQLDatabase object compatible with LangChain
    return SQLDatabase.from_uri(connection_string)
