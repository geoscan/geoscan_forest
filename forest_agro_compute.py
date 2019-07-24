from osgeo import gdal
from PyQt5.QtCore import QThread, QObject, pyqtSignal
import time
import os
from qgis.core import QgsApplication, QgsTask, QgsMessageLog

import numpy as np


from skimage.feature import peak_local_max
from skimage.filters import gaussian
from skimage.morphology import watershed
from skimage.filters import sobel
from skimage.exposure import equalize_hist
from skimage.measure import regionprops
from skimage.measure import find_contours,approximate_polygon
from skimage.exposure import rescale_intensity
from skimage.draw import polygon
from skimage.exposure import rescale_intensity
from skimage.filters import threshold_local
from scipy import ndimage as ndi


from geojson import Point, Feature, FeatureCollection, dump
from shapely.geometry import mapping, Polygon


class ForestAgroCompute(QgsTask):
    on_finished = pyqtSignal()
    progress_changed = pyqtSignal(float)
    log_sig = pyqtSignal(str)

    points_draw = pyqtSignal(str)
    polys_draw = pyqtSignal(str)

    max_square = 10000000
    min_square = 0
    watershed = 0.001
    blur = 17
    old_th = 0.4

    count = 0
    result_path = ""

    dem_required = True
    canopy_segmentation_required = True
    images_path = []

    winSize = 512
    search_area = []

    canceledFlag = False
    def __init__(self, description):
        super().__init__(description)

    def run(self):
        self.dem_required = False
        # Точка входа. Тут запускаются все функции обработки
        ind = 0

        for cur_filename in self.images_path:
            ind += 1
            if self.canceledFlag:
                return 1
            self.compute_image(cur_filename)
        return 1

    def compute_image(self, path):
        iter_start = time.time()
        QgsMessageLog.logMessage("File processing " + path)
        self.log_sig.emit("File processing " + path)

        image_data = gdal.Open(path)

        if image_data == None:
            self.log_sig.emit("\t " + path + " - invalid file format!")
            self.log_sig.emit("\t File processing aborted!!!")
            return
        if image_data.RasterCount < 3:
            self.log_sig.emit("\t " + path + " - Incorrect number of raster channels (less than 3)!")
            self.log_sig.emit("\t File processing aborted!!!")
            return



        x_size = image_data.RasterXSize
        y_size = image_data.RasterYSize
        if self.winSize > x_size or self.winSize > y_size:
            self.winSize = min(x_size, y_size)


        x_tail = x_size % self.winSize
        y_tail = y_size % self.winSize

        N_steps = int(x_size / self.winSize + 1) * int(y_size / self.winSize + 1)
        counter = 0
        for x_step in range(0, x_size, self.winSize):
            for y_step in range(0, y_size, self.winSize):

                if self.canceledFlag:
                    return 1
                t_all = time.time()

                self.progress_changed.emit(100 * counter / N_steps)
                self.setProgress(100 * counter / N_steps)
                counter += 1

                geotransform = image_data.GetGeoTransform()
                if geotransform[1] == 1 and geotransform[
                    5] == 1:  # если у нас нет геопривязки, то меняем шаг по y на -1
                    geotransform = (geotransform[0], geotransform[1], geotransform[2], geotransform[3], geotransform[4],
                                    -geotransform[5])

                geotransform = (geotransform[0] + x_step * geotransform[1], geotransform[1], geotransform[2],
                                geotransform[3] + y_step * geotransform[5], geotransform[4], geotransform[5])
                t_start = time.time()

                image = [image_data.GetRasterBand(i).ReadAsArray(x_step, y_step, self.winSize, self.winSize) for i in
                         [1, 2, 3]]

                if type(image[0]) == type(None):
                    x_out = x_size - x_step == x_tail
                    y_out = y_size - y_step == y_tail

                    win_X_Tail = self.winSize
                    win_Y_Tail = self.winSize

                    if x_out:
                        win_X_Tail = x_tail
                    if y_out:
                        win_Y_Tail = y_tail

                    image = [image_data.GetRasterBand(i).ReadAsArray(x_step, y_step, win_X_Tail, win_Y_Tail) for i in
                             [1, 2, 3]]


                clipped = self.get_clipped_image(image, geotransform)


                gray_tgi_ortho = clipped[0]



                if clipped[1] == 0 or np.all(gray_tgi_ortho.astype(int) == 0):  # либо вне полинона, либо пустой тайл
                    continue

                # ИЩЕМ ТОЧКИ - ВЕРЩИНЫ КРОН
                self.log_sig.emit(
                    "\t Tile processing " + str(int(x_step / self.winSize)) + "_" + str(int(y_step / self.winSize)))
                self.log_sig.emit("\t    Tree Search ...")
                finded_trees_points = self.find_trees_point(gray_tgi_ortho)
                self.log_sig.emit(
                    "\t    Trees search is completed. (" + str(round(time.time() - t_start, 3)) + " sec)")


                # ИЩЕМ РАСТРОВЫЕ СЕГМЕНТЫ КРОН
                if self.canopy_segmentation_required:

                    self.log_sig.emit("\t    Cron segmentation ...")
                    t_start = time.time()
                    [segments_image, mask] = self.find_trees_segments(
                        trees_points=finded_trees_points["points_mask"],
                        gray_tgi_ortho=finded_trees_points["gray_tgi_ortho"])
                    self.log_sig.emit(
                        "\t    The crowns segmentation is complete. (" + str(round(time.time() - t_start, 3)) + " sec)")


                    # ПРЕОБРАЗУЕМ РАСТРОВЫЕ СЕГМЕНТЫ В ВЕКТОРНЫЕ ПОЛИГОНЫ И ИЩЕМ РАДИУСЫ КРОН, попутно сверяя размеры
                    self.log_sig.emit("\t    Conversion of crowns to vector format ...")
                    t_start = time.time()
                    temp_points_dict = {}
                    for i in finded_trees_points["points_coords"]:
                        temp_points_dict.update({segments_image[i[0]][i[1]]: [i[0], i[1]]})

                    self.poly_dict, points_to_file = self.get_shapes(segments_image,
                                                                     [segments_image[i[0]][i[1]] for i in
                                                                      finded_trees_points["points_coords"]],
                                                                     temp_points_dict)

                    self.log_sig.emit("\t    Conversion of crowns to vector format completed. (" + str(
                        round(time.time() - t_start, 3)) + " sec)")
                    points_path = self.write_points_to_geojson(points_to_file, geotransform,
                                                               filename=path, tile_id="_" + str(
                            int(x_step / self.winSize)) + "_" + str(int(y_step / self.winSize)))
                    polys_path = self.write_polygons_to_geojson(self.poly_dict, geotransform, filename=path,
                                                                tile_id="_" + str(
                                                                    int(x_step / self.winSize)) + "_" + str(
                                                                    int(y_step / self.winSize)))

                    self.points_draw.emit(points_path)
                    self.poly_dict.clear()
                    del segments_image
                    del mask
                    self.polys_draw.emit(polys_path)
                    ######################################
                del gray_tgi_ortho
                image.clear()
                del finded_trees_points["points_mask"]
                del finded_trees_points["points_coords"]
                del finded_trees_points["blurred"]
                self.log_sig.emit("\t Tile processing completed! (" + str(round(time.time() - t_all, 3)) + " sec)")
                self.log_sig.emit("")
        self.log_sig.emit(
            "File processing " + path + " completed! (" + str(round(time.time() - iter_start, 3)) + " sec)")
        self.log_sig.emit("")

    def get_clipped_image(self, image, geotransform):

        gray_tgi_ortho = image[1] - 0.39 * image[0] - 0.61 * image[2]

        if len(self.search_area) == 0:
            return (gray_tgi_ortho, 1)

        mask = np.zeros(gray_tgi_ortho.shape, dtype=np.uint8)

        for poly in self.search_area:
            row_coord = []
            column_coord = []
            for pix in poly:
                x = int((pix[0] - geotransform[0]) / geotransform[1])
                y = int((pix[1] - geotransform[3]) / geotransform[5])
                row_coord.append(x)
                column_coord.append(y)

            rr, cc = polygon(row_coord, column_coord, shape=gray_tgi_ortho.shape)

            mask[cc, rr] = 1

        return (gray_tgi_ortho * mask, mask.max())  # возвращаем флаг, есть ли "белые" области, которые нужно обработать

    def find_trees_point(self, gray_tgi_ortho):

        gray_tgi_ortho = equalize_hist(gray_tgi_ortho, mask=gray_tgi_ortho > 0)
        # gray_tgi_ortho = rescale_intensity(gray_tgi_ortho)

        blurred = gaussian(gray_tgi_ortho, sigma=self.blur)

        # blurred = gaussian(gray_tgi_ortho, sigma=17)

        return {
            "points_mask": peak_local_max(blurred, threshold_rel=self.old_th, min_distance=1, indices=False),
            "points_coords": peak_local_max(blurred, threshold_rel=self.old_th, min_distance=1, indices=True),
            "gray_tgi_ortho": gray_tgi_ortho,
            "blurred": blurred
        }

    def find_trees_segments(self, trees_points=None, gray_tgi_ortho=None):

        gray_tgi_ortho = rescale_intensity(gray_tgi_ortho)

        # mask = ndi.maximum_filter(gray_tgi_ortho, size=5, mode='constant') > 0.5

        # temp_img = ndi.maximum_filter(gray_tgi_ortho, size=5, mode='constant')
        temp_img = ndi.maximum_filter(gray_tgi_ortho, size=5, mode='constant')

        block_size = 301  # ???????????????????????
        local_thresh = threshold_local(temp_img, block_size, method='mean')

        mask = temp_img > local_thresh

        # красим точки на маске в разные цвета (разные метки)
        markers = ndi.label(trees_points)[0]

        # получаем граниент a.k.a. bias image
        gradient = sobel(gray_tgi_ortho)
        temp = watershed(gradient, markers=markers, compactness=self.watershed, mask=mask)

        return [temp, mask]  # compactness  = 0.001
        # return [watershed(gradient, markers=markers, compactness=0.001, mask=mask, watershed_line=True),mask]  # compactness  = 0.001

    def write_points_to_geojson(self, points, geotransform, filename, tile_id):
        import os

        if not os.path.exists(self.result_path + "/output/points"):
            os.makedirs(self.result_path + "/output/points")

        path_splitted = os.path.split(filename)
        res_filename = self.result_path + "/output/points/points_" + str(path_splitted[1]).split('.')[0] + tile_id
        self.log_sig.emit("\t    Records points " + res_filename + '.geojson ...')
        t_start = time.time()



        # записываем точки в формате geojson
        features = []
        for i in points:
            features.append(
                Feature(
                    geometry=Point(
                        (geotransform[0] + geotransform[1] * i[1], geotransform[3] + geotransform[5] * i[0])),
                    properties={"class": "Tree"}
                )
            )
        feature_collection = FeatureCollection(features)
        with open(res_filename + '.geojson', 'w') as f:
            dump(feature_collection, f)
        self.log_sig.emit("\t    Record points successfully completed. (" + str(round(time.time() - t_start, 3)) + " sec)")
        return res_filename + '.geojson'

    def write_polygons_to_geojson(self, polygons_dict, geotransform, filename, tile_id):

        import os
        if not os.path.exists(self.result_path + "/output/polygons"):
            os.makedirs(self.result_path + "/output/polygons")

        path_splitted = os.path.split(filename)
        res_filename = self.result_path + "/output/polygons/polygons_" + str(path_splitted[1]).split('.')[0] + tile_id

        self.log_sig.emit("\t    Record polygons in " + res_filename + '.geojson ...')
        t_start = time.time()

        features = []

        for id in polygons_dict:
            curr_poly = []
            for ind in range(len(polygons_dict[id])):
                x = geotransform[0] + geotransform[1] * polygons_dict[id][ind][1]
                y = geotransform[3] + geotransform[5] * polygons_dict[id][ind][0]

                curr_poly.append((x, y))  #########
                polygons_dict[id][ind] = (x, y)

            features.append(
                Feature(
                    # geometry=Polygon(polygons_dict[id][1]),
                    geometry=Polygon(curr_poly),  ########
                    properties={"id": str(id)}
                )
            )
        feature_collection = FeatureCollection(features)
        with open(res_filename + '.geojson', 'w') as f:
            dump(feature_collection, f)
        self.log_sig.emit(
            "\t    Polygon recordings completed successfully. (" + str(round(time.time() - t_start, 3)) + " sec)")
        return res_filename + '.geojson'

    def cancel(self):
        self.canceledFlag = True

    def get_shapes(self, segments_image, centres, points):

        from skimage.measure import regionprops

        regions = regionprops(segments_image)
        image_shape = segments_image.shape
        points_to_file = []
        poly_dict = {}
        for i in regions:

            if i.area < 50:
                continue
            if i.area < self.min_square or i.area > self.max_square:
                continue
            transform_image = i.filled_image

            # m_polygons = list(shapes(i.filled_image.astype(int), mask=i.filled_image, connectivity=8))
            # нужно найти замену rasterio
            # m_polygon = m_polygons[0][0]['coordinates'][0]

            shape = transform_image.shape

            transform_image[0] = 0  # zeroes out row 0
            transform_image[shape[0] - 1] = 0  # zeroes out last row

            transform_image[:, 0] = 0  # zeroes out column 0
            transform_image[:, shape[1] - 1] = 0  # zeroes out last column

            contours = find_contours(transform_image, 0)
            # print(contours)
            m_polygon = approximate_polygon(contours[0], tolerance=0.9)

            bbox = i.bbox

            poly = []

            N_merge_points = 0
            for item in m_polygon:
                poly.append([item[0] + bbox[0], item[1] + bbox[1]])
                if item[0] + bbox[0] == image_shape[0] or item[1] + bbox[1] == image_shape[1]:
                    N_merge_points += 1
                elif item[0] + bbox[0] == 0 or item[1] + bbox[1] == 0:
                    N_merge_points += 1

            if len(poly) > 3 and N_merge_points == 0:
                poly_dict.update({i.label: poly})
                points_to_file.append(list(points[i.label]))

        self.count += 1
        return (poly_dict, points_to_file)

    def finished(self, result):
        """This is called when do_task is finished.
        Exception is not None if do_task raises an exception.
        Result is the return value of do_task."""
        self.progress_changed.emit(100)
        self.setProgress(100)
        time.sleep(0.5)
        self.on_finished.emit()
