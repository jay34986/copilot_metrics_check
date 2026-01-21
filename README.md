# Copilot Metrics Check

Grafana Cloud Prometheus のメトリクスを取得し、異常検知とGitHub Copilotによる解析を行うツールです。

## 概要

- **毎時サマリ**: 基本的なサーバーメトリクスを取得してLLMで状態を要約
- **異常時詳細**: 閾値を超えた異常を検知した場合、詳細メトリクスを取得して根本原因を分析
- **GitHub Copilot SDK**: GitHub Copilot SDK を使用してメトリクスを解析（デフォルトモデル: gpt-5-mini）

## セットアップ

### 1. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 2. 環境変数の設定

`.env.example` をコピーして `.env` を作成し、必要な情報を設定します。

```bash
cp .env.example .env
```

`.env` ファイルを編集：

```bash
# GitHub Copilot設定
COPILOT_MODEL=gpt-5-mini

# Grafana Cloud Prometheus設定
INSTANCE_ID=XXXXXXX
PROM_URL=https://prometheus-prod-XX-prod-ap-southeast-1.grafana.net/api/prom
API_KEY=your_api_key_here

# 異常検知の閾値（必要に応じて調整）
THRESHOLD_CPU_USAGE=80
THRESHOLD_MEMORY_USAGE=85
THRESHOLD_SWAP_USAGE=50
THRESHOLD_DISK_USAGE=90
THRESHOLD_IOWAIT=20
THRESHOLD_LOAD1_PER_CPU=2.0
THRESHOLD_NETWORK_ERRORS_PER_SEC=10
THRESHOLD_TCP_RETRANS_PER_SEC=50
```

### 3. GitHub Copilot SDKの認証

GitHub Copilot SDKを使用するには、Copilot CLIが必要です。

```bash
# Copilot CLI のインストール
curl -fsSL https://gh.io/copilot-install | bash

# 認証
copilot
/login
```

## 使用方法

### 基本実行（毎時サマリ＋異常時詳細）

```bash
python main.py
```

実行内容：

1. Prometheusからサマリメトリクスを取得
2. 異常検知を実行
3. 異常がある場合のみ詳細メトリクスを取得
4. LLMで解析（サマリのみ or 詳細込み）
5. 結果を `output/` ディレクトリに保存

### 強制的に詳細解析を実行

```bash
python main.py --detailed
```

異常がなくても詳細メトリクスを取得してLLM解析を行います。

## 出力ファイル

すべての結果は `output/` ディレクトリに保存されます。

- `metrics_YYYYMMDD_HHMMSS.json`: 全体の解析結果
- `anomaly_YYYYMMDD_HHMMSS.json`: 異常検知時のログ（異常時のみ）

## cronでの定期実行

毎時00分に実行する例：

```bash
# crontabを編集
crontab -e

# 以下を追加（パスは適宜調整）
0 * * * * cd /path/to/copilot_metrics_check && /usr/bin/python3 main.py >> logs/cron.log 2>&1
```

## ファイル構成

```bash
.
├── main.py                   # メインスクリプト
├── prometheus_client.py      # Prometheus APIクライアント
├── metrics_queries.py        # PromQLクエリ定義
├── anomaly_detector.py       # 異常検知ロジック
├── llm_analyzer.py          # Copilot SDKを使ったLLM解析
├── config.py                # 設定管理
├── utils.py                 # ユーティリティ関数（フォーマット等）
├── requirements.txt         # 依存パッケージ
├── .env.example            # 環境変数サンプル
├── .env                    # 環境変数（gitignore対象）
├── README.md
└── output/                 # 結果出力ディレクトリ
    ├── metrics_*.json      # 全体の解析結果
    └── anomaly_*.json      # 異常検知時のログ（異常時のみ）
```

## 取得メトリクス

### サマリメトリクス（毎時取得）

- **観測健全性**: up, scrape_duration
- **CPU**: 使用率, iowait, load average
- **メモリ**: 使用率, swap使用率
- **ディスクI/O**: 読み書きスループット, utilization
- **ファイルシステム**: 使用率上位3つ, readonly状態
- **ネットワーク**: 受信/送信バイト数, エラー/ドロップ
- **TCP**: 確立済み接続数, 再送, listen overflow

### 詳細メトリクス（異常時のみ取得）

- CPU詳細（モード別、コンテキストスイッチ）
- メモリ詳細（active/inactive/cached/slab/dirtyなど）
- ディスク詳細（デバイス別I/O、上位5デバイス）
- ファイルシステム詳細（全マウントポイント、inode使用率）
- ネットワーク詳細（インターフェース別、上位5デバイス）
- TCP詳細（active/passive opens, timeoutなど）
- ソケット詳細（alloc/inuse/orphan/tw）

## 異常検知の閾値

`.env` ファイルで調整可能：

- `THRESHOLD_CPU_USAGE`: CPU使用率（デフォルト: 80%）
- `THRESHOLD_MEMORY_USAGE`: メモリ使用率（デフォルト: 85%）
- `THRESHOLD_SWAP_USAGE`: スワップ使用率（デフォルト: 50%）
- `THRESHOLD_DISK_USAGE`: ディスク使用率（デフォルト: 90%）
- `THRESHOLD_IOWAIT`: iowait割合（デフォルト: 20%）
- `THRESHOLD_NETWORK_ERRORS_PER_SEC`: ネットワークエラー（デフォルト: 10/秒）
- `THRESHOLD_TCP_RETRANS_PER_SEC`: TCP再送（デフォルト: 50/秒）

## トラブルシューティング

### Prometheus APIへの接続エラー

- `.env` の `INSTANCE_ID`, `PROM_URL`, `API_KEY` が正しいか確認
- ネットワーク接続を確認
- 手動でcurlテスト:

  ```bash
  curl -u "$INSTANCE_ID:$API_KEY" "$PROM_URL/api/v1/query?query=up"
  ```

## ライセンス

MIT
