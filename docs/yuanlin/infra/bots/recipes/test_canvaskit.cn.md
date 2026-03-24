# CanvasKit 测试 Recipe (test_canvaskit)

> 源文件: `infra/bots/recipes/test_canvaskit.py`

## 概述

此 recipe 使用 Docker 容器运行 CanvasKit 的自动化测试。CanvasKit 是 Skia 的 WebAssembly 构建版本，它将 Skia 的 C++ 图形引擎编译为 WASM 并通过 JavaScript API 暴露功能。测试在预配置的 Chrome 浏览器环境（通过 Karma 测试框架）中执行，测试结果通过 Gold（Skia 的视觉回归测试平台）进行图像比对。

## 架构位置

此 recipe 是 Skia CI 测试体系中 CanvasKit/WASM 模块的测试入口：

- **上游**: 编译 recipe 生成 `canvaskit.js` 和 `canvaskit.wasm`
- **执行环境**: Docker 容器 (`gold-karma-chrome-tests:87.0.4280.88_v2`)
- **下游**: Gold 上传（通过 `gold_upload` 模块）
- **测试框架**: Karma + Chrome

## 主要类与结构体

| 名称 | 类型 | 说明 |
|------|------|------|
| `DEPS` | 列表 | 依赖模块列表，包含 checkout、docker、gold_upload 等 |
| `DOCKER_IMAGE` | 常量 | Docker 镜像路径: `gcr.io/skia-public/gold-karma-chrome-tests:87.0.4280.88_v2` |
| `INNER_KARMA_SCRIPT` | 常量 | Docker 内部执行的 Karma 测试脚本路径 |

## 公共 API 函数

### `RunSteps(api)`

Recipe 入口，执行以下流程：
1. 初始化变量和 flavor 环境
2. 将编译产物（`canvaskit.js`、`canvaskit.wasm`）复制到 Karma 测试脚本期望的 `build/` 目录
3. 构建 Docker 运行参数（builder 名称、git hash、配置信息等）
4. 对 trybot 构建附加 issue/patchset 参数
5. 通过 `api.docker.run` 在 Docker 容器中执行 Karma 测试脚本（最多重试 3 次）
6. 上传 Gold 测试结果

### `GenTests(api)`

生成两个测试用例：
- 标准 CI 构建 (`Test-Debian10-EMCC-GCE-GPU-WEBGL1-wasm-Debug-All-CanvasKit`)
- Trybot 构建 (`canvaskit_trybot`)

## 内部实现细节

- **文件复制**: Karma 脚本固定从 `./build/` 目录加载测试文件，因此需要将 `canvaskit.js` 和 `canvaskit.wasm` 从构建目录复制到该位置
- **Docker 执行**: 使用 `api.docker.run` 封装 Docker 操作，传入源目录挂载、输出目录挂载、递归读取目录等
- **recursive_read**: 将整个 `skia/` 目录设为递归读取，使 Docker 容器内可以访问测试资源文件
- **重试机制**: `attempts=3` 允许最多 3 次重试，应对测试环境的偶发不稳定性
- **Gold 集成**: 通过 `--builder`、`--git_hash`、`--browser`、`--config`、`--source_type` 参数将构建元数据传递给测试，用于 Gold 结果标识

## 依赖关系

- **checkout** -- 代码检出模块
- **docker** -- Docker 容器运行模块
- **env** -- 环境变量管理
- **flavor** -- 设备抽象层
- **infra** -- 基础设施工具
- **gold_upload** -- Gold 结果上传模块
- **run** -- 步骤执行
- **vars** -- 构建变量
- **recipe_engine/file** -- 文件操作
- **recipe_engine/path** -- 路径操作
- **recipe_engine/properties** -- 构建属性
- **recipe_engine/step** -- 步骤执行

## 设计模式与设计决策

- **Docker 隔离**: 使用 Docker 容器提供一致的浏览器测试环境，避免宿主机环境差异导致的测试不稳定
- **固定 Chrome 版本**: Docker 镜像锁定了 Chrome 87.0.4280.88 版本，确保测试结果的可重复性
- **Gold 视觉比对**: 测试输出图像通过 Gold 平台进行视觉回归检测，而非简单的像素比对
- **文件复制而非符号链接**: 显式复制构建产物到 build/ 目录，确保 Docker 容器内路径一致

## 性能考量

- Docker 容器启动有一定开销，但提供了隔离的测试环境
- `mode=0o777` 设置目录权限确保 Docker 容器内的非 root 用户可以访问
- 重试机制（3 次）在牺牲少量时间的情况下提高了测试可靠性
- Gold 上传是异步的，不阻塞后续步骤

## 相关文件

- `infra/canvaskit/test_canvaskit.sh` -- Docker 容器内执行的 Karma 测试脚本
- `modules/canvaskit/` -- CanvasKit 源代码
- `infra/bots/recipe_modules/docker/` -- Docker 执行模块
- `infra/bots/recipe_modules/gold_upload/` -- Gold 上传模块
