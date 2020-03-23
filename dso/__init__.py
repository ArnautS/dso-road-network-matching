from math import pi
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

deviation_angle = pi / 18  # radians
tolerance_distance = 20  # meters

engine = create_engine('postgresql://postgres:admin@localhost/postgres')
Session = sessionmaker(bind=engine)
session = Session()
