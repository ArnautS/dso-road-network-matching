from math import pi
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

deviation_angle = 20  # degrees
deviation_angle = deviation_angle * pi / 180  # radians
tolerance_distance = 20  # meters
match_id = 0

engine = create_engine('postgresql://postgres:admin@localhost/postgres')
Session = sessionmaker(bind=engine)
session = Session()
