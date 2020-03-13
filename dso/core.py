from dso import session_scope
from structure import RoadSectionRef, JunctionRef, RoadSectionTarget, JunctionTarget, DelimitedStrokeRef, DelimitedStrokeTarget
from helpers import classify_junctions, construct_strokes, reset_delimited_strokes, construct_stroke_from_section, construct_stroke


def process_reference(preprocessing_check):
    with session_scope() as session:
        session.query(DelimitedStrokeRef).delete()
        reset_delimited_strokes(session.query(RoadSectionRef))

        junctions_ref = session.query(JunctionRef)
        if preprocessing_check:
            classify_junctions(junctions_ref)

        print("constructing strokes reference database")
        construct_strokes(junctions_ref, DelimitedStrokeRef)
        remaining_sections_ref = session.query(RoadSectionRef).filter(RoadSectionRef.delimited_stroke_id == None)
        for road_section in remaining_sections_ref:
            construct_stroke_from_section(road_section, DelimitedStrokeRef)


def process_target(preprocessing_check):
    with session_scope() as session:
        session.query(DelimitedStrokeTarget).delete()
        reset_delimited_strokes(session.query(RoadSectionTarget))

        junctions_target = session.query(JunctionTarget)
        if preprocessing_check:
            classify_junctions(junctions_target)

        print("constructing strokes target database")
        construct_strokes(junctions_target, DelimitedStrokeTarget)
        remaining_sections_target = session.query(RoadSectionTarget).filter(RoadSectionTarget.delimited_stroke_id == None)
        for road_section in remaining_sections_target:
            if road_section.delimited_stroke is None:
                delimited_stroke = construct_stroke_from_section(road_section, DelimitedStrokeTarget)
                construct_stroke(road_section, road_section.begin_junction, delimited_stroke)


process_reference(False)
process_target(False)
