# create.py

> 源文件: infra/bots/assets/lottie-samples/create.py

## 概述

`create.py` 是 Lottie 样本资产的创建脚本模板。**注意：该脚本当前未实现**，仅包含占位符代码抛出 `NotImplementedError`。

## 架构位置

Lottie 是一种基于 JSON 的动画格式，Skia 的 Lottie 模块（SkLottie）可以渲染 Lottie 动画。该资产应包含用于测试和基准测试的 Lottie 动画样本文件。

## 公共 API 函数

### create_asset(target_dir)
```python
def create_asset(target_dir):
    """Create the asset."""
    raise NotImplementedError('Implement me!')
```

**当前状态**: 未实现，调用时会抛出 `NotImplementedError`。

**预期实现**: 应该下载或收集 Lottie JSON 动画文件到目标目录。

## 内部实现细节

### 未实现状态
该脚本是一个模板骨架，需要补充实现：
1. 定义 Lottie 样本的来源（GitHub 仓库、URL 列表等）
2. 下载或克隆样本文件
3. 组织文件结构
4. 可能需要过滤或验证文件

### 可能的实现方案

**方案 1: 从 GitHub 克隆**
```python
LOTTIE_SAMPLES_REPO = 'https://github.com/airbnb/lottie-samples.git'
subprocess.check_call(['git', 'clone', LOTTIE_SAMPLES_REPO, target_dir])
```

**方案 2: 下载特定文件**
```python
SAMPLE_URLS = [
    'https://example.com/sample1.json',
    'https://example.com/sample2.json',
]
for url in SAMPLE_URLS:
    filename = url.split('/')[-1]
    subprocess.check_call(['wget', '-P', target_dir, url])
```

## 依赖关系

当前无依赖（未实现）。实现后可能需要：
- **git**: 如果从仓库克隆
- **wget/curl**: 如果下载文件
- **`utils`**: Skia 工具模块

## 设计模式与设计决策

### 模板模式
该文件是新资产的模板，提供标准结构：
- 命令行参数解析（`--target_dir`）
- 主函数入口点
- 资产创建函数

### 延迟实现
保留未实现的脚本可能是因为：
- Lottie 样本通过其他方式管理（手动上传）
- 样本来源尚未确定
- 等待 SkLottie 团队提供样本集

## 性能考量

无（未实现）。实现后性能取决于样本集大小和下载方式。

## 相关文件

- **`modules/skottie/`**: Skia 的 Lottie 渲染模块
- **`modules/skottie/tests/`**: Lottie 测试文件
- **Lottie 规范**: `https://lottiefiles.github.io/lottie-docs/`
- **Airbnb Lottie**: `https://airbnb.design/lottie/`

## 使用建议

如果需要实现该脚本：
1. 确定 Lottie 样本的官方来源
2. 选择合适的文件集（避免过大）
3. 实现下载和组织逻辑
4. 测试资产创建流程
5. 更新版本信息（添加 `version.txt`）
