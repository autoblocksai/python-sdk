from dataclasses import dataclass
from typing import Dict
from typing import List
from typing import Optional


@dataclass
class Event:
    id: str
    trace_id: str
    message: str
    timestamp: str
    properties: Dict


@dataclass
class Trace:
    id: str
    events: List[Event]


@dataclass
class View:
    id: str
    name: str


@dataclass
class GetViewsResponse:
    views: List[View]


@dataclass
class GetTracesFromViewResponse:
    next_cursor: Optional[str]
    traces: List[Trace]
