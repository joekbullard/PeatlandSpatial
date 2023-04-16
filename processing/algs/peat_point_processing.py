# -*- coding: utf-8 -*-

"""
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

from qgis.PyQt.QtCore import QCoreApplication, QVariant
from qgis.core import (
    QgsProcessing,
    QgsFeatureSink,
    QgsProcessingException,
    QgsProject,
    QgsProcessingAlgorithm,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterBoolean,
    QgsCoordinateTransform,
    QgsCoordinateReferenceSystem,
    QgsField,
    QgsVectorLayer,
    QgsGeometry,
    edit,
    QgsPointXY,
    QgsFeature,
)
from qgis import processing


class PeatDepthPoints(QgsProcessingAlgorithm):
    """
    This is an example algorithm that takes a vector layer and
    creates a new identical one.

    It is meant to be used as an example of how to create your own
    algorithms and explain methods and variables used to do it. An
    algorithm like this will be available in all elements, and there
    is not need for additional work.

    All Processing algorithms should extend the QgsProcessingAlgorithm
    class.
    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    INPUT = "INPUT"
    OUTPUT = "OUTPUT"
    GRID50 = "GRID50"

    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate("Processing", string)

    def createInstance(self):
        return PeatDepthPoints()

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return "peatpoints"

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr("Create peat points")

    def group(self):
        """
        Returns the name of the group this algorithm belongs to. This string
        should be localised.
        """
        return self.tr(self.groupId())

    def groupId(self):
        """
        Returns the unique ID of the group this algorithm belongs to. This
        string should be fixed for the algorithm, and must not be localised.
        The group id should be unique within each provider. Group id should
        contain lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return None

    def shortHelpString(self):
        """
        Returns a localised short helper string for the algorithm. This string
        should provide a basic description about what the algorithm does and the
        parameters and outputs associated with it..
        """
        return self.tr(
            "Generates a peat depth and condition survey layer with 100m or 50m point spacings aligned to British National Grid"
        )

    def initAlgorithm(self, config=None):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """

        # input polygon geometry.
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT, self.tr("Input layer"), [QgsProcessing.TypeVectorPolygon]
            )
        )

        # We add a feature sink in which to store our processed features (this
        # usually takes the form of a newly created vector layer when the
        # algorithm is run in QGIS).
        self.addParameter(
            QgsProcessingParameterFeatureSink(self.OUTPUT, self.tr("Output layer"))
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.GRID50, self.tr("Include 50m points?"), defaultValue=True
            )
        )

    def generate_peat_layer(self):
        """
        Create a peat depth point layer
        """
        peat_layer = QgsVectorLayer("Point", "peat_depth_points", "memory")
        crs = peat_layer.crs()
        crs.createFromId(27700)
        peat_layer.setCrs(crs)
        pr = peat_layer.dataProvider()

        pr.addAttributes(
            [
                QgsField("record_id", QVariant.Int),
                QgsField("easting", QVariant.Int),
                QgsField("northing", QVariant.Int),
                QgsField("date", QVariant.Date),
                QgsField("spacing", QVariant.Int),
                QgsField("peat_depth", QVariant.Int),
                QgsField("main_con", QVariant.String),
                QgsField("sub_con", QVariant.String),
                QgsField("notes", QVariant.String),
                QgsField("photo", QVariant.String),
            ]
        )
        peat_layer.updateFields()

        return peat_layer

    def transform_geom(geom, crs):
        coord_crs = QgsCoordinateReferenceSystem(crs)
        bng = crs.createFromId(27700)
        transform = QgsCoordinateTransform(coord_crs, bng, QgsProject.instance())
        geom = transform.transform(geom)
        return geom

    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        """

        feedback.pushInfo("Starting processing algo")

        # Retrieve the feature source and sink. The 'dest_id' variable is used
        # to uniquely identify the feature sink, and must be included in the
        # dictionary returned by the processAlgorithm function.
        source = self.parameterAsVectorLayer(parameters, self.INPUT, context)

        grid50 = self.parameterAsBool(parameters, self.GRID50, context)

        peat_layer = self.generate_peat_layer()
        peat_fields = peat_layer.fields()
        peat_wkb = peat_layer.wkbType()
        peat_crs = peat_layer.crs()

        source_crs = source.sourceCrs()

        # reproject layer if not EPSG:27700
        if source_crs is not peat_crs:
            reproj = processing.run(
                "qgis:reprojectlayer",
                {
                    "INPUT": source,
                    "TARGET_CRS": "EPSG:27700",
                    "OUTPUT": "memory:",
                },
            )
            source = reproj["OUTPUT"]

        if grid50 == True:
            spacing = 50
        else:
            spacing = 100

        # If source was not found, throw an exception to indicate that the algorithm
        # encountered a fatal error. The exception text can be any string, but in this
        # case we use the pre-built invalidSourceError method to return a standard
        # helper text for when a source cannot be evaluated
        if source is None:
            raise QgsProcessingException(
                self.invalidSourceError(parameters, self.INPUT)
            )

        (sink, dest_id) = self.parameterAsSink(
            parameters,
            self.OUTPUT,
            context,
            peat_fields,
            peat_wkb,
            peat_crs,
        )

        # Send some information to the user
        # feedback.pushInfo("CRS is {}".format(peat_crs.authid()))

        # If sink was not created, throw an exception to indicate that the algorithm
        # encountered a fatal error. The exception text can be any string, but in this
        # case we use the pre-built invalidSinkError method to return a standard
        # helper text for when a sink cannot be evaluated
        if sink is None:
            raise QgsProcessingException(self.invalidSinkError(parameters, self.OUTPUT))

        # Compute the number of steps to display within the progress bar and
        # get features from source
        total = 100.0 / source.featureCount() if source.featureCount() else 0
        features = source.getFeatures()

        count = 1

        for current, feature in enumerate(features):
            # Stop the algorithm if cancel button has been clicked
            if feedback.isCanceled():
                break

            # get geom and bounding box of feature
            geom = feature.geometry()
            bbox = geom.boundingBox()
            x_max = int(bbox.xMaximum())
            y_max = int(bbox.yMaximum())
            x_min = int(bbox.xMinimum())
            y_min = int(bbox.yMinimum())

            roundup = lambda a, b: a if a % b == 0 else a + b - a % b

            start_x = roundup(x_min, spacing)
            start_y = roundup(y_min, spacing)
            end_x = x_max
            end_y = y_max

            y = start_y

            with edit(peat_layer):

                while y < end_y:

                    x = start_x

                    while x < end_x:

                        point = QgsGeometry.fromPointXY(QgsPointXY(x, y))

                        if point.within(geom):

                            feat = QgsFeature(peat_layer.fields())
                            if x % 100 == 0 and y % 100 == 0:
                                feat.setAttribute("spacing", 100)
                            else:
                                feat.setAttribute("spacing", 50)
                            feat.setGeometry(point)
                            feat.setAttribute("record_id", count)
                            feat.setAttribute("easting", x)
                            feat.setAttribute("northing", y)
                            sink.addFeature(feat, QgsFeatureSink.FastInsert)

                            count += 1

                        x += spacing

                    y += spacing

            # Add a feature in the sink
        # sink.addFeature(feature, QgsFeatureSink.FastInsert)

        # Update the progress bar
        feedback.setProgress(int(current * total))

        # To run another Processing algorithm as part of this algorithm, you can use
        # processing.run(...). Make sure you pass the current context and feedback
        # to processing.run to ensure that all temporary layer outputs are available
        # to the executed algorithm, and that the executed algorithm can send feedback
        # reports to the user (and correctly handle cancellation and progress reports!)

        # Return the results of the algorithm. In this case our only result is
        # the feature sink which contains the processed features, but some
        # algorithms may return multiple feature sinks, calculated numeric
        # statistics, etc. These should all be included in the returned
        # dictionary, with keys matching the feature corresponding parameter
        # or output names.
        return {self.OUTPUT: dest_id}
