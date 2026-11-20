import unittest
from fault_injection.engine import (
    FaultInjector,
    FaultDefinition,
    FaultType,
    TelemetrySink,
)


class TestFaultInjectionTelemetryMatrix(unittest.TestCase):
    def setUp(self):
        self.telemetry = TelemetrySink()
        self.injector = FaultInjector(telemetry=self.telemetry)

    def test_fault_matrix_exceptions_and_telemetry(self):
        # Matrix of test cases: operation, fault type, exception class, and expected message
        matrix = [
            ("db_query", FaultType.EXCEPTION, ConnectionResetError, "DB connection reset"),
            ("cache_get", FaultType.EXCEPTION, KeyError, "Cache key not found"),
            ("http_request", FaultType.TIMEOUT, TimeoutError, "Gateway timeout"),
        ]

        for op_name, fault_type, err_cls, err_msg in matrix:
            with self.subTest(operation=op_name, fault_type=fault_type):
                fault = FaultDefinition(
                    target_operation=op_name,
                    fault_type=fault_type,
                    error_class=err_cls,
                    error_message=err_msg,
                    trigger_count=1,
                )
                self.injector.register_fault(fault)

                def dummy_callable():
                    return "nominal_result"

                with self.assertRaises(err_cls) as ctx:
                    self.injector.execute(op_name, dummy_callable)
                self.assertIn(err_msg, str(ctx.exception))

                # Verify telemetry records fault_injected event
                fault_events = [
                    e for e in self.telemetry.get_events_for_operation(op_name)
                    if e["event_type"] == "fault_injected"
                ]
                self.assertEqual(len(fault_events), 1)
                self.assertEqual(fault_events[0]["metadata"]["fault_type"], fault_type.value)
                self.assertEqual(fault_events[0]["metadata"]["error_class"], err_cls.__name__)

    def test_corrupt_result_and_latency_fault_telemetry(self):
        # Test corrupt result fault
        corrupt_fault = FaultDefinition(
            target_operation="compute_hash",
            fault_type=FaultType.CORRUPT_RESULT,
            corrupt_value="corrupted_payload_data",
            trigger_count=1,
        )
        self.injector.register_fault(corrupt_fault)

        result = self.injector.execute("compute_hash", lambda: "valid_payload")
        self.assertEqual(result, "corrupted_payload_data")

        injected_events = self.telemetry.get_events_by_type("fault_injected")
        self.assertEqual(len(injected_events), 1)
        self.assertEqual(injected_events[0]["operation"], "compute_hash")
        self.assertEqual(injected_events[0]["metadata"]["fault_type"], FaultType.CORRUPT_RESULT.value)

        # Test latency fault followed by successful operation
        latency_fault = FaultDefinition(
            target_operation="quick_fetch",
            fault_type=FaultType.LATENCY,
            delay_seconds=0.01,
            trigger_count=1,
        )
        self.injector.register_fault(latency_fault)

        success_result = self.injector.execute("quick_fetch", lambda: 42)
        self.assertEqual(success_result, 42)

        op_events = self.telemetry.get_events_for_operation("quick_fetch")
        event_types = [e["event_type"] for e in op_events]
        self.assertIn("fault_injected", event_types)
        self.assertIn("operation_success", event_types)

    def test_deterministic_trigger_count_and_exhaustion(self):
        # Fault configured to trigger exactly twice
        fault = FaultDefinition(
            target_operation="transient_service",
            fault_type=FaultType.EXCEPTION,
            error_class=IOError,
            error_message="Transient disk I/O error",
            trigger_count=2,
        )
        self.injector.register_fault(fault)

        def worker():
            return "success_ok"

        # First trigger should fail
        with self.assertRaises(IOError):
            self.injector.execute("transient_service", worker)

        # Second trigger should fail
        with self.assertRaises(IOError):
            self.injector.execute("transient_service", worker)

        # Third invocation should succeed as fault limit is exhausted
        result = self.injector.execute("transient_service", worker)
        self.assertEqual(result, "success_ok")

        events = self.telemetry.get_events_for_operation("transient_service")
        injected = [e for e in events if e["event_type"] == "fault_injected"]
        successful = [e for e in events if e["event_type"] == "operation_success"]

        self.assertEqual(len(injected), 2)
        self.assertEqual(len(successful), 1)

    def test_native_operation_failure_telemetry(self):
        # Invocations without fault injector definition that fail naturally
        def buggy_operation():
            raise ValueError("Invalid parameter input")

        with self.assertRaises(ValueError):
            self.injector.execute("param_validator", buggy_operation)

        events = self.telemetry.get_events_for_operation("param_validator")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event_type"], "operation_failure")
        self.assertEqual(events[0]["metadata"]["error_class"], "ValueError")
        self.assertEqual(events[0]["metadata"]["error_message"], "Invalid parameter input")


if __name__ == "__main__":
    unittest.main()
