# -*- coding: utf-8 -*-
"""
/***************************************************************************
 ForestAgroClassification
                                 A QGIS plugin
 Forest Analysis
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                             -------------------
        begin                : 2019-06-25
        copyright            : (C) 2019 by Zakora Aleksandr, Geoscan
        email                : a.zakora@geoscan.aero
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load ForestAgroClassification class from file ForestAgroClassification.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .forest_agro_plugin import ForestAgroClassification
    return ForestAgroClassification(iface)
