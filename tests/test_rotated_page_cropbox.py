"""academic-reader fork: /Rotate pages keep the unrotated frame for the IL cropbox."""

import pytest

from babeldoc.format.pdf.new_parser.base_operations import wrap_page_base_operation
from babeldoc.format.pdf.new_parser.prepared_page import PreparedPdfPage
from babeldoc.format.pdf.new_parser.prepared_page import il_page_cropbox
from babeldoc.format.pdf.new_parser.prepared_page import page_base_operation_cropbox


def _page(rotate, cropbox=(0.0, 0.0, 595.0, 842.0)):
    return PreparedPdfPage(
        pageno=0,
        cropbox=cropbox,
        rotate=rotate,
        resource_tree=None,
        content_streams=(),
        content_bytes=b"",
    )


@pytest.mark.parametrize("rotate", [0, 90, 180, 270])
def test_cropbox_is_the_unrotated_box_for_every_rotation(rotate):
    page = _page(rotate)
    # Characters come out of the native parser unrotated; a swapped box such as
    # (0, 595, 842, 0) shifted every element of a /Rotate 90 page by -595pt.
    assert il_page_cropbox(page) == (0.0, 0.0, 595.0, 842.0)
    assert page_base_operation_cropbox(page) == (0.0, 0.0, 595.0, 842.0)


def test_base_operations_are_only_offset_by_the_real_origin():
    page = _page(90, cropbox=(20.0, 30.0, 632.0, 872.0))
    wrapped = wrap_page_base_operation("BT ET", page_base_operation_cropbox(page))
    assert wrapped.endswith("1.000000 0.000000 0.000000 1.000000 -20.000000 -30.000000 cm")
