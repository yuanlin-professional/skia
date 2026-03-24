# doxygen - Doxygen 文档生成模块

## 概述

`doxygen` 模块封装了使用 Doxygen 工具从 Skia 源代码生成 API 文档的功能。它是维护任务（housekeeper）的一部分，确保 API 文档与代码保持同步。

## 目录结构

```
doxygen/
├── __init__.py    # DEPS 依赖声明
├── api.py         # DoxygenApi 核心类
├── examples/      # 使用示例和测试
└── resources/     # 辅助资源脚本
```

## 关键文件

### api.py
实现 Doxygen 文档生成的逻辑，包括配置 Doxygen 参数和执行文档构建。

## 依赖关系

DEPS: 依赖 `recipe_engine` 中的相关模块。

## 相关文档与参考

- `infra/bots/README.recipes.md` 中 `doxygen` 模块的 API 文档
