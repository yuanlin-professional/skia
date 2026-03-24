# build - 多平台构建模块

## 概述

`build` 模块负责在各种目标平台上编译 Skia。它根据构建器名称自动选择合适的编译策略，支持 Android、Chromebook、CanvasKit（WASM）、CMake、Docker 和默认（桌面）构建。

## 目录结构

```
build/
├── __init__.py      # DEPS 依赖声明
├── api.py           # BuildApi 核心类
├── android.py       # Android 编译逻辑
├── canvaskit.py     # CanvasKit/WASM 编译逻辑
├── chromebook.py    # Chromebook 编译逻辑
├── cmake.py         # CMake 编译逻辑
├── default.py       # 默认桌面编译逻辑
├── docker.py        # Docker 容器内编译逻辑
├── util.py          # 编译工具函数
├── examples/        # 使用示例和测试
└── resources/       # 辅助资源
```

## 关键文件

### api.py

`BuildApi` 类是模块入口，根据构建器名称中的关键字选择编译策略：
- 包含 `Android`（且不含 `Flutter`） -> `android.compile_fn`
- 包含 `Chromebook` -> `chromebook.compile_fn`
- 包含 `EMCC`（且不含 `StandaloneWasm`） -> `canvaskit.compile_fn`
- 包含 `CMake` -> `cmake.compile_fn`
- 包含 `Docker` -> `docker.compile_fn`
- 其他 -> `default.compile_fn`

每个编译策略都实现了 `compile_fn` 和 `copy_build_products` 两个核心函数。

## 依赖关系

DEPS: `depot_tools/gclient`, `recipe_engine/cipd`, `recipe_engine/context`, `recipe_engine/file`, `recipe_engine/path`, `recipe_engine/step`, `docker`, `env`, `infra`, `run`, `vars`, `xcode`

## 相关文档与参考

- `infra/bots/README.recipes.md` 中 `build` 模块的 API 文档
