from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from structure import RoadSectionRef, JunctionRef, RoadSectionTarget, JunctionTarget, DelimitedStrokeRef, DelimitedStrokeTarget
from helpers import classify_junctions, construct_strokes, reset_delimited_strokes, construct_stroke_from_section

# create a connection with the database holding the road_section, junction and delimited_stroke tables
engine = create_engine('postgresql://postgres:admin@localhost/postgis_sample')
Session = sessionmaker(bind=engine)
session = Session()

junctions_ref = session.query(JunctionRef)
junctions_target = session.query(JunctionTarget)

# reset previously generated strokes

reset_delimited_strokes(session.query(RoadSectionRef))

session.query(DelimitedStrokeTarget).delete()
reset_delimited_strokes(session.query(RoadSectionTarget))

# classify_junctions(junctions_ref, session)
# classify_junctions(junctions_target, session)

# creates a delimited stroke for every road_section in the input table
# construct_strokes(junctions_ref, session)
construct_strokes(junctions_target, session)

remaining_sections_ref = session.query(RoadSectionRef).filter(RoadSectionRef.delimited_stroke_id == None)
for road_section in remaining_sections_ref:
    construct_stroke_from_section(road_section)

remaining_sections_target = session.query(RoadSectionTarget).filter(RoadSectionTarget.delimited_stroke_id == None)
for road_section in remaining_sections_target:
    construct_stroke_from_section(road_section)


session.commit()
