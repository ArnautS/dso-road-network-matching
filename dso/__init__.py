from math import pi
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

deviation_angle = pi / 18

engine = create_engine('postgresql://postgres:admin@localhost/postgis_sample')
Session = sessionmaker(bind=engine)
session = Session()
