# -*- coding: utf-8 -*-

"""
This file is to re-organize the MTWI_2018 dataset labels into CTPN anchor format.
MTWI_2018 label format: [X1, Y1, X2, Y2, X3, Y3, X4, Y4, text]
	(X1, Y1): left_top; (X2, Y2): left_bottom
	(X3, Y3): right_bottom; (X4, Y4): right_top
gt-label format: list of tuple(position, center_y, height)
Only coordinates are needed in this task.
"""

import copy
import math
import os

import cv2
import numpy as np
from PIL import Image

# generate gt-anchors
def generate_gt_anchor(image, label, anchor_width=16):
    """
    args:
        image: input image
        label: input MTWI_2018 label (without text)
        anchor_width: the width of the anchors
    return:
        list of tuple(position, center_y, height)
    """
    result = []
    coord = [float(label[i]) for i in range(len(label))]

    # get the left-side & right-side anchors' ids
    left_anchor_id = int(math.floor(max(min(coord[0], coord[2]), 0) / anchor_width))
    right_anchor_id = int(math.ceil(min(max(coord[6], coord[4]), image.shape[1]) / anchor_width))

    # the right side anchor may exceed the image width
    if right_anchor_id * 16 + 15 > image.shape[1]:
        right_anchor_id -= 1

    # combine the left-side and the right-side x-axis coords of a text anchor into a pairs
    pairs = [(i * anchor_width, (i + 1) * anchor_width - 1) for i in range(left_anchor_id, right_anchor_id)]

    # calculate anchor's top & bottom boundary
    y_top, y_bottom = cal_bound_y(image, pairs, coord)

    # return list of tuple(position, center_y, height)
    for i in range(len(pairs)):
        if pairs != [] and i < len(y_top):
            position = int(pairs[i][0] / anchor_width)
            center_y = (float(y_bottom[i]) + float(y_top[i])) / 2.0
            height = y_bottom[i] - y_top[i] + 1
            result.append((position, center_y, height))
    return result


# calculate the gt-anchor's top & bottom y-axis coordinates
def cal_bound_y(raw_image, pairs, coord):
    """
    args:
        raw_image: input image
        pairs: for example: [(0, 15), (16, 31), ...]
        coord: gt-anchor's coordinates (4 points)
    return: 
        gt-anchor's top & bottom y-axis coordinates
    """
    image = copy.deepcopy(raw_image)
    y_top = []
    y_bottom = []
    height = image.shape[0]
    # set channel 0 as mask
    for i in range(image.shape[0]):
        for j in range(image.shape[1]):
            image[i, j, 0] = 0

    # draw text box on the image
    pt = [int(i) for i in coord]
    image = cv2.line(image, (pt[0], pt[1]), (pt[2], pt[3]), 255, thickness=1)
    image = cv2.line(image, (pt[0], pt[1]), (pt[6], pt[7]), 255, thickness=1)
    image = cv2.line(image, (pt[4], pt[5]), (pt[6], pt[7]), 255, thickness=1)
    image = cv2.line(image, (pt[4], pt[5]), (pt[2], pt[3]), 255, thickness=1)

    is_top = False
    is_bottom = False
    
    for i in range(len(pairs)):
        # find top boundary
        for y in range(0, height - 1):
            # loop from left to right
            for x in range(pairs[i][0], pairs[i][1] + 1):
                if image[y, x, 0] == 255:
                    y_top.append(y)
                    is_top = True
                    break
            if is_top is True:
                break
        
        # find bottom boundary
        for y in range(height - 1, -1, -1):
            # loop from left to right
            for x in range(pairs[i][0], pairs[i][1] + 1):
                if image[y, x, 0] == 255:
                    y_bottom.append(y)
                    is_bottom = True
                    break
            if is_bottom is True:
                break
        
        is_top = False
        is_bottom = False

    return y_top, y_bottom


# get all anchors from an image
def get_anchors_from_image(image_path, label_path):
    """
    args:
        image_path: *.jpg 
        label_path: *.txt
    return:
        list of anchors
    """
    image = Image.open(image_path)
    image = np.array(image)
    label_file = open(label_path, "r", encoding='utf-8')
    result = []

    # get anchors & write to gt_file
    for line in label_file.readlines():
        line = line.split(',')
        # get rid of text
        label = [float(line[i]) for i in range(8)]
        result.append(generate_gt_anchor(image, label))
    
    label_file.close()
    return result


# reorganize original dataset
def reorganize_dataset():
    image_dir = "./image_train"
    label_dir = "./txt_train"
    all_image = os.listdir(image_dir)
    all_label = os.listdir(label_dir)
    all_image.sort()
    all_label.sort()
    count = 0
    for image_name, label_name in zip(all_image, all_label):
        image = Image.open(image_dir + '/' + image_name)
        image = np.array(image)

        # if image doesn't have RGB channels, abandon
        if len(image.shape) < 3:
            print("Bad image: " + image_name)
            os.remove(image_dir + '/' + image_name)
            os.remove(label_dir + '/' + label_name)

        else:
            os.rename(image_dir + '/' + image_name, image_dir + '/' + str(count) + ".jpg")
            os.rename(label_dir + '/' + label_name, label_dir + '/' + str(count) + ".txt")
            image_name = str(count) + ".jpg"
            label_name = str(count) + ".txt"
            count += 1
