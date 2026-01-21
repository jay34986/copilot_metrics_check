"""ユーティリティ関数."""

import logging

logger = logging.getLogger(__name__)


def format_bytes(bytes_value: float | None, unit: str = "MB") -> str:
    """バイト数を人間が読みやすい形式に変換.

    Args:
        bytes_value: バイト数
        unit: 変換先の単位 (KB, MB, GB)

    Returns:
        フォーマット済みの文字列

    """
    if bytes_value is None:
        return "N/A"

    divisors = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3}
    divisor = divisors.get(unit, 1024**2)

    return f"{bytes_value / divisor:.1f} {unit}"


def format_percentage(value: float | None, decimals: int = 1) -> str:
    """パーセンテージ値をフォーマット.

    Args:
        value: パーセンテージ値
        decimals: 小数点以下の桁数

    Returns:
        フォーマット済みの文字列

    """
    if value is None:
        return "N/A"
    return f"{value:.{decimals}f}%"


def format_rate(value: float | None, unit: str = "/s", decimals: int = 1) -> str:
    """レート値をフォーマット.

    Args:
        value: レート値
        unit: 単位
        decimals: 小数点以下の桁数

    Returns:
        フォーマット済みの文字列

    """
    if value is None:
        return "N/A"
    return f"{value:.{decimals}f}{unit}"


def safe_get_metric_value(result: dict | list | float | None) -> float | None:
    """Prometheusの結果から安全に値を取得.

    Args:
        result: Prometheusのクエリ結果

    Returns:
        メトリクス値またはNone

    """
    if result is None:
        return None

    if isinstance(result, (int, float)):
        return float(result)

    if isinstance(result, list) and len(result) > 0:
        # リスト形式の場合、最初の要素の値を返す
        first_item = result[0]
        if isinstance(first_item, dict) and "value" in first_item:
            return float(first_item["value"])

    return None
