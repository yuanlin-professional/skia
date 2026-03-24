# Skia SVG 工具

## 概述

`tools/svg` 提供了 Skia SVG 测试所需的资源管理工具。该模块包含用于渲染正确性测试和 SVG 解析测试的 SVG 文件 URL 列表，以及一个自动化下载脚本。这些 SVG 资源被 Skia 的测试基础设施用于验证 SVG 模块的渲染正确性和解析器的健壮性。

## 目录结构

```
tools/svg/
├── README.md              # 英文使用说明
├── svg_downloader.py      # SVG 文件自动下载脚本
├── svgs.txt               # SVG 渲染测试 URL 列表（约 22KB）
├── svg_images.txt         # SVG 引用的图片资源 URL 列表
└── svgs_parse_only.txt    # SVG 解析测试 URL 列表
```

## 文件说明

### svgs.txt

包含用于渲染正确性测试的 SVG 文件 URL 列表：

- 每行一个 URL
- 文件较大（约 22KB），包含大量测试 SVG
- 这些 SVG 会被完整渲染并与预期结果比较
- 覆盖各种 SVG 特性：路径、渐变、滤镜、文本、动画等

### svg_images.txt

包含 SVG 文件引用的外部图片资源 URL：

- 每行一个图片 URL
- 与 svgs.txt 中的 SVG 配合使用
- SVG 可能通过 `<image>` 元素引用外部图片

### svgs_parse_only.txt

包含仅用于解析测试的 SVG 文件 URL：

- 每行一个 URL
- 这些 SVG 仅测试解析器的正确性，不验证渲染结果
- 通常包含语法复杂或边界条件的 SVG 文件
- 用于测试解析器不会崩溃或产生未定义行为

## svg_downloader.py

自动化 SVG 和图片资源下载脚本。

### 基本用法

```bash
# 下载渲染测试 SVG 到指定目录
python tools/svg/svg_downloader.py --output_dir /tmp/svgs/
```

### 下载解析测试 SVG

```bash
python tools/svg/svg_downloader.py \
  --output_dir /tmp/svgs/ \
  --input_file svgs_parse_only.txt \
  --prefix svgparse_
```

### 保留 URL 路径层级

```bash
python tools/svg/svg_downloader.py \
  --output_dir /tmp/svgs/ \
  --keep_common_prefix
```

使用 `--keep_common_prefix` 参数时，URL 公共前缀之后的路径结构将保留在目标目录中。例如：

- `https://example.com/images/a.png` -> `output_dir/a.png`
- `https://example.com/images/subdir/b.png` -> `output_dir/subdir/b.png`

### 主要参数

| 参数 | 说明 |
|------|------|
| `--output_dir` | 下载文件的输出目录 |
| `--input_file` | 要解析的 URL 列表文件（默认 svgs.txt） |
| `--prefix` | 下载文件名的前缀 |
| `--keep_common_prefix` | 保留 URL 的目录层级结构 |

## 测试流程

```
1. 使用 svg_downloader.py 下载 SVG 文件
2. Skia 测试工具加载下载的 SVG
3. 渲染测试：
   a. 通过 SkSVGDOM 解析和渲染 SVG
   b. 将渲染结果与参考图像比较
   c. 报告差异和回归
4. 解析测试：
   a. 通过 SkSVGDOM 解析 SVG
   b. 验证解析不崩溃
   c. 检查解析结果的完整性
```

## 与其他模块的关系

- **modules/svg/**: SkSVGDOM SVG 解析和渲染引擎
- **modules/skshaper/**: SVG 文本渲染依赖的文本整形引擎
- **tools/skdiff/**: SVG 渲染结果的视觉比较
- **dm**: DM 测试工具执行 SVG 渲染测试
- **src/xml/**: XML 解析基础设施
