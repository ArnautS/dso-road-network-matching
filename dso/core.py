"""Module core.py is the main executable. It runs the construction and matching functions in order, and generates an
output of the algorithm."""

import time  # standard library

from dso import session, delimited_strokes_ref, delimited_strokes_target  # local source
from structure import RoadSectionRef, JunctionRef, RoadSectionTarget, JunctionTarget, DelimitedStrokeRef, \
    DelimitedStrokeTarget, LinkingTable
from construction import classify_junctions, construct_stroke, construct_strokes, reset_delimited_strokes, \
    construct_stroke_from_section
from matching import find_matching_candidates


def preprocess_reference(preprocessing_check):
    """"Handles the preprocessing of the reference dataset. Includes classification of junctions and construction of
    delimited strokes at level 1. The input preprocessing_check can be set to false if junctions are already classified
    and saved in the database."""
    session.query(DelimitedStrokeRef).delete()
    reset_delimited_strokes(session.query(RoadSectionRef))

    junctions_ref = session.query(JunctionRef)
    if preprocessing_check:
        print("Classifying junctions of the reference database.")
        classify_junctions(junctions_ref)

    print("Constructing strokes of the reference database.")
    construct_strokes(junctions_ref, DelimitedStrokeRef)
    remaining_sections_ref = session.query(RoadSectionRef).filter(RoadSectionRef.delimited_stroke_id == None)
    for road_section in remaining_sections_ref:
        construct_stroke_from_section(road_section, DelimitedStrokeRef)


def preprocess_target(preprocessing_check):
    """"Handles the preprocessing of the target dataset. Includes classification of junctions and construction of
        delimited strokes at level 1."""
    session.query(DelimitedStrokeTarget).delete()
    reset_delimited_strokes(session.query(RoadSectionTarget))

    junctions_target = session.query(JunctionTarget)
    if preprocessing_check:
        print("Classifying junctions of the target database.")
        classify_junctions(junctions_target)

    print("Constructing strokes of the target database.")
    construct_strokes(junctions_target, DelimitedStrokeTarget)
    remaining_sections_target = session.query(RoadSectionTarget).filter(RoadSectionTarget.delimited_stroke_id == None)
    for road_section in remaining_sections_target:
        construct_stroke_from_section(road_section, DelimitedStrokeTarget)


def prepare_strokes_lvl2(delimited_stroke_class):
    """Constructs delimited strokes of level 2 for road sections in strokes that could not be matched."""
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
    """Searches for a match for each delimited stroke in the reference database."""
    strokes_ref = session.query(DelimitedStrokeRef).filter(DelimitedStrokeRef.level == level,
                                                           DelimitedStrokeRef.match_id == None)
    count = 0
    all_matches = []
    for stroke in strokes_ref:
        try:
            matches = find_matching_candidates(stroke, tolerance_distance)
        except:
            # related to matches of looping road sections
            print('Something went wrong trying to find a match for stroke', stroke.id)
            matches = None

        if matches:
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
        count += 1
        if count % 100 == 0:
            print('Strokes analyzed:', count)

    return all_matches


def generate_output(matches):
    session.query(LinkingTable).delete()
    for match in matches:
        for stroke_ref in match.strokes_ref:
            try:
                for section_ref in delimited_strokes_ref[stroke_ref.id]:
                    for stroke_target in match.strokes_target:
                        for section_target in delimited_strokes_target[stroke_target.id]:
                            link = LinkingTable(nwb_id=section_ref.id, top10nl_id=section_target.id, match_id=match.id,
                                                similarity_score=match.similarity_score)
                            session.add(link)
                            session.flush()
            except KeyError:
                print('Stroke', stroke_ref.id, 'not recorded in delimited strokes dictionary')
        # if match.similarity_score < 0.2:
        #     print('score:', match.similarity_score, ', ref stroke', match.strokes_ref[0].id)


# execution of algorithm starts here
start_time = time.time()

preprocess_reference(1)
preprocess_target(1)

print('---------------------')
print('Matching strokes lvl 1')

matches_result = []
matches_result += matching_process(level=1, tolerance_distance=20)

session.flush()

print('---------------------')
print('Matching strokes lvl 2')

prepare_strokes_lvl2(DelimitedStrokeRef)
prepare_strokes_lvl2(DelimitedStrokeTarget)
matches_result += matching_process(level=2, tolerance_distance=20)

generate_output(matches_result)


session.commit()
session.close()

end_time = time.time()
print('time elapsed:', end_time-start_time)
