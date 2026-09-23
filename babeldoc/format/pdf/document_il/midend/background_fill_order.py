"""Keep text highlight fills underneath re-typeset paragraphs.

Typesetting draws every character of a paragraph at the paragraph's render_order (the order of
its first original character). A background fill that originally sat between the paragraph's
characters (e.g. colored highlights behind words in a caption, a shaded table row) keeps its
later render_order and is therefore painted on top of the new text, hiding it. Such fills are
moved to paragraph.render_order - 0.5: after everything that preceded the paragraph and before
its characters (all at paragraph.render_order after typesetting). render_order is only a sort
key in PDFCreater; PdfCurve has __slots__, so a sub_render_order cannot be attached instead.
"""

from __future__ import annotations

from babeldoc.format.pdf.document_il import il_version_1

MIN_OVERLAP = 0.5


def _area(box: il_version_1.Box) -> float:
    return max(0.0, box.x2 - box.x) * max(0.0, box.y2 - box.y)


def _overlap_ratio(a: il_version_1.Box, b: il_version_1.Box) -> float:
    width = min(a.x2, b.x2) - max(a.x, b.x)
    height = min(a.y2, b.y2) - max(a.y, b.y)
    if width <= 0 or height <= 0:
        return 0.0
    smaller = min(_area(a), _area(b))
    return width * height / smaller if smaller > 0 else 0.0


def lower_background_fills(page: il_version_1.Page) -> int:
    """Returns how many fills were moved beneath text on this page."""
    paragraphs = [
        paragraph
        for paragraph in page.pdf_paragraph
        if paragraph.box is not None and paragraph.render_order is not None
    ]
    moved = 0
    for curve in page.pdf_curve:
        if (
            not curve.fill_background
            or curve.stroke_path
            or curve.box is None
            or curve.render_order is None
        ):
            continue
        targets = [
            paragraph.render_order
            for paragraph in paragraphs
            if paragraph.xobj_id == curve.xobj_id
            and curve.render_order > paragraph.render_order
            and _overlap_ratio(curve.box, paragraph.box) >= MIN_OVERLAP
        ]
        if targets:
            curve.render_order = min(targets) - 0.5
            moved += 1
    return moved
