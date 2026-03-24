# create.py

> 源文件: infra/bots/assets/gsutil/create.py

## 概述

`create.py` 用于创建 `gsutil` 工具资产。`gsutil` 是 Google Cloud Storage 的命令行工具，Skia 使用它在 CI 系统中上传和下载构建产物、测试结果和资产文件。

## 架构位置

该资产为 Skia 的持续集成系统提供 GCS 访问能力，用于存储和检索大文件。

## 公共 API 函数

### create_asset(target_dir)
从 Google Cloud 下载 gsutil ZIP 包，解压并验证版本，然后移动到目标目录。

**实现**：
```python
def create_asset(target_dir):
    with utils.tmp_dir():
        subprocess.run(["curl", URL, "--output", "gsutil.zip"], check=True)
        subprocess.run(["unzip", "gsutil.zip"], check=True)
        with open("./gsutil/VERSION", "r") as f:
            version = f.read().strip()
            if version != VERSION:
                raise RuntimeError("Version mismatch")
        shutil.move('./gsutil', target_dir)
```

## 内部实现细节

### 版本验证
下载后读取 `VERSION` 文件并与期望版本对比：
```python
VERSION = "5.25"
```
确保下载的是预期版本，避免自动更新导致的意外变化。

### 下载源
```python
URL = "https://storage.googleapis.com/pub/gsutil.zip"
```
从 Google 官方存储下载，确保可靠性和安全性。

### 目录移动
使用 `shutil.move` 而非 `subprocess mv`，提供更好的跨平台兼容性。

## 依赖关系

- **curl**: HTTP 下载工具
- **unzip**: ZIP 解压工具
- **Python 3**: 脚本使用 Python 3 语法
- **`utils`**: Skia 工具模块（提供 `tmp_dir`）

## 设计模式与设计决策

### 版本固定策略
硬编码版本号并验证，确保：
- 构建可重复性
- 避免 API 变更破坏 CI
- 手动控制更新时机

### 临时目录模式
在临时目录中下载和解压，失败时自动清理。

## 性能考量

- **下载时间**: 10-30 秒（~10 MB）
- **解压时间**: 2-5 秒
- **总时间**: 15-40 秒
- **磁盘空间**: ~30 MB

## 相关文件

- **gsutil 文档**: `https://cloud.google.com/storage/docs/gsutil`
- **构建脚本**: `infra/bots/recipes/` 中使用 gsutil 上传结果
- **相关工具**: `gcloud_linux/create.py`（完整 Cloud SDK）
