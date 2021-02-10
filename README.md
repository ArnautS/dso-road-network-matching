# DSO road network matching
Implementation of the Delimited-Strokes Optimization (DSO) method for road network matching.


## Setup
This setup guide is written for the matching of NWB to TOP10NL. If other databases are used, check that the correct names are used for the tables and columns in the `sql scripts` files.

1. Install PgAdmin4 ([Download link](https://www.pgadmin.org/download/))
2. Install PostGIS ([Download link](http://postgis.net/install/) - [Install guide](https://postgis.net/workshops/postgis-intro/installation.html))
3. [Setup a spatial database in PgAdmin](https://postgis.net/workshops/postgis-intro/creating_db.html)
4. [Import the shapefiles of the two databases](https://postgis.net/workshops/postgis-intro/loading_data.html)
    - Check 'Generate simple geometries instead of MULTI geometries' under Import Options
5. Rename the tables to `nwb_area` and `top10nl_area`
6. Open the Query Tool in PgAdmin, copy and run the contents of the files in `sql scripts` seperately
7. Check the database connection in `__init__.py`
8. Run `core.py` to start the matching process
9. The output is recorded in `linking_table` in the PostGIS database
