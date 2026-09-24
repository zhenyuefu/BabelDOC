"""academic-reader fork: OCR workaround for selected pages and pass-through of empty parts."""

from types import SimpleNamespace

from babeldoc.format.pdf.translation_config import TranslationConfig


def _config(**kwargs):
    # Bypass __init__ (translator, files, fonts); only the page-selection logic is under test.
    config = TranslationConfig.__new__(TranslationConfig)
    config.ocr_workaround = kwargs.get("ocr_workaround", False)
    config.ocr_workaround_pages = frozenset(kwargs.get("pages", ()))
    config.source_page_offset = kwargs.get("offset", 0)
    return config


def _page(number):
    return SimpleNamespace(page_number=number)


def test_selected_pages_use_whole_document_numbers_inside_split_parts():
    config = _config(pages={3})
    assert config.is_ocr_page(_page(3)) and not config.is_ocr_page(_page(2))
    part = _config(pages={3}, offset=2)  # a split part starting at page index 2
    assert part.is_ocr_page(_page(1)) and not part.is_ocr_page(_page(3))


def test_global_switch_still_covers_every_page():
    config = _config(ocr_workaround=True)
    assert config.is_ocr_page(_page(0)) and config.is_ocr_page(None)
    assert not _config().is_ocr_page(None)
