# android.py - Android 设备管理 Recipe Flavor

> 源文件:
> - `infra/bots/recipe_modules/flavor/android.py`

## 概述

android.py 实现了 Skia CI/CD 基础设施中的 Android 设备管理 flavor，负责在 Android 设备上执行测试和性能基准测试。该模块封装了 ADB 操作、设备恢复、CPU/GPU 频率缩放、ASAN 配置等复杂逻辑，是 Skia 在 Android 设备上运行自动化测试的核心组件。它继承自 `DefaultFlavor`，针对 Android 设备的特殊需求进行了全面定制。

## 架构位置

```
Skia CI 基础设施 (Recipe 框架)
├── recipe_modules/flavor/
│   ├── default.py (DefaultFlavor 基类)
│   ├── android.py (Android 设备管理)  <── 本模块
│   ├── ssh.py (SSH 远程设备管理)
│   ├── chromebook.py (Chromebook 设备管理)
│   └── ios.py (iOS 设备管理)
```

## 主要类与结构体

### `AndroidFlavor`

- **继承**: `default.DefaultFlavor`
- **关键属性**:
  - `ADB_BINARY`: ADB 可执行文件路径（因 bot 类型不同而异）
  - `ADB_PUB_KEY`: ADB 公钥路径
  - `device_dirs`: 设备上的各类数据目录
  - `cant_root`: 不可 root 的设备列表
  - `cpus_to_scale`: 需要频率缩放的 CPU 映射
  - `disable_for_nanobench`: nanobench 测试时需禁用的 CPU 映射
  - `gpu_scaling`: GPU 频率缩放配置
  - `use_performance_governor_for_dm`: DM 测试使用 performance 调度器的设备
  - `use_powersave_governor_for_nanobench`: nanobench 使用 powersave 调度器的设备

## 公共 API 函数

| 函数 | 描述 |
|------|------|
| `install()` | 安装测试所需文件到设备，配置 CPU/GPU 缩放 |
| `cleanup_steps()` | 测试完成后清理：导出日志、重启设备、卸载 ASAN |
| `step(name, cmd)` | 在设备上执行命令（通过 shell 脚本推送并执行）|
| `copy_file_to_device(host, device)` | 推送文件到设备 |
| `copy_directory_contents_to_device(host, device)` | 推送目录内容到设备 |
| `copy_directory_contents_to_host(device, host)` | 从设备拉取目录内容 |
| `read_file_on_device(path)` | 读取设备上的文件内容 |
| `remove_file_on_device(path)` | 删除设备上的文件 |
| `create_clean_device_dir(path)` | 创建空的设备目录 |

## 内部实现细节

### ADB 二进制路径选择

根据 swarming bot ID 选择不同的 ADB 二进制路径：
- `skia` bot: `/usr/bin/adb.1.0.35`
- `lin-` 前缀 bot: `/opt/infra-android/tools/adb`（带专用公钥）
- 其他: `/usr/bin/adb`

### CPU 频率管理

**DM 测试 (`_scale_for_dm`)**:
- 重新启用 nanobench 禁用的 CPU
- 设置 CPU 调度器：
  - AndroidOne: `hotplug`
  - Pixel 系列: `performance`
  - 其他: `ondemand`

**Nanobench (`_scale_for_nanobench`)**:
- 部分设备使用 `powersave` 调度器（Pixel6/7/9/10）
- 其他设备使用 `userspace` 并缩放到 60%
- 禁用小核心 CPU（大小核架构设备）以减少性能噪声
- GPU 频率锁定（Nexus5: 450MHz, Nexus5x: 600MHz）

### 设备恢复机制

`recover_device` 在 ADB 步骤失败时执行：
1. 终止 ADB 服务器 (`adb kill-server`)
2. 等待设备 (`adb wait-for-device`)
3. 列出设备 (`adb devices -l`)
4. 重启设备并等待
5. 尝试 root（如果设备在白名单中）

### ADB 命令重试

`_adb` 方法默认重试 3 次，每次重试之间调用 `recover_device`。所有 ADB 步骤默认为 infra_step（基础设施步骤，与测试逻辑区分）。

### ASAN 支持

安装阶段调用 `asan_device_setup` 配置 ASAN，清理阶段等待设备启动完成后卸载 ASAN。使用 NDK 中的 LLVM ASAN 工具（Clang 18）。

### 设备命令执行

`step` 方法通过生成 shell 脚本、推送到设备、在设备上执行的方式运行命令：
```python
'set -x; LD_LIBRARY_PATH=%s %s%s; echo $? >%src'
```
设置 `LD_LIBRARY_PATH` 确保动态库能被找到，将退出码写入文件以供检查。

## 依赖关系

- **Recipe 框架**: `recipe_engine`（步骤执行、路径管理等）
- **基类**: `default.DefaultFlavor`（默认 flavor 实现）
- **外部脚本**: 多个 Python 资源脚本（`wait_for_device.py`、`set_cpu_scaling_governor.py`、`scale_cpu.py` 等）
- **ADB**: Android Debug Bridge 命令行工具
- **标准库**: `subprocess`（用于设备命令执行）

## 设计模式与设计决策

- **继承层次**: 继承 `DefaultFlavor` 并重写设备特定的方法
- **声明式设备配置**: 使用字典和列表声明式地配置各设备的 CPU/GPU 参数
- **外部脚本委托**: CPU 缩放、设备等待等操作委托给专门的 Python 脚本，便于独立测试和维护
- **重试与恢复**: ADB 操作默认重试 3 次，每次重试前执行设备恢复
- **不可 root 设备白名单**: 明确列出不可 root 的设备，避免 root 失败导致整个任务失败
- **GalaxyS20/S9 Vulkan workaround**: 将 Mali GPU 驱动库复制到 bin 目录并重命名为 `libvulkan.so`

## 性能考量

- CPU 频率锁定消除了因动态调频导致的性能波动，提高基准测试的一致性
- 大小核设备中禁用小核心，确保 nanobench 始终在同一（高性能）CPU 上运行
- GPU 频率锁定（Nexus 设备）进一步减少 GPU 性能变化
- 设备重启后的等待机制（600 秒超时）确保设备完全就绪后再开始测试
- ADB 连接使用 vendor keys 认证，避免认证弹窗导致的连接超时

## 相关文件

- `infra/bots/recipe_modules/flavor/default.py` - DefaultFlavor 基类
- `infra/bots/recipe_modules/flavor/resources/` - 辅助 Python 脚本目录
- `infra/bots/recipe_modules/flavor/examples/full.py` - 完整测试用例
- `infra/bots/recipes/` - 使用此 flavor 的 recipe 脚本
