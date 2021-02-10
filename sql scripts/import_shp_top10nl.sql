SELECT UpdateGeometrySRID('public', 'top10nl_area', 'geom', 28992) ;

UPDATE top10nl_area
   SET geom = ST_SnapToGrid(geom, 0.001);

-- create topology/vertice table
ALTER TABLE top10nl_area ADD COLUMN "source" bigint;
ALTER TABLE top10nl_area ADD COLUMN "target" bigint;
SELECT pgr_createTopology('top10nl_area', 0.00001, 'geom', 'ogc_fid'); 
SELECT pgr_analyzeGraph('top10nl_area',0.001,'geom','ogc_fid');

ALTER TABLE top10nl_area
RENAME TO top10nl_area_temp;

-- select the required columns for the matching process
SELECT ogc_fid AS id, geom, source AS begin_junction_id, target AS end_junction_id 
INTO top10nl_area
FROM top10nl_area_temp;

DROP TABLE top10nl_area_temp;

-- add new columns to safe data during matching process
ALTER TABLE top10nl_area
ADD COLUMN delimited_stroke_id int,
ADD PRIMARY KEY (id);
  
ALTER TABLE top10nl_area_vertices_pgr
ADD COLUMN type_k3 int,
ADD COLUMN angle_k3 float;

-- create new spatial index
CREATE INDEX top10nl_area_geom_idx
    ON public.top10nl_area USING gist
    (geom)
    TABLESPACE pg_default;