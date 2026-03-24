# scripts 资产管理通用模块

> 源文件: infra/bots/assets/scripts/common.py

## 概述

资产管理脚本的共享工具模块，提供路径设置和命令调用功能。该模块被 create.py、upload.py、download.py 等脚本导入，统一处理 Python 导入路径和资产名称识别。

## 架构位置

位于 `infra/bots/assets/scripts/`，是资产管理系统的核心工具模块，为所有资产包提供基础设施。

## 主要类与结构体

模块级变量和函数。

### 模块级变量

```python
FILE_DIR = os.path.dirname(os.path.abspath(__file__))  # 脚本所在目录
INFRA_BOTS_DIR = os.path.realpath(os.path.join(FILE_DIR, os.pardir, os.pardir))  # infra/bots/
ASSET_NAME = os.path.basename(FILE_DIR)  # 资产名称，从目录名推断
```

### 导入路径设置

```python
sys.path.insert(0, INFRA_BOTS_DIR)
from assets import assets
```

将 `infra/bots/` 添加到 sys.path，使得可以导入 assets 模块。

## 公共 API 函数

### `run(cmd)`

执行资产管理命令的通用函数。

**参数**:
- `cmd` (str): 命令名称，如 'upload' 或 'download'

**功能**:
调用 `assets.main()` 并传递：
- 命令名称
- 资产名称（从目录名自动推断）
- 命令行参数

**实现**:
```python
def run(cmd):
    assets.main([cmd, ASSET_NAME] + sys.argv[1:])
```

## 内部实现细节

### 自动资产名称识别

通过 `os.path.basename(FILE_DIR)` 自动识别资产名称，避免硬编码。例如：
- 在 `infra/bots/assets/mockery/` 中，ASSET_NAME 为 'mockery'
- 在 `infra/bots/assets/bloaty/` 中，ASSET_NAME 为 'bloaty'

### 参数传递

`sys.argv[1:]` 将脚本的命令行参数透传给 assets.main()，支持如 `--gsutil`, `--target_dir` 等选项。

### 路径解析

```python
INFRA_BOTS_DIR = os.path.realpath(os.path.join(FILE_DIR, os.pardir, os.pardir))
```

从 `infra/bots/assets/scripts/` 上溯两级到 `infra/bots/`。

## 设计模式与设计决策

### 约定优于配置

使用目录名作为资产名称，遵循约定优于配置原则。这种设计：
- 减少重复配置
- 降低出错概率
- 提升一致性

### 单一入口点

所有资产管理命令通过 `assets.main()` 统一处理，便于：
- 集中日志记录
- 统一错误处理
- 共享配置和状态

## 相关文件

- `infra/bots/assets/assets.py`: 核心资产管理逻辑
- 各资产包的 upload.py, download.py, create.py: 使用该模块的脚本

该模块是 Skia 资产管理基础设施的关键粘合层，使得各资产包可以复用通用功能。
