from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from structure import RoadSectionRef, JunctionRef, RoadSectionTarget, JunctionTarget, DelimitedStrokeRef, DelimitedStrokeTarget
from helpers import classify_junctions, construct_strokes, reset_delimited_strokes, construct_stroke_from_section


def run_reference(preprocessing_check):
    session.query(DelimitedStrokeRef).delete()
    reset_delimited_strokes(session.query(RoadSectionRef))

    junctions_ref = session.query(JunctionRef)
    if preprocessing_check:
        classify_junctions(junctions_ref, session)

    print("constructing strokes reference database")
    construct_strokes(junctions_ref, session, DelimitedStrokeRef)
    remaining_sections_target = session.query(RoadSectionTarget).filter(RoadSectionTarget.delimited_stroke_id == None)
    for road_section in remaining_sections_target:
        construct_stroke_from_section(road_section, session, DelimitedStrokeTarget)


def run_target(preprocessing_check):
    session.query(DelimitedStrokeTarget).delete()
    reset_delimited_strokes(session.query(RoadSectionTarget))

    junctions_target = session.query(JunctionTarget)
    if preprocessing_check:
        classify_junctions(junctions_target, session)

    print("constructing strokes target database")
    construct_strokes(junctions_target, session, DelimitedStrokeTarget)
    remaining_sections_ref = session.query(RoadSectionRef).filter(RoadSectionRef.delimited_stroke_id == None)
    for road_section in remaining_sections_ref:
        construct_stroke_from_section(road_section, session, DelimitedStrokeRef)


# create a connection with the database holding the road_section, junction and delimited_stroke tables
engine = create_engine('postgresql://postgres:admin@localhost/postgis_sample')
Session = sessionmaker(bind=engine)
session = Session()

run_reference(False)
run_target(False)

session.commit()
