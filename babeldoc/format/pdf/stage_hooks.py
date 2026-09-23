"""Extension points for callers that drive BabelDOC's PDF pipeline.

Hooks, all off by default so upstream behaviour is unchanged:

* ``TranslationConfig(il_translator_factory=...)`` replaces the paragraph translation stage.
  The factory receives ``(translate_engine, translation_config)`` and returns an object with
  ``translate(docs)``. It should report progress under ``ILTranslator.stage_name`` so the
  existing stage weight applies.
* ``TranslationConfig(extra_il_stages={hook: [stage, ...]})`` inserts IL stages at a named
  point. Each stage declares ``stage_name`` and ``stage_weight`` (registered with the progress
  monitor) and implements ``process(docs, mupdf_doc)``, returning the document or ``None`` to
  keep it.
* ``TranslationConfig(on_part_finished=...)`` is called after each split part (see
  ``PartFinishedCallback``). Each part's config carries ``source_page_offset`` so layout models
  can map part-local ``page.page_number`` back to the original document.
"""

from __future__ import annotations

from collections.abc import Callable
from collections.abc import Mapping
from collections.abc import Sequence
from typing import TYPE_CHECKING
from typing import Any
from typing import Protocol

if TYPE_CHECKING:
    from pymupdf import Document

    from babeldoc.format.pdf.document_il import il_version_1

# After LayoutParser, before TableParser/ParagraphFinder: characters can still be added
# (e.g. a synthetic OCR text layer) and will be grouped into paragraphs normally.
AFTER_LAYOUT = "after_layout"

HOOK_POINTS = (AFTER_LAYOUT,)


class ILStage(Protocol):
    stage_name: str
    stage_weight: float

    def process(
        self, docs: il_version_1.Document, mupdf_doc: Document
    ) -> il_version_1.Document | None: ...


class ILTranslatorLike(Protocol):
    def translate(self, docs: il_version_1.Document) -> None: ...


ILTranslatorFactory = Callable[[Any, Any], ILTranslatorLike]

# (part_index, part TranslateResult, first_page, last_page) with 0-based pages of the original
# document. Called synchronously after a split part is written and before its working dir is
# cleaned, so callers can publish per-part previews.
PartFinishedCallback = Callable[[int, Any, int, int], None]


def validate_extra_il_stages(
    extra_il_stages: Mapping[str, Sequence[ILStage]] | None,
) -> dict[str, list[ILStage]]:
    stages: dict[str, list[ILStage]] = {}
    for hook, items in (extra_il_stages or {}).items():
        if hook not in HOOK_POINTS:
            raise ValueError(
                f"Unknown IL stage hook {hook!r}; expected one of {HOOK_POINTS}"
            )
        for stage in items:
            name = getattr(stage, "stage_name", None)
            weight = getattr(stage, "stage_weight", None)
            if not isinstance(name, str) or not name:
                raise ValueError(f"IL stage {stage!r} must declare stage_name")
            if not isinstance(weight, int | float) or weight < 0:
                raise ValueError(
                    f"IL stage {name!r} must declare a non-negative stage_weight"
                )
            if not callable(getattr(stage, "process", None)):
                raise ValueError(f"IL stage {name!r} must implement process()")
        stages[hook] = list(items)
    names = [stage.stage_name for items in stages.values() for stage in items]
    if len(names) != len(set(names)):
        raise ValueError(f"Duplicate IL stage names: {names}")
    return stages


def run_extra_il_stages(
    hook: str,
    docs: il_version_1.Document,
    mupdf_doc: Document,
    translation_config,
) -> il_version_1.Document:
    for stage in translation_config.extra_il_stages.get(hook, []):
        translation_config.raise_if_cancelled()
        result = stage.process(docs, mupdf_doc)
        if result is not None:
            docs = result
    return docs
