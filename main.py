#!/usr/bin/env python3
"""メトリクス監視・異常検知・LLM解析のメインスクリプト.

使い方:
    python main.py [--detailed]

オプション:
    --detailed  異常がなくても詳細メトリクスを取得してLLM解析を実行
"""

import json
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from anomaly_detector import AnomalyDetector
from config import validate_config
from llm_analyzer import analyze_metrics_sync
from metrics_queries import DETAILED_QUERIES, SUMMARY_QUERIES
from prometheus_client import PrometheusClient
from utils import format_bytes, format_percentage, format_rate

logger = logging.getLogger(__name__)


def save_result(data: dict[str, Any], filename: str) -> Path | None:
    """結果をJSONファイルに保存."""
    try:
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)

        filepath = output_dir / filename
        with filepath.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info("結果を保存しました: %s", filepath)
    except OSError:
        logger.exception("ファイル保存に失敗しました")
        return None
    else:
        return filepath


def format_summary(summary: dict[str, Any]) -> str:
    """サマリメトリクスを人間が読みやすい形式にフォーマット."""
    lines = ["=" * 60, "メトリクスサマリ", "=" * 60]

    # 観測健全性
    lines.append("\n【観測健全性】")
    lines.append(f"  up: {summary.get('up', 'N/A')}")
    scrape_dur = summary.get("scrape_duration")
    lines.append(
        f"  scrape_duration: {scrape_dur:.3f}s"
        if scrape_dur
        else "  scrape_duration: N/A",
    )

    # CPU
    lines.append("\n【CPU】")
    lines.append(f"  使用率: {format_percentage(summary.get('cpu_usage'))}")
    lines.append(f"  iowait: {format_percentage(summary.get('cpu_iowait'))}")
    lines.append(
        f"  load1: {summary.get('load1', 'N/A'):.2f}"
        if summary.get("load1")
        else "  load1: N/A",
    )
    lines.append(
        f"  load5: {summary.get('load5', 'N/A'):.2f}"
        if summary.get("load5")
        else "  load5: N/A",
    )
    lines.append(
        f"  load15: {summary.get('load15', 'N/A'):.2f}"
        if summary.get("load15")
        else "  load15: N/A",
    )

    # メモリ
    lines.append("\n【メモリ】")
    lines.append(f"  使用率: {format_percentage(summary.get('memory_usage'))}")
    lines.append(f"  swap: {format_percentage(summary.get('swap_usage'))}")

    # ディスク
    lines.append("\n【ディスクI/O】")
    lines.append(
        f"  読み込み: {format_bytes(summary.get('disk_read_bytes_per_sec'))}/s",
    )
    lines.append(
        f"  書き込み: {format_bytes(summary.get('disk_write_bytes_per_sec'))}/s",
    )

    # ファイルシステム
    lines.append("\n【ファイルシステム】")
    fs_top3 = summary.get("fs_usage_top3")
    if fs_top3 and isinstance(fs_top3, list):
        for i, fs in enumerate(fs_top3, 1):
            mp = fs.get("labels", {}).get("mountpoint", "unknown")
            val = fs.get("value", 0)
            lines.append(f"  {i}. {mp}: {val:.1f}%")
    else:
        lines.append("  データなし")

    # ネットワーク
    lines.append("\n【ネットワーク】")
    lines.append(f"  受信: {format_bytes(summary.get('network_rx_bytes_per_sec'))}/s")
    lines.append(f"  送信: {format_bytes(summary.get('network_tx_bytes_per_sec'))}/s")
    lines.append(f"  エラー: {format_rate(summary.get('network_err_per_sec', 0))}")

    # TCP
    lines.append("\n【TCP】")
    lines.append(f"  確立済み接続: {summary.get('tcp_curr_estab', 'N/A')}")
    lines.append(f"  再送: {format_rate(summary.get('tcp_retrans_per_sec', 0))}")

    lines.append("=" * 60)
    return "\n".join(lines)


def main() -> int:
    """メイン処理."""
    # 設定の検証
    if not validate_config():
        logger.error("設定が不完全です。処理を中止します")
        return 1

    timestamp = datetime.now(timezone(timedelta(hours=9))).strftime("%Y%m%d_%H%M%S")
    force_detailed = "--detailed" in sys.argv

    logger.info("\n%s", "=" * 60)
    logger.info("メトリクス監視・異常検知スクリプト")
    logger.info(
        "実行時刻: %s",
        datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M:%S"),
    )
    logger.info("%s\n", "=" * 60)

    # 1. Prometheusからサマリメトリクスを取得
    logger.info("📊 サマリメトリクスを取得中...")
    try:
        prom_client = PrometheusClient()
        summary = prom_client.execute_queries(SUMMARY_QUERIES)
    except Exception:
        logger.exception("Prometheusからのメトリクス取得に失敗しました")
        return 1

    logger.info("\n%s", format_summary(summary))

    # 2. 異常検知
    logger.info("\n🔍 異常検知を実行中...")
    detector = AnomalyDetector()
    anomaly_result = detector.detect(summary)

    is_anomaly = anomaly_result["is_anomaly"]
    severity = anomaly_result["severity"]
    anomalies = anomaly_result["anomalies"]

    if is_anomaly:
        logger.warning(
            "\n⚠️  異常を検知しました (重要度: %s, 件数: %d件)",
            severity.upper(),
            len(anomalies),
        )
        for i, anomaly in enumerate(anomalies, 1):
            logger.warning(
                "  %d. [%s] %s",
                i,
                anomaly["severity"].upper(),
                anomaly["message"],
            )
    else:
        logger.info("\n✅ 異常は検知されませんでした")

    # 3. 詳細メトリクス取得(異常時または強制指定時)
    detailed = None
    if is_anomaly or force_detailed:
        logger.info("\n📈 詳細メトリクスを取得中...")
        detailed = prom_client.execute_queries(DETAILED_QUERIES)
        logger.info("✓ %d個の詳細メトリクスを取得しました", len(detailed))
    # 4. LLM解析
    logger.info("\n🤖 LLMで解析中...")
    try:
        llm_result = analyze_metrics_sync(summary, anomaly_result, detailed)

        logger.info("\n%s", "=" * 60)
        logger.info("LLM解析結果")
        logger.info("%s", "=" * 60)
        logger.info("%s", llm_result)
        logger.info("%s\n", "=" * 60)

    except Exception:
        logger.exception("LLM解析でエラーが発生しました")
        llm_result = "エラーが発生しました。ログを確認してください。"

    # 5. 結果を保存
    result_data = {
        "timestamp": datetime.now(timezone(timedelta(hours=9))).isoformat(),
        "summary": summary,
        "anomaly_detection": anomaly_result,
        "detailed_metrics": detailed,
        "llm_analysis": llm_result,
    }

    save_result(result_data, f"metrics_{timestamp}.json")

    # 異常時は別途ログにも記録
    if is_anomaly:
        anomaly_log = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "severity": severity,
            "anomalies": anomalies,
            "llm_analysis": llm_result,
        }
        save_result(anomaly_log, f"anomaly_{timestamp}.json")
        logger.warning("⚠️  異常ログも保存しました: output/anomaly_%s.json\n", timestamp)

    logger.info("✅ 処理が完了しました\n")

    # 終了コード(異常時は1を返す)
    return 1 if is_anomaly else 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
