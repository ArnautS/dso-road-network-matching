"""Module helpers.py contains several functions to calculate geometric properties of lines and planes."""

from math import pi  # standard library

from sqlalchemy.sql import func  # 3rd party packages
from sqlalchemy.dialects.postgresql import array

from dso import session, tolerance_distance  # local source


def angle_at_junction(road_section, junction):
    """Calculates the angle of the line segment of road_section at junction."""
    assert (road_section.begin_junction == junction or road_section.end_junction == junction)
    first_point_section = session.query(func.st_startpoint(road_section.geom))[0][0]
    if session.query(func.st_equals(first_point_section, junction.geom))[0][0]:
        angle = session.query(func.ST_Azimuth(junction.geom, road_section.geom.ST_PointN(2)))[0][0]
    else:
        angle = session.query(func.ST_Azimuth(junction.geom, road_section.geom.ST_PointN(-2)))[0][0]
    assert angle is not None
    return angle


def angle_difference(angle_a, angle_b):
    """Calculates the difference between two angles in radians, output in range [0, 2pi]."""
    return pi - abs(abs(angle_a - angle_b) - pi)


def clockwise_angle_difference(angle_a, angle_b):
    """Calculates the clockwise difference between two angles in radians, output in range [0, 2pi]."""
    return (angle_a - angle_b) % (2 * pi)


def get_length(list_of_strokes):
    """Calculates the length (in m) of the input array of strokes."""
    length = 0
    for stroke in list_of_strokes:
        length += session.query(func.st_length(stroke.geom)).first()[0]
    return length


def length_difference(stroke_a, stroke_b):
    """Calculates the difference in length between two strokes, normalized with the tolerance distance."""
    return abs(get_length(stroke_a) - get_length(stroke_b))/tolerance_distance


def combine_geom(list_of_strokes):
    """Expects a list of strokes, returns a combined geometry of the strokes in the list."""
    geoms = [stroke.geom for stroke in list_of_strokes]
    return session.query(func.st_astext(func.st_linemerge(func.st_collect(array(geoms)))))[0][0]


def get_area(geom):
    """Calculates the area (in m2) of a plane."""
    numpoints = session.query(func.st_numpoints(geom))[0][0]
    if numpoints > 2:
        return session.query(func.st_area(func.st_makepolygon(func.st_addpoint(geom, func.st_startpoint(geom)))))[0][0]
    else:
        return 0


