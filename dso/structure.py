from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import Column, ForeignKey, Integer, Float
from geoalchemy2 import Geometry

Base = declarative_base()
area_name = 'nunspeet'
table_ref = 'nwb_' + area_name
table_target = 'top10nl_' + area_name
junction_table = '_vertices_pgr'


# mapped class to the roadsection table of the reference database
class RoadSectionRef(Base):
    __tablename__ = table_ref
    id = Column(Integer, primary_key=True)
    geom = Column(Geometry('LINESTRING'))
    begin_junction_id = Column(Integer, ForeignKey(table_ref + junction_table + '.id'))
    end_junction_id = Column(Integer, ForeignKey(table_ref + junction_table + '.id'))
    delimited_stroke_id = Column(Integer, ForeignKey('delimited_strokes_ref.id'))

    begin_junction = relationship("JunctionRef", foreign_keys=[begin_junction_id])
    end_junction = relationship("JunctionRef", foreign_keys=[end_junction_id])
    delimited_stroke = relationship("DelimitedStrokeRef", foreign_keys=[delimited_stroke_id])

    # start_angle = func.st_azimuth(begin_junction.geom, geom.st_pointn(2))


# mapped class to the junction table of the reference database
class JunctionRef(Base):
    __tablename__ = table_ref + junction_table
    id = Column(Integer, primary_key=True)
    geom = Column('the_geom', Geometry('POINT'))
    road_sections = relationship("RoadSectionRef", primaryjoin="or_(JunctionRef.id == RoadSectionRef.begin_junction_id, "
                                                               "JunctionRef.id == RoadSectionRef.end_junction_id)")
    degree = Column('cnt', Integer)
    type_k3 = Column(Integer)
    angle_k3 = Column(Float)


# mapped class to the roadsection table of the target database
class RoadSectionTarget(Base):
    __tablename__ = table_target
    id = Column(Integer, primary_key=True)
    geom = Column(Geometry('LINESTRING'))
    begin_junction_id = Column(Integer, ForeignKey(table_target + junction_table + '.id'))
    end_junction_id = Column(Integer, ForeignKey(table_target + junction_table + '.id'))
    delimited_stroke_id = Column(Integer, ForeignKey('delimited_strokes_target.id'))

    begin_junction = relationship("JunctionTarget", foreign_keys=[begin_junction_id])
    end_junction = relationship("JunctionTarget", foreign_keys=[end_junction_id])
    delimited_stroke = relationship("DelimitedStrokeTarget", foreign_keys=[delimited_stroke_id])


# mapped class to the junction table of the target database
class JunctionTarget(Base):
    __tablename__ = table_target + junction_table
    id = Column(Integer, primary_key=True)
    geom = Column('the_geom', Geometry('POINT'))
    road_sections = relationship("RoadSectionTarget", primaryjoin="or_(JunctionTarget.id == RoadSectionTarget.begin_junction_id, "
                                                                  "JunctionTarget.id == RoadSectionTarget.end_junction_id)")
    degree = Column('cnt', Integer)
    type_k3 = Column(Integer)
    angle_k3 = Column(Float)


# mapped class to the delimited strokes table of the reference database
class DelimitedStrokeRef(Base):
    __tablename__ = 'delimited_strokes_ref'
    id = Column(Integer, primary_key=True)
    geom = Column(Geometry('LINESTRING'))
    level = Column(Integer)
    begin_junction_id = Column(Integer)
    end_junction_id = Column(Integer)


# mapped class to the delimited strokes table of the target database
class DelimitedStrokeTarget(Base):
    __tablename__ = 'delimited_strokes_target'
    id = Column(Integer, primary_key=True)
    geom = Column(Geometry('LINESTRING'))
    level = Column(Integer)
    begin_junction_id = Column(Integer)
    end_junction_id = Column(Integer)




