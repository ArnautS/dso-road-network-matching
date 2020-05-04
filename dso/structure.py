from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import Column, ForeignKey, Integer, Float
from geoalchemy2 import Geometry
from dso import match_id
import itertools

Base = declarative_base()
area_name = 'nunspeet'
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


class DelimitedStroke:
    id_iter = itertools.count()

    def __init__(self, level):
        self.id = next(self.id_iter)
        self.sections = []
        self.geom = None
        self.level = level
        self.begin_junction = None
        self.end_junction = None
        self.matches = []


class Match:
    id_iter = itertools.count()

    def __init__(self, ref, target):
        self.id = next(self.id_iter)
        self.strokes_ref = ref
        self.strokes_target = target
        self.similarity_score = 0
        self.set_stroke_match_id()

    def set_stroke_match_id(self):
        for stroke in self.strokes_ref:
            stroke.match_id = self.id
        for stroke in self.strokes_target:
            stroke.match_id = self.id
