from io import BytesIO

import numpy as np
from PIL import Image

from app.frapper import ImageFrapper
from frapper_core import FrapperConfig as conf

PRE_REDESIGN_DATE = '2020-01-01T00:00:00'  # white background → PIXEL_SUM_V1
HIGHLIGHT = (250, 250, 220)  # inside R_RANGE / G_RANGE / B_RANGE


def _two_block_screenshot():
    # Two 200px white phrase blocks between grey separator stripes.
    image = Image.new('RGB', (conf.STANDARD_WIDTH, 430), (255, 255, 255))
    pixels = image.load()
    for y in [*range(0, 10), *range(210, 220), *range(420, 430)]:
        for x in range(conf.STANDARD_WIDTH):
            pixels[x, y] = (200, 200, 200)
    buffer = BytesIO()
    image.save(buffer, format='PNG')
    return buffer.getvalue()


def test_split_records_keep_their_own_block_metadata():
    records = ImageFrapper.split_image_from_bin_data(
        _two_block_screenshot(),
        meta_id=1,
        message_id=5,
        message_date=PRE_REDESIGN_DATE,
    )

    assert len(records) == 2
    first, second = (record.metadata for record in records)
    assert first is not second
    assert (first['file_index'], second['file_index']) == (1, 2)
    assert first['y1_y2'] != second['y1_y2']
    assert first['threshold'] is not second['threshold']


def test_is_tag_with_zero_width_box_is_not_a_tag():
    array = np.full((20, 50, 3), 255, dtype=np.uint8)

    assert ImageFrapper._is_tag(None, array, ((10, 10), (10, 15))) == (False, 0)


def test_is_tag_near_top_edge_samples_first_row():
    array = np.full((40, 50, 3), 255, dtype=np.uint8)
    array[0, :] = HIGHLIGHT

    is_tag, _ = ImageFrapper._is_tag(None, array, ((5, 2), (45, 12)))

    assert is_tag
