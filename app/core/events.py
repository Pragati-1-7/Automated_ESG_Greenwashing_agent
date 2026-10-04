"""Agent event stream. Every agent step emits an AgentEvent; the API replays and
streams them over SSE, and the report writer turns them into the audit trail."""

from __future__ import annotations

import asyncio
import contextvars
from datetime import datetime, timezone
from typing import Any, Optional

from app.core.models import AgentEvent


class EventSink:
    def __init__(self) -> None:
        self.events: list[AgentEvent] = []
        self._subscribers: list[asyncio.Queue] = []
        self.closed = False

    def emit(self, agent: str, type_: str, message: str, claim_id: Optional[str] = None,
             data: Optional[dict[str, Any]] = None) -> AgentEvent:
        ev = AgentEvent(seq=len(self.events) + 1, ts=datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
                        agent=agent, type=type_, claim_id=claim_id, message=message, data=data)
        self.events.append(ev)
        for q in list(self._subscribers):
            q.put_nowait(ev)
        return ev

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        if q in self._subscribers:
            self._subscribers.remove(q)

    def close(self) -> None:
        self.closed = True
        for q in list(self._subscribers):
            q.put_nowait(None)


_current: contextvars.ContextVar[EventSink | None] = contextvars.ContextVar("event_sink", default=None)


def use_sink(sink: EventSink) -> contextvars.Token:
    return _current.set(sink)


def emit(agent: str, type_: str, message: str, claim_id: Optional[str] = None,
         data: Optional[dict[str, Any]] = None) -> None:
    sink = _current.get()
    if sink is not None:
        sink.emit(agent, type_, message, claim_id, data)
