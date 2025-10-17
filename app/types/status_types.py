from enum import Enum


class ScriptStatus(str, Enum):
    NEW = 'new'
    PREPARED = 'prepared'
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    FAILED = 'failed'


class AssetStatus(str, Enum):
    MISSING = 'missing'
    PRESENT = 'present'
    OK = 'ok'
    PARTIAL = 'partial'
    PENDING = 'pending'
    DONE = 'done'


__all__ = ['ScriptStatus', 'AssetStatus']
