"""Module matching.py contains all function related to the matching of the delimited strokes"""

from math import pi  # standard library

from sqlalchemy import func  # 3rd party packages

from dso import session, deviation_angle  # local source
from structure import JunctionTarget, Match
from helpers import angle_at_junction, angle_difference, get_length


def other_junction(road_section, junction):
    """Determines the other junction of the input road section, that is not equal to the input junction."""
    assert(road_section.begin_junction == junction or road_section.end_junction == junction)
    if road_section.begin_junction == junction:
        return road_section.end_junction
    else:
        return road_section.begin_junction


def has_good_continuity(stroke_a, stroke_b, junction):
    """Determines if the input strokes have good continuity with each other,
    that is an angle within 180 (+- deviation) degrees."""
    angle_a = angle_at_junction(stroke_a, junction)
    angle_b = angle_at_junction(stroke_b, junction)
    return pi-deviation_angle < angle_difference(angle_a, angle_b) < pi+deviation_angle


def extend_matching_pair(stroke_ref, stroke_target, junction_ref, junction_target, tolerance_distance):
    """Extends the input delimited strokes with strokes that have good continuity at input junction,
    until a good match is found or if no match is possible."""
    # create local variables of which stroke to extend and which to compare to when a new stroke is added
    if get_length(stroke_ref) < get_length(stroke_target):
        stroke_to_extend = stroke_ref
        stroke_to_compare = stroke_target
        junction_to_extend = junction_ref
        junction_to_compare = junction_target
    else:
        stroke_to_extend = stroke_target
        stroke_to_compare = stroke_ref
        junction_to_extend = junction_target
        junction_to_compare = junction_ref

    new_stroke = None
    # if the junction where the next stroke is added is a W-junction (type 1), select the stroke of the outer road
    # sections to be added
    if junction_to_extend.type_k3 == 1:
        if angle_at_junction(stroke_to_extend[-1], junction_to_extend) != junction_to_extend.angle_k3:
            for road_section in junction_to_extend.road_sections:
                if road_section.delimited_stroke != stroke_to_extend[-1] and junction_to_extend.angle_k3 != \
                        angle_at_junction(road_section, junction_to_extend):
                    new_stroke = road_section.delimited_stroke

    if junction_to_extend.degree > 1:
        for road_section in junction_to_extend.road_sections:
            if road_section.delimited_stroke != stroke_to_extend[-1] and has_good_continuity(road_section, stroke_to_extend[-1], junction_to_extend):
                new_stroke = road_section.delimited_stroke

    if new_stroke and (new_stroke.begin_junction == junction_to_extend or new_stroke.end_junction == junction_to_extend):
        stroke_to_extend.append(new_stroke)
        junction_to_extend = other_junction(stroke_to_extend[-1], junction_to_extend)
        point_distance = session.query(func.st_distance(junction_to_extend.geom, junction_to_compare.geom))[0][0]
        if point_distance < tolerance_distance:
            return Match(stroke_ref, stroke_target)
        elif session.query(func.st_distance(junction_to_extend.geom, stroke_to_compare[-1].geom))[0][0] < tolerance_distance or \
                session.query(func.st_distance(junction_to_compare.geom, stroke_to_extend[-1].geom))[0][0] < tolerance_distance:
            if stroke_to_extend == stroke_ref:
                return extend_matching_pair(stroke_ref, stroke_target, junction_to_extend, junction_target, tolerance_distance)
            elif stroke_to_extend == stroke_target:
                return extend_matching_pair(stroke_ref, stroke_target, junction_ref, junction_to_extend, tolerance_distance)
            else:
                print('Error: wrong stroke')
    return None


def get_distance(object_a, object_b):
    """Calculates the distance between two geometries."""
    assert object_a.geom is not None
    assert object_b.geom is not None
    return session.query(func.st_distance(object_a.geom, object_b.geom))[0][0]


def find_matching_candidates(stroke_ref, tolerance_distance):
    """Searches a match for stroke_ref. The starting junction of the matched stroke has to be within the
    tolerance_distance. If the end junction is not within the tolerance_distance, extend_matching_pair is called."""
    matches = []
    junction_candidates = nearby_junctions(stroke_ref.begin_junction, tolerance_distance)
    junction_ref = stroke_ref.begin_junction
    junction_ref_other = stroke_ref.end_junction
    if junction_candidates.count() == 0:
        junction_candidates = nearby_junctions(stroke_ref.end_junction, tolerance_distance)
        junction_ref = stroke_ref.end_junction
        junction_ref_other = stroke_ref.begin_junction
        if junction_candidates.count() == 0:
            # TODO set delimited stroke check true
            return matches

    for junction_target in junction_candidates:
        for section_target in junction_target.road_sections:
            stroke_target = section_target.delimited_stroke
            if stroke_ref.match_id != stroke_target.match_id or stroke_ref.match_id is None:
                match = None

                if stroke_target.begin_junction == junction_target or stroke_target.end_junction == junction_target:
                    junction_target_other = other_junction(stroke_target, junction_target)
                    if get_distance(junction_ref_other, junction_target_other) < tolerance_distance:
                        match = Match([stroke_ref], [stroke_target])
                    elif get_distance(stroke_ref, junction_target_other) < tolerance_distance or \
                            get_distance(stroke_target, junction_ref_other) < tolerance_distance:
                        match = extend_matching_pair([stroke_ref], [stroke_target], junction_ref_other,
                                                     junction_target_other, tolerance_distance)
                else:
                    if get_distance(stroke_target.begin_junction, junction_ref_other) < tolerance_distance:
                        match = extend_matching_pair([stroke_ref], [stroke_target], junction_ref, stroke_target.end_junction, tolerance_distance)
                    elif get_distance(stroke_target.end_junction, junction_ref_other) < tolerance_distance:
                        match = extend_matching_pair([stroke_ref], [stroke_target], junction_ref, stroke_target.begin_junction, tolerance_distance)

                if match:
                    matches.append(match)
    return matches


def nearby_junctions(junction_ref, tolerance_distance):
    """Finds the junctions in the target database that are within the tolerance distance of junction_ref."""
    junctions = session.query(JunctionTarget).filter(func.st_dwithin(JunctionTarget.geom, junction_ref.geom,
                                                                     tolerance_distance))
    return junctions


def reset_matches(strokes):
    """Resets the match of each delimited stroke from the input strokes."""
    for each in strokes:
        each.match_id = None
