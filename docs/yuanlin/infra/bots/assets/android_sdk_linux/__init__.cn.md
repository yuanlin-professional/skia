# Android SDK Linux 包初始化文件

> 源文件: infra/bots/assets/android_sdk_linux/__init__.py

## 概述

标准的 Python 包初始化文件，将 `android_sdk_linux` 目录标识为 Python 包。文件内容仅包含版权声明和许可证信息，无可执行代码，是 Python 包管理的标准实践。

## 架构位置

位于 `infra/bots/assets/android_sdk_linux/`，使该目录成为可导入的 Python 包，允许包内模块相互引用。

## 主要类与结构体

无类、函数或变量定义，仅有：
- 版权声明（Copyright 2021 Google LLC）
- BSD 许可证引用

## 公共 API 函数

无。该文件不导出任何接口。

## 内部实现细节

### Python 包机制

空的 `__init__.py` 文件的作用：
1. 标识目录为 Python 包
2. 允许从包中导入模块
3. 定义包的命名空间

**示例用途**:
```python
from android_sdk_linux import create
from android_sdk_linux.create import create_asset, ENV_VAR
```

### 显式包标识

虽然 Python 3.3+ 支持隐式命名空间包，Skia 项目选择显式 `__init__.py`：
- 向后兼容 Python 2.7
- 明确的包结构
- 更好的工具支持

## 依赖关系

无外部依赖。使包内的以下文件可作为模块导入：
- `create.py`
- `create_and_upload.py`
- `download.py`

## 设计模式与设计决策

### 最小化原则

保持文件为空（除版权信息）：
- 无导入时副作用
- 最小化加载时间
- 避免不必要的复杂性

### 一致性

Skia 项目中所有资产包都使用相同的模式：
- 每个包含 `__init__.py`
- 内容最小化
- 统一的版权声明

## 性能考量

空文件对性能影响可忽略不计，导入时间小于 1ms。

## 相关文件

### 同包文件

- `create.py`: 核心资产创建逻辑
- `create_and_upload.py`: 创建和上传编排
- `download.py`: 资产下载脚本

### 相似包

其他资产包的 `__init__.py`：
- `infra/bots/assets/android_ndk_linux/__init__.py`
- `infra/bots/assets/win_toolchain/__init__.py`

所有遵循相同的最小化设计模式。
