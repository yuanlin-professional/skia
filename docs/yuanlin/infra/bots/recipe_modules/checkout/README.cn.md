# checkout - 代码检出模块

## 概述

`checkout` 模块负责从代码仓库检出 Skia 源代码并同步依赖。它封装了 `gclient sync` 和 Git 操作，确保构建机器上拥有正确版本的代码和第三方依赖。

## 目录结构

```
checkout/
├── __init__.py    # DEPS 依赖声明
├── api.py         # CheckoutApi 核心类
├── examples/      # 使用示例和测试
└── resources/     # 辅助资源脚本
```

## 关键文件

### api.py
实现代码检出的主要逻辑，包括：
- 仓库克隆/更新
- 依赖同步（gclient sync）
- 补丁应用（用于 Try Job）

## 依赖关系

DEPS: 依赖 `recipe_engine` 和 `depot_tools` 中的相关模块。

## 相关文档与参考

- `infra/bots/README.recipes.md` 中 `checkout` 模块的 API 文档
