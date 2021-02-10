SELECT UpdateGeometrySRID('public', 'nwb_area', 'geom', 28992) ;

UPDATE nwb_area
   SET geom = ST_SnapToGrid(geom, 0.001);

-- create topology/vertice table
ALTER TABLE nwb_area ADD COLUMN "source" bigint;
ALTER TABLE nwb_area ADD COLUMN "target" bigint;
SELECT pgr_createTopology('nwb_area', 0.00001, 'geom', 'wvk_id'); 
SELECT pgr_analyzeGraph('nwb_area',0.001,'geom','wvk_id'); 

ALTER TABLE nwb_area
RENAME TO nwb_area_temp;

-- select the required columns for the matching process
SELECT wvk_id AS id, geom, source AS begin_junction_id, target AS end_junction_id 
INTO nwb_area
FROM nwb_area_temp;

DROP TABLE nwb_area_temp;

-- add new columns to safe data during matching process
ALTER TABLE nwb_area
ADD COLUMN delimited_stroke_id int,
ADD PRIMARY KEY (id);
  
ALTER TABLE nwb_area_vertices_pgr
ADD COLUMN type_k3 int,
ADD COLUMN angle_k3 float;

-- create new spatial index
CREATE INDEX nwb_area_geom_idx
    ON public.nwb_area USING gist
    (geom)
    TABLESPACE pg_default;