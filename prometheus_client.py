"""Prometheus APIクライアント."""

import logging

import requests

from config import API_KEY, INSTANCE_ID, PROM_URL

logger = logging.getLogger(__name__)


class PrometheusClient:
    """Grafana Cloud Prometheus APIクライアント."""

    def __init__(
        self,
        instance_id: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> None:
        """クライアントの初期化(テスト用に依存性注入可能)."""
        self.instance_id = instance_id or INSTANCE_ID
        self.base_url = base_url or PROM_URL
        self.api_key = api_key or API_KEY
        self.auth = (self.instance_id, self.api_key)

    def query(self, query: str) -> dict[str, any] | None:
        """即時クエリを実行.

        Args:
            query: PromQL クエリ文字列

        Returns:
            クエリ結果のJSON、エラー時はNone

        """
        url = f"{self.base_url}/api/v1/query"
        params = {"query": query}

        try:
            response = requests.get(url, params=params, auth=self.auth, timeout=30)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException:
            logger.exception("HTTP request error")
            logger.debug("Query was: %s", query)
            return None
        else:
            if data.get("status") == "success":
                return data.get("data", {})
            error_msg = data.get("error", "Unknown error")
            logger.error("Query failed: %s", error_msg)
            logger.debug("Query was: %s", query)
            return None

    def query_range(
        self,
        query: str,
        start: str,
        end: str,
        step: str = "1m",
    ) -> dict[str, any] | None:
        """範囲クエリを実行.

        Args:
            query: PromQL クエリ文字列
            start: 開始時刻(RFC3339またはUNIX timestamp)
            end: 終了時刻(RFC3339またはUNIX timestamp)
            step: クエリ解像度(例: "1m", "5m")

        Returns:
            クエリ結果のJSON、エラー時はNone

        """
        url = f"{self.base_url}/api/v1/query_range"
        params = {
            "query": query,
            "start": start,
            "end": end,
            "step": step,
        }

        try:
            response = requests.get(url, params=params, auth=self.auth, timeout=30)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException:
            logger.exception("HTTP request error")
            logger.debug("Query was: %s", query)
            return None
        else:
            if data.get("status") == "success":
                return data.get("data", {})
            error_msg = data.get("error", "Unknown error")
            logger.error("Query range failed: %s", error_msg)
            logger.debug("Query was: %s", query)
            return None

    def execute_queries(self, queries: dict[str, str]) -> dict[str, any]:
        """複数のクエリを実行して結果を辞書で返す.

        Args:
            queries: クエリ名とPromQLのマッピング

        Returns:
            クエリ名と結果値のマッピング

        """
        results = {}

        for name, query in queries.items():
            data = self.query(query)
            if data is None:
                results[name] = None
                continue

            result = data.get("result", [])

            # 結果の整形
            if not result:
                results[name] = None
            elif len(result) == 1:
                # 単一結果
                value = result[0].get("value", [None, None])
                results[name] = float(value[1]) if value[1] is not None else None
            else:
                # 複数結果 (topkなど)
                results[name] = [
                    {
                        "labels": item.get("metric", {}),
                        "value": float(item.get("value", [None, None])[1]),
                    }
                    for item in result
                    if item.get("value", [None, None])[1] is not None
                ]

        return results
