# infra - 基础设施工具模块

## 概述

`infra` Recipe 模块提供共享的基础设施工具函数，被其他 Recipe 和模块广泛使用。它包含了 CI 系统中常用的辅助功能，如环境准备、错误处理和通用操作。

## 目录结构

```
infra/
├── __init__.py    # DEPS 依赖声明
├── api.py         # InfraApi 核心类
├── examples/      # 使用示例和测试
└── resources/     # 辅助资源脚本
```

## 关键文件

### api.py
提供基础设施相关的通用工具函数，包括：
- CI 环境初始化和清理
- 通用的错误处理和重试机制
- CIPD 包安装管理
- Swarming 任务辅助功能

## 依赖关系

DEPS: 依赖 `recipe_engine` 中的相关模块。

## 相关文档与参考

- `infra/bots/README.recipes.md` 中 `infra` 模块的 API 文档
