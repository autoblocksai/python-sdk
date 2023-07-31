class AutoblocksException(Exception):
    pass


class NoReplayInProgressException(AutoblocksException):
    pass


class NoTraceIdForReplayException(AutoblocksException):
    pass
