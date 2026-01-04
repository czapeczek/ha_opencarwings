from enum import Enum

class SourceType(Enum):
    GPS = "gps"

# keep compatibility for imports that expect attributes at module level
GPS = SourceType.GPS