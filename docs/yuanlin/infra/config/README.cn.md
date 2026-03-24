# config - Recipe 引擎配置

## 概述

`config/` 目录包含 Skia Recipe 引擎的项目级配置文件，定义了 Recipe 系统的依赖版本和项目标识信息。

## 目录结构

```
config/
└── recipes.cfg   # Recipe 引擎配置
```

## 关键文件

### recipes.cfg

JSON 格式的 Recipe 引擎配置，包含：
- `api_version` - Recipe API 版本（当前为 2）
- `project_id` - 项目标识（"skia"）
- `recipes_path` - Recipe 脚本路径（"infra/bots"）
- `deps` - 外部依赖：
  - `depot_tools` - Chrome 开发工具集（提供 gclient、git 等 Recipe 模块）
  - `recipe_engine` - Recipe 执行引擎（来自 LUCI recipes-py）
- `autoroll_recipe_options` - 自动滚动（autoroll）Recipe 更新的配置

## 依赖关系

- 被 `recipes.py` 和 Recipe 引擎在执行 Recipe 时读取
- 定义了对 `depot_tools` 和 `recipe_engine` 的版本锁定

## 相关文档与参考

- [Recipe Engine](https://chromium.googlesource.com/infra/luci/recipes-py/)
- `infra/bots/recipes.py` - Recipe 运行工具
