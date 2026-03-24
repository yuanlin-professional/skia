# android_skp_capture.py - Android SKP 画面捕获工具

> 源文件: `platform_tools/android/skp_gen/android_skp_capture.py`

## 概述

本文件是一个 Python 脚本，使用 Android MonkeyRunner 自动化框架在 Android 设备上批量捕获应用程序的 SKP（Skia Picture）文件。SKP 是 Skia 的序列化绘图记录格式，能够精确记录一帧的所有绘图操作。该工具自动启动预配置的 Android 应用，执行指定的用户交互动作（如拖动、按键），然后通过 HWUI 的调试属性触发 SKP 捕获，最后将生成的 SKP 文件拉取到本地。

## 架构位置

该文件位于 `platform_tools/android/skp_gen/` 目录下，属于 Skia 的 Android 平台测试和性能分析工具链。它与 Android 的 HWUI（Hardware UI）渲染管线配合工作，通过设置 `debug.hwui.capture_frame_as_skp` 系统属性来触发帧捕获。捕获的 SKP 文件可用于性能分析、回归测试和渲染调试。

## 主要类与结构体

### DragAction
- **功能**: 描述触摸拖动操作
- **属性**: `start`（起点坐标）、`end`（终点坐标）、`duration`（持续时间）、`points`（采样点数）
- **方法**: `run(device)` 在设备上执行拖动

### PressAction
- **功能**: 描述按钮按下操作
- **属性**: `button`（按钮标识）、`press_type`（按下类型）
- **方法**: `run(device)` 在设备上执行按键

### App
- **功能**: 描述待捕获的 Android 应用
- **属性**: `name`（名称）、`package`（包名）、`activity`（活动名）、`app_launch_delay`（启动等待时间）、`actions`（操作列表）
- **方法**:
  - `launch(device)`: 通过 `startActivity` 启动应用并等待指定延迟
  - `kill()`: 通过 `am force-stop` 强制停止应用

## 公共 API 函数

- **`parse_action(action_dict)`**: 将字典格式的操作描述解析为 `DragAction` 或 `PressAction` 对象
- **`check_output(cmd)`**: 执行子进程命令并返回输出（类似 `subprocess.check_output`）
- **`adb_shell(cmd)`**: 执行 ADB shell 命令并模拟退出码检查
- **`remote_file_exists(filename)`**: 检测设备上指定文件是否存在
- **`capture_skp(skp_file, package, device)`**: 核心捕获函数，触发并收集 SKP 文件
- **`load_app(filename)`**: 从 JSON 配置文件加载应用描述
- **`main()`**: 主函数，遍历所有应用配置执行批量捕获

## 内部实现细节

### 主函数工作流程

`main()` 函数执行以下步骤：
1. 等待设备连接（`MonkeyRunner.waitForConnection()`）
2. 唤醒设备（`device.wake()`）
3. 执行初始化拖动操作清除锁屏（`device.drag((600,600), (10,10), 0.2, 10)`）
4. 扫描 `apps/` 目录下所有应用配置文件
5. 对每个应用依次执行：加载配置、启动应用、执行操作、捕获 SKP、关闭应用

### SKP 捕获机制

1. 删除设备上已存在的旧 SKP 文件
2. 设置系统属性 `debug.hwui.capture_frame_as_skp` 为目标路径
3. 执行一次拖动操作强制触发绘制（`device.drag((300,300), (300,350), 1, 10)`）
4. 轮询等待 SKP 文件出现（最长 10 秒超时）
5. 通过 `adb pull` 将 SKP 文件拉取到本地
6. 清除捕获属性

### 应用配置格式

应用配置以 Python 字面量格式存储（通过 `ast.literal_eval` 解析），包含字段：
- `name`: 应用名称（用于 SKP 文件命名）
- `package`: Android 包名
- `activity`: 启动活动名
- `app_launch_delay`: 启动后等待秒数
- `actions`: 操作列表（每个操作包含 `type`、参数等字段）

### ADB 退出码模拟

由于 `adb shell` 不直接传递远端进程的退出码，脚本通过在命令后追加 `; echo $?` 并检查输出最后一行来模拟退出码行为。

## 依赖关系

- **`com.android.monkeyrunner`**: Android MonkeyRunner 自动化框架（`MonkeyRunner`、`MonkeyDevice`）
- **`adb`**: Android Debug Bridge 命令行工具
- **标准库**: `ast`（配置解析）、`os`（路径操作）、`subprocess`（进程管理）、`time`（延时和超时控制）
- **apps 目录**: `skp_gen/apps/` 下的应用配置文件

## 设计模式与设计决策

- **策略模式**: `DragAction` 和 `PressAction` 通过统一的 `run(device)` 接口实现不同的操作类型
- **配置驱动**: 应用行为完全由外部 JSON 配置文件定义，添加新应用无需修改代码
- **超时保护**: SKP 捕获使用 10 秒超时机制，防止因渲染问题导致无限等待
- **清理保证**: 使用 `try/finally` 确保即使捕获失败也会清除 HWUI 调试属性
- **顺序执行**: 应用逐个处理，每个应用捕获完成后被强制停止，避免资源冲突

## 性能考量

- `WAIT_FOR_SKP_CAPTURE` 常量（1 秒）控制操作执行和 SKP 捕获之间的等待时间
- SKP 文件存储在应用的缓存目录中（`/data/data/<package>/cache/`），利用设备本地 I/O 减少延迟
- 轮询间隔为 1 秒，在响应速度和 CPU 占用之间取得平衡
- 每个应用的启动等待时间可单独配置，适应不同应用的冷启动时间差异
- SKP 文件大小取决于帧的绘图复杂度，复杂 UI 可能生成数 MB 的 SKP 文件
- `adb pull` 的传输速度受 USB 连接类型影响（USB 2.0 vs 3.0）

### 错误处理策略

- `check_output()` 在子进程返回非零退出码时抛出异常
- `adb_shell()` 通过解析输出末尾的退出码模拟远端错误检测
- `capture_skp()` 中的 `try/finally` 确保调试属性始终被清除
- 文件删除失败时（如文件不存在），通过二次检查确认是否需要抛出异常
- 超时机制防止设备无响应时脚本无限挂起

### 已知限制

- 依赖 MonkeyRunner 框架，需要在 Android SDK 环境中运行
- `ast.literal_eval` 仅支持 Python 字面量格式的配置文件，不支持完整的 JSON
- 需要设备已 root 或应用为 debuggable 才能设置 HWUI 调试属性
- 不支持并行捕获多个应用

### SKP 文件格式

SKP（Skia Picture）文件是 Skia 的序列化绘图记录格式：
- 记录了一帧中所有的 `SkCanvas` 绘图操作（drawRect、drawPath、drawImage 等）
- 包含所有引用的资源（图像、字体等）
- 可以在任何 Skia 后端上精确回放
- 常用于性能分析（通过 Skia Viewer 或 Debugger 回放）和渲染回归测试

### HWUI 集成原理

Android 的 HWUI 渲染管线内部使用 Skia 作为 2D 渲染引擎。通过设置 `debug.hwui.capture_frame_as_skp` 系统属性，HWUI 会在下一次渲染时将整个帧的绘图操作序列化为 SKP 文件。这种机制不需要修改应用代码，对应用完全透明。

## 相关文件

- `platform_tools/android/skp_gen/apps/` - 应用配置文件目录
- `tools/skp/` - SKP 相关工具
- `tools/viewer/` - SKP 查看器
- `dm/` - DM 测试工具（使用 SKP 进行渲染测试）
- `src/core/SkPicture.cpp` - SKP 核心实现
- `include/core/SkPicture.h` - SKP 公共头文件

### 与现代 Android 渲染管线的关系

在较新的 Android 版本中，HWUI 可能使用 Vulkan 而非 OpenGL 作为底层 GPU API。但 SKP 捕获机制在两种后端下都能正常工作，因为 SKP 记录的是 Skia Canvas 层面的操作，不依赖具体的 GPU 后端。

### 脚本运行环境要求

- 需要 Android SDK 中的 MonkeyRunner 工具（通常在 `tools/bin/monkeyrunner` 下）
- 设备需要通过 USB 连接并启用 USB 调试
- 需要 root 权限或应用设置为 debuggable
- Python 2.x 环境（MonkeyRunner 使用 Jython，基于 Python 2）

### 输出文件

捕获的 SKP 文件以应用名称命名（如 `AppName.skp`），保存在脚本运行的当前工作目录下。这些文件可以使用以下工具打开和分析：
- `skia_viewer` - Skia 的交互式查看器
- `skia_debugger` - Skia 的调试器，支持逐操作回放
- `dm` - Skia 的渲染测试工具，可对 SKP 进行回归测试
