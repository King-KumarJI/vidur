"""
VIDUR Schemas
Submodule: Common
Purpose: Response shapes shared across every route in the API Layer
(the uniform error envelope written by
`app.api.v1.error_handlers`).
"""

from pydantic import BaseModel, ConfigDict, Field


class ErrorResponse(BaseModel):
    """Uniform error envelope returned by every registered exception
    handler in `app.api.v1.error_handlers`."""

    model_config = ConfigDict(extra="forbid")

    error: str = Field(..., description="The raised exception's class name.")
    message: str = Field(..., description="Human-readable error detail.")
