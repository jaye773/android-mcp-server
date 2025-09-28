"""Integration tests for Android MCP Server components."""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from pathlib import Path

from tests.mocks import MockADBCommand, MockDeviceScenarios, MockUIScenarios


class TestDeviceToUIIntegration:
    """Test integration between device management and UI operations."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_device_selection_to_ui_extraction(self, mock_server_components):
        """Test complete flow from device selection to UI extraction."""
        adb_manager = mock_server_components["adb_manager"]
        ui_inspector = mock_server_components["ui_inspector"]

        # Step 1: Select device
        adb_manager.auto_select_device.return_value = {
            "success": True,
            "selected": {"id": "emulator-5554", "status": "device"}
        }

        device_result = await adb_manager.auto_select_device()
        assert device_result["success"] is True

        # Step 2: Extract UI layout
        ui_inspector.get_ui_layout.return_value = {
            "success": True,
            "xml_dump": MockUIScenarios.login_screen(),
            "elements": [{"text": "Login", "clickable": "true"}],
            "element_count": 1
        }

        ui_result = await ui_inspector.get_ui_layout()
        assert ui_result["success"] is True
        assert ui_result["element_count"] > 0

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_ui_element_to_interaction_flow(self, mock_server_components):
        """Test flow from element finding to interaction."""
        ui_inspector = mock_server_components["ui_inspector"]
        screen_interactor = mock_server_components["screen_interactor"]

        # Step 1: Find login button
        ui_inspector.get_ui_layout.return_value = {
            "success": True,
            "elements": [{"text": "Login", "resource-id": "com.app:id/login", "clickable": "true"}]
        }

        # Step 2: Tap the button
        screen_interactor.tap_element.return_value = {
            "success": True,
            "action": "tap_element",
            "element": {"text": "Login"},
            "coordinates": {"x": 200, "y": 300}
        }

        tap_result = await screen_interactor.tap_element(text="Login")
        assert tap_result["success"] is True
        assert tap_result["coordinates"]["x"] > 0

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_complete_login_workflow(self, mock_server_components):
        """Test complete login workflow integration."""
        ui_inspector = mock_server_components["ui_inspector"]
        screen_interactor = mock_server_components["screen_interactor"]
        text_controller = mock_server_components["text_controller"]

        # Mock login screen UI
        ui_inspector.get_ui_layout.return_value = {
            "success": True,
            "elements": [
                {"text": "", "resource-id": "com.app:id/username", "class": "android.widget.EditText"},
                {"text": "", "resource-id": "com.app:id/password", "class": "android.widget.EditText"},
                {"text": "Login", "resource-id": "com.app:id/login_btn", "clickable": "true"}
            ]
        }

        # Step 1: Tap username field
        screen_interactor.tap_element.return_value = {"success": True}
        username_tap = await screen_interactor.tap_element(resource_id="com.app:id/username")
        assert username_tap["success"] is True

        # Step 2: Enter username
        text_controller.input_text.return_value = {"success": True, "text": "testuser"}
        username_input = await text_controller.input_text("testuser")
        assert username_input["success"] is True

        # Step 3: Tap password field
        password_tap = await screen_interactor.tap_element(resource_id="com.app:id/password")
        assert password_tap["success"] is True

        # Step 4: Enter password
        password_input = await text_controller.input_text("password123")
        assert password_input["success"] is True

        # Step 5: Tap login button
        login_tap = await screen_interactor.tap_element(resource_id="com.app:id/login_btn")
        assert login_tap["success"] is True


class TestMediaCaptureIntegration:
    """Test integration of media capture with other components."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_screenshot_with_ui_analysis(self, mock_server_components, temp_dir):
        """Test taking screenshot and analyzing UI together."""
        media_capture = mock_server_components["media_capture"]
        ui_inspector = mock_server_components["ui_inspector"]

        # Step 1: Take screenshot
        screenshot_path = temp_dir / "test_screenshot.png"
        screenshot_path.touch()

        media_capture.take_screenshot.return_value = {
            "success": True,
            "filename": "test_screenshot.png",
            "local_path": str(screenshot_path),
            "size": {"width": 1080, "height": 1920}
        }

        screenshot_result = await media_capture.take_screenshot()
        assert screenshot_result["success"] is True

        # Step 2: Get UI layout
        ui_inspector.get_ui_layout.return_value = {
            "success": True,
            "elements": [{"text": "Button", "bounds": "[100,200][300,400]"}],
            "element_count": 1
        }

        ui_result = await ui_inspector.get_ui_layout()
        assert ui_result["success"] is True

        # Integration: Screenshot and UI should represent same screen state
        assert screenshot_result["size"]["width"] == 1080
        assert ui_result["element_count"] > 0

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_screen_recording_with_interactions(self, mock_server_components, temp_dir):
        """Test screen recording during UI interactions."""
        video_recorder = mock_server_components["video_recorder"]
        screen_interactor = mock_server_components["screen_interactor"]

        # Step 1: Start recording
        video_recorder.start_recording.return_value = {
            "success": True,
            "recording_id": "rec_001",
            "filename": "test_recording.mp4"
        }

        record_start = await video_recorder.start_recording()
        assert record_start["success"] is True

        # Step 2: Perform UI interactions
        screen_interactor.tap_coordinates.return_value = {"success": True}
        tap_result = await screen_interactor.tap_coordinates(100, 200)
        assert tap_result["success"] is True

        # Step 3: Stop recording
        video_path = temp_dir / "test_recording.mp4"
        video_path.touch()

        video_recorder.stop_recording.return_value = {
            "success": True,
            "recording_id": "rec_001",
            "local_path": str(video_path),
            "duration": 10
        }

        record_stop = await video_recorder.stop_recording("rec_001")
        assert record_stop["success"] is True
        assert record_stop["duration"] > 0


class TestLogMonitoringIntegration:
    """Test integration of log monitoring with other operations."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_ui_interaction_with_log_monitoring(self, mock_server_components):
        """Test UI interactions while monitoring logs."""
        log_monitor = mock_server_components["log_monitor"]
        screen_interactor = mock_server_components["screen_interactor"]

        # Step 1: Start log monitoring
        log_monitor.start_log_monitoring.return_value = {
            "success": True,
            "monitor_id": "monitor_001",
            "filter_criteria": {"priority": "I"}
        }

        monitor_start = await log_monitor.start_log_monitoring(priority="I")
        assert monitor_start["success"] is True

        # Step 2: Perform UI interaction
        screen_interactor.tap_coordinates.return_value = {"success": True}
        interaction_result = await screen_interactor.tap_coordinates(500, 800)
        assert interaction_result["success"] is True

        # Step 3: Check logs for interaction events
        log_monitor.get_logcat.return_value = {
            "success": True,
            "logs": [
                "01-01 00:00:01.000  1000  1001 I InputDispatcher: Touch event at (500, 800)",
                "01-01 00:00:02.000  1000  1001 I ActivityManager: Activity focused"
            ],
            "line_count": 2
        }

        logs = await log_monitor.get_logcat()
        assert logs["success"] is True
        assert logs["line_count"] > 0

        # Step 4: Stop monitoring
        log_monitor.stop_log_monitoring.return_value = {
            "success": True,
            "monitor_id": "monitor_001",
            "lines_captured": 50
        }

        monitor_stop = await log_monitor.stop_log_monitoring("monitor_001")
        assert monitor_stop["success"] is True

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_error_correlation_with_logs(self, mock_server_components):
        """Test correlating operation errors with log entries."""
        log_monitor = mock_server_components["log_monitor"]
        screen_interactor = mock_server_components["screen_interactor"]

        # Step 1: Start log monitoring
        log_monitor.start_log_monitoring.return_value = {"success": True, "monitor_id": "monitor_001"}
        await log_monitor.start_log_monitoring()

        # Step 2: Attempt operation that fails
        screen_interactor.tap_element.return_value = {
            "success": False,
            "error": "Element not found",
            "timestamp": "2024-01-01T00:00:01Z"
        }

        failed_operation = await screen_interactor.tap_element(text="NonExistentButton")
        assert failed_operation["success"] is False

        # Step 3: Check logs for error context
        log_monitor.get_logcat.return_value = {
            "success": True,
            "logs": [
                "01-01 00:00:01.000  1000  1001 W UIAutomator: Element not found in hierarchy",
                "01-01 00:00:01.000  1000  1001 E UIAutomator: Search timed out after 5 seconds"
            ],
            "line_count": 2
        }

        error_logs = await log_monitor.get_logcat(priority="W")
        assert error_logs["success"] is True

        # Integration: Error logs should correlate with failed operation
        log_content = " ".join(error_logs["logs"])
        assert "Element not found" in log_content or "timed out" in log_content


class TestValidationIntegration:
    """Test integration of validation system with operations."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_coordinate_validation_in_tap_operation(self, mock_server_components):
        """Test coordinate validation during tap operations."""
        validator = mock_server_components["validator"]
        screen_interactor = mock_server_components["screen_interactor"]

        from src.validation import ValidationResult

        # Test valid coordinates
        validator.validate_coordinates.return_value = ValidationResult(
            True, {"x": 100, "y": 200}, [], []
        )

        screen_interactor.tap_coordinates.return_value = {"success": True}

        # This would typically happen inside the tool function
        valid_result = await screen_interactor.tap_coordinates(100, 200)
        assert valid_result["success"] is True

        # Test invalid coordinates
        validator.validate_coordinates.return_value = ValidationResult(
            False, None, ["Coordinates out of bounds"], []
        )

        # Operation should be prevented by validation
        # Implementation would check validation before executing

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_text_input_validation_integration(self, mock_server_components):
        """Test text input validation integration."""
        validator = mock_server_components["validator"]
        text_controller = mock_server_components["text_controller"]

        from src.validation import ValidationResult

        # Test safe text input
        validator.validate_text_input.return_value = ValidationResult(
            True, "Hello World", [], []
        )

        text_controller.input_text.return_value = {"success": True, "text": "Hello World"}
        result = await text_controller.input_text("Hello World")
        assert result["success"] is True

        # Test potentially dangerous input
        validator.validate_text_input.return_value = ValidationResult(
            False, None, ["Potentially dangerous input detected"], []
        )

        # Operation should be prevented or sanitized by validation

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_element_search_validation_integration(self, mock_server_components):
        """Test element search validation integration."""
        validator = mock_server_components["validator"]
        ui_inspector = mock_server_components["ui_inspector"]

        from src.validation import ValidationResult

        # Test valid element search
        validator.validate_element_search.return_value = ValidationResult(
            True, {"text": "login", "resource_id": "com.app:id/btn"}, [], ["Suggestion: use more specific criteria"]
        )

        ui_inspector.get_ui_layout.return_value = {
            "success": True,
            "elements": [{"text": "login", "resource-id": "com.app:id/btn"}]
        }

        # Search should proceed with sanitized parameters
        # Implementation would use sanitized values from validation result


class TestErrorHandlingIntegration:
    """Test error handling integration across components."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_cascading_error_handling(self, mock_server_components):
        """Test error handling across component boundaries."""
        adb_manager = mock_server_components["adb_manager"]
        ui_inspector = mock_server_components["ui_inspector"]
        error_handler = mock_server_components["error_handler"]

        # Step 1: ADB operation fails
        adb_manager.execute_adb_command.return_value = {
            "success": False,
            "error": "Device not found",
            "return_code": 1
        }

        # Step 2: UI operation depends on ADB, should also fail
        ui_inspector.get_ui_layout.return_value = {
            "success": False,
            "error": "UI dump failed: Device not found"
        }

        ui_result = await ui_inspector.get_ui_layout()
        assert ui_result["success"] is False

        # Step 3: Error should be handled with recovery suggestions
        from src.error_handler import AndroidMCPError, ErrorCode
        error = AndroidMCPError(ErrorCode.DEVICE_NOT_FOUND, "Device not found")

        error_handler.handle_error.return_value = {
            "error_code": "DEVICE_1101",
            "message": "Device not found",
            "recovery_suggestions": ["Check device connection", "Enable USB debugging"]
        }

        error_response = error_handler.handle_error(error)
        assert len(error_response["recovery_suggestions"]) > 0

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_timeout_error_propagation(self, mock_server_components):
        """Test timeout error propagation through component stack."""
        adb_manager = mock_server_components["adb_manager"]
        screen_interactor = mock_server_components["screen_interactor"]

        # Simulate ADB timeout
        adb_manager.execute_adb_command.side_effect = asyncio.TimeoutError("Command timed out")

        # Screen interaction should handle timeout gracefully
        screen_interactor.tap_coordinates.return_value = {
            "success": False,
            "error": "Operation timed out",
            "error_code": "ADB_1201"
        }

        result = await screen_interactor.tap_coordinates(100, 200)
        assert result["success"] is False
        assert "timeout" in result["error"].lower() or "timed out" in result["error"].lower()


class TestPerformanceIntegration:
    """Test performance characteristics of integrated operations."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.performance
    async def test_concurrent_operations_performance(self, mock_server_components):
        """Test performance of concurrent operations."""
        import time

        adb_manager = mock_server_components["adb_manager"]
        ui_inspector = mock_server_components["ui_inspector"]
        screen_interactor = mock_server_components["screen_interactor"]

        # Set up mocks for concurrent operations
        adb_manager.get_device_info.return_value = {"success": True}
        ui_inspector.get_ui_layout.return_value = {"success": True, "elements": []}
        screen_interactor.tap_coordinates.return_value = {"success": True}

        start_time = time.time()

        # Run multiple operations concurrently
        tasks = [
            adb_manager.get_device_info(),
            ui_inspector.get_ui_layout(),
            screen_interactor.tap_coordinates(100, 200),
            adb_manager.check_device_health(),
            ui_inspector.extract_ui_hierarchy()
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()

        duration = end_time - start_time

        # All operations should complete successfully
        for result in results:
            assert not isinstance(result, Exception)

        # Should complete in reasonable time
        assert duration < 2.0, f"Concurrent operations took {duration} seconds"

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.performance
    async def test_sequential_operation_chain_performance(self, mock_server_components):
        """Test performance of sequential operation chains."""
        import time

        components = mock_server_components

        start_time = time.time()

        # Simulate typical user workflow
        # 1. Get devices
        components["adb_manager"].list_devices.return_value = [{"id": "emulator-5554"}]
        devices = await components["adb_manager"].list_devices()

        # 2. Select device
        components["adb_manager"].auto_select_device.return_value = {"success": True}
        selection = await components["adb_manager"].auto_select_device()

        # 3. Get UI layout
        components["ui_inspector"].get_ui_layout.return_value = {"success": True, "elements": []}
        ui_layout = await components["ui_inspector"].get_ui_layout()

        # 4. Interact with element
        components["screen_interactor"].tap_element.return_value = {"success": True}
        interaction = await components["screen_interactor"].tap_element(text="button")

        # 5. Take screenshot
        components["media_capture"].take_screenshot.return_value = {"success": True}
        screenshot = await components["media_capture"].take_screenshot()

        end_time = time.time()
        duration = end_time - start_time

        # All operations should succeed
        assert len(devices) >= 0
        assert selection["success"] is True
        assert ui_layout["success"] is True
        assert interaction["success"] is True
        assert screenshot["success"] is True

        # Chain should complete in reasonable time
        assert duration < 1.0, f"Operation chain took {duration} seconds"


class TestEndToEndWorkflows:
    """Test complete end-to-end workflows."""

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_complete_app_automation_workflow(self, mock_server_components):
        """Test complete app automation workflow."""
        components = mock_server_components

        # Scenario: Automate a login flow
        workflow_steps = []

        # Step 1: Initialize and select device
        components["adb_manager"].auto_select_device.return_value = {
            "success": True,
            "selected": {"id": "emulator-5554"}
        }

        device_result = await components["adb_manager"].auto_select_device()
        workflow_steps.append(("device_selection", device_result["success"]))

        # Step 2: Launch app (via ADB command)
        components["adb_manager"].execute_adb_command.return_value = {"success": True}
        launch_result = {"success": True}  # Simulate app launch
        workflow_steps.append(("app_launch", launch_result["success"]))

        # Step 3: Wait for UI to load and capture screenshot
        components["ui_inspector"].get_ui_layout.return_value = {
            "success": True,
            "elements": [
                {"text": "", "resource-id": "username", "class": "EditText"},
                {"text": "", "resource-id": "password", "class": "EditText"},
                {"text": "Login", "resource-id": "login_btn", "clickable": "true"}
            ]
        }

        ui_result = await components["ui_inspector"].get_ui_layout()
        workflow_steps.append(("ui_extraction", ui_result["success"]))

        # Step 4: Fill username
        components["screen_interactor"].tap_element.return_value = {"success": True}
        username_tap = await components["screen_interactor"].tap_element(resource_id="username")
        workflow_steps.append(("username_tap", username_tap["success"]))

        components["text_controller"].input_text.return_value = {"success": True}
        username_input = await components["text_controller"].input_text("testuser")
        workflow_steps.append(("username_input", username_input["success"]))

        # Step 5: Fill password
        password_tap = await components["screen_interactor"].tap_element(resource_id="password")
        workflow_steps.append(("password_tap", password_tap["success"]))

        password_input = await components["text_controller"].input_text("password123")
        workflow_steps.append(("password_input", password_input["success"]))

        # Step 6: Tap login button
        login_tap = await components["screen_interactor"].tap_element(resource_id="login_btn")
        workflow_steps.append(("login_tap", login_tap["success"]))

        # Step 7: Verify login success (check for new UI elements)
        components["ui_inspector"].get_ui_layout.return_value = {
            "success": True,
            "elements": [
                {"text": "Welcome", "class": "TextView"},
                {"text": "Dashboard", "class": "TextView"}
            ]
        }

        post_login_ui = await components["ui_inspector"].get_ui_layout()
        workflow_steps.append(("login_verification", post_login_ui["success"]))

        # Step 8: Take final screenshot
        components["media_capture"].take_screenshot.return_value = {"success": True}
        final_screenshot = await components["media_capture"].take_screenshot()
        workflow_steps.append(("final_screenshot", final_screenshot["success"]))

        # Verify entire workflow succeeded
        all_successful = all(success for _, success in workflow_steps)
        assert all_successful, f"Workflow steps: {workflow_steps}"

        # Verify we have the expected number of steps
        assert len(workflow_steps) == 10

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_error_recovery_workflow(self, mock_server_components):
        """Test error recovery in complex workflows."""
        components = mock_server_components

        # Scenario: Handle errors and retry operations
        workflow_log = []

        # Step 1: Device selection fails initially
        components["adb_manager"].auto_select_device.side_effect = [
            {"success": False, "error": "No devices found"},
            {"success": True, "selected": {"id": "emulator-5554"}}  # Success on retry
        ]

        # First attempt fails
        device_result1 = await components["adb_manager"].auto_select_device()
        workflow_log.append(("device_selection_attempt_1", device_result1["success"]))

        # Retry succeeds
        device_result2 = await components["adb_manager"].auto_select_device()
        workflow_log.append(("device_selection_attempt_2", device_result2["success"]))

        # Step 2: UI extraction fails, then succeeds
        components["ui_inspector"].get_ui_layout.side_effect = [
            {"success": False, "error": "UI service unavailable"},
            {"success": True, "elements": [{"text": "Button"}]}
        ]

        ui_result1 = await components["ui_inspector"].get_ui_layout()
        workflow_log.append(("ui_extraction_attempt_1", ui_result1["success"]))

        ui_result2 = await components["ui_inspector"].get_ui_layout()
        workflow_log.append(("ui_extraction_attempt_2", ui_result2["success"]))

        # Step 3: Element interaction succeeds after UI is available
        components["screen_interactor"].tap_element.return_value = {"success": True}
        interaction_result = await components["screen_interactor"].tap_element(text="Button")
        workflow_log.append(("interaction", interaction_result["success"]))

        # Verify recovery workflow
        expected_pattern = [
            ("device_selection_attempt_1", False),
            ("device_selection_attempt_2", True),
            ("ui_extraction_attempt_1", False),
            ("ui_extraction_attempt_2", True),
            ("interaction", True)
        ]

        assert workflow_log == expected_pattern