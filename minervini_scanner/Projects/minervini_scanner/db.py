from sqlalchemy import create_engine, Column, String, Float, DateTime, Integer
from sqlalchemy.orm import declarative_base, sessionmaker
import datetime

Base = declarative_base()

class ScanResult(Base):
    __tablename__ = "scan_results"
    id = Column(Integer, primary_key=True)
    ticker = Column(String, unique=True)
    score = Column(Float)
    date_scanned = Column(DateTime, default=datetime.datetime.utcnow)

engine = create_engine("sqlite:///scan_results.db")
Session = sessionmaker(bind=engine)
Base.metadata.create_all(engine)
