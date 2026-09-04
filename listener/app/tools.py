# python3

from datetime import datetime

import numpy as np
from pyocr import tesseract
from pyocr.builders import TextBuilder, WordBoxBuilder

from frapper_core.constants import DATETIME_FORMAT, FrapperConfig


conf = FrapperConfig


def parse_image_boxes(image, convert_to_gray=False):
    print("==================")
    print(image)

    if convert_to_gray:
        image = to_gray(image)
    return tesseract.image_to_string(image, lang=conf.TARGET_LANG, builder=WordBoxBuilder())


def parse_text(image, convert_to_gray=False):
    print("++++++++++++++++++++++++")
    print(image)

    if convert_to_gray:
        image = to_gray(image)
    text = tesseract.image_to_string(image, lang=conf.TARGET_LANG, builder=TextBuilder())
    return text.replace('\n', ' ')


def to_gray(image):
    image_gray = image.convert('L')
    return image_gray.point(
        lambda x: conf.WHITE_NUM if x > conf.THRES_HOLD_BLACK else conf.BLACK_NUM
    )


def find_split_height(image):
    width, _ = image.size
    array = np.array(image)

    result, point = list(), list()
    candidate_list = [x / conf.WHITE_NUM for x in (x.sum() for x in array)]

    for idx, array_x in enumerate(candidate_list, start=1):
        if int(array_x.sum()) == width:
            point.append(idx)
        else:
            if point:
                result.append(point)
            point = list()

    if point:
        point.append(idx)
        result.append(point)

    if len(result) < conf.WHITE_SEPARATOR_COUNT:
        return False

    result_by_len = [len(x) for x in result][1:-1]
    index = result_by_len.index(max(result_by_len))

    suitable_list = result[index + 1]
    return suitable_list[len(suitable_list) // 2]


def get_pixel_sum(date_str):
    date = datetime.strptime(date_str, DATETIME_FORMAT)
    version_date = datetime.strptime(FrapperConfig.PIXEL_SUM_DATE, DATETIME_FORMAT)
    return conf.PIXEL_SUM_V1 if date < version_date else conf.PIXEL_SUM_V2


def in_a_range(pixel):
    a, b, c = pixel
    return all([a in range(*conf.R_RANGE), b in range(*conf.G_RANGE), c in range(*conf.B_RANGE)])
