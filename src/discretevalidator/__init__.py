"""DiscreteValidator: MCP-facing wrapper over DiscreteStructureTool."""

from discretevalidator.core import validate_discrete_structure
from discretevalidator.migration_report import build_validation_report

__all__ = ["validate_discrete_structure", "build_validation_report"]
__version__ = "0.1.0"
