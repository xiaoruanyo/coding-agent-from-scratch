"""N10：把结构化测试事实转换为可供 Graph Guard 使用的状态字段。"""

from typing import Literal, TypedDict


class TestResult(TypedDict):
    status: Literal["PASS", "FAIL", "TIMEOUT", "ERROR"]
    exit_code: int | None
    output: str


def sync_test_result(
    *,
    result: TestResult,
    previous_retry_count: int,
) -> dict:
    """注意：这是教学用的纯函数；它没有真正运行 pytest。"""
    status = result["status"]

    if status == "PASS":
        return {
            "test_passed": True,
            "last_error_type": "",
            "retry_count": previous_retry_count,
        }

    if status == "FAIL":
        return {
            "test_passed": False,
            "last_error_type": "TEST_FAIL",
            "retry_count": previous_retry_count + 1,
        }

    if status == "TIMEOUT":
        return {
            "test_passed": False,
            "last_error_type": "TEST_TIMEOUT",
            "retry_count": previous_retry_count,
        }

    return {
        "test_passed": False,
        "last_error_type": "TEST_ERROR",
        "retry_count": previous_retry_count,
    }


if __name__ == "__main__":
    for status in ("PASS", "FAIL", "TIMEOUT", "ERROR"):
        example = {
            "status": status,
            "exit_code": 0 if status == "PASS" else None,
            "output": "教学模拟",
        }
        print(status, sync_test_result(result=example, previous_retry_count=2))
