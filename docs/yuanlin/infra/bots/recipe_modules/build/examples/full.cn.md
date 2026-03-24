# Build Recipe 完整示例

> 源文件: infra/bots/recipe_modules/build/examples/full.py

## 概述

`full.py` 是 Build Recipe 模块的完整使用示例和测试套件。该文件展示了如何使用 Build API 编译 Skia 并复制构建产物,同时包含超过 100 个不同构建配置的测试用例,覆盖多平台、多编译器、多特性组合,是 Skia 构建系统测试的核心文件。

## 架构位置

该文件位于 Recipe 模块的示例和测试层:

- **层级**: 基础设施 / Recipe 示例和测试
- **功能域**: 构建流程的集成测试和使用示例
- **覆盖范围**: 100+ 构建配置
- **作用**: 既是文档,也是回归测试

## 主要类与结构体

该文件不定义类,而是提供三个核心组件:

### DEPS (依赖列表)

声明 Recipe 依赖的模块。

### RunSteps (执行函数)

定义 Recipe 的主要执行流程。

### TEST_BUILDERS (测试构建器列表)

包含 100+ 个测试构建器名称。

### GenTests (测试生成器)

生成所有测试用例。

## 公共 API 函数

### RunSteps

```python
def RunSteps(api):
    api.vars.setup()
    checkout_root = api.vars.cache_dir.joinpath('work')
    out_dir = checkout_root.joinpath(
        'skia', 'out', api.vars.builder_name, api.vars.configuration)
    api.build(checkout_root=checkout_root, out_dir=out_dir)
    dst = api.vars.swarming_out_dir.joinpath('out', api.vars.configuration)
    api.build.copy_build_products(out_dir=out_dir, dst=dst)
    api.run.check_failure()
```

**执行步骤**:
1. 初始化构建变量
2. 配置检出根目录和输出目录
3. 调用 Build API 执行编译
4. 复制构建产物到 Swarming 输出目录
5. 检查是否有失败的步骤

**路径结构**:
- 检出根: `cache/work`
- 输出: `cache/work/skia/out/{builder_name}/{configuration}`
- 产物: `swarming_out_dir/out/{configuration}`

### GenTests

```python
def GenTests(api):
    for buildername in TEST_BUILDERS:
        test = (
            api.test(buildername) +
            api.properties(**defaultProps(buildername))
        )
        if 'Win' in buildername:
            test += api.platform('win', 64)
        yield test
```

**测试生成策略**:
- 为每个 `TEST_BUILDERS` 生成一个测试
- 使用默认属性配置
- Windows 构建器添加平台标记
- 包含一个异常测试用例

## 内部实现细节

### 依赖声明

```python
DEPS = [
    'build',
    'recipe_engine/path',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
    'run',
    'vars',
]
```

依赖核心 Recipe 模块和 Skia 自定义模块。

### TEST_BUILDERS 列表

包含以下类别的构建器:

**Android 构建** (API 26, ASAN, HWASAN, Graphite, Dawn, Vulkan, Wuffs等):
- `Build-Debian10-Clang-arm-Release-Android_API26`
- `Build-Debian10-Clang-arm-Release-Android_ASAN`
- `Build-Debian10-Clang-arm64-Release-Android_Graphite_Dawn_Vulkan`

**Chromebook 构建** (ARM, ARM64, x86_64):
- `Build-Debian10-Clang-arm-Release-Chromebook_GLES`
- `Build-Debian10-Clang-arm64-Debug-Chromebook_GLES`
- `Build-Debian10-Clang-x86_64-Debug-Chromebook_GLES`

**Linux 构建** (Clang, GCC, Docker):
- `Build-Debian10-Clang-x86_64-Debug-ASAN`
- `Build-Debian10-Clang-x86_64-Debug-MSAN`
- `Build-Debian10-Clang-x86_64-Debug-TSAN`
- `Build-Debian10-Clang-x86_64-Debug-Vulkan`
- `Build-Debian11-GCC-x86_64-Release-Docker`

**macOS/iOS 构建** (Metal, Dawn, Graphite):
- `Build-Mac-Clang-arm64-Debug-iOS`
- `Build-Mac-Clang-arm64-Debug-Graphite_Native_Metal`
- `Build-Mac-Clang-arm64-Debug-Graphite_Dawn_Metal`
- `Build-Mac-Clang-arm64-Release-iOS18_Metal`

**Windows 构建** (Clang, MSVC, ANGLE, Direct3D, Vulkan):
- `Build-Win-Clang-x86_64-Debug-ANGLE`
- `Build-Win-Clang-x86_64-Release-Direct3D`
- `Build-Win-Clang-x86_64-Release-Vulkan`
- `Build-Win-MSVC-x86_64-Release-Graphite_Dawn_D3D12`

**WebAssembly 构建** (CanvasKit):
- `Build-Debian10-EMCC-wasm-Debug-CanvasKit`
- `Build-Debian10-EMCC-wasm-Release-CanvasKit_CPU`
- `Build-Debian10-EMCC-wasm-Release-CanvasKit_WebGPU`

**特殊构建**:
- `Build-Debian10-Clang-x86_64-Debug-Coverage`: 代码覆盖率
- `Build-Debian10-Clang-x86_64-Debug-Tidy`: ClangTidy 检查
- `Build-Debian10-Clang-x86_64-Release-CMake`: CMake 构建
- `Build-Debian10-Clang-x86_64-Release-NoDEPS`: 最小依赖
- `Build-Debian10-Clang-x86_64-OptimizeForSize`: 大小优化
- `Build-Ubuntu24.04-Clang-x86_64-Release-Fuzz`: 模糊测试

### 默认属性函数

```python
defaultProps = lambda buildername: dict(
    buildername=buildername,
    repository='https://skia.googlesource.com/skia.git',
    revision='abc123',
    path_config='kitchen',
    patch_set=2,
    swarm_out_dir='[SWARM_OUT_DIR]'
)
```

**配置说明**:
- `buildername`: 构建器名称
- `repository`: Skia 官方仓库
- `revision`: 示例提交哈希
- `path_config`: Kitchen 环境
- `patch_set`: Gerrit patch set 编号
- `swarm_out_dir`: Swarming 输出目录占位符

### 异常测试

```python
yield (
    api.test('unknown-docker-image') +
    api.properties(**defaultProps('Build-Unix-GCC-x86_64-Release-Docker')) +
    api.expect_exception('Exception')
)
```

测试未知 Docker 配置时是否正确抛出异常。

## 依赖关系

### 模块依赖
- `build`: Build API 模块
- `run`: 命令执行模块
- `vars`: 变量管理模块
- `recipe_engine/*`: Recipe Engine 核心模块

### 数据流
1. Recipe Engine 注入属性
2. `vars.setup()` 解析构建器名称
3. `api.build()` 选择策略并编译
4. `copy_build_products()` 复制产物
5. `check_failure()` 验证成功

## 设计模式与设计决策

### 参数化测试

为每个构建器生成独立测试:
- 确保所有配置被测试
- 快速定位失败的配置
- 支持并行测试执行

### 真实构建器名称

使用实际 CI 构建器名称:
- 测试反映真实场景
- 便于追踪 CI 问题
- 文档作用(展示支持的配置)

### 平台检测

Windows 构建器自动添加平台标记:
- 测试平台特定逻辑
- 模拟真实执行环境

### 最小示例

RunSteps 保持简洁:
- 只包含必要步骤
- 易于理解和复制
- 作为其他 Recipe 的模板

### 异常测试

包含失败场景测试:
- 验证错误处理
- 确保失败时正确报告
- 回归保护

## 性能考量

### 测试数量

100+ 测试用例:
- **运行时间**: 每个测试 <1 秒(模拟)
- **总时间**: ~2 分钟(串行)
- **并行化**: Recipe 测试框架支持并行

### 测试数据

使用占位符和模拟数据:
- 无实际文件 I/O
- 无网络访问
- 快速反馈

### CI 集成

每次代码变更触发测试:
- 早期发现破坏性变更
- 保护构建系统稳定性

## 相关文件

### 被测试模块
- `infra/bots/recipe_modules/build/api.py`: BuildApi 类
- `infra/bots/recipe_modules/build/default.py`: 默认构建
- `infra/bots/recipe_modules/build/android.py`: Android 构建
- `infra/bots/recipe_modules/build/docker.py`: Docker 构建
- `infra/bots/recipe_modules/build/cmake.py`: CMake 构建
- `infra/bots/recipe_modules/build/canvaskit.py`: CanvasKit 构建
- `infra/bots/recipe_modules/build/chromebook.py`: Chromebook 构建

### 测试基础设施
- `.recipes/`: 测试期望输出目录
- Recipe Engine 测试框架

### 实际 Recipe
- `infra/bots/recipes/compile.py`: 使用 build 模块的实际 Recipe

### CI 配置
- `infra/bots/tasks.json`: 所有测试构建器的定义
- `infra/bots/jobs.json`: 调度配置

### 文档
- Recipe Engine 文档
- Skia 构建系统文档

该文件是 Skia 构建系统质量保证的核心,通过覆盖所有支持的平台和配置,确保构建基础设施的可靠性和正确性。它既是最佳实践的示例,也是防止回归的安全网。
