# recipe_modules - Skia Recipe 共享模块

## 概述

`recipe_modules/` 目录包含 Skia 专用的 Recipe 模块，供 `recipes/` 目录中的顶层 Recipe 脚本使用。这些模块封装了构建、测试、部署等常用功能，实现了代码复用和关注点分离。

每个 Recipe 模块包含以下标准文件：
- `api.py` - 模块的核心实现（API 类）
- `__init__.py` - 包含 `DEPS` 变量，声明对其他模块的依赖
- `examples/` - 使用示例和模拟测试

## 目录结构

```
recipe_modules/
├── build/                   # 多平台构建模块
├── builder_name_schema/     # 构建器名称解析模块
├── checkout/                # 代码检出模块
├── docker/                  # Docker 操作模块
├── doxygen/                 # Doxygen 文档生成模块
├── env/                     # 环境变量管理模块
├── flavor/                  # 平台特定行为抽象模块
├── git/                     # Git 操作模块
├── gold_upload/             # Gold 结果上传模块
├── gsutil/                  # Google Cloud Storage 操作模块
├── infra/                   # 基础设施工具模块
├── run/                     # 命令运行模块
├── vars/                    # 全局变量模块
├── xcode/                   # Xcode 管理模块
└── README.md                # 原始说明文档
```

## 模块概览

| 模块 | 说明 |
|------|------|
| `build` | 多平台 Skia 构建（Android、Chromebook、CanvasKit、CMake、Docker、默认） |
| `builder_name_schema` | 从任务/构建器名称中推断预期行为 |
| `checkout` | 代码仓库检出和同步 |
| `docker` | Docker 容器操作 |
| `doxygen` | Doxygen API 文档生成 |
| `env` | 环境变量和路径设置 |
| `flavor` | 平台无关的高级命令抽象（由具体 flavor 处理平台细节） |
| `git` | Git 版本控制操作 |
| `gold_upload` | 将测试结果上传到 Skia Gold |
| `gsutil` | Google Cloud Storage 文件操作 |
| `infra` | 共享的基础设施工具 |
| `run` | 命令执行工具 |
| `vars` | Skia Recipe/模块使用的全局变量 |
| `xcode` | Apple Xcode 安装和管理 |

## 修改指南

修改 Recipe 模块后需要重新训练模拟测试：

```bash
python infra/bots/infra_tests.py --train
# 或
cd infra/bots && make train
```

## 依赖关系

- Recipe Engine（`recipe_engine` 包）
- depot_tools Recipe 模块（`depot_tools` 包）
- 模块之间存在内部依赖（通过 `__init__.py` 中的 `DEPS` 声明）

## 相关文档与参考

- `infra/bots/README.recipes.md` - 自动生成的 Recipe API 文档
- [Recipe Engine 文档](https://chromium.googlesource.com/infra/luci/recipes-py/)
