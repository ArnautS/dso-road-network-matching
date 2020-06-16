from dso import session, deviation_angle
from structure import JunctionTarget, Match
from sqlalchemy import func
from helpers import angle_at_junction, angle_difference, get_length
from math import pi


def other_junction(road_section, junction):
    assert(road_section.begin_junction == junction or road_section.end_junction == junction)
    if road_section.begin_junction == junction:
        return road_section.end_junction
    else:
        return road_section.begin_junction


def has_good_continuity(stroke_a, stroke_b, junction):
    angle_a = angle_at_junction(stroke_a, junction)
    angle_b = angle_at_junction(stroke_b, junction)
    return pi-deviation_angle < angle_difference(angle_a, angle_b) < pi+deviation_angle


def extend_matching_pair(stroke_ref, stroke_target, junction_ref, junction_target, tolerance_distance):
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

    new_stroke = None
    if junction_to_extend.type_k3 == 1:
        for road_section in junction_to_extend.road_sections:
            if road_section.delimited_stroke != stroke_to_extend[-1] and junction_to_extend.angle_k3 != \
                    angle_at_junction(road_section, junction_to_extend):
                new_stroke = road_section.delimited_stroke

    if junction_to_extend.degree > 1:
        print(f'extend stroke {stroke_to_extend[-1].id} at junction {junction_to_extend.id}, compare with {junction_to_compare.id}')
        for road_section in junction_to_extend.road_sections:
            # print(f'road_section: {road_section.delimited_stroke.id}, stroke to extend: {stroke_to_extend[-1].id}, junction_to_extend: {junction_to_extend.id}')
            if road_section.delimited_stroke != stroke_to_extend[-1] and has_good_continuity(road_section, stroke_to_extend[-1], junction_to_extend):
                new_stroke = road_section.delimited_stroke

    if new_stroke and (new_stroke.begin_junction == junction_to_extend or new_stroke.end_junction == junction_to_extend):
        stroke_to_extend.append(new_stroke)
        new_end_junction = other_junction(stroke_to_extend[-1], junction_to_extend)
        point_distance = session.query(func.st_distance(new_end_junction.geom, junction_to_compare.geom))[0][0]
        if point_distance < tolerance_distance:
            print(f'new match with {stroke_ref[0].id}')
            return Match(stroke_ref, stroke_target)

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


def find_matching_candidates(stroke_ref, tolerance_distance):
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
    """Finds the junctions in the target database that are within the tolerance distance of junction_ref"""
    junctions = session.query(JunctionTarget).filter(func.st_dwithin(JunctionTarget.geom, junction_ref.geom,
                                                                     tolerance_distance))
    return junctions


def reset_matches(strokes):
    """Resets the match of each delimited stroke from the input strokes"""
    for each in strokes:
        each.match_id = None
