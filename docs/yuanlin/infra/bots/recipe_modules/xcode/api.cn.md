# Xcode Recipe Module API

> 源文件: `infra/bots/recipe_modules/xcode/api.py`

## 概述

`api.py` 实现了 `SkiaXCodeApi` 配方模块，提供 Xcode 的版本管理和自动安装功能。它使用 `mac_toolchain` 工具从 CIPD 获取指定版本的 Xcode，并通过 `xcode-select` 激活。

## 架构位置

位于 `infra/bots/recipe_modules/xcode/` 目录，被 macOS/iOS 编译和测试任务使用。

## 主要类与结构体

- **`SkiaXCodeApi`** (recipe_api.RecipeApi): Xcode 管理 API
  - `XCODE_BUILD_VERSION = '16a242d'`: Xcode 16.0 版本号

## 公共 API 函数

- **`version`** (属性): 返回当前 Xcode 构建版本号
- **`path`** (属性): 返回 Xcode.app 安装路径（缓存目录下）
- **`install()`**: 安装并激活指定版本的 Xcode

## 内部实现细节

1. `install()` 的嵌套步骤 "ensure xcode":
   - 检查 `mac_toolchain` 是否存在，不存在则通过 CIPD 下载
   - 使用固定版本的 `mac_toolchain`（`git_revision:0cb1e51344...`）
   - 查找 CIPD 下载路径（通过 listdir 搜索）
   - 调用 `mac_toolchain install -kind ios -xcode-version <version> -output-dir <path>`
   - 使用 `sudo xcode-select -switch` 激活 Xcode

## 依赖关系

- `recipe_engine/cipd`: CIPD 包管理
- `recipe_engine/file`: 文件操作
- `recipe_engine/path`: 路径管理
- `recipe_engine/step`: 步骤执行
- `vars`: Skia 变量（workdir, cache_dir）

## 设计模式与设计决策

- 延迟安装: 仅在 `install()` 被调用时安装 Xcode
- 版本固定: `mac_toolchain` 使用 git revision 固定版本
- iOS 模式: `-kind ios` 确保包含 iOS 模拟器支持

## 性能考量

- Xcode 安装路径使用缓存目录，避免重复下载
- mac_toolchain 支持增量更新

## 相关文件

- `infra/bots/recipe_modules/xcode/__init__.py`: 模块初始化
- `infra/bots/recipe_modules/xcode/examples/full.py`: 使用示例
