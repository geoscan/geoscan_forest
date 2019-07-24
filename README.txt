The plugin was created to search for tree tops in the forest along an orthophotomap. The approximate spatial resolution should be about 5 centimeters per pixel.
Cron segmentation is also performed for found trees.

To get started you need:
1) Add a raster layer with an orthophotomap to the QGIS project (Layer -> Add Raster Layer)
2) Open the plugin window and select the path to the directory where to save the results in GeoJSON format.
3) Click the Compute button.

This is the minimum set of actions to run.

You can also customize the work as follows:
1) Adjust the window size - the size of the tile that is processed in one iteration of the work (too large tiles require a large amount of RAM)
2) Disable cron segmentation if only tree tops are needed
3) Set the search area. A polygon layer must be created in the QGIS program. The search will be performed inside the polygons for this.

For work, the following libraries are needed:
1) skimage
2) scipy
3) geojson
4) shapely

These libs will be installed automatically (with notifications).

But you can easily install them manually, for example, through the OSGeo4W Shell console.

1) First, enter "python -V" in the command line.
If in the answer you received a 3. *. * - go to step 2.
Otherwise, enter the command py3_env

2) Open this console and enter for each library:

python -m install scikit-image
python -m install geojson

[python -m install scipy]
[python -m install shapely]

After that, your environment is ready to go.