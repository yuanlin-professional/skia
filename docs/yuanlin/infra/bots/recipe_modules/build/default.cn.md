# Default 构建模块

> 源文件: infra/bots/recipe_modules/build/default.py

## 概述

`default.py` 是 Skia 项目的核心构建模块,实现基于 GN (Generate Ninja) 和 Ninja 的默认构建流程。该模块支持多平台(Linux、Mac、Windows)、多编译器(Clang、GCC、MSVC)、多配置(Debug、Release、OptimizeForSize)以及各种特殊构建选项(ASAN、MSAN、TSAN、Dawn、Vulkan 等)。它是 Skia CI/CD 系统中使用最广泛的构建实现。

## 架构位置

该模块位于构建系统的默认策略层:

- **层级**: 基础设施 / 构建模块 / 默认 GN 构建
- **功能域**: 跨平台编译配置和执行
- **构建工具链**: GN + Ninja
- **覆盖范围**: 90% 以上的 Skia 构建任务

## 主要类与结构体

该模块不定义类,而是提供核心函数:

### compile_swiftshader

编译 SwiftShader (软件 Vulkan 实现)。

### get_compile_flags

生成 GN 编译参数和环境变量。

### finalize_gn_flags

将参数字典转换为 GN 命令行格式。

### compile_fn

执行完整的编译流程。

### copy_build_products

复制构建产物并处理平台特定文件。

## 公共 API 函数

### compile_swiftshader

```python
def compile_swiftshader(api, extra_tokens, swiftshader_root, ninja_root, cc, cxx, out):
```

**功能**: 使用 CMake 构建 SwiftShader Vulkan 软件实现。

**参数**:
- `api`: Recipe API 对象
- `extra_tokens`: 额外配置标记 (如 MSAN)
- `swiftshader_root`: SwiftShader 源码根目录
- `ninja_root`: Ninja 二进制所在目录
- `cc`, `cxx`: C/C++ 编译器路径
- `out`: 输出目录

**CMake 选项**:
- `SWIFTSHADER_BUILD_TESTS=OFF`: 禁用测试
- `SWIFTSHADER_WARNINGS_AS_ERRORS=OFF`: 警告不作为错误
- `REACTOR_ENABLE_MEMORY_SANITIZER_INSTRUMENTATION=OFF`: 禁用 MSAN 插桩(性能原因)

**MSAN 支持**:
- 添加自定义 libcxx 路径和编译标志
- 配置 `-fsanitize=memory` 和相关标志
- 避免使用 SwiftShader 预期的标准 MSAN 路径

**构建步骤**:
1. 创建输出目录
2. 运行 CMake 配置
3. 运行 Ninja 构建 `vk_swiftshader` 目标

### get_compile_flags

```python
def get_compile_flags(api, checkout_root, out_dir, workdir):
```

**功能**: 生成 GN 编译参数、环境变量和 ccache 配置。

**返回值**: `(args, env, ccache)` 三元组
- `args`: GN 参数字典
- `env`: 环境变量字典
- `ccache`: ccache 路径 (如果启用)

**基础参数**:
- `is_trivial_abi`: 启用 trivial ABI 优化
- `link_pool_depth`: 链接并发深度为 2
- `werror`: 将警告视为错误

**平台特定配置**:

**Mac/iOS**:
- 设置 Xcode 构建版本宏
- 配置部署目标 (MACOSX_DEPLOYMENT_TARGET, IPHONEOS_DEPLOYMENT_TARGET)
- iOS 签名证书和 mobileprovision 配置

**Linux**:
- 启用 ccache (除非 Tidy 构建)
- 配置 ccache 最大大小 75GB
- 设置 ccache 目录和选项

**编译器选择**:

**Clang (Linux)**:
- 使用 `clang_linux` CIPD 包
- 配置 `-B` 标志使用正确的 binutils
- 使用 lld 链接器
- Static 模式下静态链接 libstdc++ 和 libgcc

**GCC**:
- 使用 `-g1` 减少调试符号大小

**特殊构建模式**:

**Tidy**: ClangTidy 代码检查
- 使用 `tools/clang-tidy.sh` 包装器
- 启用额外特性以提高代码覆盖率

**Fuzz**: 模糊测试
- 设置 `skia_build_fuzzers=true`

**Coverage**: 代码覆盖率
- 添加 `-fprofile-instr-generate` 和 `-fcoverage-mapping`

**Debug 优化**: Debug 模式使用 `-O1` 加速编译

**OptimizeForSize**: 优化二进制大小
- 启用 `skia_enable_optimize_size`
- 使用运行时 ICU
- 禁用 JPEG gainmaps

**Sanitizer 支持**:
- **ASAN**: 启用地址消毒器,禁用 SPIRV 验证
- **MSAN**: 禁用 fontconfig,配置自定义 libcxx
- **TSAN**: 配置线程消毒器 libcxx

**图形后端**:

**Dawn (WebGPU)**:
- 调用 `util.set_dawn_args_and_env`
- 配置 D3D11/D3D12/Metal/Vulkan/GLES 后端

**SwiftShader**:
- 编译 SwiftShader
- 设置 `SK_GPU_TOOLS_VK_LIBRARY_NAME` 宏

**Vulkan**:
- 启用 Vulkan 和调试层
- TSAN 模式下额外启用 GL (workaround)

**Direct3D**: 启用 D3D,禁用 GL

**Metal**: 启用 Metal,禁用 GL

**特殊配置**:

**NoDEPS**: 最小依赖构建
- 禁用大部分第三方库
- 启用空 FontManager

**Graphite**: 启用实验性 Graphite 后端

**Fontations**: Rust 字体渲染

**RustPNG/RustBMP**: Rust 图像编解码器

**ICU4X**: Rust ICU 实现

### finalize_gn_flags

```python
def finalize_gn_flags(args):
```

**功能**: 将参数字典转换为 GN 命令行字符串。

**处理**:
- `extra_cflags` 和 `extra_ldflags` 列表转换为 JSON 格式
- 键按字母顺序排序确保输出稳定
- 格式: `key1=value1 key2=value2 ...`

### compile_fn

```python
def compile_fn(api, checkout_root, out_dir):
```

**功能**: 执行完整的 GN/Ninja 编译流程。

**执行步骤**:
1. 下载 GN 工具 (`fetch-gn`)
2. 下载 Ninja 工具 (`fetch-ninja`)
3. Mac/iOS 平台安装 Xcode
4. iOS 构建下载 provisioning profile
5. 生成编译参数和环境变量
6. 设置 PATH 环境变量包含 Ninja
7. 可选: 显示 ccache 统计
8. 运行 `gn gen` 生成 Ninja 文件
9. Fontations 构建: 运行 `gn clean`
10. 运行 `ninja` 执行编译
11. 可选: 显示 ccache 统计

### copy_build_products

```python
def copy_build_products(api, src, dst):
```

**功能**: 复制构建产物到目标目录,处理平台特定文件。

**基础复制**: 使用 `util.copy_listed_files` 复制默认产物列表

**特殊处理**:

**SwiftShader**: 复制 `swiftshader_out/` 目录内容

**OptimizeForSize**: 额外复制 `skottie_tool_cpu` 和 `skottie_tool_gpu`

**Mac + Sanitizer**: 复制 Xcode 的 sanitizer 动态库
- 查找 Xcode 中的 Clang 版本目录
- 定位 `lib/darwin/libclang_rt.*san_osx_dynamic.dylib`
- 复制所有 sanitizer dylib 到输出目录

## 内部实现细节

### SwiftShader 特殊构建

SwiftShader 使用 CMake 而非 GN:
- 独立的构建系统
- 自定义环境变量(CC, CXX, PATH)
- MSAN 支持通过自定义 libcxx 路径

### ccache 配置

```python
env['CCACHE_MAXSIZE'] = '75G'
env['CCACHE_DIR'] = workdir.joinpath('cache', 'ccache')
env['CCACHE_MAXFILES'] = '0'
env['CCACHE_COMPILERCHECK'] = 'content'
```

- 最大 75GB 缓存,足够 Debian10-Clang-x86 所有构建
- 基于内容而非时间戳检查编译器(CIPD 包时间戳不可靠)
- 无文件数限制

### 编译器版本标记

```python
extra_cflags.append('-DPLACEHOLDER_clang_linux_version=%s' %
                    api.run.asset_version('clang_linux', skia_dir))
```

将 CIPD 包版本注入宏,确保工具链更新时触发重新编译。

### iOS 签名配置

```python
args['skia_ios_identity'] = '".*83FNP.*"'  # Chromium 签名证书
args['skia_ios_profile'] = '"%s"' % provisioning_profile_path
```

使用 Chromium 团队的企业证书和 provisioning profile。

### Dawn Python 路径

```python
env['PYTHONPATH'] = api.path.pathsep.join([
    str(skia_dir.joinpath('third_party', 'externals')), '%%(PYTHONPATH)s'])
```

Dawn 构建脚本需要访问 `third_party/externals` 中的依赖。

### Fontations 清理

```python
if 'Fontations' in extra_tokens:
    api.run(api.step, 'gn clean', cmd=[gn, 'clean', out_dir])
```

Fontations 使用 Rust,需要完全清理以确保正确重新构建。

## 依赖关系

### 直接依赖
- `util.py`: 工具函数 (`py_to_gn`, `copy_listed_files`, `set_dawn_args_and_env`)
- GN: 元构建系统
- Ninja: 实际构建工具
- Clang/GCC: 编译器
- ccache: 编译缓存(Linux)
- Xcode: Apple 平台开发工具
- CIPD: 包管理器

### 被依赖者
- `api.py`: BuildApi 默认策略
- `docker.py`: 复用 `get_compile_flags`
- 所有构建 Recipe

## 设计模式与设计决策

### 数据驱动配置

使用字典管理 GN 参数:
- 易于修改和扩展
- 支持条件配置
- 集中管理所有选项

### 条件编译

基于 `extra_tokens` 启用特性:
- 灵活的特性组合
- 通过构建器名称控制
- 避免复杂的配置文件

### 增量编译支持

- 输出目录持久化
- GN/Ninja 自动检测变更
- ccache 加速重复编译

### 平台抽象

统一接口处理平台差异:
- 自动选择编译器路径
- 平台特定标志封装在条件分支中
- 路径使用 Recipe API 抽象

## 性能考量

### ccache 加速

- 典型场景: 提速 5-10 倍
- 75GB 缓存支持多个配置
- 基于内容的检查避免误判

### 并行编译

Ninja 默认使用所有 CPU 核心:
- 显著缩短编译时间
- 链接池深度限制为 2 避免内存溢出

### Debug 优化

Debug 模式使用 `-O1`:
- 减少编译时间
- 保持调试可行性
- 平衡速度和可调试性

### 工具下载缓存

GN 和 Ninja 通过 CIPD 缓存:
- 避免重复下载
- 版本固定确保一致性

## 相关文件

### 同模块文件
- `infra/bots/recipe_modules/build/util.py`: 工具函数
- `infra/bots/recipe_modules/build/api.py`: API 入口
- `infra/bots/recipe_modules/build/android.py`: Android 构建
- `infra/bots/recipe_modules/build/docker.py`: Docker 构建

### 构建工具
- `bin/fetch-gn`: GN 下载脚本
- `bin/fetch-ninja`: Ninja 下载脚本
- `tools/clang-tidy.sh`: ClangTidy 包装脚本

### GN 配置
- `.gn`: GN 根配置
- `BUILD.gn`: 构建文件
- `gn/`: GN 辅助文件

### 第三方依赖
- `third_party/externals/swiftshader/`: SwiftShader 源码
- `third_party/externals/dawn/`: Dawn 源码

### CIPD 包
- `clang_linux`: Linux Clang 工具链
- `clang_win`: Windows Clang 工具链
- `android_ndk_*`: Android NDK
- `ccache_linux`: ccache 工具

### 资源文件
- `infra/bots/recipe_modules/build/resources/ios.ensure`: iOS CIPD 包配置
- `infra/bots/recipe_modules/build/resources/copy_build_products.py`: 文件复制脚本

该模块是 Skia 构建系统的核心,支持极其丰富的配置选项和平台组合,通过精心设计的参数生成逻辑和工具链管理,确保在各种环境下都能可靠地构建 Skia。
