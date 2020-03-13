from dso import session, tolerance_distance
from structure import JunctionTarget
from sqlalchemy import func


def find_matching_candidates(strokes_ref, strokes_target):
    for delimited_stroke in strokes_ref:
        nearby_junctions(delimited_stroke.begin_junction)


def nearby_junctions(junction_ref):
    """Finds the junctions in the target database that are within the tolerance distance of junction_ref"""
    junctions = session.query(JunctionTarget).filter(func.st_dwithin(JunctionTarget.geom, junction_ref.geom, tolerance_distance))
    return junctions
