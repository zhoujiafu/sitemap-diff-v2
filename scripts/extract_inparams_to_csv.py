#!/usr/bin/env python3
"""
从包含 `data.inParams` 的 JSON 文本文件中提取 `ip`、`time` 字段并导出为 CSV。

用法示例：
  python3 scripts/extract_inparams_to_csv.py \
    --input "/Users/yangjay/Desktop/临时目录/IP提数单跑崩溃的入参.txt" \
    --output "/Users/yangjay/Desktop/临时目录/IP提数单跑崩溃的入参.csv"

如果未指定 --output，将在输入文件同目录生成同名 .csv。
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys


def extract_to_csv(input_path: Path, output_path: Path | None = None) -> Path:
    """读取 JSON 文件，提取 data.inParams[*].(ip,time)，写入 CSV 并返回输出路径。

    - 对缺失字段以空字符串填充。
    - 如果输入不存在或格式异常，会抛出异常。
    """
    if not input_path.exists():
        raise FileNotFoundError(f"输入文件不存在: {input_path}")

    if output_path is None:
        output_path = input_path.with_suffix(".csv")

    # 读取并解析 JSON（文件较大时也足够轻量）
    with input_path.open("r", encoding="utf-8") as f:
        try:
            payload = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON 解析失败: {e}") from e

    # 定位到 inParams 数组
    data = payload.get("data", {}) if isinstance(payload, dict) else {}
    in_params = data.get("inParams", []) if isinstance(data, dict) else []
    if not isinstance(in_params, list):
        raise ValueError("data.inParams 不是数组，无法解析")

    # 提取行
    rows = []
    for item in in_params:
        if not isinstance(item, dict):
            continue
        ip_value = item.get("ip", "")
        time_value = item.get("time", "")
        rows.append({"ip": ip_value, "time": time_value})

    # 写出 CSV
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["ip", "time"])
        writer.writeheader()
        writer.writerows(rows)

    return output_path


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="从 JSON 文本中导出 data.inParams 的 ip、time 为 CSV")
    parser.add_argument(
        "--input",
        required=True,
        help="输入文件的绝对路径（包含 data.inParams 的 JSON 文本）",
    )
    parser.add_argument(
        "--output",
        required=False,
        help="输出 CSV 的绝对路径（可选，不填则与输入同名同目录，后缀为 .csv）",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    input_path = Path(args.input).expanduser()
    output_path = Path(args.output).expanduser() if args.output else None

    try:
        csv_path = extract_to_csv(input_path, output_path)
    except Exception as exc:  # noqa: BLE001 - 集中处理并给出中文提示
        print(f"导出失败: {exc}", file=sys.stderr)
        return 1

    print(f"已导出 CSV: {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))


