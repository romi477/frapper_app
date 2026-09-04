from datetime import datetime


DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S'


class FrapperConfig:

    PIXEL_SUM_V1 = 255 + 255 + 255
    PIXEL_SUM_V2 = 243 + 247 + 250  # images since 10.05.2023 because of the new design of Reverso
    PIXEL_SUM_DATE = '2023-05-10T00:00:00'

    TAG_OFFSET = 4
    MIN_IMAGE_HEIGHT = 140

    STANDARD_WIDTH = 1080
    IMAGE_OFFSET_L = 32
    IMAGE_OFFSET_R = 112
    CUT_THE_ARROW_OFFSET = 73  # depends on IMAGE_OFFSET_L, sum = 105

    THRES_HOLD_TAG = 15
    THRES_HOLD_BLACK = 150
    WHITE_SEPARATOR_COUNT = 3

    BLACK_NUM = 0
    WHITE_NUM = 255

    R_RANGE = (245, 255)
    G_RANGE = (245, 255)
    B_RANGE = (212, 228)

    IS_TRUE = '1'
    IS_FALSE = '0'

    TO_DO = 'todo'
    ERROR = 'error'
    DONE = 'done'

    TARGET_LANG = 'pol'


def datetime_now():
    return datetime.now().strftime(DATETIME_FORMAT)
