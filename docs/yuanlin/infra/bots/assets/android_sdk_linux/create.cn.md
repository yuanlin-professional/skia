# Android SDK Linux 资产创建脚本

> 源文件: infra/bots/assets/android_sdk_linux/create.py

## 概述

Android SDK Linux 版本的资产创建核心脚本。该脚本通过递归复制完整的 Android SDK 目录来创建资产，从环境变量读取源 SDK 路径，确保所有必需的构建工具、平台文件和库都被包含。

## 架构位置

位于 `infra/bots/assets/android_sdk_linux/`，负责将开发者本地安装的 Android SDK 打包成可分发的资产，供 CI 系统使用。

## 主要类与结构体

函数式风格，使用标准库模块。

### 模块级常量

```python
ENV_VAR = 'ANDROID_SDK_LINUX_SDK_ROOT'
```

定义环境变量名，用于接收来自 create_and_upload.py 的 SDK 路径。

## 公共 API 函数

### `getenv(key)`

安全的环境变量读取函数，提供友好的错误提示。

**参数**:
- `key` (str): 环境变量名

**返回**: 环境变量值

**错误处理**: 如果变量不存在，打印错误消息并退出。

### `create_asset(target_dir, android_sdk_root)`

核心资产创建函数，执行SDK目录复制。

**参数**:
- `target_dir` (str): 资产输出目录
- `android_sdk_root` (str): 源 Android SDK 根目录

**实现**:
```python
def create_asset(target_dir, android_sdk_root):
    dst = os.path.join(target_dir, 'android-sdk')
    shutil.copytree(android_sdk_root, dst)
```

简单但完整地复制整个SDK目录树。

### `main()`

脚本入口，从环境变量读取SDK路径并执行复制。

## 内部实现细节

### 完整复制策略

使用 `shutil.copytree()` 完整复制 SDK 目录，包括：
- **build-tools/**: 各版本的构建工具（aapt, dx, zipalign 等）
- **platforms/**: Android API 级别的库和接口定义
- **platform-tools/**: adb, fastboot 等工具
- **tools/**: SDK 管理器和模拟器工具
- **sources/**: Android 源码（如果已下载）
- **system-images/**: 模拟器系统镜像（如果已下载）
- **emulator/**: Android 模拟器
- **ndk/**: Android NDK（如果已安装）
- **extras/**: Google Play 服务等额外组件

### 目录命名

复制后的目录命名为 `android-sdk`，而非保留原名。这种统一命名：
- 简化路径配置
- 与平台无关
- 避免版本号污染路径

### 环境变量模式

与 Windows 工具链资产使用相同的环境变量通信模式：
```
create_and_upload.py 设置环境变量 → create.py 读取环境变量
```

这避免了通过 sk 工具传递自定义参数的限制。

### 符号链接处理

`shutil.copytree()` 默认行为：
- Python 3.8+: 保留符号链接
- 早期版本: 复制符号链接指向的文件

Android SDK 中可能包含符号链接，保留符号链接可以：
- 减小资产体积
- 保持目录结构一致性

## 依赖关系

### 源依赖

- **本地 Android SDK**: 通过 Android Studio 或 sdkmanager 安装
- **完整安装**: 需要包含所有构建 Skia 所需的组件

### Python 依赖

- **Python 标准库**: argparse, os, shutil, sys
- **Python 版本**: 兼容 Python 2 和 3

### 磁盘空间

- **源 SDK**: 10-50 GB（取决于安装的组件）
- **复制目标**: 需要相同大小的可用空间
- **峰值使用**: 2倍 SDK 大小

## 设计模式与设计决策

### 完整复制vs选择性复制

选择完整复制而非选择性过滤的原因：

**优点**:
- **简单**: 无需维护复杂的过滤规则
- **完整**: 确保不遗漏任何必需文件
- **灵活**: 支持不同的 Android API 级别和工具版本

**缺点**:
- **体积大**: 包含可能不需要的组件
- **时间长**: 复制大量文件耗时
- **带宽**: 上传和下载需要更多带宽

对于 CI 系统，完整性比体积更重要，因此这是合理的权衡。

### 环境变量优于参数

使用环境变量而非命令行参数的原因：
- sk 工具不支持传递自定义参数
- 环境变量是跨进程通信的简单方式
- 与其他资产脚本保持一致

### 统一命名约定

将 SDK 复制到 `android-sdk` 目录：
- 避免路径中包含主机特定信息
- 简化不同环境的配置
- 提供一致的接口

## 性能考量

### 复制性能

影响复制速度的因素：
- **文件数量**: Android SDK 包含数万个文件
- **文件大小**: 从几字节到几百 MB
- **磁盘类型**: SSD 比 HDD 快 5-10 倍
- **文件系统**: ext4, xfs, btrfs 性能不同

典型复制时间：
- **完整 SDK (30 GB)**: 5-30 分钟
- **最小 SDK (5 GB)**: 1-5 分钟

### 优化建议

潜在的优化方向：
1. **选择性复制**: 只复制必需的组件
2. **并行复制**: 使用多线程复制
3. **增量更新**: 只复制变化的文件
4. **硬链接**: 在支持的文件系统上使用硬链接

但这些优化会增加复杂性，目前的简单方案已满足需求。

### 压缩传输

上传到 CIPD 时会压缩资产：
- **原始大小**: 30 GB
- **压缩后**: 8-12 GB（压缩率 60-70%）
- **压缩时间**: 10-20 分钟

CIPD 使用高效的压缩算法（如 zstd）平衡压缩率和速度。

## 相关文件

### 资产管理

- **`create_and_upload.py`**: 上层编排脚本
- **`__init__.py`**: Python 包标识
- **`VERSION`**: 资产版本号
- **`download.py`**: 从 CIPD 下载资产

### Android SDK 组件

- **`platforms/android-*/`**: 各 API 级别的库和资源
- **`build-tools/*/`**: 构建工具的各个版本
- **`platform-tools/`**: adb 等跨版本工具
- **`tools/`**: SDK 管理和模拟器工具

### 使用场景

- **CI 构建任务**: 使用下载的 SDK 资产编译 Android 版本的 Skia
- **交叉编译**: 在 Linux x86_64 主机上编译 ARM Android 代码
- **测试**: 使用 adb 在设备或模拟器上运行测试

### Android 开发工具

- **Android Studio**: GUI 方式管理 SDK
- **sdkmanager**: 命令行 SDK 管理工具
- **avdmanager**: Android Virtual Device 管理

### 环境配置

使用下载的资产时需要设置：
```bash
export ANDROID_SDK_ROOT=/path/to/extracted/android-sdk
export PATH=$ANDROID_SDK_ROOT/platform-tools:$PATH
```

GN 构建配置：
```gn
# args.gn
android_sdk_root = "/path/to/android-sdk"
android_ndk_root = "/path/to/android-ndk"
```

该脚本确保 Skia CI 系统有完整一致的 Android SDK 环境，支持为数十亿 Android 设备构建高性能图形库。
