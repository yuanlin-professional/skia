# Build Util 工具模块

> 源文件: infra/bots/recipe_modules/build/util.py

## 概述

`util.py` 是 Skia 构建系统中的核心工具模块,提供构建过程中常用的辅助函数和常量定义。该模块主要负责数据格式转换、文件复制操作、以及构建参数配置,特别是针对 Dawn (WebGPU) 和 GN (Generate Ninja) 构建系统的支持。

## 架构位置

该模块位于 Recipe 构建系统的工具层:

- **层级**: 基础设施 / 构建工具 / 辅助函数
- **功能域**: 构建参数处理、产物管理、编译器配置
- **使用者**: 所有构建相关的 Recipe 模块 (default.py, android.py, docker.py 等)
- **作用**: 提供构建系统的通用功能抽象

## 主要类与结构体

该模块不定义类,而是提供全局常量和函数。

### 常量

#### DEFAULT_BUILD_PRODUCTS

```python
DEFAULT_BUILD_PRODUCTS = [
    'dm', 'dm.exe', 'dm.app',
    'nanobench.app',
    'get_images_from_skps', 'get_images_from_skps.exe',
    'nanobench', 'nanobench.exe',
    '*.so', '*.dll', '*.dylib',
    'skottie_tool',
    'lib/*.so',
    'run_testlab',
]
```

定义需要作为构建产物隔离的文件列表,支持多平台:
- **测试工具**: `dm` (DM 测试工具)
- **性能工具**: `nanobench` (性能基准测试)
- **动态库**: `.so` (Linux), `.dll` (Windows), `.dylib` (macOS)
- **应用包**: `.app` (macOS 应用)
- **其他工具**: `skottie_tool`, `run_testlab`

## 公共 API 函数

### py_to_gn

```python
def py_to_gn(val):
    """Convert val to a string that can be used as GN args."""
```

**功能**: 将 Python 数据类型转换为 GN 构建系统的参数格式。

**参数**:
- `val`: Python 值 (bool, str, list, tuple, dict)

**返回值**: GN 格式的字符串

**转换规则**:
- `True/False` → `"true"/"false"`
- 字符串 → 带引号的字符串 `"string"`
- 列表/元组 → `[item1,item2,...]`
- 字典 → `key1=val1 key2=val2 ...`

**示例**:
```python
py_to_gn(True)  # "true"
py_to_gn("path/to/file")  # '"path/to/file"'
py_to_gn(['opt1', 'opt2'])  # '["opt1","opt2"]'
py_to_gn({'cc': 'clang', 'is_debug': False})  # 'cc="clang" is_debug=false'
```

**注意事项**:
- 暂未处理引号转义 (`"$\`)
- 不支持的类型会抛出异常

### copy_listed_files

```python
def copy_listed_files(api, src, dst, product_list):
    """Copy listed files src to dst."""
```

**功能**: 复制指定的构建产物从源目录到目标目录。

**参数**:
- `api`: Recipe API 对象
- `src`: 源目录路径
- `dst`: 目标目录路径
- `product_list`: 要复制的文件模式列表

**实现**:
- 调用 Python 脚本 `copy_build_products.py`
- 使用逗号分隔的产物列表作为参数
- 标记为基础设施步骤 (`infra_step=True`)

**用途**:
- 将构建输出复制到隔离环境
- 准备测试或发布的文件
- 在不同构建阶段间传递产物

### set_dawn_args_and_env

```python
def set_dawn_args_and_env(args, env, api, extra_tokens, skia_dir):
    """Add to ``args`` and ``env`` the gn args and environment vars needed to
    make a build targeting Dawn."""
```

**功能**: 配置 Dawn (WebGPU) 构建所需的 GN 参数和环境变量。

**参数**:
- `args`: GN 参数字典 (会被修改)
- `env`: 环境变量字典 (会被修改)
- `api`: Recipe API 对象
- `extra_tokens`: 额外的配置标记列表
- `skia_dir`: Skia 源码目录

**配置内容**:

1. **基础 Dawn 参数**:
   - `skia_use_dawn = true`
   - `skia_use_gl = false` (禁用 OpenGL)

2. **后端选择** (默认全部禁用,根据 tokens 启用):
   - `dawn_enable_d3d11` (D3D11 token)
   - `dawn_enable_d3d12` (D3D12 token)
   - `dawn_enable_metal` (Metal token)
   - `dawn_enable_opengles` (GLES token)
   - `dawn_enable_vulkan` (Vulkan token)

3. **环境变量**:
   - `PYTHONPATH`: 添加 `third_party/externals` 以支持 Dawn 的 Python 脚本

**设计意图**:
- 精细控制 Dawn 后端,减少编译时间和产物大小
- 支持多平台后端 (D3D, Metal, Vulkan, OpenGL ES)
- 配置 Python 环境以支持 Dawn 的构建脚本

## 内部实现细节

### py_to_gn 类型检测

函数使用 `isinstance()` 和字符串格式化检测类型:

```python
if isinstance(val, bool):
    return 'true' if val else 'false'
elif '%s' % val == val:  # 字符串检测
    return '"%s"' % val
elif isinstance(val, (list, tuple)):
    return '[%s]' % (','.join(py_to_gn(x) for x in val))
elif isinstance(val, dict):
    # 按键排序确保输出稳定
    gn = ' '.join('%s=%s' % (k, py_to_gn(v)) for (k, v) in sorted(val.items()))
    return gn
```

- 递归处理嵌套结构
- 字典键排序确保输出可重现

### copy_build_products 脚本调用

```python
script = api.build.resource('copy_build_products.py')
api.step(
    name='copy build products',
    cmd=['python3', script, src, dst, ','.join(product_list)],
    infra_step=True
)
```

- 使用 Python 3 执行脚本
- 产物列表用逗号连接传递
- `infra_step=True` 标记为基础设施步骤,不计入主构建时间

### Dawn 后端配置逻辑

采用"默认全禁用 + 选择性启用"策略:

```python
args['dawn_enable_d3d11'] = 'false'
# ... 其他后端也设为 false
if 'D3D11' in extra_tokens:
    args['dawn_enable_d3d11'] = 'true'
```

这确保只编译需要的后端,避免不必要的依赖和编译时间。

## 依赖关系

### 直接依赖
- `copy_build_products.py`: 实际执行文件复制的 Python 脚本
- Recipe API: 用于执行步骤和访问资源

### 被依赖者
- `default.py`: 默认构建流程
- `android.py`: Android 构建
- `chromebook.py`: Chromebook 构建
- `docker.py`: Docker 构建
- `cmake.py`: CMake 构建
- `canvaskit.py`: CanvasKit (WebAssembly) 构建

### 外部依赖
- GN 构建系统:需要理解生成的参数格式
- Dawn 项目:Python 脚本和构建配置

## 设计模式与设计决策

### 单一职责原则

每个函数专注于一个明确的任务:
- `py_to_gn`: 数据转换
- `copy_listed_files`: 文件操作
- `set_dawn_args_and_env`: Dawn 配置

### 配置数据驱动

`DEFAULT_BUILD_PRODUCTS` 作为配置数据:
- 易于维护和扩展
- 支持跨平台 (通配符 `*.so`, `*.dll` 等)
- 集中管理构建产物

### 条件编译优化

Dawn 后端配置采用细粒度控制:
- 减少不必要的依赖
- 缩短编译时间
- 减小二进制文件大小

### 异常处理策略

`py_to_gn` 对不支持的类型抛出异常:
```python
else:  # pragma: nocover
    raise Exception('Converting %s to gn is not implemented.' % type(val))
```

这确保在遇到未预期类型时立即失败,而非产生错误的配置。

## 性能考量

### 构建产物选择

精心选择的产物列表:
- 只隔离必要的文件,减少传输开销
- 使用通配符 (如 `*.so`) 自动适应不同配置
- 平衡完整性和效率

### 脚本化文件操作

使用独立脚本复制文件而非 Recipe 步骤:
- Python 脚本可以高效处理通配符匹配
- 减少 Recipe 执行步骤数量
- 支持批量复制和错误处理

### Dawn 编译优化

按需启用后端显著影响编译性能:
- 全后端编译可能增加数分钟时间
- 单后端编译大幅减少编译时间
- 减少链接时间和产物大小

### 路径操作

使用 `api.path.pathsep.join()`:
- 自动适应不同操作系统的路径分隔符
- 避免硬编码 `:` 或 `;`
- 提高跨平台可移植性

## 相关文件

### 同模块文件
- `infra/bots/recipe_modules/build/default.py`: 主要调用者,默认构建流程
- `infra/bots/recipe_modules/build/android.py`: Android 特定构建
- `infra/bots/recipe_modules/build/api.py`: Build API 入口
- `infra/bots/recipe_modules/build/resources/copy_build_products.py`: 文件复制脚本

### 构建系统
- `gn`: Google 的元构建系统
- `ninja`: 实际的构建工具
- `third_party/externals/dawn`: Dawn WebGPU 实现

### 配置文件
- `.gn`: GN 配置文件
- `BUILD.gn`: 各模块的构建定义
- `args.gn`: 构建参数文件

### 相关工具
- `bin/fetch-gn`: 下载 GN 工具
- `bin/fetch-ninja`: 下载 Ninja 工具

该模块是 Skia 构建系统的基石,提供了必要的抽象和工具函数,使得各种构建场景能够共享通用逻辑,同时保持代码简洁和可维护性。
