# env - 环境变量管理模块

## 概述

`env` 模块负责管理 Recipe 执行过程中的环境变量配置。它确保各平台和配置下的工具路径、编译器设置等环境变量被正确设置。

## 目录结构

```
env/
├── __init__.py    # DEPS 依赖声明
├── api.py         # EnvApi 核心类
└── examples/      # 使用示例和测试
```

## 关键文件

### api.py
提供环境变量管理接口，包括：
- PATH 路径追加
- 编译器和工具链路径设置
- 平台特定的环境配置

## 依赖关系

DEPS: 依赖 `recipe_engine` 中的相关模块。

## 相关文档与参考

- `infra/bots/README.recipes.md` 中 `env` 模块的 API 文档
