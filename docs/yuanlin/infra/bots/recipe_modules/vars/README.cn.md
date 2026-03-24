# vars - 全局变量模块

## 概述

`vars` 模块定义了 Skia Recipe 和模块共用的全局变量，包括路径配置、平台信息、构建参数等。它是其他模块的基础依赖之一，几乎所有 Recipe 都会使用此模块。

## 目录结构

```
vars/
├── __init__.py    # DEPS 依赖声明
├── api.py         # VarsApi 核心类
├── examples/      # 使用示例和测试
└── resources/     # 辅助资源脚本
```

## 关键文件

### api.py
定义并管理全局变量，包括：
- 工作目录路径
- 平台和架构信息
- 构建配置参数
- 构建器名称解析结果
- 资源路径映射

## 依赖关系

DEPS: 依赖 `builder_name_schema` 和 `recipe_engine` 中的相关模块。

## 相关文档与参考

- `infra/bots/README.recipes.md` 中 `vars` 模块的 API 文档
