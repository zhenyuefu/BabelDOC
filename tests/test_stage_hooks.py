"""academic-reader fork: stage injection points in the PDF pipeline."""

from pathlib import Path

import pymupdf
import pytest
from babeldoc.docvision.base_doclayout import DocLayoutModel
from babeldoc.docvision.base_doclayout import YoloResult
from babeldoc.format.pdf.document_il.midend.il_translator import ILTranslator
from babeldoc.format.pdf.document_il.midend.layout_parser import LayoutParser
from babeldoc.format.pdf.high_level import get_translation_stage
from babeldoc.format.pdf.high_level import translate
from babeldoc.format.pdf.stage_hooks import AFTER_LAYOUT
from babeldoc.format.pdf.translation_config import TranslationConfig
from babeldoc.format.pdf.translation_config import WatermarkOutputMode
from babeldoc.translator.translator import BaseTranslator


class NoLayout(DocLayoutModel):
    @property
    def stride(self) -> int:
        return 32

    def handle_document(self, pages, mupdf_doc, translate_config, save_debug_image):
        for page in pages:
            yield page, YoloResult(names={}, boxes=[])


class OfflineTranslator(BaseTranslator):
    name = "offline-test"

    def __init__(self):
        super().__init__("en", "zh", ignore_cache=True)
        self.model = "offline"

    def do_translate(self, text, rate_limit_params=None):
        return text

    def do_llm_translate(self, text, rate_limit_params=None):
        raise NotImplementedError


class RecordingStage:
    stage_name = "Recording Stage"
    stage_weight = 1.5

    def __init__(self, calls):
        self.calls = calls

    def process(self, docs, mupdf_doc):
        # Layouts from LayoutParser (incl. its fallback lines) must already exist.
        self.calls.append(
            ("stage", len(docs.page), all(p.page_layout is not None for p in docs.page))
        )


class RecordingTranslator:
    def __init__(self, calls, engine, config):
        self.calls, self.engine, self.config = calls, engine, config

    def translate(self, docs):
        with self.config.progress_monitor.stage_start(
            ILTranslator.stage_name, 1
        ) as pbar:
            self.calls.append(("translate", type(self.engine).__name__))
            pbar.advance(1)


def _config(tmp_path: Path, **kwargs) -> TranslationConfig:
    source = tmp_path / "in.pdf"
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((72, 100), "Hello layout hooks, this is a sentence.", fontsize=12)
    doc.save(source)
    return TranslationConfig(
        translator=OfflineTranslator(),
        input_file=source,
        lang_in="en",
        lang_out="zh",
        doc_layout_model=NoLayout(),
        output_dir=tmp_path / "out",
        working_dir=tmp_path / "work",
        use_rich_pbar=False,
        auto_extract_glossary=False,
        skip_scanned_detection=True,
        watermark_output_mode=WatermarkOutputMode.NoWatermark,
        **kwargs,
    )


def test_defaults_keep_upstream_stage_table(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert config.il_translator_factory is None
    assert config.extra_il_stages == {}
    names = [name for name, _ in get_translation_stage(config)]
    assert "Recording Stage" not in names


def test_extra_stage_is_registered_right_after_layout(tmp_path: Path) -> None:
    config = _config(tmp_path, extra_il_stages={AFTER_LAYOUT: [RecordingStage([])]})
    stages = get_translation_stage(config)
    names = [name for name, _ in stages]
    assert names[names.index(LayoutParser.stage_name) + 1] == "Recording Stage"
    assert dict(stages)["Recording Stage"] == 1.5


@pytest.mark.parametrize(
    ("hooks", "message"),
    [
        ({"before_everything": []}, "Unknown IL stage hook"),
        ({AFTER_LAYOUT: [object()]}, "must declare stage_name"),
        ({AFTER_LAYOUT: [RecordingStage([]), RecordingStage([])]}, "Duplicate"),
    ],
)
def test_invalid_hooks_fail_at_config_time(tmp_path: Path, hooks, message) -> None:
    with pytest.raises(ValueError, match=message):
        _config(tmp_path, extra_il_stages=hooks)


def test_pipeline_runs_injected_stage_and_translator_in_order(tmp_path: Path) -> None:
    calls: list = []
    config = _config(
        tmp_path,
        extra_il_stages={AFTER_LAYOUT: [RecordingStage(calls)]},
        il_translator_factory=lambda engine, cfg: RecordingTranslator(
            calls, engine, cfg
        ),
    )

    result = translate(config)

    assert calls == [("stage", 1, True), ("translate", "OfflineTranslator")]
    assert Path(result.mono_pdf_path).exists()
    assert Path(result.dual_pdf_path).exists()
