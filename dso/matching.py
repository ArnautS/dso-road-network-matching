from dso import session, tolerance_distance
from structure import JunctionTarget, Match
from sqlalchemy import func


def other_junction(road_section, junction):
    if road_section.begin_junction == junction:
        return road_section.end_junction
    else:
        return road_section.begin_junction


def find_matching_candidates(stroke_ref):
    matches = []
    junction_candidates = nearby_junctions(stroke_ref.begin_junction)
    junction_ref = stroke_ref.begin_junction
    if junction_candidates.count() == 0:
        junction_candidates = nearby_junctions(stroke_ref.end_junction)
        junction_ref = stroke_ref.end_junction
        if junction_candidates.count() == 0:
            # set delimited stroke check true
            return matches
    for junction_target in junction_candidates:
        for section_target in junction_target.road_sections:
            stroke_target = section_target.delimited_stroke
            junction_target_other = other_junction(stroke_target, junction_target)
            for line_distance in session.query(func.st_distance(stroke_ref.geom, junction_target_other.geom)):
                if line_distance[0] < tolerance_distance:
                    junction_ref_other = other_junction(stroke_ref, junction_ref)
                    for point_distance in session.query(func.st_distance(junction_ref_other.geom, junction_target_other.geom)):
                        if point_distance[0] < tolerance_distance:
                            match = Match(stroke_ref, stroke_target)
                            matches.append(match)
                            print(f'stroke_ref: {stroke_ref.id}, stroke_target: {stroke_target.id}, junction_target: {junction_target.id}, section_target: {section_target.id}')
    return matches


def nearby_junctions(junction_ref):
    """Finds the junctions in the target database that are within the tolerance distance of junction_ref"""
    junctions = session.query(JunctionTarget).filter(func.st_dwithin(JunctionTarget.geom, junction_ref.geom, tolerance_distance))
    return junctions
