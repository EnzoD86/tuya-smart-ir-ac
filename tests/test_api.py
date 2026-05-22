import asyncio
import pytest

from tuya_smart_ir_ac.api import TuyaBaseAPI, TuyaSensorAPI, TuyaAPIResult


class DummyClient:
    def __init__(self, response):
        self.response = response

    async def get(self, url, params=None):
        return self.response

    async def post(self, url, body=None):
        return self.response


@pytest.mark.asyncio
async def test_base_api_request_returns_success_result():
    client = DummyClient({"success": True, "result": {"value": 1}})
    api = TuyaBaseAPI(None, client, log_prefix="[test]")

    result = await api._request("GET", "/test", payload=None, factory=lambda data: data)

    assert result.success is True
    assert result.data == {"value": 1}


@pytest.mark.asyncio
async def test_base_api_request_handles_business_error():
    client = DummyClient({"success": False, "code": "ERR", "msg": "failure"})
    api = TuyaBaseAPI(None, client, log_prefix="[test]")

    result = await api._request("GET", "/test")

    assert result.success is False
    assert "ERR" in result.error_info


@pytest.mark.asyncio
async def test_base_api_request_handles_factory_parse_failure():
    def broken_factory(_):
        raise ValueError("bad parse")

    client = DummyClient({"success": True, "result": {"value": 1}})
    api = TuyaBaseAPI(None, client, log_prefix="[test]")

    result = await api._request("GET", "/test", factory=broken_factory)

    assert result.success is False
    assert "PARSE_ERROR" in result.error_code


@pytest.mark.asyncio
async def test_sensor_api_throttles_concurrency():
    api = TuyaSensorAPI(None, DummyClient(None), log_prefix="[test]")
    active_count = 0
    max_concurrent = 0
    lock = asyncio.Lock()

    async def fake_fetch(device_id: str) -> TuyaAPIResult:
        nonlocal active_count, max_concurrent
        async with lock:
            active_count += 1
            max_concurrent = max(max_concurrent, active_count)
        await asyncio.sleep(0)
        async with lock:
            active_count -= 1
        return TuyaAPIResult(success=True, data=device_id)

    api.async_fetch_data = fake_fetch
    result = await api.async_fetch_all_data([f"device_{i}" for i in range(6)])

    assert result.success is True
    assert len(result.data) == 6
    assert max_concurrent <= 3
