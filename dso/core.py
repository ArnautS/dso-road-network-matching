from dso import session, delimited_strokes
from structure import RoadSectionRef, JunctionRef, RoadSectionTarget, JunctionTarget, DelimitedStrokeRef, \
    DelimitedStrokeTarget
from helpers import classify_junctions, construct_strokes, reset_delimited_strokes, construct_stroke_from_section, \
    construct_stroke, reset_matches
from matching import find_matching_candidates
from sqlalchemy.sql import func


def preprocess_reference(preprocessing_check):
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


def preprocess_target(preprocessing_check):
    session.query(DelimitedStrokeTarget).delete()
    reset_delimited_strokes(session.query(RoadSectionTarget))

    junctions_target = session.query(JunctionTarget)
    if preprocessing_check:
        classify_junctions(junctions_target)

    print("constructing strokes target database")
    construct_strokes(junctions_target, DelimitedStrokeTarget)
    remaining_sections_target = session.query(RoadSectionTarget).filter(RoadSectionTarget.delimited_stroke_id == None)
    for road_section in remaining_sections_target:
        construct_stroke_from_section(road_section, DelimitedStrokeTarget)


def prepare_strokes_lvl2(delimited_stroke_class):
    not_matched_strokes = session.query(delimited_stroke_class).filter(delimited_stroke_class.match_id == None)
    for delimited_stroke in not_matched_strokes:
        for road_section in delimited_strokes[delimited_stroke.id]:
            road_section.delimited_stroke = None
        begin_junction = delimited_stroke.begin_junction
        for road_section in delimited_strokes[delimited_stroke.id]:
            if road_section.delimited_stroke is None:
                new_stroke = construct_stroke_from_section(road_section, delimited_stroke_class, level=2,
                                                           begin_junction=begin_junction)
                extended_stroke = construct_stroke(road_section, begin_junction, new_stroke, level=2)
                begin_junction = extended_stroke.end_junction

    session.query(delimited_stroke_class).filter(delimited_stroke_class.level == 1,
                                                 delimited_stroke_class.match_id == None).delete()


def matching_process(level):
    strokes_ref = session.query(DelimitedStrokeRef).filter(DelimitedStrokeRef.level == level)
    strokes_target = session.query(DelimitedStrokeTarget).filter(DelimitedStrokeTarget.level == level)

    reset_matches(strokes_ref)
    reset_matches(strokes_target)

    all_matches = []
    for stroke_ref in strokes_ref:
        matches = find_matching_candidates(stroke_ref)
        all_matches.append(matches)
        print(' ')
    print('-----------------------------------------------------------')
    for matches in all_matches:
        if len(matches) > 1:
            for match in matches:
                print('Match:', match.id)
                for stroke in match.strokes_ref:
                    print('reference stroke', stroke.id)
                for stroke in match.strokes_target:
                    print('target stroke', stroke.id)
            print(' ')


road_sections_ref = {}
for section in session.query(RoadSectionRef):
    road_sections_ref[section.id] = section

# for section in road_sections_ref:
#     print(road_sections_ref[section].delimited_stroke_id) #, ' = ',
#           strokes_ref[road_sections_ref[section].delimited_stroke_id].id)

# , func.st_length(DelimitedStrokeRef.geom).label('length'))
# for stroke, length in strokes_ref_query:
#     stroke.length = length
# add this to query extra attributes ^


preprocess_reference(0)
preprocess_target(0)

matching_process(1)

prepare_strokes_lvl2(DelimitedStrokeRef)
prepare_strokes_lvl2(DelimitedStrokeTarget)

matching_process(2)

# for stroke in delimited_strokes:
#     print(stroke)
#     for section in delimited_strokes[stroke]:
#         print(section.id)


session.commit()
session.close()
