import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# Load .env values
load_dotenv()

# Build database URL
dbUser = os.getenv("MYSQL_USER")
dbPass = os.getenv("MYSQL_PASSWORD")
dbHost = os.getenv("MYSQL_HOST")
dbPort = os.getenv("MYSQL_PORT")
dbName = os.getenv("MYSQL_DB")

DATABASE_URL = f"mysql+pymysql://{dbUser}:{dbPass}@{dbHost}:{dbPort}/{dbName}"

# SQLAlchemy engine and session
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()
