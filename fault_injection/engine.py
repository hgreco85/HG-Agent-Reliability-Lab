import enum
import time
from typing import Any, Callable, Dict, List, Optional, Type


class FaultType(enum.Enum):
    EXCEPTION = "exception"
    LATENCY = "latency"
    CORRUPT_RESULT = "corrupt_result"
    TIMEOUT = "timeout"


class FaultDefinition:
    def __init__(
        self,
        target_operation: str,
        fault_type: FaultType,
        error_class: Optional[Type[BaseException]] = None,
        error_message: str = "Injected fault",
        delay_seconds: float = 0.0,
        corrupt_value: Any = None,
        trigger_count: int = 1,
    ):
        self.target_operation = target_operation
        self.fault_type = fault_type
        self.error_class = error_class or RuntimeError
        self.error_message = error_message
        self.delay_seconds = delay_seconds
        self.corrupt_value = corrupt_value
        self.trigger_count = trigger_count
        self.executed_count = 0

    def should_trigger(self) -> bool:
        return self.executed_count < self.trigger_count

    def record_trigger(self) -> None:
        self.executed_count += 1


class TelemetrySink:
    def __init__(self):
        self.events: List[Dict[str, Any]] = []

    def emit(self, event_type: str, operation: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        payload = {
            "event_type": event_type,
            "operation": operation,
            "timestamp": time.time(),
            "metadata": metadata or {},
        }
        self.events.append(payload)

    def get_events_for_operation(self, operation: str) -> List[Dict[str, Any]]:
        return [evt for evt in self.events if evt["operation"] == operation]

    def get_events_by_type(self, event_type: str) -> List[Dict[str, Any]]:
        return [evt for evt in self.events if evt["event_type"] == event_type]

    def clear(self) -> None:
        self.events.clear()


class FaultInjector:
    def __init__(self, telemetry: Optional[TelemetrySink] = None):
        self.faults: Dict[str, List[FaultDefinition]] = {}
        self.telemetry = telemetry or TelemetrySink()

    def register_fault(self, fault: FaultDefinition) -> None:
        if fault.target_operation not in self.faults:
            self.faults[fault.target_operation] = []
        self.faults[fault.target_operation].append(fault)

    def execute(self, operation_name: str, callable_fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        matched_fault = None
        if operation_name in self.faults:
            for fault in self.faults[operation_name]:
                if fault.should_trigger():
                    matched_fault = fault
                    break

        if matched_fault:
            matched_fault.record_trigger()
            self.telemetry.emit(
                event_type="fault_injected",
                operation=operation_name,
                metadata={
                    "fault_type": matched_fault.fault_type.value,
                    "error_class": matched_fault.error_class.__name__,
                },
            )

            if matched_fault.fault_type == FaultType.LATENCY:
                time.sleep(matched_fault.delay_seconds)
            elif matched_fault.fault_type == FaultType.EXCEPTION:
                raise matched_fault.error_class(matched_fault.error_message)
            elif matched_fault.fault_type == FaultType.TIMEOUT:
                raise TimeoutError(matched_fault.error_message)
            elif matched_fault.fault_type == FaultType.CORRUPT_RESULT:
                return matched_fault.corrupt_value

        try:
            result = callable_fn(*args, **kwargs)
            self.telemetry.emit(
                event_type="operation_success",
                operation=operation_name,
                metadata={"result_type": type(result).__name__},
            )
            return result
        except Exception as ex:
            self.telemetry.emit(
                event_type="operation_failure",
                operation=operation_name,
                metadata={
                    "error_class": ex.__class__.__name__,
                    "error_message": str(ex),
                },
            )
            raise
