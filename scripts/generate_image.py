#!/usr/bin/env python3
"""
文章配图生成脚本
使用 Replicate API 生成公众号文章配图

环境变量:
  REPLICATE_API_TOKEN: Replicate API 密钥

用法:
  python3 generate_image.py --prompt "你的图片描述" --output image.png
  python3 generate_image.py --test
"""

import argparse
import os
import sys
import urllib.request
import urllib.error
import json
import time


# Replicate API 配置
REPLICATE_API_BASE = "https://api.replicate.com"


def get_api_token():
    """获取 API Token"""
    token = os.environ.get("REPLICATE_API_TOKEN")
    if not token:
        print("错误: 请设置 REPLICATE_API_TOKEN 环境变量")
        print("  macOS/Linux: export REPLICATE_API_TOKEN=your_token")
        print("  Windows: $env:REPLICATE_API_TOKEN='your_token'")
        sys.exit(1)
    return token


def create_prediction(prompt: str, token: str) -> dict:
    """创建图片生成任务"""
    url = f"{REPLICATE_API_BASE}/v1/predictions"

    # 使用 Flux Schnell 模型 (快速生成)
    # 如需更高质量可使用 flux-dev
    data = {
        "version": "c846a69991daf4c0e5d016514849d14ee5b2e6846ce6b9d6f21369e564cfe51e",
        "input": {
            "prompt": prompt,
            "aspect_ratio": "16:9",
            "num_inference_steps": 4,
            "guidance_scale": 0,
            "num_outputs": 1
        }
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers=headers,
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else str(e)
        print(f"API 错误: {e.code} - {error_body}")
        sys.exit(1)


def get_prediction(prediction_id: str, token: str) -> dict:
    """获取预测结果"""
    url = f"{REPLICATE_API_BASE}/v1/predictions/{prediction_id}"

    headers = {
        "Authorization": f"Bearer {token}",
    }

    req = urllib.request.Request(url, headers=headers, method="GET")

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"获取结果错误: {e.code}")
        sys.exit(1)


def wait_for_completion(prediction_id: str, token: str, max_wait: int = 120) -> dict:
    """等待图片生成完成"""
    start_time = time.time()

    while True:
        if time.time() - start_time > max_wait:
            print("错误: 生成超时")
            sys.exit(1)

        prediction = get_prediction(prediction_id, token)

        status = prediction.get("status")

        if status == "succeeded":
            return prediction
        elif status == "failed":
            print(f"生成失败: {prediction.get('error')}")
            sys.exit(1)
        elif status == "canceled":
            print("生成已取消")
            sys.exit(1)

        # 显示进度
        logs = prediction.get("logs", [])
        if logs:
            print(f"  {logs[-1].get('message', '')}")

        print(f"  状态: {status}... (等待中)")
        time.sleep(3)


def download_image(url: str, output_path: str) -> None:
    """下载图片"""
    print(f"  下载到: {output_path}")

    # 确保输出目录存在
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)

    try:
        urllib.request.urlretrieve(url, output_path)
        print(f"  完成! 文件大小: {os.path.getsize(output_path) / 1024:.1f} KB")
    except urllib.error.HTTPError as e:
        print(f"  下载失败: {e.code}")
        sys.exit(1)


def generate_image(prompt: str, output_path: str, token: str) -> None:
    """生成图片主流程"""
    print(f"📝 提示词: {prompt}")
    print("-" * 50)

    # 1. 创建预测任务
    print("🚀 创建图片生成任务...")
    prediction = create_prediction(prompt, token)
    prediction_id = prediction.get("id")
    print(f"  任务ID: {prediction_id}")

    # 2. 等待完成
    print("⏳ 等待图片生成...")
    result = wait_for_completion(prediction_id, token)

    # 3. 获取结果
    output = result.get("output", {})
    if isinstance(output, list):
        image_url = output[0]
    else:
        image_url = output

    if not image_url:
        print("错误: 无法获取图片URL")
        sys.exit(1)

    # 4. 下载图片
    download_image(image_url, output_path)
    print("✅ 图片生成成功!")


def test_connection():
    """测试 API 连接"""
    print("🧪 测试 Replicate API 连接...")
    token = get_api_token()
    print(f"  Token: {token[:8]}...{token[-4:]}")

    url = f"{REPLICATE_API_BASE}/v1/models"

    headers = {
        "Authorization": f"Bearer {token}",
    }

    req = urllib.request.Request(url, headers=headers, method="GET")

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
            print(f"  ✅ 连接成功! 可用模型数: {len(data.get('results', []))}")
    except urllib.error.HTTPError as e:
        print(f"  ❌ 连接失败: {e.code}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="使用 Replicate API 生成公众号文章配图",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python3 generate_image.py --prompt "科技风格封面图" --output cover.png
  python3 generate_image.py --test

环境变量:
  export REPLICATE_API_TOKEN=your_token_here
        """
    )

    parser.add_argument(
        "--prompt", "-p",
        type=str,
        help="图片描述提示词"
    )

    parser.add_argument(
        "--output", "-o",
        type=str,
        default="output.png",
        help="输出文件路径 (默认: output.png)"
    )

    parser.add_argument(
        "--test", "-t",
        action="store_true",
        help="测试 API 连接"
    )

    args = parser.parse_args()

    if args.test:
        test_connection()
        return

    if not args.prompt:
        print("错误: 请提供 --prompt 参数")
        parser.print_help()
        sys.exit(1)

    token = get_api_token()
    generate_image(args.prompt, args.output, token)


if __name__ == "__main__":
    main()
