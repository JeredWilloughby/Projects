from sqlalchemy import create_engine, Column, String, Float, Boolean, Date, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime

Base = declarative_base()

class ScanResult(Base):
    __tablename__ = 'scan_results'
    ticker = Column(String, primary_key=True)
    scan_date = Column(Date, primary_key=True)
    score = Column(Float)
    filter_passed = Column(Boolean)
    rules_passed = Column(String)  # "basic", "advanced", or "both"
    data_json = Column(Text)
    error_msg = Column(Text)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

engine = create_engine("sqlite:///scan_results.db")
Session = sessionmaker(bind=engine)
Base.metadata.create_all(engine)
