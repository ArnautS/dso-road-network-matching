"""Module __init__.py is used to set tolerance values and creates a session to connect to the PostGIS database."""

from math import pi  # standard library

from sqlalchemy import create_engine  # 3rd party packages
from sqlalchemy.orm import sessionmaker

# dictionaries used to store generated delimited strokes
delimited_strokes_ref = {}
delimited_strokes_target = {}

# tolerance values
deviation_angle = 20  # degrees
deviation_angle = deviation_angle * pi / 180  # radians
tolerance_distance = 20  # meters
tolerance_length = 20  # meters
tolerance_hausdorff = 20  # meters
tolerance_area_normalized = 1.5  # ratio of length to area difference

# connection to PostGIS database
engine = create_engine('postgresql://postgres:admin@localhost/postgres')
Session = sessionmaker(bind=engine)
session = Session()
