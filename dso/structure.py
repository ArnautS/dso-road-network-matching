from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import Column, ForeignKey, Integer, Float
from geoalchemy2 import Geometry

Base = declarative_base()
table_ref = 'nwb_nunspeet'


# mapped class to the roadsection table of the reference database
class RoadSectionRef(Base):
    __tablename__ = table_ref
    id = Column(Integer, primary_key=True)
    geom = Column(Geometry('LINESTRING'))
    begin_junction_id = Column(Integer, ForeignKey(table_ref + '_vertices_pgr.id'))
    end_junction_id = Column(Integer, ForeignKey(table_ref + '_vertices_pgr.id'))
    delimited_stroke_id = Column(Integer, ForeignKey('delimitedstrokes.id'))

    begin_junction = relationship("JunctionRef", foreign_keys=[begin_junction_id])
    end_junction = relationship("JunctionRef", foreign_keys=[end_junction_id])
    delimited_stroke = relationship("DelimitedStroke", foreign_keys=[delimited_stroke_id])

    # start_angle = func.st_azimuth(begin_junction.geom, geom.st_pointn(2))


# mapped class to the junction table of the reference database
class JunctionRef(Base):
    __tablename__ = table_ref + '_vertices_pgr'
    id = Column(Integer, primary_key=True)
    geom = Column('the_geom', Geometry('POINT'))
    road_sections = relationship("RoadSectionRef", primaryjoin="or_(JunctionRef.id == RoadSectionRef.begin_junction_id, "
                                                               "JunctionRef.id == RoadSectionRef.end_junction_id)")
    degree = Column('cnt', Integer)
    type_k3 = Column(Integer)
    angle_k3 = Column(Float)


# mapped class to the roadsection table of the target database
class RoadSectionTarget(Base):
    __tablename__ = 'top10nl'
    id = Column('ogc_fid', Integer, primary_key=True)
    geom = Column(Geometry('LINESTRING'))
    begin_junction_id = Column('source', Integer, ForeignKey('top10nl_vertices_pgr.id'))
    end_junction_id = Column('target', Integer, ForeignKey('top10nl_vertices_pgr.id'))

    begin_junction = relationship("JunctionTarget", foreign_keys=[begin_junction_id])
    end_junction = relationship("JunctionTarget", foreign_keys=[end_junction_id])


# mapped class to the junction table of the target database
class JunctionTarget(Base):
    __tablename__ = 'top10nl_vertices_pgr'
    id = Column(Integer, primary_key=True)
    road_sections = relationship("RoadSectionTarget", primaryjoin="or_(JunctionTarget.id == RoadSectionTarget.begin_junction_id, "
                                                                  "JunctionTarget.id == RoadSectionTarget.end_junction_id)")
    degree = Column('cnt', Integer)


# mapped class to the delimited strokes table
class DelimitedStroke(Base):
    __tablename__ = 'delimitedstrokes'
    id = Column(Integer, primary_key=True)
    geom = Column(Geometry('LINESTRING'))
    level = Column(Integer)
    begin_junction_id = Column(Integer)
    end_junction_id = Column(Integer)




