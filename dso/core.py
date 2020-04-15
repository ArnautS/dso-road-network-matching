from sqlalchemy.orm import lazyload

from dso import session
from structure import RoadSectionRef, JunctionRef, RoadSectionTarget, JunctionTarget, DelimitedStrokeRef, \
    DelimitedStrokeTarget
from helpers import classify_junctions, construct_strokes, reset_delimited_strokes, construct_stroke_from_section, \
    construct_stroke, reset_matches
from matching import find_matching_candidates
from sqlalchemy.sql import func


def process_reference(preprocessing_check):
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
    session.query(DelimitedStrokeTarget).delete()
    reset_delimited_strokes(session.query(RoadSectionTarget))

    junctions_target = session.query(JunctionTarget).options(lazyload(JunctionTarget.road_sections)).all()
    # JunctionTarget.id, JunctionTarget.degree, JunctionTarget.type_k3, JunctionTarget.road_sections
    if preprocessing_check:
        classify_junctions(junctions_target)

    print("constructing strokes target database")
    construct_strokes(junctions_target, DelimitedStrokeTarget)
    remaining_sections_target = session.query(RoadSectionTarget).filter(RoadSectionTarget.delimited_stroke_id == None)
    for road_section in remaining_sections_target:
        if road_section.delimited_stroke is None:
            delimited_stroke = construct_stroke_from_section(road_section, DelimitedStrokeTarget)
            construct_stroke(road_section, road_section.begin_junction, delimited_stroke)


# process_reference(True)
# process_target(True)

# strokes_ref = {}
strokes_ref = session.query(DelimitedStrokeRef)
# , func.st_length(DelimitedStrokeRef.geom).label('length'))
# for stroke, length in strokes_ref_query:
#     stroke.length = length
# add this to query extra attributes ^
strokes_target = session.query(DelimitedStrokeTarget)

# for each in strokes_ref:
#     print(each.length)

reset_matches(strokes_ref)
reset_matches(strokes_target)

all_matches = []
for stroke_ref in strokes_ref:
    matches = find_matching_candidates(stroke_ref)
    all_matches.append(matches)
    for match in matches:
        print('Match:', match.id)
        for stroke in match.strokes_ref:
            print('reference stroke', stroke.id)
        for stroke in match.strokes_target:
            print('target stroke', stroke.id)
    print(' ')
print(all_matches)
session.commit()
session.close()
