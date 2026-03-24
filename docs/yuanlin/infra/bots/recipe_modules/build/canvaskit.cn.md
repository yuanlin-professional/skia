# CanvasKit 构建模块

> 源文件: infra/bots/recipe_modules/build/canvaskit.py

## 概述

`canvaskit.py` 是 Skia 项目中用于构建 CanvasKit 的 Recipe 模块。CanvasKit 是 Skia 的 WebAssembly (Wasm) 版本,通过 Emscripten 编译器将 Skia 编译成可在浏览器中运行的 JavaScript 和 Wasm 代码。该模块使用 Docker 容器提供一致的 Emscripten SDK 环境,支持多种图形后端(CPU、GPU/Ganesh、WebGPU/Graphite)和配置模式(Debug、Release)。

## 架构位置

该模块位于构建系统的 WebAssembly 策略层:

- **层级**: 基础设施 / 构建模块 / CanvasKit 支持
- **功能域**: WebAssembly 编译
- **构建工具链**: Emscripten (EMCC) + Docker
- **目标平台**: Web 浏览器

## 主要类与结构体

该模块不定义类,而是提供常量和函数。

### 常量

#### DOCKER_IMAGE

```python
DOCKER_IMAGE = 'gcr.io/skia-public/canvaskit-emsdk:3.1.26_v2'
```

CanvasKit 使用的 Emscripten SDK Docker 镜像。
- 版本: Emscripten 3.1.26
- 镜像变体: v2

#### INNER_BUILD_SCRIPT

```python
INNER_BUILD_SCRIPT = '/SRC/skia/infra/canvaskit/build_canvaskit.sh'
```

容器内执行的构建脚本路径。

#### CANVASKIT_BUILD_PRODUCTS

```python
CANVASKIT_BUILD_PRODUCTS = [
    'canvaskit.*'
]
```

需要复制的构建产物模式(匹配所有 canvaskit 文件)。

## 公共 API 函数

### compile_fn

```python
def compile_fn(api, checkout_root, _ignore):
```

**功能**: 使用 Emscripten 在 Docker 容器中编译 CanvasKit。

**参数**:
- `api`: Recipe API 对象
- `checkout_root`: Skia 源码根目录
- `_ignore`: 忽略的输出目录参数(使用自定义路径)

**执行流程**:
1. 配置输出目录为 `cache/docker/canvaskit`
2. 提取构建配置(configuration, extra_config)
3. 创建输出目录并设置权限 777
4. 激活 Emscripten SDK (下载二进制文件)
5. 构建 Docker 命令
6. 根据 extra_config 添加后端参数(cpu/webgpu)
7. 根据 configuration 添加调试标志
8. 在 Docker 容器中执行构建脚本

**输出目录特殊处理**:
- 使用独立的 `docker/canvaskit` 子目录
- 避免与其他构建冲突
- 设置 777 权限防止 Docker root 用户导致的权限问题

**图形后端选择**:

**GPU (默认)**:
- 使用 Ganesh 渲染后端
- WebGL 图形 API
- 不传递额外参数

**CPU**:
- 无 GPU 后端
- 纯软件渲染
- extra_config 包含 'CPU' 时启用

**WebGPU**:
- 使用 Graphite 渲染后端
- WebGPU 图形 API
- extra_config 包含 'WebGPU' 时启用

**配置模式**:
- **Release** (默认): 优化构建,体积小
- **Debug**: 调试符号,未优化

### copy_build_products

```python
def copy_build_products(api, _ignore, dst):
```

**功能**: 复制 CanvasKit 构建产物到目标目录。

**特殊实现**:

使用自定义脚本 `copy_build_products_no_delete.py` 而非标准的 `copy_listed_files`:

**原因**:
- Docker 以 root 用户创建输出文件
- 文件为只读且属于 root
- 标准脚本使用 `shutil.move`,会尝试删除源文件
- 删除操作失败(权限不足)

**解决方案**:
- 使用非删除式复制脚本
- 避免修改 Docker 创建的文件

**产物列表**:
- `canvaskit.js`: JavaScript 加载器
- `canvaskit.wasm`: WebAssembly 二进制
- `canvaskit.d.ts`: TypeScript 类型定义(如果启用)
- 其他相关文件

## 内部实现细节

### Emscripten SDK 激活

```python
with api.context(cwd=skia_dir):
    api.run(api.step, 'activate-emsdk',
            cmd=['python3', skia_dir.joinpath('bin', 'activate-emsdk')],
            infra_step=True)
```

**作用**:
- 下载 Emscripten 工具链二进制文件
- 配置 SDK 路径和环境
- 虽然 Docker 镜像包含 SDK,但使用本地版本以支持 GN 构建

### Docker 命令构建

```python
cmd = ['docker', 'run', '--rm', '--volume', '%s:/SRC' % checkout_root,
       '--volume', '%s:/OUT' % out_dir,
       DOCKER_IMAGE, INNER_BUILD_SCRIPT]
```

**卷挂载**:
- `/SRC`: 绑定源码目录(只读访问)
- `/OUT`: 绑定输出目录(写入产物)

**优势**:
- 构建脚本不在镜像中,可以更新而无需重建镜像
- 源码和产物在宿主机,便于调试

### 后端参数传递

```python
if 'CPU' in extra:
    cmd.append('cpu')
if 'WebGPU' in extra:
    cmd.append('webgpu')
```

传递给 `build_canvaskit.sh` 的位置参数:
- 无参数: GPU (Ganesh + WebGL)
- `cpu`: CPU 渲染
- `webgpu`: WebGPU (Graphite + WebGPU)

### 调试模式

```python
if configuration == 'Debug':
    cmd.append('debug')  # It defaults to Release
```

`build_canvaskit.sh` 默认 Release 模式,Debug 需显式指定。

### Docker 配置覆盖

```python
env = {'DOCKER_CONFIG': '/home/chrome-bot/.docker'}
with api.env(env):
    api.run(...)
```

Kitchen 默认设置的 `DOCKER_CONFIG` 可能不适用,使用标准路径。

### 从零构建

```python
# Of note, the wasm build doesn't re-use any intermediate steps from the
# previous builds, so it's essentially a build from scratch every time.
```

**特点**:
- 每次完全重新编译
- 不支持增量构建
- Emscripten 缓存机制不同于 Ninja

**原因**:
- WebAssembly 构建链较简单
- 完全编译通常只需数分钟
- 增量构建收益有限

## 依赖关系

### 直接依赖
- Docker: 容器运行时
- `build_canvaskit.sh`: 实际构建脚本
- Emscripten SDK Docker 镜像: 编译环境
- `bin/activate-emsdk`: Emscripten 激活脚本
- `copy_build_products_no_delete.py`: 文件复制脚本

### 被依赖者
- `api.py`: BuildApi 根据 'EMCC' 关键字选择此模块
- CanvasKit 相关 Recipe:
  - `compile.py`: 编译
  - `test_canvaskit.py`: 测试执行
  - `perf.py`: 性能测试(可能)

### 外部依赖
- Docker daemon: 必须在宿主机运行
- GCR (Google Container Registry): 镜像托管
- Emscripten: WebAssembly 编译器
- Node.js: 测试环境(用于运行 JS)

## 设计模式与设计决策

### 容器化构建

**优势**:
- **环境一致性**: 所有开发者使用相同的 Emscripten 版本
- **隔离性**: 不污染宿主机环境
- **可重现性**: 固定版本镜像确保构建一致

**权衡**:
- 增加容器启动开销(~1秒)
- 需要 Docker 基础设施

### 脚本外置

构建逻辑在 `build_canvaskit.sh` 而非 Docker 镜像:

**优势**:
- 更新构建逻辑无需重建镜像
- 脚本可独立测试和迭代
- 减少镜像大小和复杂度

### 多后端支持

通过简单的参数选择后端:
- 灵活组合特性
- 单一脚本支持多配置
- 通过构建器名称控制

### 完全重建策略

每次从零构建而非增量:
- 简化构建逻辑
- 避免缓存失效问题
- WebAssembly 构建速度足够快

### 权限问题解决

使用非删除式复制避免权限问题:
- 务实的解决方案
- 避免修改 Docker 配置
- 保持构建流程简单

## 性能考量

### 编译时间

**典型时间**:
- Release 构建: 3-5 分钟
- Debug 构建: 2-4 分钟(优化少)
- 完全重建无增量优势

### Docker 开销

- **镜像拉取**: 首次 ~500MB, 后续缓存
- **容器启动**: <1 秒
- **卷挂载**: 零拷贝 bind mount

### 产物大小

**Release 构建**:
- `canvaskit.wasm`: ~6-8 MB (gzipped ~2-3 MB)
- `canvaskit.js`: ~100-200 KB

**Debug 构建**:
- wasm 文件更大(~10-15 MB)
- 包含调试符号

### Emscripten 优化

Release 构建使用激进优化:
- `-O3`: 最大代码优化
- `--closure 1`: Google Closure Compiler 压缩 JS
- `--strip-debug`: 移除调试信息
- Link-time optimization (LTO)

### 并行编译

Emscripten 支持多核编译:
- 利用宿主机所有 CPU 核心
- 显著加速编译

## 相关文件

### 构建脚本
- `infra/canvaskit/build_canvaskit.sh`: 主构建脚本
- `bin/activate-emsdk`: Emscripten 激活脚本
- `infra/bots/recipe_modules/build/resources/copy_build_products_no_delete.py`: 文件复制脚本

### Docker 镜像
- `infra/canvaskit/docker/canvaskit-emsdk/Dockerfile`: 镜像定义
- 镜像托管在 GCR: `gcr.io/skia-public/canvaskit-emsdk`

### CanvasKit 源码
- `modules/canvaskit/`: CanvasKit 模块源码
- `modules/canvaskit/canvaskit_bindings.cpp`: C++ 绑定
- `modules/canvaskit/interface.js`: JavaScript 接口

### GN 配置
- `modules/canvaskit/BUILD.gn`: CanvasKit 构建规则
- `gn/BUILDCONFIG.gn`: 全局构建配置

### Recipe 模块
- `infra/bots/recipe_modules/build/api.py`: Build API 入口
- `infra/bots/recipe_modules/build/util.py`: 工具函数

### Recipe 使用
- `infra/bots/recipes/compile.py`: 编译 Recipe
- `infra/bots/recipes/test_canvaskit.py`: CanvasKit 测试

### 测试和示例
- `modules/canvaskit/tests/`: 测试套件
- `modules/canvaskit/demos/`: 在线演示

### CI 配置
- `infra/bots/tasks.json`: CanvasKit 构建任务
- `infra/bots/jobs.json`: 任务调度

### 文档
- `modules/canvaskit/README.md`: CanvasKit 文档
- `modules/canvaskit/CHANGELOG.md`: 变更日志

### NPM 发布
- `modules/canvaskit/npm_build/`: NPM 包构建配置
- `modules/canvaskit/package.json`: NPM 包元数据

该模块展示了 Skia 如何通过 Emscripten 和 Docker 将强大的 2D 图形库带到 Web 平台,使开发者能够在浏览器中使用与原生应用相同的 Skia API,实现高性能的图形渲染。CanvasKit 是 Skia 跨平台战略的重要组成部分,使 Flutter for Web 和其他 Web 应用能够获得一致的渲染质量。
