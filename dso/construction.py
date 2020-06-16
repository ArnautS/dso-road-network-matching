from math import pi
from sqlalchemy import func
from dso import deviation_angle, session, delimited_strokes_ref, delimited_strokes_target
from helpers import angle_at_junction, clockwise_angle_difference
from structure import DelimitedStrokeRef, DelimitedStrokeTarget


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
    if type(delimited_stroke) == DelimitedStrokeRef:
        delimited_strokes = delimited_strokes_ref
    else:
        delimited_strokes = delimited_strokes_target

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

    if delimited_stroke_class == DelimitedStrokeRef:
        delimited_strokes_ref[delimited_stroke.id] = [road_section]
    else:
        delimited_strokes_target[delimited_stroke.id] = [road_section]
    return delimited_stroke


def reset_delimited_strokes(road_sections):
    """Resets each delimited stroke of the input road sections"""
    for each in road_sections:
        each.delimited_stroke = None

