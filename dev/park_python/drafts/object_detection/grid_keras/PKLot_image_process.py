##################################################################
#        MESURE DU TAUX D'OCCUPATION DE PARKINGS A L'AIDE        #
#                       DE CAMERAS VIDEOS                        #
# -------------------------------------------------------------- #
#              Rémi Jacquemard - TB 2018 - HEIG-VD               #
#                   remi.jacquemard@heig-vd.ch                   #
#               https://github.com/remij1/TB_2018                #
#                           July 2018                            #
# -------------------------------------------------------------- #
# Used to process PKLot images and count cars from xmls          #
##################################################################

import park_python.camera.image_processing as process
from skimage import io
import os
from lxml import etree
from joblib import Parallel, delayed # parallelizing
import math
import warnings
import numpy as np


PKLOT_PATH = "C:/DS/PKLot/PKLot/PKLot/UFPR05"
IMAGE_EXT = ".jpg"
XML_EXT = ".xml"

OUTPUT_PATH = "C:/DS/PKLot/PKLot/PKLot/UFPR05_processed"
os.makedirs(OUTPUT_PATH, exist_ok=True)
OUTPUT_EXT = ".bmp"
OUTPUT_METADATA = "NB_CARS"

GRID_SIZE = 22
IMAGE_SIZE = (720, 1280)
CEIL_DIM = (math.ceil(IMAGE_SIZE[0] / GRID_SIZE), math.ceil(IMAGE_SIZE[1] / GRID_SIZE))


def find_cars(xml_file):
    # parsing the xml
    tree = etree.parse(xml_file)

    # finding cars
    cars = tree.xpath("/parking/space[@occupied='1']/rotatedRect/center")
    
    # 2D array representing the grid
    grid = np.zeros((GRID_SIZE, GRID_SIZE))

    # mapping the cars to the grid
    for car in cars:
        pixel_x, pixel_y = (int(car.attrib['x']), int(car.attrib['y']))
        grid_x, grid_y = (math.floor(pixel_x / CEIL_DIM[1]), math.floor(pixel_y / CEIL_DIM[0]))

        grid[grid_y][grid_x] = 1.0

    # print(sum(sum(grid)))

    return grid


find_cars(r"C:\Users\Remi\Downloads\PKLot\PKLot\UFPR05\Sunny\2013-03-02\2013-03-02_10_45_05.xml")
    

def processing(root, f):
    image_file = os.path.join(root, f)
    xml_file = os.path.join(root, f[:-len(IMAGE_EXT)] + XML_EXT) # corresponding xml file
    
    # Processing the image
    image = process.process_image(image_file)


    # Counting cars
    nb_cars = count_cars(xml_file)

    # The file format name is 'image_name.nb_cars.bmp'. The number of cars within the capture is so save.
    output_file = "{}/{}.{}{}".format(OUTPUT_PATH, f[:-len(IMAGE_EXT)], nb_cars, OUTPUT_EXT)
    
    # the label is set as a folder name
    output_folder = "{}/{}".format(OUTPUT_PATH, nb_cars)
    os.makedirs(output_folder, exist_ok=True)
    output_file = "{}/{}{}".format(output_folder, f[:-len(IMAGE_EXT)], OUTPUT_EXT)

    # saving the image
    with warnings.catch_warnings(): # used to ignore loss of precision warning
        warnings.simplefilter("ignore")
        io.imsave(output_file, image)
        print(output_file)


'''
for root, _, files in os.walk(PKLOT_PATH) :
    for f in files:
        if f.endswith(IMAGE_EXT):
'''
# Processing the images with parallels job
if __name__ == "__main__":
    Parallel(n_jobs=4)(delayed(processing)(root, f) for root, _, files in os.walk(PKLOT_PATH) for f in files if f.endswith(IMAGE_EXT))
