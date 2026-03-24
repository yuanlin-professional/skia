# Chromebook 构建模块

> 源文件: infra/bots/recipe_modules/build/chromebook.py

## 概述

`chromebook.py` 是 Skia 项目中专门用于 Chromebook 平台编译的 Recipe 模块。该模块配置交叉编译环境,使用 Clang 编译器和特定的 sysroot,支持 ARM、ARM64 和 x86_64 架构。Chromebook 构建主要用于在 Chrome OS 设备上运行 Skia 测试和基准测试,特别是针对 ARM Mali GPU 的图形性能测试。

## 架构位置

该模块位于构建系统的 Chromebook 特定策略层:

- **层级**: 基础设施 / 构建模块 / Chromebook 支持
- **功能域**: Chrome OS 平台交叉编译
- **构建工具链**: Clang + custom sysroot + GN + Ninja
- **支持架构**: ARM (armhf), ARM64 (aarch64), x86_64

## 主要类与结构体

该模块不定义类,而是提供两个核心函数。

## 公共 API 函数

### compile_fn

```python
def compile_fn(api, checkout_root, out_dir):
```

**功能**: 使用交叉编译工具链为 Chromebook 编译 Skia。

**参数**:
- `api`: Recipe API 对象
- `checkout_root`: Skia 源码根目录
- `out_dir`: 构建输出目录

**执行流程**:
1. 提取构建配置(配置模式、目标架构)
2. 根据目标架构配置编译器标志和 sysroot
3. 构建 GN 参数字典
4. 下载 GN 和 Ninja 工具
5. 运行 `gn gen` 生成 Ninja 文件
6. 运行 `ninja` 编译 `nanobench` 和 `dm`

**支持架构**:

**ARM (32 位)**:
- Target triple: `armv7a-linux-gnueabihf`
- FPU: NEON
- ISA: Thumb
- Sysroot: `armhf_sysroot`
- GL 库: `chromebook_arm_gles`

**ARM64 (64 位)**:
- Target triple: `aarch64-linux-gnueabihf`
- Architecture: ARMv8-A
- Sysroot: `arm64_sysroot`
- GL 库: `chromebook_arm64_gles`
- 链接器: lld

**x86_64**:
- Native 编译(非交叉编译)
- GL 库: `chromebook_x86_64_gles`
- 链接器: lld

### copy_build_products

```python
def copy_build_products(api, src, dst):
```

**功能**: 复制 Chromebook 构建产物。

**实现**: 使用 `util.copy_listed_files` 复制默认产物列表。

## 内部实现细节

### 编译器配置

所有架构使用 Clang:
```python
clang_linux = os.path.join(top_level, 'clang_linux')
args = {
    'cc': "%s" % os.path.join(clang_linux, 'bin','clang'),
    'cxx': "%s" % os.path.join(clang_linux, 'bin','clang++'),
    # ...
}
```

### ARM 32 位配置

**Sysroot 和 GL 库**:
```python
sysroot_dir = os.path.join(top_level, 'armhf_sysroot')
gl_dir = os.path.join(top_level, 'chromebook_arm_gles')
```

**汇编标志**:
```python
args['extra_asmflags'] = [
    '--target=armv7a-linux-gnueabihf',
    '--sysroot=%s' % sysroot_dir,
    '-march=armv7-a',
    '-mfpu=neon',
    '-mthumb',
]
```
- ARMv7-A 架构
- NEON SIMD 支持
- Thumb 指令集(减小代码体积)

**编译标志**:
```python
args['extra_cflags'] = [
    '--target=armv7a-linux-gnueabihf',
    '--sysroot=%s' % sysroot_dir,
    '-I%s' % os.path.join(gl_dir, 'include'),
    '-I%s' % os.path.join(sysroot_dir, 'include'),
    '-I%s' % os.path.join(sysroot_dir, 'include', 'c++', '10'),
    '-I%s' % os.path.join(sysroot_dir, 'include', 'c++', '10', 'arm-linux-gnueabihf'),
    '-DMESA_EGL_NO_X11_HEADERS',
    '-U_GLIBCXX_DEBUG',
]
```
- 指定 sysroot 和头文件路径
- GCC 10 C++ 标准库头文件
- Mesa EGL 无 X11 模式
- 禁用 GLIBCXX debug 模式

**链接标志**:
```python
args['extra_ldflags'] = [
    '--target=armv7a-linux-gnueabihf',
    '--sysroot=%s' % sysroot_dir,
    '-static-libstdc++', '-static-libgcc',
    '-B%s' % os.path.join(sysroot_dir, 'bin'),
    '-B%s' % os.path.join(sysroot_dir, 'gcc-cross'),
    '-L%s' % os.path.join(sysroot_dir, 'gcc-cross'),
    '-L%s' % os.path.join(sysroot_dir, 'lib'),
    '-L%s' % os.path.join(gl_dir, 'lib'),
]
```
- 静态链接 libstdc++ 和 libgcc (避免运行时依赖)
- `-B` 标志指定二进制工具(ld, as)路径
- `-L` 标志指定库搜索路径

**环境变量**:
```python
env = {'LD_LIBRARY_PATH': os.path.join(sysroot_dir, 'lib')}
```

### ARM64 配置

**Sysroot 和 GL 库**:
```python
sysroot_dir = os.path.join(top_level, 'arm64_sysroot')
gl_dir = os.path.join(top_level, 'chromebook_arm64_gles')
```

**汇编标志**:
```python
args['extra_asmflags'] = [
    '--target=aarch64-linux-gnueabihf',
    '--sysroot=%s' % sysroot_dir,
    '-march=armv8-a',
    '-mfpu=neon',  # 实际 ARM64 不需要此标志
    '-mthumb',     # ARM64 不使用 Thumb
]
```
**注意**: `-mfpu=neon` 和 `-mthumb` 在 ARM64 中实际无效,可能是从 ARM 32 位复制的遗留标志。

**编译标志**:
```python
args['extra_cflags'] = [
    '--target=aarch64-linux-gnueabihf',
    '--sysroot=%s' % sysroot_dir,
    '-I%s' % os.path.join(sysroot_dir, 'include'),
    '-I%s' % os.path.join(sysroot_dir, 'include', 'c++', '12'),
    '-I%s' % os.path.join(sysroot_dir, 'include', 'c++', '12', 'aarch64-linux-gnu'),
    '-I%s' % os.path.join(gl_dir, 'include'),
    '-U_GLIBCXX_DEBUG',
]
```
- 使用 GCC 12 C++ 标准库头文件

**链接标志**:
```python
args['extra_ldflags'] = [
    '--target=aarch64-linux-gnueabihf',
    '--sysroot=%s' % sysroot_dir,
    '-static-libstdc++', '-static-libgcc',
    '-fuse-ld=%s' % os.path.join(clang_linux, 'bin', 'ld.lld'),
    '-B%s' % os.path.join(sysroot_dir, 'bin'),
    '-B%s' % os.path.join(sysroot_dir, 'gcc-cross'),
    '-L%s' % os.path.join(sysroot_dir, 'gcc-cross'),
    '-L%s' % os.path.join(sysroot_dir, 'lib'),
    '-L%s' % os.path.join(gl_dir, 'lib'),
    '-Wl,-u,__aarch64_swp4_acq_rel',
    '-Wl,-u,__aarch64_cas4_acq_rel',
    os.path.join(sysroot_dir, 'gcc-cross', 'libgcc.a'),
]
```
- 显式使用 lld 链接器
- 显式链接原子操作符号(ARMv8.1-A LSE)
- 静态链接 libgcc.a

### x86_64 配置

**GL 库**:
```python
gl_dir = os.path.join(top_level,'chromebook_x86_64_gles')
env = {}
```

**编译标志**:
```python
args['extra_cflags'] = [
    '-DMESA_EGL_NO_X11_HEADERS',
    '-I%s' % os.path.join(gl_dir, 'include'),
]
```

**链接标志**:
```python
args['extra_ldflags'] = [
    '-L%s' % os.path.join(gl_dir, 'lib'),
    '-static-libstdc++', '-static-libgcc',
    '-fuse-ld=lld',
]
```
- 不需要交叉编译工具
- 使用 lld 链接器

### 通用配置

**基础参数**:
```python
args = {
    'extra_cflags': [],
    'extra_ldflags': [],
    'extra_asmflags': [],
    'is_trivial_abi': True,
    'target_cpu': target_arch,
    'skia_use_fontconfig': False,
    'skia_use_system_freetype2': False,
    'skia_use_egl': True,
    'werror': True,
}
```
- 禁用 fontconfig 和系统 freetype
- 使用 EGL (而非 GLX)
- 警告视为错误

**Clang 版本标记**:
```python
args['extra_cflags'].append('-DREBUILD_IF_CHANGED_clang_linux_version=%s' %
                    api.run.asset_version('clang_linux', skia_dir))
```

**Release 模式**:
```python
if configuration != 'Debug':
    args['is_debug'] = False
```

### 构建目标

```python
api.run(api.step, 'ninja',
        cmd=[ninja, '-C', out_dir, 'nanobench', 'dm'])
```

只构建两个目标:
- `nanobench`: 性能基准测试工具
- `dm`: 渲染正确性测试工具

## 依赖关系

### 直接依赖
- `util.py`: 工具函数 (`py_to_gn`, `copy_listed_files`)
- `clang_linux`: Clang 编译器 CIPD 包
- Sysroot: 交叉编译根文件系统
  - `armhf_sysroot`: ARM 32 位
  - `arm64_sysroot`: ARM 64 位
- GLES 库:
  - `chromebook_arm_gles`: ARM Mali 驱动
  - `chromebook_arm64_gles`: ARM64 Mali 驱动
  - `chromebook_x86_64_gles`: x86_64 Mesa 驱动
- GN: 元构建系统
- Ninja: 构建工具

### 被依赖者
- `api.py`: BuildApi 根据 'Chromebook' 关键字选择此模块
- Chromebook 相关 Recipe:
  - `compile.py`: 编译
  - `test.py`: 测试执行
  - `perf.py`: 性能测试

### 外部依赖
- Chrome OS 设备或远程 SSH 访问
- `infra/bots/recipe_modules/flavor/chromebook.py`: 执行测试的 flavor 模块

## 设计模式与设计决策

### 交叉编译策略

从 x86_64 Linux 编译到 ARM:
- **优势**: 快速编译(利用强大的构建服务器)
- **挑战**: 需要完整的 sysroot 和交叉编译工具链
- **权衡**: 复杂的配置 vs. 性能提升

### 静态链接

使用 `-static-libstdc++` 和 `-static-libgcc`:
- **优势**: 减少运行时依赖,简化部署
- **劣势**: 增加二进制大小
- **适用场景**: 测试工具(不需要频繁更新)

### 架构特定配置

每种架构独立配置:
- 清晰的架构边界
- 易于添加新架构
- 明确的平台差异

### EGL 而非 GLX

```python
'skia_use_egl': True
```

Chrome OS 使用 EGL (嵌入式 OpenGL):
- 轻量级窗口系统集成
- 支持无头(headless)渲染
- 跨平台兼容性好

## 性能考量

### 交叉编译性能

- **编译主机**: x86_64 多核服务器
- **目标设备**: ARM Chromebook (通常低功耗)
- **性能提升**: 编译速度快 5-10 倍

### 静态链接权衡

- **二进制大小**: 增加 ~5-10 MB
- **部署简化**: 无需确保设备上有正确的库版本
- **加载时间**: 静态链接避免动态链接器开销

### NEON 优化

ARM 构建启用 NEON SIMD:
- 显著加速图形操作
- 矢量化数学运算
- 现代 ARM 设备标配

### lld 链接器

ARM64 和 x86_64 使用 lld:
- 比 GNU ld 更快
- 更好的错误诊断
- Clang/LLVM 生态的一部分

### 目标选择

只构建 `nanobench` 和 `dm`:
- 减少构建时间
- 减小传输的文件大小
- 满足测试需求

## 相关文件

### 同模块文件
- `infra/bots/recipe_modules/build/api.py`: API 入口
- `infra/bots/recipe_modules/build/util.py`: 工具函数
- `infra/bots/recipe_modules/build/default.py`: 默认构建(参考)

### Sysroot 资产
- `infra/bots/assets/armhf_sysroot/`: ARM 32 位 sysroot 定义
- `infra/bots/assets/arm64_sysroot/`: ARM 64 位 sysroot 定义

### GLES 驱动资产
- `infra/bots/assets/chromebook_arm_gles/`: ARM Mali GLES 库
- `infra/bots/assets/chromebook_arm64_gles/`: ARM64 Mali GLES 库
- `infra/bots/assets/chromebook_x86_64_gles/`: x86_64 Mesa GLES 库

### 编译器资产
- `infra/bots/assets/clang_linux/`: Clang 工具链

### Recipe 模块
- `infra/bots/recipe_modules/flavor/chromebook.py`: Chromebook 测试执行
- `infra/bots/recipe_modules/flavor/ssh.py`: SSH 远程执行基类

### Recipe 使用
- `infra/bots/recipes/compile.py`: 编译 Recipe
- `infra/bots/recipes/test.py`: Chromebook 测试
- `infra/bots/recipes/perf.py`: Chromebook 性能测试

### GN 配置
- `BUILD.gn`: Chromebook 相关构建规则
- `gn/`: GN 辅助文件

### CI 配置
- `infra/bots/tasks.json`: Chromebook 构建和测试任务
- `infra/bots/jobs.json`: 任务调度配置

该模块展示了 Skia 如何通过精心配置的交叉编译工具链支持 Chrome OS 平台,特别是针对 ARM 设备的优化构建。通过使用完整的 sysroot 和特定的 GLES 驱动,确保在各种 Chromebook 设备上获得正确的图形渲染行为和性能。
