"""Marker for the academic-reader fork of BabelDOC.

Consumers assert FORK_NAME and a minimum FORK_REVISION at startup instead of silently running
against an upstream build that lacks the stage hooks (babeldoc.format.pdf.stage_hooks).
Bump FORK_REVISION whenever the fork's public extension surface changes.
"""

FORK_NAME = "academic-reader"
FORK_REVISION = 3  # r3: rotated pages keep the unrotated IL cropbox
UPSTREAM_VERSION = "0.6.4"
