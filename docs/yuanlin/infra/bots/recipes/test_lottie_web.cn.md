# Lottie-Web 测试 Recipe (test_lottie_web)

> 源文件: `infra/bots/recipes/test_lottie_web.py`

## 概述

此 recipe 使用 Docker 容器生成 Lottie-Web 渲染的 Gold 图像，用于视觉回归测试。Lottie-Web 是 Airbnb 开源的 Web 端 Lottie 动画渲染库，此 recipe 通过 Puppeteer 控制 Chrome 浏览器渲染 Lottie 动画，捕获输出图像并上传到 Skia Gold 平台进行视觉比对。这使得 Skia 团队可以将 Skottie（Skia 的 Lottie 实现）的渲染结果与 Lottie-Web 的渲染结果进行对比。

## 架构位置

该 recipe 是 Skia CI 中 Lottie 动画渲染质量监控体系的组成部分：

- **执行环境**: Docker 容器 (`gold-lottie-web-puppeteer:v2`)
- **上游**: CIPD 提供的 Lottie 样本文件和 lottie-web 库构建产物
- **下游**: Gold 平台接收图像输出进行视觉回归检测
- **对比对象**: Skottie (Skia Lottie) 渲染输出

## 主要类与结构体

| 名称 | 类型 | 说明 |
|------|------|------|
| `DEPS` | 列表 | 依赖模块列表 |
| `DOCKER_IMAGE` | 常量 | Docker 镜像: `gcr.io/skia-public/gold-lottie-web-puppeteer:v2` |
| `LOTTIECAP_SCRIPT` | 常量 | Lottie 截图脚本路径: `skia/infra/lottiecap/docker/lottiecap_gold.sh` |

## 公共 API 函数

### `RunSteps(api)`

Recipe 入口，执行以下流程：
1. 初始化变量和 flavor 环境
2. 准备 Lottie 文件：将 CIPD 的符号链接文件复制到临时目录（Docker 不支持符号链接挂载）
3. 配置 Docker 挂载卷：`LOTTIE_BUILD`（lottie-web 构建产物）和 `LOTTIE_FILES`（Lottie 动画文件）
4. 构建命令行参数（builder、git hash、bot/task ID、browser、config）
5. 对 trybot 附加 issue/patchset/patch_storage 参数
6. 通过 Docker 运行 Puppeteer 截图脚本（最多 3 次重试）
7. 上传 Gold 结果

### `GenTests(api)`

生成两个测试用例：标准 CI 构建和 trybot 构建。

## 内部实现细节

- **CIPD 符号链接处理**: CIPD 默认以符号链接模式安装文件，但 Docker 卷挂载不支持宿主机上的符号链接。解决方案是先用 `api.file.copytree` 将文件复制到 `/tmp/lottie_files` 临时目录（去除符号链接），再挂载该目录
- **Docker 卷挂载**: 使用 `--mount type=bind` 将 lottie-web 构建产物和动画文件挂载到容器的固定路径 `/LOTTIE_BUILD` 和 `/LOTTIE_FILES`
- **lottie-web DEP**: lottie-web 仓库作为 Skia 的 DEP 依赖引入，其构建产物位于 `checkout_root/lottie/build/player/`
- **Puppeteer 截图**: Docker 容器内使用 Puppeteer（Chrome 无头浏览器控制工具）渲染每个 Lottie 动画并截取帧图像

## 依赖关系

- **checkout** -- 代码检出模块
- **docker** -- Docker 容器运行模块
- **env** -- 环境变量管理
- **flavor** -- 设备抽象层
- **gold_upload** -- Gold 结果上传
- **infra** -- 基础设施工具
- **run** -- 步骤执行
- **vars** -- 构建变量
- **recipe_engine/file** -- 文件操作
- **recipe_engine/path** -- 路径操作
- **recipe_engine/properties** -- 构建属性
- **recipe_engine/step** -- 步骤执行

## 设计模式与设计决策

- **Docker 隔离**: 使用 Docker 提供一致的浏览器和 Node.js 环境，确保渲染结果的可重复性
- **符号链接去除**: 为兼容 Docker 卷挂载机制，采用先复制后挂载的方式处理 CIPD 符号链接
- **目录预创建**: 在启动 Docker 前确保输出目录存在，否则 Docker 会以 root 权限创建，导致后续权限问题
- **重试机制**: `attempts=3` 应对 Docker 和浏览器的偶发不稳定性
- **Gold 集成**: 传递完整的构建元数据到 Gold，支持按配置维度查询和比较结果

## 性能考量

- Docker 容器启动和初始化有一定开销
- 文件复制步骤（去除符号链接）对大量 Lottie 文件有 I/O 开销
- 先删除旧文件 (`rmtree`) 再复制，确保不会积累旧数据
- Puppeteer 渲染每个 Lottie 文件需要启动/停止浏览器页面，是主要的时间消耗

## 相关文件

- `infra/lottiecap/docker/lottiecap_gold.sh` -- Docker 内执行的截图脚本
- `infra/bots/recipe_modules/docker/` -- Docker 执行模块
- `infra/bots/recipe_modules/gold_upload/` -- Gold 上传模块
- `infra/bots/recipes/perf_skottiewasm_lottieweb.py` -- Lottie-Web 性能测试（非视觉测试）
- `modules/skottie/` -- Skottie 模块源代码
