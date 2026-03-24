# DefaultFlavor - 桌面平台默认执行风味

> 源文件: `infra/bots/recipe_modules/flavor/default.py`

## 概述

`default.py` 定义了 Skia CI/CD 基础设施中桌面平台（Desktop）的默认执行风味（Flavor）。它提供了在桌面机器上运行测试和性能基准程序的基础框架，包括设备目录管理、文件传输、环境变量配置以及各种 Sanitizer（ASAN/MSAN/TSAN）的支持。所有其他平台特定的 Flavor（如 Android、ChromeOS）都继承自此类。

## 架构位置

该模块位于 Skia 的 recipe 基础设施层，是 `flavor` recipe 模块的核心组件。在构建系统的层次结构中：

- **上层**: `flavor/api.py` (SkiaFlavorApi) 选择并实例化对应的 Flavor
- **本层**: `DefaultFlavor` 提供桌面平台的默认实现
- **下层**: `AndroidFlavor`、`SSHFlavor`、`ChromebookFlavor` 继承并扩展此类

## 主要类与结构体

### `DeviceDirs` (namedtuple)
设备目录的命名元组，包含以下字段：
- `bin_dir` - 可执行文件目录
- `dm_dir` - DM 测试输出目录
- `perf_data_dir` - 性能数据目录
- `resource_dir` - 资源文件目录
- `images_dir` / `fonts_dir` / `lotties_dir` / `skp_dir` / `svg_dir` - 各类测试资产目录
- `tmp_dir` / `texttraces_dir` - 临时文件和文本追踪目录

### `DefaultFlavor`
桌面平台的默认 Flavor 类，核心属性包括：
- `app_name` - 运行的应用名称（dm 或 nanobench）
- `module` - 父 recipe 模块的引用
- `device_dirs` / `host_dirs` - 设备和主机目录（桌面平台两者相同）

## 公共 API 函数

| 方法 | 说明 |
|------|------|
| `device_path_join(*args)` | 在连接设备上拼接路径 |
| `copy_directory_contents_to_device(host_dir, device_dir)` | 复制目录到设备（桌面平台要求路径相同） |
| `copy_directory_contents_to_host(device_dir, host_dir)` | 从设备复制目录到主机 |
| `copy_file_to_device(host_path, device_path)` | 复制单个文件到设备 |
| `create_clean_device_dir(path)` | 在设备上创建干净目录 |
| `create_clean_host_dir(path)` | 在主机上创建干净目录 |
| `read_file_on_device(path)` | 读取设备上的文件 |
| `remove_file_on_device(path)` | 删除设备上的文件 |
| `install()` | 执行设备特定的安装步骤 |
| `cleanup_steps()` | 执行清理步骤 |
| `step(name, cmd)` | 执行测试/基准命令 |

## 内部实现细节

### `step()` 方法的环境配置
`step()` 方法是核心执行逻辑，它根据构建器配置动态设置环境变量：

1. **Intel GPU 驱动路径**: 设置 `LIBGL_DRIVERS_PATH` 和 `VK_ICD_FILENAMES`，区分 IrisXe 使用 mesa_intel_driver_linux_22
2. **Vulkan SDK**: 配置 `VULKAN_SDK`、`VK_LAYER_PATH`，Debug 模式下启用验证层（排除 ASAN/TSAN）
3. **SwiftShader**: 将 swiftshader 库路径加入 `LD_LIBRARY_PATH`
4. **Sanitizer 配置**:
   - ASAN: 设置 `ASAN_OPTIONS`、`LSAN_OPTIONS`、`UBSAN_OPTIONS`，Mac/Win 不支持 leak 检测
   - MSAN: 配置 `MSAN_OPTIONS` 和符号化路径
   - TSAN: 设置 `TSAN_OPTIONS`，Linux 下使用 `setarch -R` 禁用地址随机化
5. **Coverage**: 设置 `LLVM_PROFILE_FILE` 输出路径
6. **符号化**: Linux 非 Sanitizer 构建使用 `symbolize_stack_trace.py`
7. **Windows**: 通过 PowerShell 脚本 `win_run_and_check_log.ps1` 执行

### `_run()` 和 `_py()` 方法
内部辅助方法，分别用于执行命令行步骤和 Python 脚本。

## 依赖关系

- `collections` - 用于 `namedtuple` 定义 `DeviceDirs`
- **recipe 模块**: `run`、`vars`、`step`、`file`、`path`、`raw_io`、`context`
- **外部资源**: `symbolize_stack_trace.py`、`win_run_and_check_log.ps1`

## 设计模式与设计决策

1. **策略模式**: `DefaultFlavor` 作为基类定义统一接口，各平台 Flavor 作为策略实现平台特定逻辑
2. **主机即设备**: 桌面平台 `device_dirs` 和 `host_dirs` 指向相同目录，复制操作在路径不一致时抛出异常
3. **环境隔离**: 使用 `self.m.context(env=env)` 确保环境变量修改不泄漏到其他步骤
4. **渐进式环境构建**: `step()` 方法根据 builder 名称中的 token 逐步构建 `PATH` 和 `LD_LIBRARY_PATH`

## 性能考量

- Sanitizer 构建中 `fast_unwind_on_malloc=0` 会导致 2-25x 的性能下降，仅在 dm + Vulkan 场景下启用
- TSAN 禁用地址随机化（`setarch -R`）可避免 TSAN 误报，但可能影响真实场景代表性
- 符号化步骤仅对 `dm` 和 `nanobench` 启用，避免不必要的性能开销

## 相关文件

- `infra/bots/recipe_modules/flavor/android.py` - Android 平台 Flavor
- `infra/bots/recipe_modules/flavor/ssh.py` - SSH 远程设备 Flavor
- `infra/bots/recipe_modules/flavor/chromebook.py` - Chromebook Flavor
- `infra/bots/recipe_modules/flavor/api.py` - Flavor API 入口
- `infra/bots/recipe_modules/flavor/resources/symbolize_stack_trace.py` - 堆栈符号化脚本
- `infra/bots/recipe_modules/flavor/resources/win_run_and_check_log.ps1` - Windows 执行脚本
