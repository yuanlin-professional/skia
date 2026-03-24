# infra - Skia CI/CD 基础设施

## 概述

`infra/` 目录是 Skia 图形库的持续集成与持续部署（CI/CD）基础设施的核心所在。它包含了自动化构建、测试、性能评估以及部署所需的全部配置、脚本和工具。Skia 使用 Google 的 LUCI（Layered Universal Continuous Integration）系统来管理其 CI/CD 流水线，通过 Swarming 任务调度系统在分布式机器池中执行任务。

本目录的主要职责包括：

- **任务生成与调度**：通过 Go 语言程序和 JSON 配置文件定义在每次提交时运行的任务 DAG（有向无环图）
- **Recipe 框架**：使用 Python Recipe 系统定义构建、测试和上传等工作流程
- **资源管理**：管理构建机器人所需的工具链、SDK 和测试数据等资源
- **Docker 镜像**：为各种构建和测试环境提供 Docker 容器化支持
- **Web 应用部署**：管理 Skia 相关 Web 应用（如 Fiddle、Debugger、Skottie 等）的 Docker 镜像构建
- **交叉编译支持**：提供针对不同架构和平台的交叉编译环境配置

## 目录结构

```
infra/
├── bots/                    # CI 机器人核心配置与脚本
│   ├── gen_tasks_logic/     # 任务生成核心逻辑（Go）
│   ├── recipe_modules/      # Recipe 共享模块
│   ├── recipes/             # 顶层 Recipe 入口脚本
│   ├── task_drivers/        # 任务驱动程序（Go）
│   ├── assets/              # 版本化的构建资源
│   ├── analysis/            # 作业分析脚本
│   ├── buildstats/          # 构建统计脚本
│   ├── deps/                # 依赖管理
│   ├── format_jobs_json/    # jobs.json 格式化工具
│   └── tools/               # 基础设施工具（LUCI-Go 二进制）
├── docker/                  # Docker 构建配置
│   ├── debian9/             # Debian 9 基础镜像
│   ├── binary-size/         # 二进制体积分析镜像
│   └── cmake-release/       # CMake 构建镜像
├── cmake/                   # CMake 构建脚本
├── config/                  # Recipe 引擎配置
├── canvaskit/               # CanvasKit 构建与测试脚本
├── wasm-common/             # WebAssembly 通用工具
├── lottiecap/               # Lottie 动画捕获工具
├── gcc/                     # GCC 编译 Docker 配置
├── cross-compile/           # 交叉编译 Docker 配置
├── fiddler-backend/         # Fiddler 后端 Docker 镜像
├── jsfiddle/                # JSFiddle Docker 镜像
├── shaders/                 # Shaders 应用 Docker 镜像
├── debugger-app/            # 调试器应用 Docker 镜像
├── skottie/                 # Skottie 应用 Docker 镜像
├── project-config/          # Chrome-Infra 项目级配置
├── skcq.json                # Skia CQ（Commit Queue）配置
├── BUILD.bazel              # Bazel 构建文件
└── README.md                # 原始说明文档
```

## 核心组件

### 1. 任务调度系统 (bots/)

Skia 使用任务 DAG 来组织 CI 工作流。核心流程如下：

1. `gen_tasks.go` 调用 `gen_tasks_logic/` 中的逻辑来生成 `tasks.json`
2. `tasks.json` 定义了所有任务和作业的完整 DAG
3. Task Scheduler 在每次提交时读取 `tasks.json` 来决定运行哪些作业
4. 任务通过 Swarming 在分布式机器池中执行

关键配置文件：
- `cfg.json` - 基础配置（Google Storage bucket、服务账户等）
- `jobs.json` - 所有作业的列表（添加/删除机器人时编辑此文件）

### 2. Recipe 系统 (bots/recipes/, bots/recipe_modules/)

Recipe 是 Skia 基础设施在 Swarming 任务中执行工作的框架。主要组件：

- **recipes/** - 每种任务类型的入口脚本（编译、测试、性能评测等）
- **recipe_modules/** - Recipe 之间共享的功能模块
- **recipes.py** - 用于运行和测试 Recipe 的入口工具

### 3. 任务驱动 (bots/task_drivers/)

用 Go 语言编写的任务驱动程序，处理更复杂的 CI 任务，例如：
- Bazel 构建
- CanvasKit Gold 测试
- 代码体积分析
- WASM GM 测试编译与运行
- SKP 文件重新生成

### 4. 资源管理 (bots/assets/)

通过版本化的方式管理 CI 系统使用的各种工具和数据。每个资源目录通常包含：
- `VERSION` - 当前版本号
- `create.py` - 自动化创建脚本（可选）
- `create_and_upload.py` - 创建并上传的便捷脚本（可选）

资源类别包括：编译器工具链、Android NDK/SDK、构建工具、测试数据等。

### 5. Docker 环境

提供标准化的构建和测试环境：
- `docker/` - 核心 Docker 构建配置
- `gcc/` - GCC 编译环境
- `cross-compile/` - 交叉编译环境
- `canvaskit/` - CanvasKit/WASM 构建环境
- `wasm-common/` - WebAssembly 通用 Docker 镜像

### 6. Web 应用部署

为 Skia 的在线工具提供 Docker 镜像构建支持：
- `fiddler-backend/` - fiddler.skia.org 后端
- `jsfiddle/` - jsfiddle.skia.org
- `shaders/` - shaders.skia.org
- `debugger-app/` - debugger.skia.org
- `skottie/` - skottie.skia.org

## 关键文件

| 文件 | 说明 |
|------|------|
| `skcq.json` | Skia Commit Queue 配置，定义可见性、任务路径、提交者列表等 |
| `BUILD.bazel` | Bazel 构建系统入口文件 |
| `bots/tasks.json` | 自动生成的任务 DAG（不要手动编辑） |
| `bots/jobs.json` | 所有作业列表（添加/删除机器人时编辑） |
| `bots/cfg.json` | 基础配置（bucket、服务账户等） |
| `bots/gen_tasks.go` | 任务生成入口程序 |
| `bots/infra_tests.py` | 基础设施测试运行器 |
| `bots/Makefile` | 便捷的 make 命令（test/train） |
| `config/recipes.cfg` | Recipe 引擎配置（依赖版本等） |

## 常用操作

### 重新生成 tasks.json

当修改 `gen_tasks.go`、JSON 配置文件或资源时，需要重新生成：

```bash
# 方式一：直接运行 Go 程序
go run infra/bots/gen_tasks.go

# 方式二：使用 Makefile
make -C infra/bots train
```

### 测试任务配置

```bash
# 测试模式（检查一致性，验证 tasks.json 未改变）
go run infra/bots/gen_tasks.go --test

# 或使用 Makefile
make -C infra/bots test
```

### 运行 Recipe 测试

```bash
# 训练模式（更新预期结果）
python infra/bots/recipes.py test train

# 运行模式（验证结果）
python infra/bots/recipes.py test run
```

### 触发 Try Job

```bash
# 获取 SK CLI 工具
./bin/fetch-sk

# 登录 LUCI
luci-auth login

# 触发指定作业
./bin/sk try <作业名称>
```

## 服务账户

系统使用以下服务账户来执行不同类型的任务：

| 服务账户 | 用途 |
|----------|------|
| `skia-canary@...` | 金丝雀测试 |
| `skia-external-compile-tasks@...` | 编译任务 |
| `skia-external-housekeeper@...` | 维护任务 |
| `skia-recreate-skps@...` | SKP 重新生成 |
| `skia-external-binary-uploader@...` | 二进制上传 |
| `skia-external-gm-uploader@...` | GM 结果上传 |
| `skia-external-nano-uploader@...` | 性能结果上传 |

## 依赖关系

- **LUCI 系统**：Task Scheduler、Swarming、CAS（Content Addressable Storage）
- **Recipe Engine**：来自 `chromium/tools/depot_tools` 和 `infra/luci/recipes-py`
- **Go 工具链**：用于任务生成和任务驱动程序
- **Python 3**：用于 Recipe 系统和资源管理脚本
- **Docker**：用于构建环境容器化
- **Google Cloud Storage**：用于存储构建产物和测试结果
- **CIPD**：Chrome Infrastructure Package Deployment，用于工具分发

## 相关文档与参考

- [Task Scheduler 文档](https://skia.googlesource.com/buildbot/+/main/task_scheduler/README.md)
- [SK CLI 工具文档](https://chromium.googlesource.com/skia/+/HEAD/site/docs/dev/tools/sk.md)
- [LUCI 项目主页](https://chromium.googlesource.com/infra/luci/)
- [Recipe Engine 文档](https://chromium.googlesource.com/infra/luci/recipes-py/)
- [Swarming 文档](https://chromium.googlesource.com/infra/luci/luci-py/+/HEAD/appengine/swarming/doc/)
- 本目录下各子目录的 README.md 文件
