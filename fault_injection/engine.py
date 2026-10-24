import enum
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


class FaultType(str, enum.Enum):
    EXCEPTION = "EXCEPTION"
    LATENCY = "LATENCY"
    CORRUPTION = "CORRUPTION"
    RESOURCE_EXHAUSTION = "RESOURCE_EXHAUSTION"


class InjectionTiming(str, enum.Enum):
    BEFORE = "BEFORE"
    AFTER = "AFTER"


@dataclass
class FaultRule:
    rule_id: str
    target_operation: str
    fault_type: FaultType
    timing: InjectionTiming = InjectionTiming.BEFORE
    parameters: Dict[str, Any] = field(default_factory=dict)
    probability: float = 1.0
    enabled: bool = True
    trigger_count: int = 0
    max_triggers: Optional[int] = None

    def should_trigger(self, op_name: str, step_index: int) -> bool:
        if not self.enabled:
            return False
        if self.target_operation != "*" and self.target_operation != op_name:
            return False
        if self.max_triggers is not None and self.trigger_count >= self.max_triggers:
            return False
        return True


@dataclass
class TelemetryEvent:
    event_id: str
    timestamp: float
    operation: str
    event_type: str
    fault_applied: Optional[str] = None
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class TelemetryCollector:
    def __init__(self):
        self.events: List[TelemetryEvent] = []

    def record(self, event: TelemetryEvent) -> None:
        self.events.append(event)

    def get_events(self, operation: Optional[str] = None, event_type: Optional[str] = None) -> List[TelemetryEvent]:
        result = self.events
        if operation is not None:
            result = [e for e in result if e.operation == operation]
        if event_type is not None:
            result = [e for e in result if e.event_type == event_type]
        return list(result)

    def clear(self) -> None:
        self.events.clear()


class InjectedFaultException(Exception):
    pass


class FaultInjectionEngine:
    def __init__(self, telemetry_collector: Optional[TelemetryCollector] = None):
        self.rules: List[FaultRule] = []
        self.telemetry = telemetry_collector if telemetry_collector is not None else TelemetryCollector()
        self._step_counter = 0

    def add_rule(self, rule: FaultRule) -> None:
        self.rules.append(rule)

    def clear_rules(self) -> None:
        self.rules.clear()

    def _apply_fault(self, rule: FaultRule, op_name: str, payload: Any = None) -> Any:
        rule.trigger_count += 1
        self.telemetry.record(
            TelemetryEvent(
                event_id=str(uuid.uuid4()),
                timestamp=time.time(),
                operation=op_name,
                event_type="FAULT_INJECTED",
                fault_applied=rule.fault_type.value,
                metadata={"rule_id": rule.rule_id, "params": rule.parameters}
            )
        )

        if rule.fault_type == FaultType.EXCEPTION:
            exc_class = rule.parameters.get("exception_cls", InjectedFaultException)
            exc_msg = rule.parameters.get("message", f"Fault injected on {op_name}")
            raise exc_class(exc_msg)
        elif rule.fault_type == FaultType.LATENCY:
            delay = rule.parameters.get("delay_seconds", 0.0)
            time.sleep(delay)
            return payload
        elif rule.fault_type == FaultType.CORRUPTION:
            corruptor = rule.parameters.get("corruptor", lambda x: None)
            return corruptor(payload)
        elif rule.fault_type == FaultType.RESOURCE_EXHAUSTION:
            resource = rule.parameters.get("resource", "DISK_SPACE")
            raise InjectedFaultException(f"Resource exhausted: {resource}")
        return payload

    def execute(self, op_name: str, target_fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        self._step_counter += 1
        step_idx = self._step_counter

        self.telemetry.record(
            TelemetryEvent(
                event_id=str(uuid.uuid4()),
                timestamp=time.time(),
                operation=op_name,
                event_type="OPERATION_START",
            )
        )

        # Check BEFORE rules
        for rule in self.rules:
            if rule.timing == InjectionTiming.BEFORE and rule.should_trigger(op_name, step_idx):
                try:
                    self._apply_fault(rule, op_name)
                except Exception as exc:
                    self.telemetry.record(
                        TelemetryEvent(
                            event_id=str(uuid.uuid4()),
                            timestamp=time.time(),
                            operation=op_name,
                            event_type="OPERATION_ERROR",
                            fault_applied=rule.fault_type.value,
                            error_type=type(exc).__name__,
                            error_message=str(exc),
                        )
                    )
                    raise

        # Execute operation
        try:
            result = target_fn(*args, **kwargs)
        except Exception as exc:
            self.telemetry.record(
                TelemetryEvent(
                    event_id=str(uuid.uuid4()),
                    timestamp=time.time(),
                    operation=op_name,
                    event_type="OPERATION_ERROR",
                    error_type=type(exc).__name__,
                    error_message=str(exc),
                )
            )
            raise

        # Check AFTER rules (e.g. data corruption or post-execution latency)
        for rule in self.rules:
            if rule.timing == InjectionTiming.AFTER and rule.should_trigger(op_name, step_idx):
                try:
                    result = self._apply_fault(rule, op_name, result)
                except Exception as exc:
                    self.telemetry.record(
                        TelemetryEvent(
                            event_id=str(uuid.uuid4()),
                            timestamp=time.time(),
                            operation=op_name,
                            event_type="OPERATION_ERROR",
                            fault_applied=rule.fault_type.value,
                            error_type=type(exc).__name__,
                            error_message=str(exc),
                        )
                    )
                    raise

        self.telemetry.record(
            TelemetryEvent(
                event_id=str(uuid.uuid4()),
                timestamp=time.time(),
                operation=op_name,
                event_type="OPERATION_SUCCESS",
            )
        )
        return result
