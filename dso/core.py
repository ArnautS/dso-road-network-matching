from dso import session, delimited_strokes_ref, delimited_strokes_target
from structure import RoadSectionRef, JunctionRef, RoadSectionTarget, JunctionTarget, DelimitedStrokeRef, \
    DelimitedStrokeTarget, LinkingTable
from construction import classify_junctions, construct_stroke, construct_strokes, reset_delimited_strokes, \
    construct_stroke_from_section
from matching import find_matching_candidates, reset_matches
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
    if delimited_stroke_class == DelimitedStrokeRef:
        delimited_strokes = delimited_strokes_ref
    else:
        delimited_strokes = delimited_strokes_target

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


def matching_process(level, tolerance_distance):
    strokes_ref = session.query(DelimitedStrokeRef).filter(DelimitedStrokeRef.level == level,
                                                           DelimitedStrokeRef.match_id == None)
    strokes_target = session.query(DelimitedStrokeTarget).filter(DelimitedStrokeTarget.level == level)

    # reset_matches(strokes_ref)
    # reset_matches(strokes_target)

    all_matches = []
    for stroke_ref in strokes_ref:
        matches = find_matching_candidates(stroke_ref, tolerance_distance)
        if matches:
            if len(matches) > 2:
                print('LOTS OF MATCHES HERE !!!!!!!!!!!!!')
            best_score = 0
            best_match = None
            for match in matches:
                if match.similarity_score > best_score:
                    best_match = match
                    best_score = match.similarity_score

            if best_match:
                for stroke_ref in best_match.strokes_ref:
                    stroke_ref.match_id = best_match.id
                for stroke_target in best_match.strokes_target:
                    stroke_target.match_id = best_match.id

                all_matches.append(best_match)
    print('-----------------------------------------------------------')

    return all_matches


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

matches_result = []
# matches_result += matching_process(level=1, tolerance_distance=5)
# matches_result += matching_process(level=1, tolerance_distance=10)
matches_result += matching_process(level=1, tolerance_distance=20)

session.flush()

prepare_strokes_lvl2(DelimitedStrokeRef)
# prepare_strokes_lvl2(DelimitedStrokeTarget)

matches_result += matching_process(level=2, tolerance_distance=20)

session.query(LinkingTable).delete()
for match in matches_result:
    for stroke_ref in match.strokes_ref:
        for section_ref in delimited_strokes_ref[stroke_ref.id]:
            for stroke_target in match.strokes_target:
                for section_target in delimited_strokes_target[stroke_target.id]:
                    link = LinkingTable(nwb_id=section_ref.id, top10nl_id=section_target.id, match_id=match.id, similarity_score=match.similarity_score)
                    session.add(link)
                    session.flush()

        print('score:', match.similarity_score, ', ref stroke', match.strokes_ref[0].id)


session.commit()
session.close()
