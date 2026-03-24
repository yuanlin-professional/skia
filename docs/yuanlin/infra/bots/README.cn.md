# bots - Skia CI 机器人核心配置

## 概述

`infra/bots/` 目录是 Skia CI/CD 系统的核心，包含了定义、生成和执行自动化构建/测试/性能评估任务所需的全部配置和脚本。该目录使用任务 DAG（有向无环图）来组织每次 Skia 代码提交后需要运行的所有工作。

核心工作流程：
1. `gen_tasks.go` 读取 `cfg.json` 和 `jobs.json`，调用 `gen_tasks_logic/` 中的逻辑生成 `tasks.json`
2. LUCI Task Scheduler 在每次提交时读取 `tasks.json` 来调度任务
3. 任务通过 Swarming 在分布式机器上执行，使用 Recipe 系统定义具体工作内容
4. 结果上传到 Google Cloud Storage 和 Gold/Perf 等服务

## 目录结构

```
bots/
├── gen_tasks.go              # 任务生成入口（调用 gen_tasks_logic）
├── gen_tasks_logic/          # 任务生成核心逻辑
├── cfg.json                  # 基础配置（bucket、服务账户等）
├── jobs.json                 # 所有作业列表
├── tasks.json                # 自动生成的完整任务 DAG（勿手动编辑）
├── recipe_modules/           # Recipe 共享模块
├── recipes/                  # 顶层 Recipe 脚本
├── recipes.py                # Recipe 运行和测试工具
├── task_drivers/             # Go 语言任务驱动程序
├── assets/                   # 版本化构建资源
├── analysis/                 # 作业分析脚本
├── buildstats/               # 构建统计工具
├── deps/                     # 依赖管理工具
├── format_jobs_json/         # jobs.json 格式化工具
├── tools/                    # LUCI-Go 工具二进制文件
├── infra_tests.py            # 基础设施测试入口
├── Makefile                  # 便捷 make 命令
├── find_tasks.py             # 任务查找工具
├── run_recipe.py             # Recipe 运行辅助脚本
├── build_task_drivers.sh     # 任务驱动编译脚本
├── bundle_recipes.sh         # Recipe 打包脚本
├── check_deps.py             # 依赖检查工具
├── git_utils.py              # Git 操作工具
├── utils.py                  # 通用工具函数
├── test_utils.py             # 测试工具函数
├── zip_utils.py              # ZIP 文件工具
├── zip_utils_test.py         # ZIP 工具单元测试
├── BUILD.bazel               # Bazel 构建文件
├── README.md                 # 原始说明文档
└── README.recipes.md         # Recipe 自动生成文档
```

## 关键文件

### cfg.json

基础配置文件，定义了：
- Google Storage bucket（GM 结果、性能数据、代码覆盖率）
- Gold 服务的哈希值 URL
- Swarming 池名称和项目名称
- 不上传结果的任务类型列表（ASAN、MSAN、TSAN 等）
- 各类任务使用的服务账户

### jobs.json

所有 CI 作业的列表。添加或删除机器人时需要编辑此文件。每个作业是 DAG 中的一个入口点，定义了一组相关联的任务集合。

### tasks.json

由 `gen_tasks.go` 自动生成的完整任务定义文件。**绝对不要手动编辑此文件**。包含所有任务的定义、依赖关系、资源需求、CAS（Content Addressable Storage）输入等。

### infra_tests.py

基础设施测试运行器，执行三类测试：
1. Python 单元测试（发现并运行 `*_test.py` 文件）
2. Recipe 模拟测试（验证 Recipe 步骤的正确性）
3. 任务生成测试（验证 tasks.json 的一致性）

### Makefile

提供两个便捷命令：
- `make test` - 运行所有基础设施测试
- `make train` - 训练模式（更新预期结果文件）

## 任务与作业

### 任务（Task）

任务是通过 Swarming 在机器池中运行的小型独立单元。任务可以链式连接，例如一个任务编译测试二进制文件，另一个任务实际运行测试。

### 作业（Job）

作业是相关任务的集合，定义了 DAG 的子部分。每个作业是 DAG 的一个入口点，可用作 Try Job。

### CAS 配置

任务使用 CAS（Content Addressable Storage）来传输仓库文件到执行机器。预定义的 CAS 配置包括：
- `compile` - 编译所需文件
- `test` - 测试所需文件
- `perf` - 性能评测所需文件
- `recipes` - Recipe 脚本文件
- `task-drivers` - 任务驱动程序
- `whole-repo` - 完整仓库

## 常用操作

### 添加新作业

1. 编辑 `jobs.json` 添加新的作业定义
2. 如需修改任务生成逻辑，编辑 `gen_tasks_logic/` 中的文件
3. 重新生成 `tasks.json`：
   ```bash
   go run infra/bots/gen_tasks.go
   ```
4. 使用 SK CLI 在提交前测试新作业：
   ```bash
   ./bin/sk try <作业名称>
   ```

### 修改 Recipe

1. 编辑 `recipes/` 或 `recipe_modules/` 中的文件
2. 重新训练模拟测试：
   ```bash
   python infra/bots/infra_tests.py --train
   ```

### 更新资源

1. 修改 `assets/<资源名>/create.py`（如适用）
2. 上传新版本：`sk asset upload <资源名>`
3. 重新生成 `tasks.json`：`make -C infra/bots train`

## 机器类型

任务可在不同规格的 GCE 机器上运行：
- **Small** (`n1-highmem-2`) - 2 核心
- **Medium** (`n1-standard-16`) - 16 核心
- **Large** (`n1-highcpu-64`) - 64 核心

## 依赖关系

- `gen_tasks_logic/` - 任务生成的核心依赖
- `recipe_modules/` - Recipe 之间的共享模块
- `assets/` - 各任务依赖的工具和数据资源
- Recipe Engine（通过 `infra/config/recipes.cfg` 配置）
- depot_tools（Chrome 开发工具集）
- Go 工具链（用于任务生成和任务驱动）

## 相关文档与参考

- [Task Scheduler 文档](https://skia.googlesource.com/buildbot/+/main/task_scheduler/README.md)
- [Isolate 工具文档](https://github.com/luci/luci-py/tree/main/appengine/isolate/doc)
- [SK CLI 工具文档](https://chromium.googlesource.com/skia/+/HEAD/site/docs/dev/tools/sk.md)
- `README.recipes.md` - 自动生成的 Recipe API 文档
