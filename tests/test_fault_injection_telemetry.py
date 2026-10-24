import unittest
from fault_injection import (
    FaultInjectionEngine,
    FaultRule,
    FaultType,
    InjectionTiming,
    InjectedFaultException,
    TelemetryCollector,
)


class TestFaultInjectionTelemetry(unittest.TestCase):
    def setUp(self):
        self.telemetry = TelemetryCollector()
        self.engine = FaultInjectionEngine(telemetry_collector=self.telemetry)

    def test_baseline_operation_telemetry(self):
        """Verify telemetry captures standard successful execution without faults."""
        def sample_add(a, b):
            return a + b

        res = self.engine.execute("add_op", sample_add, 3, 4)
        self.assertEqual(res, 7)

        events = self.telemetry.get_events(operation="add_op")
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].event_type, "OPERATION_START")
        self.assertEqual(events[1].event_type, "OPERATION_SUCCESS")
        self.assertIsNone(events[1].error_type)

    def test_deterministic_fault_injection_matrix(self):
        """Verify a matrix of deterministic fault injection types and corresponding error telemetry."""
        class CustomTestError(Exception):
            pass

        matrix_cases = [
            {
                "name": "exception_fault",
                "fault_type": FaultType.EXCEPTION,
                "params": {"exception_cls": CustomTestError, "message": "Custom DB Failure"},
                "expected_error": CustomTestError,
                "expected_msg": "Custom DB Failure",
            },
            {
                "name": "resource_exhaustion_fault",
                "fault_type": FaultType.RESOURCE_EXHAUSTION,
                "params": {"resource": "NETWORK_BANDWIDTH"},
                "expected_error": InjectedFaultException,
                "expected_msg": "Resource exhausted: NETWORK_BANDWIDTH",
            },
        ]

        for case in matrix_cases:
            with self.subTest(case=case["name"]):
                self.telemetry.clear()
                self.engine.clear_rules()

                rule = FaultRule(
                    rule_id=f"rule_{case['name']}",
                    target_operation="matrix_op",
                    fault_type=case["fault_type"],
                    parameters=case["params"],
                )
                self.engine.add_rule(rule)

                with self.assertRaises(case["expected_error"]) as ctx:
                    self.engine.execute("matrix_op", lambda: "ok")

                self.assertIn(case["expected_msg"], str(ctx.exception))

                # Verify telemetry records
                fault_events = self.telemetry.get_events(operation="matrix_op", event_type="FAULT_INJECTED")
                error_events = self.telemetry.get_events(operation="matrix_op", event_type="OPERATION_ERROR")

                self.assertEqual(len(fault_events), 1)
                self.assertEqual(fault_events[0].fault_applied, case["fault_type"].value)
                self.assertEqual(len(error_events), 1)
                self.assertEqual(error_events[0].error_type, case["expected_error"].__name__)
                self.assertIn(case["expected_msg"], error_events[0].error_message)

    def test_after_timing_data_corruption_and_max_triggers(self):
        """Verify post-execution fault injection (corruption) and deterministic trigger budget limits."""
        rule = FaultRule(
            rule_id="corrupt_after",
            target_operation="fetch_data",
            fault_type=FaultType.CORRUPTION,
            timing=InjectionTiming.AFTER,
            parameters={"corruptor": lambda data: {**data, "corrupted": True}},
            max_triggers=1,
        )
        self.engine.add_rule(rule)

        # First execution should be corrupted
        res1 = self.engine.execute("fetch_data", lambda: {"data": 123})
        self.assertTrue(res1.get("corrupted"))

        # Second execution should exceed max_triggers and not be corrupted
        res2 = self.engine.execute("fetch_data", lambda: {"data": 123})
        self.assertNotIn("corrupted", res2)

        fault_events = self.telemetry.get_events(operation="fetch_data", event_type="FAULT_INJECTED")
        self.assertEqual(len(fault_events), 1)

    def test_latency_fault_injection(self):
        """Verify latency fault injection completes execution and logs fault telemetry."""
        rule = FaultRule(
            rule_id="latency_rule",
            target_operation="timed_op",
            fault_type=FaultType.LATENCY,
            timing=InjectionTiming.BEFORE,
            parameters={"delay_seconds": 0.005},
        )
        self.engine.add_rule(rule)

        result = self.engine.execute("timed_op", lambda: "completed")
        self.assertEqual(result, "completed")

        fault_events = self.telemetry.get_events(operation="timed_op", event_type="FAULT_INJECTED")
        success_events = self.telemetry.get_events(operation="timed_op", event_type="OPERATION_SUCCESS")
        self.assertEqual(len(fault_events), 1)
        self.assertEqual(len(success_events), 1)


if __name__ == "__main__":
    unittest.main()
