# git - Git 操作模块

## 概述

`git` 模块封装了 Skia CI 中常用的 Git 版本控制操作，提供了代码提交、分支管理和历史查询等功能的高级接口。

## 目录结构

```
git/
├── __init__.py    # DEPS 依赖声明
├── api.py         # GitApi 核心类
└── examples/      # 使用示例和测试
```

## 关键文件

### api.py
提供 Git 操作的高级接口，封装了常用的 git 命令。

## 依赖关系

DEPS: 依赖 `recipe_engine` 中的相关模块。

## 相关文档与参考

- `infra/bots/README.recipes.md` 中 `git` 模块的 API 文档
