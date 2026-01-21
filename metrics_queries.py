"""Prometheusクエリ定義."""

from config import QUERY_RANGE

# 基本サマリメトリクス (毎時必ず取得)
SUMMARY_QUERIES = {
    # 観測健全性
    "up": "up",
    "scrape_duration": "scrape_duration_seconds",
    # CPU
    "cpu_usage": (
        f'100 * (1 - avg(rate(node_cpu_seconds_total{{mode="idle"}}[{QUERY_RANGE}])))'
    ),
    "cpu_iowait": (
        f'100 * avg(rate(node_cpu_seconds_total{{mode="iowait"}}[{QUERY_RANGE}]))'
    ),
    "load1": "node_load1",
    "load5": "node_load5",
    "load15": "node_load15",
    # メモリ
    "memory_usage": """100 * (1 - (
        node_memory_MemFree_bytes +
        node_memory_Cached_bytes +
        node_memory_Buffers_bytes +
        node_memory_SReclaimable_bytes
    ) / node_memory_MemTotal_bytes)""",
    "swap_usage": (
        "100 * (1 - node_memory_SwapFree_bytes / node_memory_SwapTotal_bytes)"
    ),
    # ディスクI/O
    "disk_read_bytes_per_sec": (
        f"sum(rate(node_disk_read_bytes_total[{QUERY_RANGE}]))"
    ),
    "disk_write_bytes_per_sec": (
        f"sum(rate(node_disk_written_bytes_total[{QUERY_RANGE}]))"
    ),
    "disk_io_util": (
        f"100 * sum(rate(node_disk_io_time_seconds_total[{QUERY_RANGE}]))"
    ),
    # ファイルシステム (使用率上位3つ)
    "fs_usage_top3": """topk(3, 100 * (1 - node_filesystem_avail_bytes{fstype!~"tmpfs|fuse.*"} /
                        node_filesystem_size_bytes{fstype!~"tmpfs|fuse.*"}))""",
    "fs_readonly": "max(node_filesystem_readonly)",
    # ネットワーク
    "network_rx_bytes_per_sec": (
        f"sum(rate(node_network_receive_bytes_total[{QUERY_RANGE}]))"
    ),
    "network_tx_bytes_per_sec": (
        f"sum(rate(node_network_transmit_bytes_total[{QUERY_RANGE}]))"
    ),
    "network_drop_per_sec": (
        f"sum(rate(node_network_receive_drop_total[{QUERY_RANGE}]) +"
        f" rate(node_network_transmit_drop_total[{QUERY_RANGE}]))"
    ),
    "network_err_per_sec": (
        f"sum(rate(node_network_receive_errs_total[{QUERY_RANGE}]) +"
        f" rate(node_network_transmit_errs_total[{QUERY_RANGE}]))"
    ),
    # TCP/ソケット
    "tcp_curr_estab": "node_netstat_Tcp_CurrEstab",
    "tcp_retrans_per_sec": (f"sum(rate(node_netstat_Tcp_RetransSegs[{QUERY_RANGE}]))"),
    "tcp_listen_overflow_per_sec": (
        f"sum(rate(node_netstat_TcpExt_ListenOverflows[{QUERY_RANGE}]) +"
        f" rate(node_netstat_TcpExt_ListenDrops[{QUERY_RANGE}]))"
    ),
}

# 詳細メトリクス (異常検知時のみ取得)
DETAILED_QUERIES = {
    # CPU詳細 (モード別)
    "cpu_by_mode": (
        f"100 * sum by (mode) (rate(node_cpu_seconds_total[{QUERY_RANGE}]))"
    ),
    "context_switches_per_sec": (f"rate(node_context_switches_total[{QUERY_RANGE}])"),
    # メモリ詳細
    "memory_active": "node_memory_Active_bytes",
    "memory_inactive": "node_memory_Inactive_bytes",
    "memory_cached": "node_memory_Cached_bytes",
    "memory_buffers": "node_memory_Buffers_bytes",
    "memory_slab": "node_memory_Slab_bytes",
    "memory_dirty": "node_memory_Dirty_bytes",
    # ディスク詳細 (デバイス別上位5つ)
    "disk_read_ops_top5": (
        f"topk(5, sum by (device) "
        f"(rate(node_disk_reads_completed_total[{QUERY_RANGE}])))"
    ),
    "disk_write_ops_top5": (
        f"topk(5, sum by (device) "
        f"(rate(node_disk_writes_completed_total[{QUERY_RANGE}])))"
    ),
    "disk_read_bytes_top5": (
        f"topk(5, sum by (device) (rate(node_disk_read_bytes_total[{QUERY_RANGE}])))"
    ),
    "disk_write_bytes_top5": (
        f"topk(5, sum by (device) (rate(node_disk_written_bytes_total[{QUERY_RANGE}])))"
    ),
    "disk_io_time_top5": (
        f"topk(5, sum by (device) "
        f"(rate(node_disk_io_time_seconds_total[{QUERY_RANGE}])))"
    ),
    # ファイルシステム詳細 (全マウントポイント)
    "fs_all_usage": """100 * (1 - node_filesystem_avail_bytes{fstype!~"tmpfs|fuse.*"} /
                       node_filesystem_size_bytes{fstype!~"tmpfs|fuse.*"})""",
    "fs_inodes_usage": (
        """100 * (1 - node_filesystem_files_free{fstype!~"tmpfs|fuse.*"} /
                          node_filesystem_files{fstype!~"tmpfs|fuse.*"})"""
    ),
    # ネットワーク詳細 (インターフェース別上位5つ)
    "network_rx_top5": (
        f"topk(5, sum by (device) "
        f"(rate(node_network_receive_bytes_total[{QUERY_RANGE}])))"
    ),
    "network_tx_top5": (
        f"topk(5, sum by (device) "
        f"(rate(node_network_transmit_bytes_total[{QUERY_RANGE}])))"
    ),
    "network_drop_top5": (
        f"topk(5, sum by (device) ("
        f"rate(node_network_receive_drop_total[{QUERY_RANGE}]) +"
        f" rate(node_network_transmit_drop_total[{QUERY_RANGE}])))"
    ),
    "network_err_top5": (
        f"topk(5, sum by (device) ("
        f"rate(node_network_receive_errs_total[{QUERY_RANGE}]) +"
        f" rate(node_network_transmit_errs_total[{QUERY_RANGE}])))"
    ),
    # TCP詳細
    "tcp_active_opens_per_sec": (f"rate(node_netstat_Tcp_ActiveOpens[{QUERY_RANGE}])"),
    "tcp_passive_opens_per_sec": (
        f"rate(node_netstat_Tcp_PassiveOpens[{QUERY_RANGE}])"
    ),
    "tcp_in_errs_per_sec": f"rate(node_netstat_Tcp_InErrs[{QUERY_RANGE}])",
    "tcp_out_rsts_per_sec": f"rate(node_netstat_Tcp_OutRsts[{QUERY_RANGE}])",
    "tcp_timeouts_per_sec": (f"rate(node_netstat_TcpExt_TCPTimeouts[{QUERY_RANGE}])"),
    # ソケット詳細
    "sockets_used": "node_sockstat_sockets_used",
    "tcp_alloc": "node_sockstat_TCP_alloc",
    "tcp_inuse": "node_sockstat_TCP_inuse",
    "tcp_orphan": "node_sockstat_TCP_orphan",
    "tcp_tw": "node_sockstat_TCP_tw",
}
