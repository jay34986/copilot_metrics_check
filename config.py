"""設定管理モジュール."""

import logging
import os

from dotenv import load_dotenv

load_dotenv()

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)
logger = logging.getLogger(__name__)

# Prometheus設定
INSTANCE_ID = os.getenv("INSTANCE_ID")
PROM_URL = os.getenv("PROM_URL")
API_KEY = os.getenv("API_KEY")

# 異常検知の閾値
THRESHOLDS: dict[str, float] = {
    "cpu_usage": float(os.getenv("THRESHOLD_CPU_USAGE", "80")),
    "memory_usage": float(os.getenv("THRESHOLD_MEMORY_USAGE", "85")),
    "swap_usage": float(os.getenv("THRESHOLD_SWAP_USAGE", "50")),
    "disk_usage": float(os.getenv("THRESHOLD_DISK_USAGE", "90")),
    "iowait": float(os.getenv("THRESHOLD_IOWAIT", "20")),
    "load1_per_cpu": float(os.getenv("THRESHOLD_LOAD1_PER_CPU", "2.0")),
    "network_errors_per_sec": float(
        os.getenv("THRESHOLD_NETWORK_ERRORS_PER_SEC", "10"),
    ),
    "tcp_retrans_per_sec": float(os.getenv("THRESHOLD_TCP_RETRANS_PER_SEC", "50")),
}

# 異常検知のスコアリング重み
SEVERITY_WEIGHTS: dict[str, int] = {
    "system_down": 100,
    "cpu_high": 30,
    "iowait_high": 20,
    "load_extreme": 15,
    "memory_high": 25,
    "swap_high": 20,
    "disk_high": 20,
    "fs_readonly": 50,
    "network_errors": 15,
    "tcp_retrans": 15,
    "tcp_overflow": 20,
}

# 重要度スコアの閾値
SEVERITY_THRESHOLDS: dict[str, int] = {
    "critical": 80,
    "high": 40,
    "medium": 20,
    "low": 1,
}

# Copilot設定
COPILOT_MODEL = os.getenv("COPILOT_MODEL", "gpt-5-mini")

# クエリの時間範囲
QUERY_RANGE = "5m"  # レート計算用
HISTORY_RANGE = "1h"  # 履歴比較用


def validate_config() -> bool:
    """必須設定が存在するかチェック."""
    required_vars = {
        "INSTANCE_ID": INSTANCE_ID,
        "PROM_URL": PROM_URL,
        "API_KEY": API_KEY,
    }

    missing = [name for name, value in required_vars.items() if not value]

    if missing:
        logger.error("必須環境変数が設定されていません: %s", ", ".join(missing))
        logger.error(".env ファイルを確認してください")
        return False

    logger.info("設定の検証が完了しました")
    return True
