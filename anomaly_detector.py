"""異常検知モジュール."""

import logging
from typing import Any

from config import SEVERITY_THRESHOLDS, SEVERITY_WEIGHTS, THRESHOLDS

logger = logging.getLogger(__name__)

# 閾値定数
CRITICAL_USAGE_THRESHOLD = 95  # CPU/メモリ/ディスク使用率の重大レベル閾値(%)


class AnomalyDetector:
    """メトリクスの異常を検知."""

    def __init__(
        self,
        thresholds: dict[str, float] | None = None,
        weights: dict[str, int] | None = None,
        severity_thresholds: dict[str, int] | None = None,
    ) -> None:
        """異常検知器の初期化(テスト用に依存性注入可能)."""
        self.thresholds = thresholds or THRESHOLDS
        self.weights = weights or SEVERITY_WEIGHTS
        self.severity_thresholds = severity_thresholds or SEVERITY_THRESHOLDS

    def detect(self, summary: dict[str, Any]) -> dict[str, Any]:
        """サマリメトリクスから異常を検知.

        Args:
            summary: メトリクスサマリの辞書

        Returns:
            異常検知結果(is_anomaly, anomalies, severity)

        """
        anomalies = []
        severity_score = 0  # 0-100で重要度をスコアリング

        # 観測健全性チェック
        if summary.get("up") == 0:
            anomalies.append(
                {
                    "metric": "up",
                    "message": "監視対象がダウンしています",
                    "severity": "critical",
                    "value": 0,
                },
            )
            severity_score += self.weights["system_down"]

        # CPUチェック
        cpu_usage = summary.get("cpu_usage")
        if cpu_usage is not None and cpu_usage > self.thresholds["cpu_usage"]:
            anomalies.append(
                {
                    "metric": "cpu_usage",
                    "message": f"CPU使用率が高い ({cpu_usage:.1f}%)",
                    "severity": "warning"
                    if cpu_usage < CRITICAL_USAGE_THRESHOLD
                    else "critical",
                    "value": cpu_usage,
                    "threshold": self.thresholds["cpu_usage"],
                },
            )
            excess = (cpu_usage - self.thresholds["cpu_usage"]) / 2
            severity_score += min(self.weights["cpu_high"], excess)

        # iowaitチェック
        iowait = summary.get("cpu_iowait")
        if iowait is not None and iowait > self.thresholds["iowait"]:
            anomalies.append(
                {
                    "metric": "cpu_iowait",
                    "message": f"I/O待ちが多い ({iowait:.1f}%)",
                    "severity": "warning",
                    "value": iowait,
                    "threshold": self.thresholds["iowait"],
                },
            )
            excess = iowait - self.thresholds["iowait"]
            severity_score += min(self.weights["iowait_high"], excess)

        # load averageチェック(簡易的に閾値のみで判定)
        load1 = summary.get("load1")
        if load1 is not None:
            # CPUコア数がわからないため、絶対値での警告は控えめに
            extreme_load_threshold = 10
            if load1 > extreme_load_threshold:
                anomalies.append(
                    {
                        "metric": "load1",
                        "message": f"Load Average (1分) が高い ({load1:.2f})",
                        "severity": "warning",
                        "value": load1,
                    },
                )
                severity_score += min(self.weights["load_extreme"], load1)

        # メモリチェック
        memory_usage = summary.get("memory_usage")
        if memory_usage is not None and memory_usage > self.thresholds["memory_usage"]:
            anomalies.append(
                {
                    "metric": "memory_usage",
                    "message": f"メモリ使用率が高い ({memory_usage:.1f}%)",
                    "severity": "warning"
                    if memory_usage < CRITICAL_USAGE_THRESHOLD
                    else "critical",
                    "value": memory_usage,
                    "threshold": self.thresholds["memory_usage"],
                },
            )
            excess = (memory_usage - self.thresholds["memory_usage"]) / 2
            severity_score += min(self.weights["memory_high"], excess)

        # スワップチェック
        swap_usage = summary.get("swap_usage")
        if swap_usage is not None and swap_usage > self.thresholds["swap_usage"]:
            anomalies.append(
                {
                    "metric": "swap_usage",
                    "message": f"スワップ使用率が高い ({swap_usage:.1f}%)",
                    "severity": "warning",
                    "value": swap_usage,
                    "threshold": self.thresholds["swap_usage"],
                },
            )
            excess = swap_usage - self.thresholds["swap_usage"]
            severity_score += min(self.weights["swap_high"], excess)

        # ファイルシステムチェック
        fs_top3 = summary.get("fs_usage_top3")
        if fs_top3 and isinstance(fs_top3, list):
            for fs in fs_top3:
                usage = fs.get("value")
                if usage is not None and usage > self.thresholds["disk_usage"]:
                    mountpoint = fs.get("labels", {}).get("mountpoint", "unknown")
                    anomalies.append(
                        {
                            "metric": "fs_usage",
                            "message": f"ディスク使用率が高い ({mountpoint}: {usage:.1f}%)",
                            "severity": "warning"
                            if usage < CRITICAL_USAGE_THRESHOLD
                            else "critical",
                            "value": usage,
                            "threshold": self.thresholds["disk_usage"],
                            "mountpoint": mountpoint,
                        },
                    )
                    excess = (usage - self.thresholds["disk_usage"]) / 2
                    severity_score += min(self.weights["disk_high"], excess)

        # 読み取り専用ファイルシステムチェック
        if summary.get("fs_readonly", 0) > 0:
            anomalies.append(
                {
                    "metric": "fs_readonly",
                    "message": "読み取り専用のファイルシステムが存在",
                    "severity": "critical",
                    "value": 1,
                },
            )
            severity_score += self.weights["fs_readonly"]

        # ネットワークエラー・ドロップチェック
        net_err = summary.get("network_err_per_sec", 0)
        if net_err > self.thresholds["network_errors_per_sec"]:
            anomalies.append(
                {
                    "metric": "network_err_per_sec",
                    "message": f"ネットワークエラーが多い ({net_err:.1f}/秒)",
                    "severity": "warning",
                    "value": net_err,
                    "threshold": self.thresholds["network_errors_per_sec"],
                },
            )
            excess = net_err - self.thresholds["network_errors_per_sec"]
            severity_score += min(self.weights["network_errors"], excess)

        # TCP再送チェック
        tcp_retrans = summary.get("tcp_retrans_per_sec", 0)
        if tcp_retrans > self.thresholds["tcp_retrans_per_sec"]:
            anomalies.append(
                {
                    "metric": "tcp_retrans_per_sec",
                    "message": f"TCP再送が多い ({tcp_retrans:.1f}/秒)",
                    "severity": "warning",
                    "value": tcp_retrans,
                    "threshold": self.thresholds["tcp_retrans_per_sec"],
                },
            )
            excess = (tcp_retrans - self.thresholds["tcp_retrans_per_sec"]) / 5
            severity_score += min(self.weights["tcp_retrans"], excess)

        # TCPリッスンオーバーフローチェック
        tcp_overflow = summary.get("tcp_listen_overflow_per_sec", 0)
        if tcp_overflow > 0:
            anomalies.append(
                {
                    "metric": "tcp_listen_overflow_per_sec",
                    "message": f"TCPリッスンキューがあふれている ({tcp_overflow:.1f}/秒)",
                    "severity": "warning",
                    "value": tcp_overflow,
                },
            )
            severity_score += min(self.weights["tcp_overflow"], tcp_overflow * 2)

        # 総合判定
        is_anomaly = len(anomalies) > 0
        severity = self._calculate_severity(severity_score)

        return {
            "is_anomaly": is_anomaly,
            "anomalies": anomalies,
            "severity": severity,
            "severity_score": min(100, severity_score),
            "anomaly_count": len(anomalies),
        }

    def _calculate_severity(self, score: float) -> str:
        """スコアからseverityレベルを判定."""
        if score >= self.severity_thresholds["critical"]:
            return "critical"
        if score >= self.severity_thresholds["high"]:
            return "high"
        if score >= self.severity_thresholds["medium"]:
            return "medium"
        if score >= self.severity_thresholds["low"]:
            return "low"
        return "normal"
