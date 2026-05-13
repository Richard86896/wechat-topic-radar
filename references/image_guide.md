# 配图与环境变量指南

## 配图脚本

调用 `scripts/generate_image.py` 使用 Replicate API 生成配图。

需要设置环境变量 `REPLICATE_API_TOKEN`：
```bash
export REPLICATE_API_TOKEN="your_api_token_here"
```

## 配图流程

1. **生成提示词**：根据选题内容，从 `references/image_prompts.md` 读取模板
2. **调用API**：`python3 scripts/generate_image.py --prompt "..." --output path`
3. **保存图片**：`04.选题决策/每日选题/images/`

## 支持的配图尺寸

| 用途 | 尺寸 | 宽高比 |
|------|------|--------|
| 封面图 | 900x383 | 2.35:1 |
| 文中图 | 800x600 | 4:3 |
| 结尾图 | 800x400 | 2:1 |
| 朋友圈图 | 1080x1080 | 1:1 |

## 环境变量配置

| 变量名 | 说明 | 获取方式 |
|--------|------|----------|
| `REPLICATE_API_TOKEN` | Replicate API密钥 | https://replicate.com/account/api-tokens |

配置方法：
```bash
# macOS/Linux
export REPLICATE_API_TOKEN="your_token_here"

# 永久保存
echo 'export REPLICATE_API_TOKEN="your_token_here"' >> ~/.zshrc
source ~/.zshrc
```
