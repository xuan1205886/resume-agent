"""
API 鉴权和速率限制单元测试
"""

import time
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from src.api.auth import RateLimiter, verify_api_key, check_rate_limit


class TestRateLimiter:
    """速率限制器测试"""

    def test_allows_within_limit(self):
        limiter = RateLimiter(max_requests=10, window_seconds=60)
        for _ in range(10):
            assert limiter.is_allowed("client-1") is True

    def test_blocks_over_limit(self):
        limiter = RateLimiter(max_requests=3, window_seconds=60)
        for _ in range(3):
            assert limiter.is_allowed("client-2") is True
        assert limiter.is_allowed("client-2") is False

    def test_unlimited_when_zero(self):
        limiter = RateLimiter(max_requests=0, window_seconds=60)
        for _ in range(100):
            assert limiter.is_allowed("client-3") is True

    def test_independent_clients(self):
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        assert limiter.is_allowed("client-a") is True
        assert limiter.is_allowed("client-a") is True
        assert limiter.is_allowed("client-a") is False
        # client-b 不受影响
        assert limiter.is_allowed("client-b") is True

    def test_cleanup_removes_expired(self):
        limiter = RateLimiter(max_requests=2, window_seconds=1)
        limiter.is_allowed("client-c")
        limiter.is_allowed("client-c")
        assert len(limiter._clients) == 1
        # 等待窗口过期
        time.sleep(1.1)
        limiter.cleanup()
        assert len(limiter._clients) == 0


class TestVerifyApiKey:
    """API Key 鉴权测试"""

    @patch("src.api.auth.get_config")
    def test_skip_when_no_key_configured(self, mock_get_config):
        mock_config = MagicMock()
        mock_config.server.api_key = ""
        mock_get_config.return_value = mock_config

        result = verify_api_key(x_api_key=None)
        assert result is None

    @patch("src.api.auth.get_config")
    def test_401_when_key_required_but_missing(self, mock_get_config):
        mock_config = MagicMock()
        mock_config.server.api_key = "secret-key"
        mock_get_config.return_value = mock_config

        with pytest.raises(HTTPException) as exc:
            verify_api_key(x_api_key=None)
        assert exc.value.status_code == 401

    @patch("src.api.auth.get_config")
    def test_401_when_key_mismatch(self, mock_get_config):
        mock_config = MagicMock()
        mock_config.server.api_key = "secret-key"
        mock_get_config.return_value = mock_config

        with pytest.raises(HTTPException) as exc:
            verify_api_key(x_api_key="wrong-key")
        assert exc.value.status_code == 401

    @patch("src.api.auth.get_config")
    def test_success_when_key_matches(self, mock_get_config):
        mock_config = MagicMock()
        mock_config.server.api_key = "secret-key"
        mock_get_config.return_value = mock_config

        result = verify_api_key(x_api_key="secret-key")
        assert result == "secret-key"
