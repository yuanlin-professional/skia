# xcode - Xcode 管理模块

## 概述

`xcode` 模块负责管理 Apple Xcode 开发工具的安装和配置，确保 macOS 和 iOS 构建任务使用正确版本的 Xcode。

## 目录结构

```
xcode/
├── __init__.py    # DEPS 依赖声明
├── api.py         # XcodeApi 核心类
└── examples/      # 使用示例和测试
```

## 关键文件

### api.py
提供 Xcode 管理功能，包括：
- 安装指定版本的 Xcode
- 切换活动 Xcode 版本
- 配置 iOS 开发环境

## 依赖关系

DEPS: 依赖 `recipe_engine` 中的相关模块。

## 相关文档与参考

- `infra/bots/README.recipes.md` 中 `xcode` 模块的 API 文档
- `infra/bots/assets/xcode-11.4.1/` - Xcode 版本资源
