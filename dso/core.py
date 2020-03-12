from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from structure import RoadSectionRef, JunctionRef, RoadSectionTarget, JunctionTarget, DelimitedStrokeRef, DelimitedStrokeTarget
from helpers import classify_junctions, construct_strokes

# create a connection with the database holding the road_section, junction and delimited_stroke tables
engine = create_engine('postgresql://postgres:admin@localhost/postgis_sample')
Session = sessionmaker(bind=engine)
session = Session()

junctions_ref = session.query(JunctionRef) #.limit(10)
junctions_target = session.query(JunctionTarget)

# reset previously generated strokes
session.query(DelimitedStrokeTarget).delete()
road_sections_ref = session.query(RoadSectionRef)
for each in road_sections_ref:
    each.delimited_stroke = None

road_sections_target = session.query(RoadSectionTarget)
for each in road_sections_target:
    each.delimited_stroke = None

# classify_junctions(junctions_ref, session)
# classify_junctions(junctions_target, session)

# construct_strokes(junctions_ref, session)
construct_strokes(junctions_target, session)

# creates a delimited stroke for every road_section in the input table
session.commit()
