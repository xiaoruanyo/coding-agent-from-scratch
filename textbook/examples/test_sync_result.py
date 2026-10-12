"""N10：验证结构化规则，不需要模型 API。"""

import importlib.util
from pathlib import Path


# 文件名以数字开头，不适合直接使用普通 import；按路径载入
module_path = Path(__file__).with_name("06_sync_test_result.py")
spec = importlib.util.spec_from_file_location("sync_test_result", module_path)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
sync_test_result = module.sync_test_result


def make_result(status, exit_code=None):
    return {"status": status, "exit_code": exit_code, "output": "sample"}


def test_pass_sets_success_without_increasing_failures():
    got = sync_test_result(
        result=make_result("PASS", 0), previous_retry_count=2
    )
    assert got["test_passed"] is True
    assert got["retry_count"] == 2


def test_normal_fail_increments_counter():
    got = sync_test_result(
        result=make_result("FAIL", 1), previous_retry_count=2
    )
    assert got["test_passed"] is False
    assert got["retry_count"] == 3
    assert got["last_error_type"] == "TEST_FAIL"


def test_timeout_does_not_consume_normal_fail_budget():
    got = sync_test_result(
        result=make_result("TIMEOUT"), previous_retry_count=2
    )
    assert got["retry_count"] == 2
    assert got["last_error_type"] == "TEST_TIMEOUT"


def test_error_does_not_consume_normal_fail_budget():
    got = sync_test_result(
        result=make_result("ERROR"), previous_retry_count=2
    )
    assert got["retry_count"] == 2
    assert got["last_error_type"] == "TEST_ERROR"
