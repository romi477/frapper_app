# python3

from io import BytesIO
from copy import deepcopy

import numpy as np
from PIL import Image

from app.tools import (
    conf,
    to_gray,
    in_a_range,
    parse_text,
    get_pixel_sum,
    parse_image_boxes,
    find_split_height,
)


class ImageFrapper:

    def __init__(self, pil_image, metadata=None):
        self._state = conf.TO_DO
        self._image = pil_image
        self.metadata = metadata or dict()

        target, translate = self.split_row_image()

        self.target_image = target
        self.translate_image = translate

        self._target_array = np.array(target)
        self._translate_array = np.array(translate)

        self.target_image_gray = to_gray(target)
        self.translate_image_gray = to_gray(translate)

        self.target_string = ''
        self.target_tag = ''
        self.target_mask = ''

        self.translate_string = ''
        self.translate_tag = ''
        self.translate_mask = ''

    def __repr__(self):
        return '<ImageFrapper(%s)>' % self.metadata

    @classmethod
    def split_image_from_bin_data(cls, bin_data, **kw):

        with Image.open(BytesIO(bin_data)) as image:
            image.load()

        width, height = image.size

        if width != conf.STANDARD_WIDTH:
            new_height = int((height / width) * conf.STANDARD_WIDTH)
            image = image.resize((conf.STANDARD_WIDTH, new_height))
            width, height = image.size

        image_px = image.crop((conf.IMAGE_OFFSET_L, 0, conf.IMAGE_OFFSET_L + 1, height))
        image_array = np.array(image_px)

        need_second = False
        candidate_list, point = list(), list()

        pixel_sum = get_pixel_sum(kw['message_date'])

        for idx, pixel in enumerate(image_array, start=1):
            if int(pixel.sum()) == pixel_sum:
                if not need_second:
                    point.append(idx)
                    need_second = True
            else:
                if need_second:
                    point.append(idx)
                    candidate_list.append(point)
                    need_second = False
                    point = list()

        if need_second:
            point.append(idx)
            candidate_list.append(point)

        candidate_filtered = [(x, y) for x, y in candidate_list if (y - x) > conf.MIN_IMAGE_HEIGHT]

        result = list()
        for idx, (y1, y2) in enumerate(candidate_filtered, start=1):
            image_x = image.crop((conf.IMAGE_OFFSET_L, y1, width - conf.IMAGE_OFFSET_R, y2))

            kw['size'] = image_x.size
            kw['y1_y2'] = (y1, y2)
            kw['threshold'] = list()
            kw['file_index'] = idx

            record = cls(image_x, metadata=kw)
            result.append(record)

        return result

    @property
    def state(self):
        return self._state

    @property
    def is_done(self):
        return all([
            self.state == conf.DONE,
            self.target_string,
            self.target_tag,
            self.translate_string,
            self.translate_tag,
        ])

    def parse(self):
        if self.state == conf.ERROR:
            return False  # Do the math

        self.parse_target_string()
        self.parse_target_tag()

        self.parse_translate_string()
        self.parse_translate_tag()

        self._state = conf.DONE
        return True

    def parse_target_string(self):
        text = parse_text(self.target_image_gray)
        self.target_string = text
        return text

    def parse_translate_string(self):
        text = parse_text(self.translate_image_gray)
        self.translate_string = text
        return text

    def parse_target_tag(self):
        text, mask = self._parse_tag_text(self.target_image_gray, self._target_array)

        self.target_tag = text
        self.target_mask = mask
        return text

    def parse_translate_tag(self):
        text, mask = self._parse_tag_text(self.translate_image_gray, self._translate_array)

        self.translate_tag = text
        self.translate_mask = mask
        return text

    def split_row_image(self):
        width, height = self._image.size
        targer_image = translate_image = self._image

        gray_image = to_gray(self._image)
        split_height = find_split_height(gray_image)

        if not split_height:
            self._state = conf.ERROR
        else:
            targer_image = self._image.crop((0, 0, width, split_height))
            translate_image = self._image.crop((conf.CUT_THE_ARROW_OFFSET, split_height, width, height))

        return targer_image, translate_image

    def get_metainfo(self, to_string=False):
        metadata = deepcopy(self.metadata)

        metadata.pop('meta_id', False)
        metadata.pop('message_id', False)
        metadata.pop('message_date', False)

        if to_string:
            return str(metadata)
        return metadata

    def to_dict(self):
        return dict(
            meta_id =self.metadata['meta_id'],
            state=self.state,
            active=self.is_done,
            target=self.target_string,
            target_tag=self.target_tag,
            translate=self.translate_string,
            translate_tag=self.translate_tag,
            target_mask=self.target_mask,
            translate_mask=self.translate_mask,
            message_id=self.metadata['message_id'],
            message_date=self.metadata['message_date'],
            metadata=self.get_metainfo(to_string=True),
        )

    def _parse_tag_text(self, image, image_array):
        parse_result = list()
        threshold = list()
        box_list = parse_image_boxes(image)

        mask = list()
        for box in box_list:
            is_tag, value = self._is_tag(image_array, box.position)
            if is_tag:
                mask_value = conf.IS_TRUE
                parse_result.append(box.content.rstrip(',.'))
            else:
                mask_value = conf.IS_FALSE

            threshold.append(value)
            mask.append(mask_value)

        data = self.metadata['threshold']
        data.append(tuple(filter(None, threshold)))

        text = ' '.join(x.lower() for x in parse_result)
        text = text.replace('\n', ' ')

        return text, ''.join(mask)

    def _is_tag(self, array, coordinates):
        ((x1, y1), (x2, _)) = coordinates
        array_slice = array[y1 - conf.TAG_OFFSET][x1:x2]

        counter = int()
        for pixel in array_slice:
            if in_a_range(pixel):
                counter += 1

        value = 100 * counter / len(array_slice)
        return value >= conf.THRES_HOLD_TAG, int(value)


