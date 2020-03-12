from structure import DelimitedStrokeTarget
from sqlalchemy.sql import func
from math import pi
from dso import deviation_angle


# calculates the angle of the line segment of road_section at junction
def angle_at_junction(road_section, junction, session):
    assert(road_section in junction.road_sections)
    if road_section.begin_junction == junction:
        angle = session.query(func.ST_Azimuth(junction.geom, road_section.geom.ST_PointN(2)))[0][0]
    else:
        angle = session.query(func.ST_Azimuth(junction.geom, road_section.geom.ST_PointN(-2)))[0][0]
    return angle


# calculates the difference between two angles in radians, output in range [0, 2pi]
def angle_difference(angle_a, angle_b):
    return pi - abs(abs(angle_a - angle_b) - pi)


# determines the classification of each junction with degree 3 or 4
def classify_junction(junction, session):
    angles = []
    for road_section in junction.road_sections:
        angles.append(angle_at_junction(road_section, junction, session))
    angles.sort()
    angles.append(angles[0])
    angle_differences = []
    for i, angle in enumerate(angles[:-1]):
        angle_differences.append(angle_difference(angle, angles[i+1]))
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


def classify_junctions(junctions, session):
    for junction in junctions:
        if junction.degree == 3 or junction.degree == 4:
            classify_junction(junction, session)


# constructs a delimited stroke from the road_section, with junction as its starting point
# if a delimited_stroke is given as input, the next road_section is added to this delimited_stroke
def construct_stroke(road_section, junction, session, delimited_stroke=None):
    if delimited_stroke is None:
        delimited_stroke = DelimitedStrokeTarget(geom=road_section.geom, begin_junction_id=junction.id, level=1)
        session.add(delimited_stroke)
        session.flush()
        # print(f'stroke created with id: {delimited_stroke.id}, starting at {junction.id}')

    road_section.delimited_stroke = delimited_stroke
    if junction == road_section.begin_junction:
        next_junction = road_section.end_junction
    else:
        next_junction = road_section.begin_junction

    # print(f'junction: {junction.id}, next junction: {next_junction.id}')
    if next_junction.degree == 2 or next_junction.degree == 3:
        current_angle = angle_at_junction(road_section, next_junction, session)
        for next_road_section in next_junction.road_sections:
            if next_road_section != road_section:
                angle_between_sections = angle_difference(current_angle, angle_at_junction(next_road_section, next_junction, session))
                if pi - deviation_angle < angle_between_sections < pi + deviation_angle:
                    print(f'continuity at junction: {next_junction.id}, from road {road_section.id} to {next_road_section.id}, stroke id = {delimited_stroke.id}')
                    if func.st_startpoint(delimited_stroke.geom) == func.st_startpoint(delimited_stroke.geom):
                        print("help")
                        break
                    delimited_stroke.geom = session.query(func.st_linemerge(func.st_collect(delimited_stroke.geom, next_road_section.geom)))

                    return construct_stroke(next_road_section, next_junction, session, delimited_stroke)

    delimited_stroke.end_junction_id = next_junction.id
    road_section.delimited_stroke = delimited_stroke
    return delimited_stroke


# starts the construction of a stroke from every node that is an effective terminating node
def construct_strokes(junctions, session):
    for junction in junctions:
        # print(f'selected junction: {junction_ref.id} with degree {junction_ref.degree}')
        if junction.degree == 1 or junction.degree > 2:
            if junction.type_k3 == 2:
                for road_section in junction.road_sections:
                    if junction.angle_k3 == angle_at_junction(road_section, junction, session):
                        construct_stroke(road_section, junction, session)
                        break
            else:
                for road_section in junction.road_sections:
                    if road_section.delimited_stroke is None:
                        construct_stroke(road_section, junction, session)
                    # print(f'id = {road_section_ref.id}, begin at: {road_section_ref.begin_junction.id}, end at: {road_section_ref.end_junction.id}')
        # print(' ')
