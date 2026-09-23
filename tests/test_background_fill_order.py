"""academic-reader fork: highlight fills must stay underneath re-typeset text."""

from babeldoc.format.pdf.document_il import il_version_1 as il
from babeldoc.format.pdf.document_il.midend.background_fill_order import (
    lower_background_fills,
)


def _box(x, y, x2, y2):
    return il.Box(x=x, y=y, x2=x2, y2=y2)


def _curve(box, order, *, fill=True, stroke=False, xobj=0):
    return il.PdfCurve(
        box=box,
        render_order=order,
        fill_background=fill,
        stroke_path=stroke,
        xobj_id=xobj,
    )


def test_fills_drawn_after_paragraph_start_move_beneath_its_text():
    paragraph = il.PdfParagraph(
        box=_box(50, 660, 560, 710), render_order=58, xobj_id=0, unicode="caption"
    )
    highlight = _curve(_box(244, 693, 312, 708), 95)  # inside, originally mid-paragraph
    row_shade = _curve(_box(40, 650, 570, 715), 120)  # larger than the paragraph
    earlier = _curve(_box(244, 693, 312, 708), 10)  # already underneath
    outline = _curve(_box(244, 693, 312, 708), 96, stroke=True)
    other_xobj = _curve(_box(244, 693, 312, 708), 97, xobj=3)
    elsewhere = _curve(_box(10, 10, 40, 40), 98)
    page = il.Page(
        pdf_paragraph=[paragraph],
        pdf_curve=[highlight, row_shade, earlier, outline, other_xobj, elsewhere],
    )

    assert lower_background_fills(page) == 2

    assert highlight.render_order == row_shade.render_order == 57.5
    assert [c.render_order for c in (earlier, outline, other_xobj, elsewhere)] == [
        10,
        96,
        97,
        98,
    ]
