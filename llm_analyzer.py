"""GitHub Copilot SDK を使ったLLM解析モジュール."""

import asyncio
import json
import logging
from types import TracebackType
from typing import Any

from copilot import CopilotClient, SessionEvent

from config import COPILOT_MODEL

logger = logging.getLogger(__name__)


def _custom_exception_handler(_: asyncio.AbstractEventLoop, context: dict) -> None:
    """asyncioのカスタム例外ハンドラー - copilotライブラリ内のAssertionErrorを抑制."""
    exception = context.get("exception")

    # copilot内部のAssertionErrorは無視
    if isinstance(exception, AssertionError) and any(
        "copilot" in str(part)
        for part in [
            context.get("message", ""),
            context.get("task"),
            context.get("future"),
        ]
    ):
        logger.debug("Suppressed copilot internal assertion error")
        return

    # その他のエラーは通常通りログに記録
    if exception:
        logger.error("Async exception: %s", exception, exc_info=exception)
    else:
        logger.error("Async error: %s", context.get("message", "Unknown error"))


class LLMAnalyzer:
    """GitHub Copilot SDKを使ったメトリクス解析."""

    def __init__(self, model: str = COPILOT_MODEL) -> None:
        """Initialize the LLMAnalyzer with a model."""
        self.model = model
        self.client = None

    async def __aenter__(self) -> "LLMAnalyzer":
        """非同期コンテキストマネージャのエントリ."""
        self.client = CopilotClient()
        await self.client.start()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """非同期コンテキストマネージャの終了."""
        if self.client:
            await self.client.stop()

    async def analyze_summary(
        self,
        summary: dict[str, Any],
        anomaly_result: dict[str, Any],
    ) -> str:
        """サマリメトリクスと異常検知結果をLLMで解析.

        Args:
            summary: メトリクスサマリ
            anomaly_result: 異常検知結果

        Returns:
            LLMの解析結果(テキスト)

        """
        prompt = self._build_summary_prompt(summary, anomaly_result)
        return await self._execute_analysis(prompt)

    async def analyze_detailed(
        self,
        summary: dict[str, Any],
        detailed: dict[str, Any],
        anomaly_result: dict[str, Any],
    ) -> str:
        """詳細メトリクスを含めてLLMで解析.

        Args:
            summary: メトリクスサマリ
            detailed: 詳細メトリクス
            anomaly_result: 異常検知結果

        Returns:
            LLMの解析結果(テキスト)

        """
        prompt = self._build_detailed_prompt(summary, detailed, anomaly_result)
        return await self._execute_analysis(prompt)

    def _build_summary_prompt(
        self,
        summary: dict[str, Any],
        anomaly_result: dict[str, Any],
    ) -> str:
        """サマリ解析用プロンプトを構築."""
        is_anomaly = anomaly_result.get("is_anomaly", False)
        anomalies = anomaly_result.get("anomalies", [])

        prompt = f"""以下はLinuxサーバーの監視メトリクスです。現在の状態を簡潔に要約してください。

## メトリクスサマリ
```json
{json.dumps(summary, indent=2, ensure_ascii=False)}
```

## 異常検知結果
- 異常検知: {"あり" if is_anomaly else "なし"}
- 異常件数: {len(anomalies)}件
- 重要度: {anomaly_result.get("severity", "normal")}

検知された異常:
"""
        for i, anomaly in enumerate(anomalies, 1):
            prompt += f"\n{i}. {anomaly['message']} (severity: {anomaly['severity']})"

        prompt += """

## 出力形式
以下の形式で簡潔に回答してください：

### 総合状態
(1-2行で現在の全体的な状態を説明)

### 主な問題点
(異常がある場合のみ、箇条書きで2-3項目)

### 推奨アクション
(必要に応じて、優先度の高いアクションを1-2項目)
"""
        return prompt

    def _build_detailed_prompt(
        self,
        summary: dict[str, Any],
        detailed: dict[str, Any],
        anomaly_result: dict[str, Any],
    ) -> str:
        """詳細解析用プロンプトを構築."""
        anomalies = anomaly_result.get("anomalies", [])

        prompt = f"""以下はLinuxサーバーで異常が検知された際の詳細メトリクスです。
根本原因の仮説と対処方法を提案してください。

## サマリメトリクス
```json
{json.dumps(summary, indent=2, ensure_ascii=False)}
```

## 詳細メトリクス
```json
{json.dumps(detailed, indent=2, ensure_ascii=False)}
```

## 検知された異常 ({len(anomalies)}件)
"""
        for i, anomaly in enumerate(anomalies, 1):
            prompt += f"\n{i}. [{anomaly['severity'].upper()}] {anomaly['message']}"
            if "value" in anomaly:
                prompt += f" (値: {anomaly['value']:.2f}"
                if "threshold" in anomaly:
                    prompt += f", 閾値: {anomaly['threshold']:.2f}"
                prompt += ")"

        prompt += """

## 出力形式
以下の形式で詳細に分析してください：

### 根本原因の仮説
(メトリクスから推測される根本原因を、優先度の高い順に2-3個)

### 影響範囲の推定
(この異常がシステムやアプリケーションに与える影響)

### 推奨する調査・対処手順
(優先度順に3-5項目、具体的なコマンドや確認ポイントを含む)

### 予防策
(今後同様の問題を防ぐための推奨事項を1-2項目)
"""
        return prompt

    async def _execute_analysis(self, prompt: str) -> str:
        """LLMにプロンプトを送信して結果を取得."""
        if not self.client:
            msg = "Client not started. Use async with context manager."
            raise RuntimeError(msg)

        session = await self.client.create_session(
            {
                "model": self.model,
                "streaming": False,  # 完全な結果を一度に取得
            },
        )

        try:
            # 結果を格納する変数
            result_content = []
            done = asyncio.Event()

            def on_event(event: SessionEvent) -> None:
                try:
                    if event.type.value == "assistant.message":
                        result_content.append(event.data.content)
                    elif event.type.value == "session.idle":
                        done.set()
                    elif event.type.value == "session.error":
                        error_msg = event.data.message
                        logger.error("LLM Error: %s", error_msg)
                        done.set()
                except (AttributeError, KeyError, TypeError) as e:
                    # イベント処理中のエラーを記録するが、処理は継続
                    logger.debug("Event handler error (non-critical): %s", e)

            session.on(on_event)
            await session.send({"prompt": prompt})

            # タイムアウトを設定して無限待機を防ぐ
            try:
                await asyncio.wait_for(done.wait(), timeout=120.0)
            except asyncio.TimeoutError:
                logger.warning("LLM応答待機がタイムアウトしました")
                # 部分的な結果でも返す

            return (
                "\n".join(result_content)
                if result_content
                else "解析結果を取得できませんでした。"
            )

        finally:
            await session.destroy()


def analyze_metrics_sync(
    summary: dict[str, Any],
    anomaly_result: dict[str, Any],
    detailed: dict[str, Any] | None = None,
) -> str:
    """同期的なラッパー関数(メインスクリプトから簡単に呼べるように).

    Args:
        summary: メトリクスサマリ
        anomaly_result: 異常検知結果
        detailed: 詳細メトリクス(異常時のみ)

    Returns:
        LLMの解析結果

    """

    async def _run() -> str:
        try:
            # カスタム例外ハンドラーを設定
            loop = asyncio.get_running_loop()
            loop.set_exception_handler(_custom_exception_handler)

            async with LLMAnalyzer() as analyzer:
                if detailed:
                    return await analyzer.analyze_detailed(
                        summary,
                        detailed,
                        anomaly_result,
                    )
                return await analyzer.analyze_summary(
                    summary,
                    anomaly_result,
                )
        except Exception:
            logger.exception("LLM解析中にエラー")
            raise

    return asyncio.run(_run())
