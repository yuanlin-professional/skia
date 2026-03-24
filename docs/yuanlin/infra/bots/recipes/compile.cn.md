# Skia 编译 Recipe (compile)

> 源文件: `infra/bots/recipes/compile.py`

## 概述

此 recipe 负责在代码已通过 CAS（Content Addressable Storage）获取的情况下编译 Skia。与 `sync_and_compile.py`（需要完整检出）不同，此 recipe 假设代码已经就绪，直接执行编译步骤。它还处理了 Windows 平台上路径长度限制的问题，通过使用 MD5 缩短的输出目录名来避免超过 250 字符的路径限制。

## 架构位置

该 recipe 是 Skia CI 构建流水线中最常用的编译入口：

- **触发**: 由 Swarming 任务调度器触发，代码通过 CAS 分发
- **上游**: 代码库内容已通过 CAS 下载到 `start_dir`
- **下游**: 编译产物复制到 `swarming_out_dir`，供测试/性能 recipe 使用
- **关联**: `sync_and_compile.py` 处理需要完整 git 检出的场景

## 主要类与结构体

| 名称 | 类型 | 说明 |
|------|------|------|
| `DEPS` | 列表 | 依赖模块列表 |
| `TEST_BUILDERS` | 列表 | 测试用构建器名称: `['Build-Win-Clang-x86-Debug']` |

## 公共 API 函数

### `RunSteps(api)`

Recipe 入口，执行以下流程：

1. **清理旧缓存**: 删除旧路径格式的输出目录（由于路径命名方案变更）
2. **生成短路径名**: 将 `builder_name + configuration` 通过 MD5 哈希取前 6 位作为输出目录名
3. **编译**: 调用 `api.build` 执行编译
4. **复制构建产物**: 将输出复制到 Swarming 输出目录
5. **Windows 清理**: 在 Windows 平台上清理遗留进程

### `GenTests(api)`

生成 Windows 编译的测试用例。

## 内部实现细节

- **路径缩短**: Windows 有 250 字符的路径限制，完整的 `builder_name`（如 `Build-Win-Clang-x86-Debug`）可能导致路径过长。使用 `hashlib.md5(long_name)[:6]` 生成 6 字符的唯一短名称
- **旧缓存清理**: 由于路径命名方案从完整名称变更为 MD5 缩短名称，需要删除旧格式的目录以释放磁盘空间。`api.file.rmtree` 在目录不存在时静默返回
- **缓存路径**: 输出目录使用 `cache_dir/work/skia/out/{short_name}`，利用 Swarming 缓存机制加速增量编译
- **try/finally 清理**: Windows 编译后清理遗留的编译器进程（cl.exe、link.exe 等）

## 依赖关系

- **build** -- 编译模块，执行 GN 配置和 Ninja 构建
- **checkout** -- 代码检出模块（此 recipe 中仅用于辅助功能）
- **run** -- 步骤执行和失败检查
- **vars** -- 构建变量管理
- **recipe_engine/context** -- 执行上下文
- **recipe_engine/file** -- 文件操作
- **recipe_engine/json** -- JSON 处理
- **recipe_engine/path** -- 路径操作
- **recipe_engine/platform** -- 平台检测
- **recipe_engine/properties** -- 构建属性
- **recipe_engine/step** -- 步骤执行

## 设计模式与设计决策

- **MD5 路径缩短**: 使用哈希解决 Windows 路径长度限制，6 位十六进制字符（16^6 = 约 1600 万种组合）在实际使用中碰撞概率极低
- **缓存利用**: 将输出放在持久化的 `cache_dir` 下，Swarming 在同一机器人上重用此缓存，实现增量编译加速
- **旧缓存迁移**: 主动清理旧路径格式的目录，防止磁盘空间浪费
- **CAS 优先**: 假设代码已通过 CAS 分发，省去了 git 检出的开销，适合大多数编译场景
- **平台条件清理**: 仅 Windows 需要进程清理，其他平台跳过

## 性能考量

- MD5 哈希计算开销可忽略不计
- `cache_dir` 缓存显著加速增量编译（Ninja 增量构建通常只需编译改动的文件）
- 旧缓存清理（`rmtree`）在首次运行时可能有 I/O 开销，但后续运行无影响
- Windows 进程清理脚本的运行时间极短

## 相关文件

- `infra/bots/recipes/sync_and_compile.py` -- 需要完整检出的编译 recipe
- `infra/bots/recipe_modules/build/` -- 编译模块
- `infra/bots/recipe_modules/build/resources/cleanup_win_processes.py` -- Windows 进程清理脚本
- `infra/bots/recipe_modules/vars/` -- 构建变量模块
