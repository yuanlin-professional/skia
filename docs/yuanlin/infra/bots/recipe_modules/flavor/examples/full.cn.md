# full.py - Flavor Recipe Module 完整测试用例

> 源文件:
> - `infra/bots/recipe_modules/flavor/examples/full.py`

## 概述

full.py 是 Skia flavor recipe module 的完整集成测试脚本，用于验证不同平台 flavor（Android、ChromeOS、iOS、桌面等）的设备管理功能。它定义了多种构建器（builder）配置，并通过模拟执行来测试文件操作、设备安装、测试执行和结果收集等流程。该脚本同时作为 flavor 模块的使用示例和回归测试。

## 架构位置

```
infra/bots/recipe_modules/flavor/
├── __init__.py (模块初始化)
├── api.py (公共 API)
├── android.py / ssh.py / chromebook.py (各平台 flavor)
└── examples/
    └── full.py (集成测试)  <── 本文件
```

## 主要类与结构体

无类定义。本文件为 Recipe 测试脚本。

## 公共 API 函数

### Recipe 入口

| 函数 | 描述 |
|------|------|
| `RunSteps(api)` | Recipe 执行入口，根据 builder 名称选择 app 并执行测试流程 |
| `test_exceptions(api)` | 测试异常处理路径（未配置时的 ValueError）|
| `GenTests(api)` | 生成测试用例 |

## 内部实现细节

### 测试流程（RunSteps）

1. **变量设置**: `api.vars.setup()` 初始化构建变量
2. **App 选择**: 根据 builder 名称确定应用类型：
   - `SkottieTracing` -> `None`
   - `Test` -> `dm`
   - `Perf` -> `nanobench`
3. **Flavor 初始化**: `api.flavor.setup(app)` 根据 builder 配置自动选择 flavor
4. **设备操作测试**:
   - `copy_file_to_device` / `read_file_on_device` / `remove_file_on_device`
   - `create_clean_host_dir` / `create_clean_device_dir`
5. **安装**: 根据 builder 类型安装不同资源（skps, images, svgs, resources, lotties, texttraces）
6. **执行**: 运行 dm 或 nanobench
7. **结果收集**: 从设备拷贝结果目录
8. **清理**: `api.flavor.cleanup_steps()`

### 测试构建器矩阵（TEST_BUILDERS）

覆盖 27 种构建器配置，涵盖：

| 平台 | 设备/环境 | 特殊配置 |
|------|-----------|----------|
| Android | AndroidOne, GalaxyS7, GalaxyS20, Nexus5x, Pixel3a, Pixel6, MokeyGo32, MotoG73 | Vulkan, ASAN, SkottieTracing |
| ChromeOS | Cherry (MaliG57) | - |
| Debian | GCE (CPU), NUC7i5BNK (Intel GPU), NUC11TZi5 (IntelIrisXe) | MSAN, TSAN, ASAN, Coverage, Lottie, SwiftShader, Vulkan |
| iOS | iPhone8 (AppleA11) | RPI |
| macOS | MacBookPro11.5 (AVX2) | ASAN |
| Windows | GCE (AVX2), NUC5i7RYH (AVX2) | ASAN, NativeFonts_DWriteCore |

### 错误注入测试

`GenTests` 生成多种故障场景测试：
- `failed_infra_step`: 日志导出失败
- `failed_read_version`: 版本文件读取失败
- `retry_adb_command`: ADB 命令首次失败后重试成功
- `retry_adb_command_retries_exhausted`: ADB 命令重试耗尽
- `retry_ios_install` / `retry_ios_install_retries_exhausted`: iOS 安装重试
- `ios_rerun_with_debug`: iOS 测试失败后调试重跑
- `cpu_scale_failed_once` / `cpu_scale_failed`: CPU 缩放失败（不同 bot 环境）
- `internal_hardware_label`: 内部硬件标签（受限设备）

## 依赖关系

- **Recipe 模块**: `flavor`、`run`、`vars`
- **Recipe 引擎**: `platform`、`properties`、`raw_io`
- **测试 API**: `api.test`、`api.properties`、`api.step_data`、`api.platform`

## 设计模式与设计决策

- **数据驱动测试**: 通过 `TEST_BUILDERS` 列表驱动测试生成，添加新构建器配置只需添加一行字符串
- **错误注入**: 使用 `api.step_data` 注入步骤失败，测试重试和恢复逻辑
- **平台感知**: 根据 builder 名称中的平台标识自动设置 `api.platform`
- **try/finally 清理**: 确保即使测试步骤失败也能执行清理

## 性能考量

- 测试用例使用 Recipe 引擎的模拟执行机制，不需要实际设备
- `defaultProps` lambda 减少了重复的属性定义
- 每个测试用例独立运行，互不影响

## 相关文件

- `infra/bots/recipe_modules/flavor/api.py` - Flavor API 定义
- `infra/bots/recipe_modules/flavor/android.py` - Android flavor 实现
- `infra/bots/recipe_modules/flavor/ssh.py` - SSH flavor 实现
- `infra/bots/recipe_modules/flavor/chromebook.py` - Chromebook flavor 实现
- `infra/bots/recipe_modules/run/` - Run recipe module
- `infra/bots/recipe_modules/vars/` - Vars recipe module
