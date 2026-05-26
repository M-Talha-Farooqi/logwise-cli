from __future__ import annotations

import dataclasses
import json

from logwise.analysis.analyzer import Analysis


def render_json(analysis: Analysis) -> str:
    """Serialize the full analysis to pretty JSON. EndpointStat dataclasses convert
    cleanly via asdict, so downstream tools get structured data, not scraped text."""
    return json.dumps(dataclasses.asdict(analysis), indent=2, default=str)
