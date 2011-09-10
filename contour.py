#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#       contour.py
#
#       Copyright 2009 Lionel Roubeyrie <lionel.roubeyrie@gmail.com>
#       Copyright 2011 Josh Doe <josh@joshdoe.com>
#
#       This program is free software; you can redistribute it and/or modify
#       it under the terms of the GNU General Public License as published by
#       the Free Software Foundation; either version 2 of the License, or
#       (at your option) any later version.
#
#       This program is distributed in the hope that it will be useful,
#       but WITHOUT ANY WARRANTY; without even the implied warranty of
#       MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#       GNU General Public License for more details.
#
#       You should have received a copy of the GNU General Public License
#       along with this program; if not, write to the Free Software
#       Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#       MA 02110-1301, USA.

#  Modified by Chris Crook <ccrook@linz.govt.nz> to contour irregular data


import sys
import os.path
import string
import math
import inspect

import numpy as np
import matplotlib
matplotlib.use("Agg")  # use non-graphical backend
import matplotlib.pyplot as plt
from matplotlib.mlab import griddata
from shapely.geometry import MultiLineString, MultiPolygon
import shapely
import ogr


# global constants
EPSILON = 1.e-27


class ContourError(Exception):
    """Used for all exceptions created by this module."""
    def __init__(self, message):
        self._message = message

    def __str__(self):
        return self._message


class Contours():
    """This class allows the creation of contour lines and/or filled contour
    polygons from irregular point data
    """
    def __init__(self):
        self._data = None
        self._gridData = None
        self._levels = None

    def getLevels(self):
        return self._levels

    def setLevels(self, start, stop, num):
        self._levels = np.linspace(float(start), float(stop), num)

    # generate grid and interpolate
    def computeGrid(self):
        x, y, z = self._data

        self.gridSpacing = math.sqrt((max(x) - min(x)) *
                                     (max(y) - min(y)) / len(x)) / 2.0
        gridSpacing = self.gridSpacing

        if gridSpacing <= 0.0:
            raise ContourError("Grid spacing must be greater than 0")

        # make grid
        x0 = math.floor(min(x) / gridSpacing) * gridSpacing
        nx = int(math.floor((max(x) - x0) / gridSpacing)) + 1
        gx = np.linspace(x0, x0 + gridSpacing * nx, nx)

        y0 = math.floor(min(y) / gridSpacing) * gridSpacing
        ny = int(math.floor((max(y) - y0) / gridSpacing)) + 1
        gy = np.linspace(y0, y0 + gridSpacing * ny, ny)

        try:
            # interpolate values on grid
            gz = griddata(x, y, z, gx, gy)
        except:
            raise ContourError("Unable to generate a grid for this data set")

        self._gridData = (gx, gy, gz)

    def getDataFromOGR(self, dataSrcName, fieldName, layerName=None, sql=None):
        self._gridData = None
        self._data = None

        datasrc = ogr.Open(dataSrcName)
        if datasrc == None:
            raise ContourError("Failed to open data source '%s'" % dataSrcName)

        if layerName:
            layer = datasrc.GetLayerByName(layerName)
        elif sql:
            layer = datasrc.ExecuteSQL(sql)
        else:
            layer = datasrc.GetLayer(0)
        if layer is None:
            raise ContourError("Failed to read layer")

        x = list()
        y = list()
        z = list()
        # read points
        fieldIndex = None
        while 1:
            feat = layer.GetNextFeature()
            if not feat:
                break

            if fieldIndex is None and fieldName is not None:
                fieldIndex = feat.GetFieldIndex(fieldName)

            inGeom = shapely.wkb.loads(feat.GetGeometryRef().ExportToWkb())
            x.append(inGeom.x)
            y.append(inGeom.y)
            if fieldIndex:
                z.append(feat.GetFieldAsDouble(fieldIndex))
            else:
                z.append(inGeom.z)

        # convert to numpy arrays
        x = np.array(x)
        y = np.array(y)
        z = np.array(z)
        self._data = [x, y, z]
        return x, y, z

    def computeContours(self):
        gx, gy, gz = self._gridData
        levels = self.getLevels()
        # cs = plt.tricontour(x, y, z, levels, extend=extend)
        CS = plt.contour(gx, gy, gz, levels, extend='neither')
        lines = list()
        for i, line in enumerate(CS.collections):
            lines.append([i, levels[i],
                          [path.vertices for path in line.get_paths()]])
        self._lines = lines

    def computeFilledContours(self):
        gx, gy, gz = self._gridData
        levels = self.getLevels()
        #cs = plt.tricontourf(x, y, z, levels, extend=extend)
        CS = plt.contourf(gx, gy, gz, levels, extend='neither')
        polygons = list()
        for i, polygon in enumerate(CS.collections):
            mpoly = []
            for path in polygon.get_paths():
                path.should_simplify = False
                poly = path.to_polygons()
                exterior = []
                holes = []
                if len(poly) > 0:
                    exterior = poly[0]  # and interiors (holes) are in poly[1:]
                    # Crazy correction of one vertice polygon,
                    #  mpl doesn't care about it
                    if len(exterior) == 1:
                        p0 = exterior[0]
                        exterior = np.vstack(exterior, self.epsi_point(p0),
                                             self.epsi_point(p0))
                    if len(poly) > 1:  # There's some holes
                        for h in poly[1:]:
                            if len(h) > 2:
                                holes.append(h)

                mpoly.append([exterior, holes])
            polygons.append([i, levels[i], levels[i + 1], mpoly])
        self._polygons = polygons

    def epsi_point(self, point):
        x = point[0] + EPSILON * np.random.random()
        y = point[1] + EPSILON * np.random.random()
        return [x, y]

    # TODO: use OGR instead of QGIS
#    def createContourLayer(self, lines):
#        dec = self.uPrecision.value()
#        name = "%s" % str(self.uOutputName.text())
#        vl = self.createVectorLayer("MultiLineString", name)
#        pr = vl.dataProvider()
#        pr.addAttributes( [QgsField("index", QVariant.Int, "Int"),
#                           QgsField(self._zField, QVariant.Double, "Double"),
#                           QgsField("label", QVariant.String, "String")] )
#        msg = list()
#        for i, level, line in lines:
#            try:
#                fet = QgsFeature()
#                fet.setGeometry(QgsGeometry.fromWkt(QString(MultiLineString(line).to_wkt())))
#                fet.setAttributeMap( { 0 : QVariant(i), 1 : QVariant(level),
#                                       2 : QVariant( str("%s"%np.round(level, dec)) )
#
#                                     } )
#                pr.addFeatures( [ fet ] )
#            except:
#                msg.append("%s"%level)
#        if len(msg) > 0:
#            self.message("Levels not represented : %s"%", ".join(msg),"Contour issue")
#        vl.updateExtents()
#        vl.commitChanges()
#        return vl

    def createFilledContourLayer(self, driverName, fileName="/vsistdout"):
        self.computeFilledContours()

        drv = ogr.GetDriverByName(driverName)
        if drv is None:
            raise ContourError("%s driver not available." % driverName)

        #name = "%s"%str(self.uOutputName.text())
        #pr.addAttributes( [QgsField("index", QVariant.Int, "Int"),
        #                   QgsField(self._zField+"_min", QVariant.Double, "Double"),
        #                   QgsField(self._zField+"_max", QVariant.Double, "Double"),
        #                   QgsField("label", QVariant.String, "String")] )

        ds = drv.CreateDataSource(fileName)
        if ds is None:
            raise ContourError("Creation of output file %s failed" % fileName)

        lyr = ds.CreateLayer("filled_contours", None, ogr.wkbMultiPolygon)
        if lyr is None:
            raise ContourError("Layer creation failed.")

        field_defn = ogr.FieldDefn("level_min", ogr.OFTReal)
        if lyr.CreateField(field_defn) != 0:
            raise ContourError("Creating level_min field failed.")

        msg = list()
        for i, level_min, level_max, polygon in self._polygons:
            try:
                feat = ogr.Feature(lyr.GetLayerDefn())

                feat.SetField("level_min", level_min)

                wkb = MultiPolygon(polygon).to_wkb()
                pt = ogr.CreateGeometryFromWkb(wkb)

                feat.SetGeometry(pt)

                if lyr.CreateFeature(feat) != 0:
                    raise ContourError("Failed to create feature in shapefile.")

                feat.Destroy()
            except:
                msg.append(str(sys.exc_info()[1]))
                msg.append("%s" % level_min)

        ds = None

if __name__ == "__main__":
    # Testing Contours using points.shp with 'cost' attribute
    c = Contours(dataSrcName='points.shp', fieldName='cost')
    c.setLevels(0.0, 2.0, 5)
    # Create filled contour layer and write to stdout as GeoJSON
    c.createFilledContourLayer(driverName="GeoJSON")
