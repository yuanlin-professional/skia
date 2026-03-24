# recipes - Skia Recipe 脚本

## 概述

`recipes/` 目录包含在 Swarming 任务中执行的顶层 Recipe 脚本。Recipe 是 Skia 自动化测试的入口点，每个 Recipe 对应一种特定类型的 CI 任务。Recipe 使用 `recipe_modules/` 中的共享模块来实现具体功能。

## 目录结构

```
recipes/
├── compile.py                    # 编译任务
├── compile.expected/             # 编译测试预期结果
├── test.py                       # 运行测试
├── test.expected/                # 测试预期结果
├── perf.py                       # 性能评测
├── perf.expected/                # 性能评测预期结果
├── housekeeper.py                # 维护任务
├── housekeeper.expected/         # 维护任务预期结果
├── infra.py                      # 基础设施任务
├── infra.expected/               # 基础设施任务预期结果
├── sync_and_compile.py           # 同步并编译
├── sync_and_compile.expected/    # 同步编译预期结果
├── compute_buildstats.py         # 计算构建统计
├── compute_buildstats.expected/  # 构建统计预期结果
├── test_canvaskit.py             # CanvasKit 测试
├── test_canvaskit.expected/      # CanvasKit 测试预期结果
├── test_lottie_web.py            # Lottie Web 测试
├── test_lottie_web.expected/     # Lottie Web 测试预期结果
├── perf_skottietrace.py          # Skottie 追踪性能测试
├── perf_skottietrace.expected/   # Skottie 追踪预期结果
├── perf_skottiewasm_lottieweb.py # Skottie WASM/Lottie Web 性能测试
├── perf_skottiewasm_lottieweb.expected/
├── upload_dm_results.py          # 上传 DM 测试结果
├── upload_dm_results.expected/
├── upload_nano_results.py        # 上传 Nanobench 性能结果
├── upload_nano_results.expected/
├── upload_buildstats_results.py  # 上传构建统计结果
├── upload_buildstats_results.expected/
└── README.md                     # 原始说明文档
```

## 关键 Recipe

| Recipe | 说明 |
|--------|------|
| `compile.py` | 编译 Skia，支持多平台和多配置 |
| `test.py` | 运行 DM 测试（绘图和图像处理测试） |
| `perf.py` | 运行 Nanobench 性能基准测试 |
| `housekeeper.py` | 运行维护任务（代码检查、清理等） |
| `sync_and_compile.py` | 同步依赖并编译 |
| `test_canvaskit.py` | 运行 CanvasKit（WASM）测试 |
| `test_lottie_web.py` | 运行 Lottie Web 动画测试 |
| `upload_dm_results.py` | 将 DM 测试结果上传到 Gold |
| `upload_nano_results.py` | 将性能结果上传到 Perf 服务 |

## 使用方法

### 本地运行 Recipe

```bash
python infra/bots/recipes.py run --workdir=/tmp/<workdir> <recipe名称> key1=value1 key2=value2 ...
```

### 训练模拟测试

修改 Recipe 后需要更新预期结果文件：

```bash
python infra/bots/recipes.py test train
# 或
cd infra/bots && make train
```

### 预期结果文件

每个 Recipe 都有对应的 `.expected/` 目录，包含模拟测试的预期结果。这些文件描述了在给定输入下 Recipe 应该执行的步骤序列。修改 Recipe 时需要检查这些文件的差异以确认更改的正确性。

## 依赖关系

- `recipe_modules/` - 共享的 Recipe 模块
- `recipes.py` - Recipe 运行和测试框架
- Recipe Engine（通过 `infra/config/recipes.cfg` 配置）
- depot_tools Recipe 模块

## 相关文档与参考

- `infra/bots/README.recipes.md` - 自动生成的 Recipe API 文档
- `infra/bots/recipe_modules/` - 共享模块文档
