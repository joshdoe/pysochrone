#!/usr/bin/python

import os
import sys
import cgi
import cgitb
cgitb.enable()

# set HOME env var to a directory the httpd server can write to
os.environ['HOME'] = '/tmp/'

from contour import Contours,ContourError

form = cgi.FieldStorage()
if "startpoint" not in form:
    print "Content-Type: text/plain\n"
    print "Error, no startpoint specified"

pt = form["startpoint"].value
sql = """SELECT *
          FROM vertices_tmp
          JOIN
          (SELECT * FROM driving_distance('
             SELECT gid AS id,
                 source::int4,
                 target::int4,
                 length::float8 AS cost
             FROM ways',
             (SELECT id FROM vertices_tmp ORDER BY distance(the_geom,
             ST_GeomFromText('POINT("""+pt+""")',4326)) LIMIT 1),
             3,
             false,
             false)) AS route
          ON
          vertices_tmp.id = route.vertex_id;""";

#c = Contours(dataSrcName='points.shp', fieldName='cost')
c = Contours(dataSrcName='PG: host=localhost dbname=virginia '
                         'user=postgres password=postgres', fieldName='cost', sql=sql)
c.setLevels(0.0, 1.6, 5)

try:
    tempname = '/tmp/walk.json'
    if os.path.exists(tempname):
        os.remove(tempname)
    c.createFilledContourLayer(driverName="GeoJSON", fileName=tempname)
    json = open(tempname, 'r')
    print "Content-Type: application/json\n"
    print json.read()
except ContourError as detail:
    print "Content-Type: text/plain\n",detail
