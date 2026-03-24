# create.py - macOS 平台 Android NDK 资源创建脚本

> 源文件: [infra/bots/assets/android_ndk_darwin/create.py](https://github.com/aspect-build/aspect-cli/blob/main/infra/bots/assets/android_ndk_darwin/create.py)

## 概述

`create.py` 用于创建 macOS 平台上 Android NDK（Native Development Kit）的 CIPD 资源包。Android NDK 提供了在 Android 平台上编译 C/C++ 原生代码所需的工具链、头文件和库。Skia 通过 NDK 交叉编译生成 Android 平台的原生库。该脚本从 Google 官方下载 NDK r27d 的 macOS DMG 安装映像，挂载并提取 NDK 内容。此脚本仅能在 macOS 上运行。

## 架构位置

该脚本属于 Skia 跨平台编译基础设施的一部分。

```
infra/bots/assets/
├── android_ndk_darwin/
│   └── create.py              # 本文件 - macOS 上的 Android NDK
├── android_ndk_linux/         # Linux 上的 Android NDK（如存在）
└── ...

Android 构建链:
macOS 宿主机 -> Android NDK (r27d) -> Clang 交叉编译器 -> Skia Android 版本
```

## 主要类与结构体

本脚本无类定义。关键常量：

| 常量 | 值 | 说明 |
|------|-----|------|
| `NDK_VER` | `"android-ndk-r27d"` | NDK 版本标识 |
| `NDK_URL` | `https://dl.google.com/.../android-ndk-r27d-darwin.dmg` | DMG 下载地址 |
| `DMG` | `"ndk.dmg"` | 下载后的本地文件名 |
| `MOUNTED_NAME_START` | `'/Volumes/Android NDK'` | DMG 挂载卷名前缀 |

## 公共 API 函数

### `create_asset(target_dir)`

下载并提取 Android NDK。

**参数**：
- `target_dir` (str): 资源输出目录路径

**行为**：
1. 检查运行平台是否为 macOS，非 macOS 则退出
2. 使用 `curl` 下载 NDK DMG 文件
3. 使用 `hdiutil attach` 挂载 DMG
4. 解析挂载输出定位挂载点
5. 使用 `shutil.copytree` 复制 NDK 内容到目标目录
6. 使用 `hdiutil detach` 卸载 DMG
7. 清理下载的 DMG 文件

### `find_ndk(volume)`

在挂载的 DMG 卷中查找 NDK 目录。

**参数**：
- `volume` (str): 挂载卷的路径

**返回**：
- NDK 内容路径（`.app/Contents/NDK` 格式内）

### `main()`

命令行入口，解析 `--target_dir` / `-t` 参数并调用 `create_asset`。

## 内部实现细节

### DMG 挂载与解析

macOS 的 DMG（Disk Image）是一种磁盘映像格式。挂载过程：

```python
# 挂载 DMG
output = subprocess.check_output(['hdiutil', 'attach', DMG])

# 解析 hdiutil 输出以找到挂载点
lines = output.decode('utf-8').split('\n')
for line in lines:
    words = line.split('\t')
    if len(words) == 3:
        if words[2].startswith(MOUNTED_NAME_START):
            # words[0] = 设备节点 (如 /dev/disk2s1)
            # words[2] = 挂载点 (如 /Volumes/Android NDK r27d)
```

`hdiutil attach` 的输出是制表符分隔的，每行包含设备节点、类型和挂载点。

### NDK 在 DMG 中的结构

Android NDK 的 macOS DMG 包含一个 `.app` 包（macOS 应用程序包格式），NDK 的实际内容位于 `.app/Contents/NDK/` 目录中：

```python
def find_ndk(volume):
    for f in os.listdir(volume):
        if f.endswith('.app'):
            return os.path.join(volume, f, 'Contents/NDK')
```

### 目标目录处理

`shutil.copytree` 在 Python 2 和 Python 3 默认行为下要求目标目录不存在，因此脚本先删除目标目录（如果存在）：

```python
if os.path.isdir(target_dir):
    os.rmdir(target_dir)
shutil.copytree(find_ndk(words[2]), target_dir)
```

### 清理流程

挂载的 DMG 通过 `hdiutil detach` 卸载，设备节点从挂载输出中提取。下载的 DMG 文件随后被删除。

## 依赖关系

### 外部工具

- `curl`：下载 DMG 文件
- `hdiutil`：macOS 磁盘映像工具，用于挂载/卸载 DMG
- `rm`：清理临时文件

### 网络依赖

- Google 官方 NDK 下载服务器：`https://dl.google.com/android/repository/`

### 平台依赖

- **仅限 macOS**：脚本在非 macOS 系统上会退出（`platform.system() != 'Darwin'`）

### 标准库

- `argparse`、`os`、`platform`、`shutil`、`subprocess`、`sys`

## 设计模式与设计决策

### 平台限制设计

脚本通过 `platform.system()` 检查强制要求在 macOS 上运行。这是因为 DMG 格式和 `hdiutil` 工具是 macOS 特有的。Linux 版本的 NDK 可能使用不同的分发格式（如 .zip）。

### DMG 解析方式

通过解析 `hdiutil attach` 的文本输出来确定挂载点，这种方式虽然有效但比较脆弱——如果 `hdiutil` 输出格式变化，解析可能失败。更健壮的方式是使用 `hdiutil attach -plist` 获取 plist 格式输出。

### 错误处理

如果无法找到挂载点，脚本会打印 `hdiutil attach` 的完整输出用于调试，然后以退出码 2 退出。这种详细的错误报告有助于 CI 环境中的故障排查。

### NDK 版本管理

NDK 版本（r27d）硬编码在脚本中，版本升级需要同时更新 `NDK_VER` 和可能变化的 DMG 内部结构。

## 性能考量

- **下载大小**：Android NDK DMG 文件体积较大（约 1-2 GB），下载时间可能较长
- **DMG 挂载**：`hdiutil attach` 操作涉及磁盘 I/O，但通常在几秒内完成
- **文件复制**：NDK 包含数千个文件，`shutil.copytree` 的 I/O 操作可能需要较长时间
- **整体耗时**：脚本执行时间主要取决于网络下载速度和磁盘 I/O 性能
- 该脚本仅在创建 CIPD 包时运行一次，CI 任务通过 CIPD 下载预打包的 NDK

## 相关文件

- `infra/bots/assets/android_ndk_darwin/VERSION` - CIPD 资源版本号
- `infra/bots/assets/android_ndk_linux/create.py` - Linux 版本 NDK 创建脚本（如存在）
- GN 构建配置中的 Android 交叉编译定义
- `toolchain/` - 交叉编译工具链配置
