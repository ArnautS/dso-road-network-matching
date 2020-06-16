from math import pi
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

deviation_angle = 20  # degrees
deviation_angle = deviation_angle * pi / 180  # radians
match_id = 0
delimited_strokes = {}

# tolerance values
tolerance_distance = 20  # meters
tolerance_length = 20  # meters
tolerance_hausdorff = 20  # meters
tolerance_area_normalized = 1.5  # ratio of length to area difference


engine = create_engine('postgresql://postgres:admin@localhost/postgres')
Session = sessionmaker(bind=engine)
session = Session()
