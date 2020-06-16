from sqlalchemy.sql import func
from math import pi
from dso import deviation_angle, session, delimited_strokes, tolerance_distance
from sqlalchemy.dialects.postgresql import array
from sqlalchemy.types import ARRAY


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


def classify_junction(junction):
    """Determines the structure classification of a junction with degree 3."""
    angles = []
    for road_section in junction.road_sections:
        angles.append(angle_at_junction(road_section, junction))
    angles.sort()
    angles.append(angles[0])
    angle_differences = []
    for i, angle in enumerate(angles[:-1]):
        angle_differences.append(clockwise_angle_difference(angles[i+1], angle))
    alpha = max(angle_differences)

    if junction.degree == 3:
        index_perpendicular = angle_differences.index(alpha) - 1
        if index_perpendicular < 0:
            index_perpendicular = 2
        if alpha < pi - deviation_angle:
            junction.type_k3 = 0
        elif alpha > pi + deviation_angle:
            junction.type_k3 = 1
            junction.angle_k3 = angles[index_perpendicular]
        else:
            junction.type_k3 = 2
            junction.angle_k3 = angles[index_perpendicular]


def classify_junctions(junctions):
    """Classifies each junction from the input set of junctions."""
    for junction in junctions:
        if junction.degree == 3 or junction.degree == 4:
            classify_junction(junction)


def construct_stroke(road_section, junction, delimited_stroke, level=1):
    """Constructs a delimited stroke from the road_section, with junction as its starting point.
    If a delimited_stroke is given as input, the next road_section is added to this delimited_stroke."""
    session.flush()
    road_section.delimited_stroke = delimited_stroke
    if junction == road_section.begin_junction:
        next_junction = road_section.end_junction
    else:
        next_junction = road_section.begin_junction
    # print(f'junction: {junction.id}, next junction: {next_junction.id}')
    if next_junction.id == delimited_stroke.begin_junction_id:
        delimited_stroke.end_junction_id = next_junction.id
        return delimited_stroke

    if next_junction.degree == 2:
        for next_road_section in next_junction.road_sections:
            if next_road_section != road_section:
                delimited_stroke.geom = session.query(func.st_linemerge(func.st_collect(delimited_stroke.geom, next_road_section.geom)))
                delimited_strokes[delimited_stroke.id].append(next_road_section)
                return construct_stroke(next_road_section, next_junction, delimited_stroke, level)

    if level == 1:
        if next_junction.type_k3 == 2:
            current_angle = angle_at_junction(road_section, next_junction)
            if current_angle != next_junction.angle_k3:
                # select the next stroke which has good continuity
                for next_road_section in next_junction.road_sections:
                    if next_road_section != road_section and next_road_section.delimited_stroke is None:
                        next_angle = angle_at_junction(next_road_section, next_junction)
                        if next_angle != next_junction.angle_k3:
                            # print(f'continuity at junction: {next_junction.id}, from road {road_section.id} to {next_road_section.id}, stroke id = {delimited_stroke.id}')
                            if next_road_section.begin_junction == next_road_section.end_junction:
                                # print("looping section found with id", next_road_section.id, " at junction ", next_junction.id)
                                delimited_stroke.end_junction_id = next_junction.id
                                return delimited_stroke
                            delimited_stroke.geom = session.query(func.st_linemerge(func.st_collect(
                                delimited_stroke.geom, next_road_section.geom)))
                            delimited_strokes[delimited_stroke.id].append(next_road_section)
                            return construct_stroke(next_road_section, next_junction, delimited_stroke, level)

    delimited_stroke.end_junction_id = next_junction.id
    return delimited_stroke


def construct_strokes(junctions, delimited_stroke_class):
    """Starts the construction of a stroke from every node that is an effective terminating node."""
    for junction in junctions:
        # print(f'selected junction: {junction.id} with degree {junction.degree}')
        if junction.degree == 1 or junction.degree > 2:
            if junction.type_k3 == 2:
                for road_section in junction.road_sections:
                    if junction.angle_k3 == angle_at_junction(road_section, junction) and road_section.delimited_stroke is None:
                        delimited_stroke = construct_stroke_from_section(road_section, delimited_stroke_class)
                        delimited_stroke.begin_junction_id = junction.id
                        construct_stroke(road_section, junction, delimited_stroke)
                        break
            else:
                for road_section in junction.road_sections:
                    if road_section.delimited_stroke is None:
                        delimited_stroke = construct_stroke_from_section(road_section, delimited_stroke_class)
                        delimited_stroke.begin_junction_id = junction.id
                        construct_stroke(road_section, junction, delimited_stroke)
                    # print(f'id = {road_section_ref.id}, begin at: {road_section_ref.begin_junction.id}, end at: {road_section_ref.end_junction.id}')
        # print(' ')


def reset_delimited_strokes(road_sections):
    """Resets each delimited stroke of the input road sections"""
    for each in road_sections:
        each.delimited_stroke = None


def reset_matches(strokes):
    """Resets the match of each delimited stroke from the input strokes"""
    for each in strokes:
        each.match_id = None


def construct_stroke_from_section(road_section, delimited_stroke_class, level=1, begin_junction=None):
    """Constructs a stroke from a single section"""
    delimited_stroke = delimited_stroke_class(geom=road_section.geom, begin_junction_id=road_section.begin_junction_id,
                                              end_junction_id=road_section.end_junction_id, level=level)
    if begin_junction:
        delimited_stroke.begin_junction_id = begin_junction.id
        if begin_junction == road_section.end_junction:
            delimited_stroke.end_junction_id = road_section.begin_junction_id
    session.add(delimited_stroke)
    session.flush()
    road_section.delimited_stroke = delimited_stroke
    delimited_strokes[delimited_stroke.id] = [road_section]
    return delimited_stroke


def get_length(list_of_strokes):
    length = 0
    for stroke in list_of_strokes:
        length += session.query(func.st_length(stroke.geom)).first()[0]
    return length


def length_difference(stroke_a, stroke_b):
    return abs(get_length(stroke_a) - get_length(stroke_b))/tolerance_distance


def combine_geom(list_of_strokes):
    '''Expects a list of strokes, returns a combined geometry of the strokes in the list'''
    geoms = [stroke.geom for stroke in list_of_strokes]
    return session.query(func.st_astext(func.st_linemerge(func.st_collect(array(geoms)))))[0][0]


def get_area(geom):
    numpoints = session.query(func.st_numpoints(geom))[0][0]
    if numpoints > 2:
        return session.query(func.st_area(func.st_makepolygon(func.st_addpoint(geom, func.st_startpoint(geom)))))[0][0]
    else:
        return 0


