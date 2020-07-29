"""Module construction.py handles the classification of junctions and construction of delimited strokes."""

from math import pi  # standard library

from sqlalchemy import func  # 3rd party packages

from dso import deviation_angle, session, delimited_strokes_ref, delimited_strokes_target  # local source
from helpers import angle_at_junction, clockwise_angle_difference
from structure import DelimitedStrokeRef


def classify_junction(junction):
    """Determines the type of a junction with degree 3. Types are numbered 0 to 2.
    0 = Y-junction, 1 = W-junction, 2 = T-junction. Junctions of type 1 and 2 have an angle property, that is the angle
    of the middle road section referenced from the north."""
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
    """Constructs a delimited stroke from road_section, with junction as its starting point.
    If a delimited_stroke is given as input, the next road_section is added to this delimited_stroke."""
    session.flush()
    # used delimited stroke dictionary based on type of the input stroke
    if type(delimited_stroke) == DelimitedStrokeRef:
        delimited_strokes = delimited_strokes_ref
    else:
        delimited_strokes = delimited_strokes_target
    road_section.delimited_stroke = delimited_stroke

    # determine which from which junction the next road section should be added
    if junction == road_section.begin_junction:
        next_junction = road_section.end_junction
    else:
        next_junction = road_section.begin_junction

    # if the next_junction is the same as the begin_junction of the delimited stroke, it is a loop and can be returned
    if next_junction.id == delimited_stroke.begin_junction_id:
        delimited_stroke.end_junction_id = next_junction.id
        return delimited_stroke

    # if the degree of the next junction is 2, the road section not equal to the input is added to the delimited stroke
    if next_junction.degree == 2:
        for next_road_section in next_junction.road_sections:
            if next_road_section != road_section:
                delimited_stroke.geom = session.query(func.st_linemerge(func.st_collect(delimited_stroke.geom, next_road_section.geom)))
                delimited_strokes[delimited_stroke.id].append(next_road_section)
                return construct_stroke(next_road_section, next_junction, delimited_stroke, level)

    # only strokes at level 1, are extended with sections that have good continuity
    if level == 1:
        if next_junction.type_k3 == 2:
            current_angle = angle_at_junction(road_section, next_junction)
            if current_angle != next_junction.angle_k3:

                # select the next section that has good continuity
                for next_road_section in next_junction.road_sections:
                    if next_road_section != road_section and next_road_section.delimited_stroke is None:
                        next_angle = angle_at_junction(next_road_section, next_junction)
                        if next_angle != next_junction.angle_k3:
                            # if the next section is a loop, it is not added to the delimited stroke
                            if next_road_section.begin_junction == next_road_section.end_junction:
                                delimited_stroke.end_junction_id = next_junction.id
                                return delimited_stroke

                            # merge the selected section with the existing delimited stroke to extend it
                            delimited_stroke.geom = session.query(func.st_linemerge(func.st_collect(
                                delimited_stroke.geom, next_road_section.geom)))
                            delimited_strokes[delimited_stroke.id].append(next_road_section)
                            return construct_stroke(next_road_section, next_junction, delimited_stroke, level)

    # if the stroke is not extended, the end junction is set
    delimited_stroke.end_junction_id = next_junction.id
    return delimited_stroke


def construct_strokes(junctions, delimited_stroke_class):
    """Starts the construction of a stroke from every node that is an effective terminating node."""
    for junction in junctions:
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


def construct_stroke_from_section(road_section, delimited_stroke_class, level=1, begin_junction=None):
    """Constructs a stroke from a single road section."""
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
    """Resets each delimited stroke of the input road sections."""
    for each in road_sections:
        each.delimited_stroke = None

