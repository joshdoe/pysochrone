pysochrone
==========
pysochrone is a simple Python script for creating isochrone maps. Isochrones are curves of equal travel time from a certain point of origin. Really this can be used for any type of isoline (aka contour) map. For more information:
* http://en.wikipedia.org/wiki/Contour_line
* http://wiki.openstreetmap.org/wiki/Isochrone

Code is heavily borrowed from the [Quantum GIS](http://www.qgis.org/) Contour plugin.

Requirements
------------
* [Python](http://www.python.org/)
* [numpy](http://numpy.scipy.org/)
* [matplotlib](http://matplotlib.sourceforge.net/)
* [Shapely](http://pypi.python.org/pypi/Shapely)
* [OGR](http://www.gdal.org/ogr/)
* [pgRouting](http://www.pgrouting.org/) (optional)

Use
---
The contour module has a class Contours which creates contour lines or filled contour polygons from an OGR compatible datasource. A cgi script, isochrone.py, uses this class to provide a RESTful service 

Todo
----
* Include simple Dijkstra algorithm to compute shortest path tree to remove
  the need for a PostGIS/pgRouting database
* Allow download of OSM data on demand (for small areas)
* Provide more options, such as changing grid size
* Provide more methods, such as alpha shapes or buffered roads
