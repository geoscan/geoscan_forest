# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Geoscan Forest
                                 A QGIS plugin
 Forest Analysis
                              -------------------
        begin                : 2019-06-25
        git sha              : $Format:%H$
        copyright            : (C) 2019 by Zakora Aleksandr, Geoscan
        email                : support@geoscan.aero
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from PyQt5.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, QThread
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction, QFileDialog

# checking dependencies from scripts/requitements.txt
from .scripts import install_deps
ans = install_deps.check_deps()

# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .forest_agro_plugin_dialog import ForestAgroClassificationDialog

import os.path
from qgis.core import QgsApplication, QgsTask, QgsMessageLog


import random
from time import sleep

N = 0

class ForestAgroClassification:
    """QGIS Plugin Implementation."""
    no_ortho = True

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface

        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'ForestAgroClassification_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Geoscan Forest')

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None




    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('Geoscan Forest', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/forest_agro_plugin/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Geoscan Forest'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # will be set False in run()
        self.first_start = True






    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Geoscan Forest'),
                action)
            self.iface.removeToolBarIcon(action)


    def run(self):
        """Run method that performs all the real work"""

        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        if self.first_start == True:
            self.first_start = False
            self.dlg = ForestAgroClassificationDialog()


        
        self.configure_GUI() #функция, которая полностью настраивает интерфейс

        # show the dialog
        self.dlg.show()


    def start_compute(self):
        #if we have active task then do nothing, else start task
        isActive = False
        try:
            isActive = globals()['ForestAgroComputeObj'].isActive()
        except:
            pass
        if not isActive:
            from .forest_agro_compute import ForestAgroCompute
            # hide progress elements -> show only when task is running

            self.dlg.PB_start.setEnabled(False)
            self.dlg.PB_cancel.setHidden(False)

            globals()['ForestAgroComputeObj'] = ForestAgroCompute("Geoscan Forest Task")
            globals()['ForestAgroComputeObj'].progress_changed.connect(self.progress_bar_value_changed)
            globals()['ForestAgroComputeObj'].on_finished.connect(self.task_finished)
            globals()['ForestAgroComputeObj'].points_draw.connect(self.points_draw)
            globals()['ForestAgroComputeObj'].polys_draw.connect(self.polys_draw)
            globals()['ForestAgroComputeObj'].log_sig.connect(self.update_log)
            globals()['ForestAgroComputeObj'].dem_required = False
            globals()['ForestAgroComputeObj'].winSize = self.dlg.SB_win_size.value()
            globals()['ForestAgroComputeObj'].canopy_segmentation_required = self.dlg.CB_segmentation_req.isChecked()
            globals()['ForestAgroComputeObj'].result_path = self.dlg.LE_result_path.text()

            globals()['ForestAgroComputeObj'].images_path = [self.dlg.CB_ortho_layer.currentData().dataProvider().dataSourceUri()]
            # form search_area arrays
            if self.dlg.CB_interest_area.currentIndex() != 0:
                features = self.dlg.CB_interest_area.currentData().getFeatures()

            interest_area = []
            try:
                for feature in features:
                    poly = []
                    geom = feature.geometry()
                    x = geom.asPolygon()
                    for i in x[0]:
                        poly.append((i.x(), i.y()))
                    interest_area.append(poly)
            except:
                # default select or some error
                pass
            globals()['ForestAgroComputeObj'].search_area = interest_area
            QgsApplication.taskManager().addTask(globals()['ForestAgroComputeObj'])


    def progress_bar_value_changed(self, value):
        # change progress bar value
        self.dlg.PrB_main.setValue(value)

    def configure_GUI(self):
        # signals
        self.dlg.PB_start.clicked.connect(self.start_compute) # start button
        self.dlg.PB_result_dir.clicked.connect(self.get_result_dir_path) # button to choose where results must be saved
        self.dlg.PB_cancel.clicked.connect(self.exit_task) # button to choose where results must be saved

        # hide params button // need to be implemented
        self.dlg.PB_seg_configue.setHidden(True)

        # hide progress elements -> show only when task is running
        try:
            globals()['ForestAgroComputeObj'].isActive()
        except:
            self.dlg.PB_cancel.setHidden(True)

        # set True for no_ortho (if we have valid ortho, we set False later)
        self.no_ortho = True

        # clear all combobox when open main window
        self.dlg.CB_ortho_layer.clear()
        self.dlg.CB_interest_area.clear()

        # default item if there are no valid vector polygons
        self.dlg.CB_interest_area.addItem("Whole orthophoto")

        # filling comboboxes with items from qgis gui
        layers = self.iface.mapCanvas().layers()
        for i in layers:
            # if type == raster -> add this layer to orthophotos list
            if (i.type() == 1):
                self.dlg.CB_ortho_layer.addItem(i.name(), userData = i)

                self.no_ortho = False

            # if type == vector and geometryType == polygon -> add this layer to interest area list
            if i.type() == 0:
                if i.geometryType() == 2:
                    if "Canopy" not in i.name():
                        self.dlg.CB_interest_area.addItem(i.name(), userData = i)

        # if there are no valid rasters -> add default
        if self.dlg.CB_ortho_layer.count() == 0:
            self.dlg.CB_ortho_layer.addItem("No matching rasters found.")
        self.update_control()


    def update_control(self):
        # This feature will enable and disable the ability to interact with system elements.
        # For example, if there are no orthophoto available, then the start button must be turned off.

        PB_should_be_Enabled = \
            (not self.no_ortho) and \
            (not self.dlg.LE_result_path.text() == "")

        self.dlg.PB_start.setEnabled(PB_should_be_Enabled)

    def get_result_dir_path(self):
        #open dialog in user home dir; choose only directory to save results
        dir = QFileDialog.getExistingDirectory(None, "Open Directory", "", QFileDialog.ShowDirsOnly)
        self.dlg.LE_result_path.setText(dir)
        self.update_control()

#     ///////////////////////////////////////////////////
    def task_finished(self):
        self.update_control()
        self.dlg.PrB_main.setValue(0)
        self.dlg.TE_log.append("Job aborted!")
        self.dlg.PB_cancel.setHidden(True)
        self.dlg.PB_cancel.setText("Cancel")
        self.dlg.PB_cancel.setEnabled(True)



    def update_log(self, log_str):
        self.dlg.TE_log.append(log_str)

    def exit_task(self):
        self.dlg.PB_cancel.setText("Wait...")
        self.dlg.PB_cancel.setEnabled(False)
        QgsApplication.taskManager().activeTasks()[0].cancel()

    def polys_draw(self, path):
        print(path)
        self.iface.addVectorLayer(path, "Canopy_", "ogr")

    def points_draw(self, path):
        print(path)
        self.iface.addVectorLayer(path, "Trees_", "ogr")



