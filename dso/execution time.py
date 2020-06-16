from dso import session
from structure import RoadSectionRef, JunctionRef, RoadSectionTarget, JunctionTarget, DelimitedStrokeRef, DelimitedStrokeTarget
from construction import classify_junctions, construct_stroke, construct_strokes, reset_delimited_strokes, \
    construct_stroke_from_section
from matching import find_matching_candidates

junctions = session.query(JunctionRef)
for junction in junctions:
    for section in junction.road_sections:
        print(section.id)
