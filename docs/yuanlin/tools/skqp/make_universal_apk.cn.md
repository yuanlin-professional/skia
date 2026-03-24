# make_universal_apk.py

> 源文件: tools/skqp/make_universal_apk.py

## 概述

`make_universal_apk.py` 是 Skia SkQP (Skia Quality Program) 项目的通用 APK 构建脚本。该脚本简化了创建包含多架构原生库的 Android APK 的流程，支持 ARM、ARM64、x86 和 x64 四种架构。它是 `create_apk.py` 的高层封装，自动处理资源目录的符号链接管理。

SkQP 是 Skia 的 Android 质量保证工具，用于在 Android 设备上运行自动化测试，验证 Skia 图形库的正确性和性能。

## 架构位置

该文件位于 Skia SkQP 工具集中：

```
skia/
  tools/
    skqp/
      make_universal_apk.py     # 本文件（高层封装）
      create_apk.py             # 底层 APK 构建逻辑
      download_model            # 下载模型数据
  platform_tools/
    android/
      apps/
        skqp/                   # SkQP Android 应用
          src/main/assets/
            resources/          # 测试资源（符号链接）
  resources/                    # Skia 资源目录
```

在 SkQP 构建流程中的位置：
- **用户接口层**: 提供简洁的命令行接口
- **资源管理层**: 处理符号链接和资源组织
- **构建协调层**: 调用 `create_apk.py` 执行实际构建

## 主要类与结构体

该脚本不定义类，使用函数式设计。

## 公共 API 函数

### make_apk(opts)

```python
def make_apk(opts):
    assert '/' in [os.sep, os.altsep]  # 确保路径分隔符兼容

    skia_dir = os.path.dirname(__file__) + '/../..'
    create_apk.makedirs(opts.build_dir)
    assets_dir = skia_dir + '/platform_tools/android/apps/skqp/src/main/assets'
    resources_path = assets_dir + '/resources'

    with create_apk.RemoveFiles(resources_path):  # 清理上下文管理器
        create_apk.remove(resources_path)
        os.symlink('../../../../../../../resources', resources_path)
        create_apk.create_apk(opts)
```

**功能**: 构建通用 APK 的主流程。

**流程**:
1. 创建构建目录
2. 确定 assets 目录路径
3. 使用上下文管理器确保清理
4. 删除旧的 resources 符号链接
5. 创建新的符号链接指向 Skia 资源目录
6. 调用 `create_apk.create_apk()` 构建 APK

**关键设计**:
- **符号链接**: 避免复制大量资源文件，节省磁盘空间和时间
- **上下文管理器**: 确保即使构建失败也会清理符号链接
- **相对路径**: 使用相对路径创建符号链接，提高可移植性

### main()

```python
def main():
    options = create_apk.SkQP_Build_Options()
    if options.error:
        sys.stderr.write(options.error + __doc__)
        sys.exit(1)
    options.write(sys.stdout)
    make_apk(options)
```

**功能**: 脚本入口点。

**流程**:
1. 解析构建选项（从命令行和环境变量）
2. 检查错误，打印帮助文档
3. 输出构建配置
4. 调用 `make_apk()` 执行构建

## 内部实现细节

### 符号链接路径计算

```python
resources_path = assets_dir + '/resources'
# 符号链接目标
'../../../../../../../resources'
```

**路径解析**:
```
platform_tools/android/apps/skqp/src/main/assets/resources
                                                  ↓ (符号链接)
../../../../../../../resources
= platform_tools/android/apps/skqp/resources (向上 7 级)
= skia/resources (实际目录)
```

### 上下文管理器使用

```python
with create_apk.RemoveFiles(resources_path):
    # 构建代码
    pass
# 退出时自动删除 resources_path
```

**优势**:
- 异常安全：即使构建失败也会清理
- 代码简洁：无需手动 try-finally
- 可读性好：意图清晰

### 路径分隔符断言

```python
assert '/' in [os.sep, os.altsep]
```

**目的**:
- 确保脚本在 Unix-like 系统上运行
- 硬编码的 '/' 路径分隔符仅在 Unix/Linux/macOS 上有效
- Windows 上此断言会失败（os.sep 是 '\\'）

## 依赖关系

**Python 标准库**:
- `os`: 文件系统操作
- `sys`: 系统交互

**内部模块**:
- `create_apk`: 底层 APK 构建模块
  - `SkQP_Build_Options`: 构建选项类
  - `makedirs()`: 创建目录
  - `remove()`: 删除文件/目录
  - `RemoveFiles`: 清理上下文管理器
  - `create_apk()`: APK 构建函数

**外部工具依赖** (通过 create_apk.py):
- Android NDK (环境变量 `ANDROID_NDK_HOME`)
- Android SDK (环境变量 `ANDROID_HOME`)
- Ninja 构建系统
- Skia 资源文件

**依赖图**:
```
make_universal_apk.py (本文件)
    ↓
create_apk.py
    ↓
├── skqp_gn_args.py (GN 参数生成)
├── Ninja (构建系统)
├── Android NDK (原生库编译)
└── Android SDK (APK 打包)
```

## 设计模式与设计决策

### 设计模式

1. **外观模式**: 封装复杂的 `create_apk` 接口
2. **上下文管理器模式**: `RemoveFiles` 确保资源清理
3. **委托模式**: 将实际构建委托给 `create_apk`

### 设计决策

**1. 符号链接而非复制**:
```python
os.symlink('../../../../../../../resources', resources_path)
```
- **优点**: 节省磁盘空间（resources 目录可能有数百 MB）
- **优点**: 构建更快（无需复制）
- **优点**: 始终使用最新资源
- **缺点**: 要求 Unix-like 系统

**2. 临时符号链接**:
```python
with create_apk.RemoveFiles(resources_path):
    # 使用符号链接
pass  # 自动删除
```
- 构建前创建，构建后立即删除
- 避免残留状态污染仓库
- 不影响 Git 跟踪

**3. 命令行架构参数**:
```bash
python make_universal_apk.py arm x86
```
- 默认: 所有架构 (arm, arm64, x86, x64)
- 可选: 仅指定架构
- 灵活性高，适合不同场景

**4. 环境变量配置**:
- `ANDROID_NDK_HOME`: NDK 位置
- `ANDROID_HOME`: SDK 位置
- `SKQP_BUILD_DIR`: 构建目录（可选）
- `SKQP_OUTPUT_DIR`: 输出目录（可选）
- `SKQP_DEBUG`: 调试模式（可选）

**5. 错误前置检查**:
```python
if options.error:
    sys.stderr.write(options.error + __doc__)
    sys.exit(1)
```
- 在构建前验证所有前置条件
- 立即失败，节省时间

### 与 create_apk.py 的分工

| 功能 | make_universal_apk.py | create_apk.py |
|------|----------------------|---------------|
| 符号链接管理 | ✓ | - |
| 构建选项解析 | - | ✓ |
| GN 配置生成 | - | ✓ |
| Ninja 编译 | - | ✓ |
| APK 打包 | - | ✓ |
| 多架构支持 | - | ✓ |

## 性能考量

### 时间开销

| 阶段 | 时间（估算） | 说明 |
|------|------------|------|
| 符号链接创建 | <1 秒 | 极快 |
| 单架构编译 | 5-15 分钟 | 取决于机器性能 |
| 四架构编译 | 20-60 分钟 | 并行编译部分重叠 |
| APK 打包 | 1-2 分钟 | 签名和对齐 |

### 磁盘占用

- **符号链接方案**: ~0 MB（仅链接元数据）
- **复制方案（假设）**: ~200-500 MB（resources 目录）

**节省**: 数百 MB 磁盘空间

### 优化策略

1. **增量构建**: Ninja 支持增量编译
2. **架构选择**: 仅构建需要的架构
3. **符号链接**: 避免资源复制
4. **并行编译**: Ninja 自动并行

## 相关文件

### 同目录文件
- `tools/skqp/create_apk.py`: 底层 APK 构建逻辑
- `tools/skqp/download_model`: 下载 ML 模型数据
- `tools/skqp/README.md`: SkQP 使用文档

### 构建配置
- `gn/skqp_gn_args.py`: GN 参数生成脚本
- `platform_tools/android/apps/skqp/build.gradle`: Gradle 构建脚本

### Android 应用
- `platform_tools/android/apps/skqp/src/main/`: Android 应用源码
- `platform_tools/android/apps/skqp/src/main/assets/`: 资源目录

### SkQP 源码
- `tools/skqp/src/`: SkQP 测试框架源码
- `bench/`: 性能基准测试
- `gm/`: 黄金图像测试

### 资源文件
- `resources/`: Skia 测试资源（图片、字体等）

### 使用示例

**基本用法（所有架构）**:
```bash
export ANDROID_NDK_HOME=/path/to/ndk
export ANDROID_HOME=/path/to/sdk
python tools/skqp/make_universal_apk.py
```

**指定架构**:
```bash
python tools/skqp/make_universal_apk.py arm64 x64
```

**自定义构建和输出目录**:
```bash
export SKQP_BUILD_DIR=/tmp/skqp_build
export SKQP_OUTPUT_DIR=~/Desktop
python tools/skqp/make_universal_apk.py
```

**调试模式**:
```bash
export SKQP_DEBUG=1
python tools/skqp/make_universal_apk.py
```

**前置步骤**:
```bash
# 同步依赖
python tools/git-sync-deps

# 下载模型数据
python tools/skqp/download_model

# 构建 APK
python tools/skqp/make_universal_apk.py
```

**输出**:
- APK 文件位于 `SKQP_OUTPUT_DIR` 或默认位置
- 文件名类似: `skqp-universal-debug.apk` 或 `skqp-universal-release.apk`
