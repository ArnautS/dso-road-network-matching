from dso import session, tolerance_distance, deviation_angle
from structure import JunctionTarget, Match
from sqlalchemy import func
from helpers import angle_at_junction, angle_difference
from math import pi


def other_junction(road_section, junction):
    if road_section.begin_junction == junction:
        return road_section.end_junction
    else:
        return road_section.begin_junction


def has_good_continuity(stroke_a, stroke_b, junction):
    angle_a = angle_at_junction(stroke_a, junction)
    angle_b = angle_at_junction(stroke_b, junction)
    return pi-deviation_angle < angle_difference(angle_a, angle_b) < pi+deviation_angle


def get_length(list_of_strokes):
    length = 0
    for stroke in list_of_strokes:
        length += session.query(func.st_length(stroke.geom)).first()[0]
    return length


def extend_matching_pair(stroke_ref, stroke_target, junction_ref, junction_target):
    """Extends the input delimited strokes with strokes that have good continuity at input junction,
    until a good match is found or if no match is possible"""
    if get_length(stroke_ref) < get_length(stroke_target):
        stroke_to_extend = stroke_ref
        junction_to_extend = junction_ref
        junction_to_compare = junction_target
    else:
        stroke_to_extend = stroke_target
        junction_to_extend = junction_target
        junction_to_compare = junction_ref

    for section in junction_to_extend.road_sections:
        if has_good_continuity(section, stroke_to_extend[-1], junction_to_extend):
            stroke_to_extend.append(section.delimited_stroke)
            new_end_junction = other_junction(stroke_to_extend[-1], junction_to_extend)
            point_distance = session.query(func.st_distance(new_end_junction.geom, junction_to_compare.geom)).first()[0]
            if point_distance < tolerance_distance:
                print(f'new match with {stroke_ref[0].id}')
                return Match(stroke_ref, stroke_target)
            print(f'Extending test at stroke {stroke_to_extend.id}, has good continuity with section '
                  f'{section.delimited_stroke.id}')

    # TODO make recursive
    max_iterations = 3
    i = 0
    while i < max_iterations:
        i += 1

    return None


def get_distance(object_a, object_b):
    assert object_a.geom is not None
    assert object_b.geom is not None
    return session.query(func.st_distance(object_a.geom, object_b.geom)).first()[0]


def find_matching_candidates(stroke_ref):
    matches = []
    junction_candidates = nearby_junctions(stroke_ref.begin_junction)
    junction_ref = stroke_ref.begin_junction
    junction_ref_other = stroke_ref.end_junction
    if junction_candidates.count() == 0:
        junction_candidates = nearby_junctions(stroke_ref.end_junction)
        junction_ref = stroke_ref.end_junction
        junction_ref_other = stroke_ref.begin_junction
        if junction_candidates.count() == 0:
            # set delimited stroke check true
            print(f'id: {stroke_ref.id} has no nearby junctions')
            return matches
    print(f'searching for stroke {stroke_ref.id} at junction {junction_ref.id}')
    for junction_target in junction_candidates:
        for section_target in junction_target.road_sections:
            stroke_target = section_target.delimited_stroke
            junction_target_other = other_junction(stroke_target, junction_target)
            # check if stroke_target start or ends at junction_target
            if stroke_target.begin_junction == junction_target or stroke_target.end_junction == junction_target:
                # check if selected strokes already have a match
                if stroke_target not in [match.strokes_target[0] for match in matches]:  # TODO extend for N:M matches
                    line_distance_ref = get_distance(stroke_ref, junction_target_other)
                    line_distance_target = get_distance(stroke_target, junction_ref_other)
                    if line_distance_ref < tolerance_distance or line_distance_target < tolerance_distance:
                        junction_ref_other = other_junction(stroke_ref, junction_ref)
                        point_distance = get_distance(junction_ref_other, junction_target_other)
                        if point_distance < tolerance_distance:
                            match = Match([stroke_ref], [stroke_target])
                        else:
                            # match = None
                            print('Can possible extend this stroke', stroke_ref.id)
                            match = extend_matching_pair([stroke_ref], [stroke_target], junction_ref_other,
                                                         junction_target_other)
                        if match:
                            if matches:
                                print(f'extra match for stroke {stroke_ref.id}')
                            matches.append(match)
                            print(f'stroke_ref: {stroke_ref.id}, stroke_target: {stroke_target.id}, '
                                  f'junction_target: {junction_target.id}, section_target: {section_target.id}')
            # elif get_distance(junction_ref_other, junction_target_other)

    return matches


def nearby_junctions(junction_ref):
    """Finds the junctions in the target database that are within the tolerance distance of junction_ref"""
    junctions = session.query(JunctionTarget).filter(func.st_dwithin(JunctionTarget.geom, junction_ref.geom,
                                                                     tolerance_distance))
    return junctions
