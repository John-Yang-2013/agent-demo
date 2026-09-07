"""Structured-output schemas enforced through tool calls.

``with_structured_output`` does not compose with a tool-calling ReAct agent
(it forces *every* response into one schema). Instead we invert the pattern:
the agent must submit calculation/conversion results through the
``submit_calculation`` tool, whose arguments ARE the pydantic schema —
invalid submissions bounce back as tool errors the model can self-correct.
"""

from typing import Literal

from pydantic import BaseModel, Field


class CalculationResult(BaseModel):
    """Machine-readable result for arithmetic / unit-conversion questions."""

    expression: str = Field(
        description="The expression or conversion performed, e.g. '2 ** 10' or '100 mph -> kph'"
    )
    value: float = Field(description="The numeric result obtained from the tools")
    unit: str | None = Field(
        default=None, description="Unit of the result, if any (e.g. 'kph', 'kg')"
    )
    category: Literal["calculation", "conversion"] = Field(
        default="calculation", description="Whether this was arithmetic or unit conversion"
    )
    explanation: str = Field(
        default="", description="One short sentence explaining the result to the user"
    )


__all__ = ["CalculationResult"]
