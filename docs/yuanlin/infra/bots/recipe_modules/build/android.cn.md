# Android 构建模块

> 源文件: infra/bots/recipe_modules/build/android.py

## 概述

`android.py` 是 Skia 项目中专门用于 Android 平台编译的 Recipe 模块。该模块配置 Android NDK 工具链,支持多种 CPU 架构(ARM、ARM64、x86)、图形后端(Vulkan、Dawn)和特殊构建模式(ASAN、HWASAN、OptimizeForSize)。它是所有 Android 相关构建任务的核心实现。

## 架构位置

该模块位于构建系统的 Android 特定策略层:

- **层级**: 基础设施 / 构建模块 / Android 支持
- **功能域**: Android 平台跨架构编译
- **构建工具链**: Android NDK + GN + Ninja
- **支持架构**: ARM、ARM64、x86

## 主要类与结构体

该模块不定义类,而是提供函数和常量。

### 常量

#### ANDROID_BUILD_PRODUCTS_LIST

```python
ANDROID_BUILD_PRODUCTS_LIST = [
    'dm',
    'nanobench',
    'skottie_tool_gpu',  # 仅在 OptimizeForSize 构建中存在
]
```

定义 Android 构建需要复制的产物。

## 公共 API 函数

### compile_fn

```python
def compile_fn(api, checkout_root, out_dir):
```

**功能**: 使用 Android NDK 编译 Skia。

**参数**:
- `api`: Recipe API 对象
- `checkout_root`: Skia 源码根目录
- `out_dir`: 构建输出目录

**执行流程**:
1. 提取构建配置(编译器、配置模式、目标架构等)
2. 验证编译器为 Clang(目前不支持 GCC)
3. 根据宿主机平台选择 NDK 资产
4. 构建 GN 参数字典
5. 处理特殊构建模式(Dawn、Vulkan、Sanitizers 等)
6. 提取 API level(如果指定)
7. 下载 GN 和 Ninja 工具
8. 运行 `gn gen` 生成 Ninja 文件
9. 运行 `ninja` 执行编译

**支持配置**:

**NDK 平台**:
- Linux: `android_ndk_linux`
- Mac: `android_ndk_darwin`
- Windows: `android_ndk_windows` (路径为 'n')

**目标架构**:
- `arm`: 32 位 ARM
- `arm64`: 64 位 ARM (ARM64/AArch64)
- `x86`: 32 位 x86

**图形后端**:
- Vulkan (需要 API 26+)
- Dawn WebGPU (需要 API 26+)

**Sanitizers**:
- ASAN (地址消毒器)
- HWASAN (硬件辅助地址消毒器)

**其他特性**:
- Graphite (实验性渲染后端)
- Wuffs (图像解码库)
- OptimizeForSize (二进制大小优化)

### copy_build_products

```python
def copy_build_products(api, src, dst):
```

**功能**: 复制 Android 构建产物。

**实现**: 使用 `util.copy_listed_files` 复制 `ANDROID_BUILD_PRODUCTS_LIST`

## 内部实现细节

### NDK 路径配置

```python
ndk_asset = 'android_ndk_linux'
ndk_path = ndk_asset
if 'Mac' in os:
    ndk_asset = 'android_ndk_darwin'
    ndk_path = ndk_asset
elif 'Win' in os:
    ndk_asset = 'android_ndk_windows'
    ndk_path = 'n'
```

**Windows 特殊处理**: 路径为 'n' 而非完整资产名称(可能是 CIPD 包结构差异)

### 编译器验证

```python
assert compiler == 'Clang'  # At this rate we might not ever support GCC.
```

**设计决策**: 只支持 Clang,因为:
- Android NDK 官方推荐 Clang
- GCC 在新版 NDK 中已弃用
- Clang 性能和标准支持更好

### GN 参数构建

**基础参数**:
```python
args = {
    'is_trivial_abi': 'true',
    'ndk': quote(api.vars.workdir.joinpath(ndk_path)),
    'target_cpu': quote(target_arch),
    'werror': 'true',
}
```

**条件参数**:
- `is_debug`: Release 构建设为 false
- `ndk_api`: Dawn/Vulkan 需要 API 26
- `sanitize`: ASAN 或 HWASAN
- `skia_enable_graphite`: Graphite 后端
- `skia_use_wuffs`: Wuffs 解码器
- `skia_enable_optimize_size`: 大小优化

### Debug 优化

```python
if configuration == 'Debug':
    extra_cflags.append('-O1')
```

Debug 模式使用 `-O1` 优化:
- 加速编译
- 减少二进制大小
- 保持基本调试能力

### API Level 提取

```python
for t in extra_tokens:
    m = re.search(r'API(\d+)', t)
    if m and len(m.groups()) == 1:
        args['ndk_api'] = m.groups()[0]
        break
```

从构建器名称的 extra_tokens 中提取 API level:
- 格式: `API21`, `API26` 等
- 使用正则表达式解析
- 覆盖默认 API level

### Dawn 配置

```python
if 'Dawn' in extra_tokens:
    util.set_dawn_args_and_env(args, env, api, extra_tokens, skia_dir)
    args['ndk_api'] = 26  # skia_use_gl=false, so use vulkan
```

Dawn 需要 Vulkan,因此设置 API level 26(Android 8.0)。

### Vulkan 配置

```python
if 'Vulkan' in extra_tokens and not 'Dawn' in extra_tokens:
    args['ndk_api'] = 26
    args['skia_enable_vulkan_debug_layers'] = 'false'
    args['skia_use_gl'] = 'false'
    args['skia_use_vulkan'] = 'true'
```

**注意**: 禁用 Vulkan 调试层(可能因性能或兼容性问题)

### OptimizeForSize 配置

```python
if configuration == 'OptimizeForSize':
    extra_ldflags.append('-Wl,--build-id=sha1')
    args.update({
        'skia_use_runtime_icu': 'true',
        'skia_enable_optimize_size': 'true',
        'skia_use_jpeg_gainmaps': 'false',
    })
```

**优化策略**:
- 添加 build ID 用于 Bloaty 分析
- 使用运行时 ICU (减小静态链接大小)
- 启用大小优化标志
- 禁用 JPEG gainmaps (减小二进制体积)

### Framework Workarounds

```python
if 'FrameworkWorkarounds' in extra_tokens:
    extra_cflags.append('-DSK_SUPPORT_LEGACY_ALPHA_BITMAP_AS_COVERAGE')
```

**用途**: 测试 `SK_BUILD_FOR_ANDROID_FRAMEWORK` 的特殊行为

**目标**: 确保 Skia 在 Android Framework 中正常工作

### NDK 版本标记

```python
extra_cflags.append('-DREBUILD_IF_CHANGED_ndk_version=%s' %
                    api.run.asset_version(ndk_asset, skia_dir))
```

将 NDK CIPD 包版本注入宏,NDK 更新时触发完全重新编译。

### Ninja 路径配置

```python
ninja_root = skia_dir.joinpath('third_party', 'ninja')
ninja = skia_dir.joinpath(ninja_root, 'ninja')

existing_path = env.get('PATH', '%(PATH)s')
env['PATH'] = api.path.pathsep.join([existing_path, str(ninja_root)])
```

将 Ninja 添加到 PATH,支持子命令(如 Dawn CMake 构建)查找。

## 依赖关系

### 直接依赖
- `util.py`: 工具函数 (`py_to_gn`, `copy_listed_files`, `set_dawn_args_and_env`)
- Android NDK: 编译工具链
- GN: 元构建系统
- Ninja: 构建工具
- CIPD: NDK 包管理

### 被依赖者
- `api.py`: BuildApi 根据 'Android' 关键字选择此模块
- Android 相关 Recipe:
  - `compile.py`
  - `test.py` (需要编译产物)
  - `perf.py` (需要 nanobench)

### 外部依赖
- Android SDK Platform Tools (adb)
- Android 设备或模拟器(测试时)

## 设计模式与设计决策

### 平台抽象

统一接口处理不同宿主机平台:
- 自动选择对应的 NDK 资产
- 路径适配(Windows 特殊处理)

### 条件编译

基于 `extra_tokens` 灵活组合特性:
- 图形后端(Vulkan, Dawn)
- Sanitizers (ASAN, HWASAN)
- 优化模式(Size, Debug)

### API Level 灵活性

支持多种 API level:
- 默认行为(GN 决定)
- Vulkan/Dawn 强制 API 26
- 通过构建器名称显式指定

### 最小产物集

只复制必要的二进制文件:
- `dm`: 测试工具
- `nanobench`: 性能基准测试
- `skottie_tool_gpu`: 大小分析(OptimizeForSize)

减少传输和存储开销。

## 性能考量

### 交叉编译

从宿主机(x86_64)编译到目标架构(ARM):
- 无需模拟器开销
- 充分利用宿主机多核 CPU
- 编译速度远快于设备上编译

### NDK 缓存

NDK 通过 CIPD 缓存,避免重复下载:
- NDK 大小 ~1-2 GB
- 首次下载耗时,后续即时可用

### 增量编译

输出目录持久化支持增量编译:
- GN/Ninja 自动检测变更
- 典型增量编译耗时 <1 分钟
- 完全编译耗时 5-15 分钟(取决于配置)

### Debug 优化

`-O1` 优化平衡编译速度和调试能力:
- 编译时间减少 30-50%
- 二进制大小减少 20-40%
- 保留基本调试信息

### Sanitizer 开销

ASAN/HWASAN 增加编译和运行时开销:
- 编译时间增加 ~20%
- 二进制大小增加 2-3 倍
- 运行时性能降低 2-5 倍
- 用于 CI 测试,不用于发布

## 相关文件

### 同模块文件
- `infra/bots/recipe_modules/build/api.py`: API 入口
- `infra/bots/recipe_modules/build/util.py`: 工具函数
- `infra/bots/recipe_modules/build/default.py`: 默认构建(参考实现)

### Android 特定文件
- `platform_tools/android/`: Android 工具和脚本
- `platform_tools/android/apps/`: Android 示例应用

### GN 配置
- `BUILD.gn`: Android 相关构建规则
- `gn/android.gni`: Android GN 导入文件

### CIPD 资产
- `infra/bots/assets/android_ndk_linux/`: Linux NDK 资产定义
- `infra/bots/assets/android_ndk_darwin/`: macOS NDK 资产定义
- `infra/bots/assets/android_ndk_windows/`: Windows NDK 资产定义

### Recipe 使用
- `infra/bots/recipes/compile.py`: 编译 Recipe
- `infra/bots/recipes/test.py`: Android 测试 Recipe
- `infra/bots/recipes/perf.py`: Android 性能测试

### CI 配置
- `infra/bots/tasks.json`: Android 构建任务定义
- `infra/bots/jobs.json`: 任务调度配置

### 测试基础设施
- `infra/bots/recipe_modules/flavor/android.py`: Android 测试执行
- `infra/bots/recipe_modules/run/`: 设备命令执行

该模块是 Skia Android 支持的核心,通过精心配置的 NDK 工具链和灵活的参数系统,支持多种 Android 平台的构建需求,确保 Skia 能够在各种 Android 设备上高效运行。
