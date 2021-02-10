"""Module structure.py contains all the classes used in for the matching process.
The Base classes are used to map to the PostGIS tables for easy access of all the data."""

import itertools  # standard library

from sqlalchemy.ext.declarative import declarative_base  # 3rd party packages
from sqlalchemy.orm import relationship
from sqlalchemy import Column, ForeignKey, Integer, Float, func
from geoalchemy2 import Geometry

from dso import session, tolerance_area_normalized, tolerance_hausdorff, tolerance_length  # local source
from helpers import length_difference, combine_geom, get_area, get_length


Base = declarative_base()

area_name = 'oost'  # name components of the tables to connect to
table_ref = 'nwb_' + area_name
table_target = 'top10nl_' + area_name
junction_table = '_vertices_pgr'


class RoadSectionRef(Base):
    """Mapped class to the roadsection table of the reference database."""
    __tablename__ = table_ref
    id = Column(Integer, primary_key=True)
    geom = Column(Geometry('LINESTRING'))
    begin_junction_id = Column(Integer, ForeignKey(table_ref + junction_table + '.id'))
    end_junction_id = Column(Integer, ForeignKey(table_ref + junction_table + '.id'))
    delimited_stroke_id = Column(Integer, ForeignKey('delimited_strokes_ref.id'))

    begin_junction = relationship("JunctionRef", foreign_keys=[begin_junction_id])
    end_junction = relationship("JunctionRef", foreign_keys=[end_junction_id])
    delimited_stroke = relationship("DelimitedStrokeRef", foreign_keys=[delimited_stroke_id])


class JunctionRef(Base):
    """Mapped class to the junction table of the reference database."""
    __tablename__ = table_ref + junction_table
    id = Column(Integer, primary_key=True)
    geom = Column('the_geom', Geometry('POINT'))
    road_sections = relationship("RoadSectionRef", primaryjoin="or_(JunctionRef.id == RoadSectionRef.begin_junction_id, "
                                                               "JunctionRef.id == RoadSectionRef.end_junction_id)",
                                 lazy='joined')
    degree = Column('cnt', Integer)
    type_k3 = Column(Integer)
    angle_k3 = Column(Float)


class RoadSectionTarget(Base):
    """Mapped class to the roadsection table of the target database."""
    __tablename__ = table_target
    id = Column(Integer, primary_key=True)
    geom = Column(Geometry('LINESTRING'))
    begin_junction_id = Column(Integer, ForeignKey(table_target + junction_table + '.id'))
    end_junction_id = Column(Integer, ForeignKey(table_target + junction_table + '.id'))
    delimited_stroke_id = Column(Integer, ForeignKey('delimited_strokes_target.id'))

    begin_junction = relationship("JunctionTarget", foreign_keys=[begin_junction_id])
    end_junction = relationship("JunctionTarget", foreign_keys=[end_junction_id])
    delimited_stroke = relationship("DelimitedStrokeTarget", foreign_keys=[delimited_stroke_id])


class JunctionTarget(Base):
    """Mapped class to the junction table of the target database."""
    __tablename__ = table_target + junction_table
    id = Column(Integer, primary_key=True)
    geom = Column('the_geom', Geometry('POINT'))
    road_sections = relationship("RoadSectionTarget", primaryjoin="or_(JunctionTarget.id == RoadSectionTarget.begin_junction_id, "
                                                                  "JunctionTarget.id == RoadSectionTarget.end_junction_id)", lazy='joined')
    degree = Column('cnt', Integer)
    type_k3 = Column(Integer)
    angle_k3 = Column(Float)


class DelimitedStrokeRef(Base):
    """Mapped class to the delimited strokes table of the reference database."""
    __tablename__ = 'delimited_strokes_ref'
    id = Column(Integer, primary_key=True)
    geom = Column(Geometry('LINESTRING'))
    level = Column(Integer)
    begin_junction_id = Column(Integer, ForeignKey(table_ref + junction_table + '.id'))
    end_junction_id = Column(Integer, ForeignKey(table_ref + junction_table + '.id'))
    match_id = Column(Integer)
    length = None

    begin_junction = relationship("JunctionRef", foreign_keys=[begin_junction_id])
    end_junction = relationship("JunctionRef", foreign_keys=[end_junction_id])


class DelimitedStrokeTarget(Base):
    """"Mapped class to the delimited strokes table of the target database."""
    __tablename__ = 'delimited_strokes_target'
    id = Column(Integer, primary_key=True)
    geom = Column(Geometry('LINESTRING'))
    level = Column(Integer)
    begin_junction_id = Column(Integer, ForeignKey(table_target + junction_table + '.id'))
    end_junction_id = Column(Integer, ForeignKey(table_target + junction_table + '.id'))
    match_id = Column(Integer)

    begin_junction = relationship("JunctionTarget", foreign_keys=[begin_junction_id])
    end_junction = relationship("JunctionTarget", foreign_keys=[end_junction_id])


class LinkingTable(Base):
    """Mapped class to table which stores the output of the matching process."""
    __tablename__ = 'linking_table'
    id = Column(Integer, primary_key=True)
    nwb_id = Column(Integer)
    top10nl_id = Column(Integer)
    match_id = Column(Integer)
    similarity_score = Column(Float)


class Match:
    """Local class used to save information related to a match of strokes."""
    id_iter = itertools.count()  # generates incremental ID

    def __init__(self, ref, target):
        """Set properties of the match according to input strokes."""
        self.id = next(self.id_iter)
        self.strokes_ref = ref
        self.strokes_target = target
        self.geom_ref = None
        self.geom_target = None
        self.set_combined_geom()
        self.similarity_score = 0
        if self.geom_ref is not None and self.geom_target is not None:
            try:
                self.similarity_score = self.set_similarity_score()
            except TypeError as e:
                print(e)
                print('Could not calculate score for match', self.id)

    def set_combined_geom(self):
        """Combines the geometries of the strokes in the match, such that geometric properties can be calculated."""
        if len(self.strokes_ref) > 1:
            self.geom_ref = combine_geom(self.strokes_ref)
        else:
            self.geom_ref = self.strokes_ref[0].geom
        if len(self.strokes_target) > 1:
            self.geom_target = combine_geom(self.strokes_target)
        else:
            self.geom_target = self.strokes_target[0].geom

    def set_stroke_match_id(self):
        for stroke in self.strokes_ref:
            stroke.match_id = self.id
        for stroke in self.strokes_target:
            stroke.match_id = self.id

    def set_area_difference(self):
        """Calculates the difference in areas between the reference and target strokes."""
        return abs(get_area(self.geom_ref) - get_area(self.geom_target))

    def set_similarity_score(self):
        """Calculates the similarity score of the match. It is a weighted sum of scaled attributes, which are
        difference in length, difference in distance (hausdorff distance) and difference in area."""
        length_diff = length_difference(self.strokes_ref, self.strokes_target)
        hausdorff = session.query(func.st_hausdorffdistance(self.geom_ref, self.geom_target))[0][0]
        area_diff = self.set_area_difference()
        area_diff_normalized = area_diff/get_length(self.strokes_ref)

        weights = [0.5, 0.35, 0.15]  # sum equal to 1
        metrics = [length_diff/tolerance_length, hausdorff/tolerance_hausdorff, area_diff_normalized/tolerance_area_normalized]
        score = 0

        for index, metric in enumerate(metrics):
            score += weights[index] * (1 - metric)

        return score



