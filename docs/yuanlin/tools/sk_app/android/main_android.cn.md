# main_android.cpp

> 源文件: tools/sk_app/android/main_android.cpp

## 概述

`main_android.cpp` 是 Skia 应用程序框架在 Android 平台上的入口点实现。该文件实现了 Android Native Activity 的主函数 `android_main`，负责初始化 Skia 应用程序并运行主事件循环。它使用 Android NDK 提供的 `android_native_app_glue` 库来简化原生应用程序的开发，处理应用程序生命周期和事件循环管理。

该文件的设计非常简洁，主要职责包括：
- 配置应用程序的默认启动参数（如 SKP 文件路径）
- 创建 Skia Application 实例
- 实现事件循环，使用 ALooper 等待和处理系统事件
- 在每次事件处理后调用应用程序的空闲回调

这是一个典型的 Android Native Activity 实现，展示了如何将 Skia 的跨平台应用程序框架集成到 Android 系统中。

## 架构位置

在 Skia 应用程序框架的平台抽象层中的位置：

```
tools/sk_app/
  ├── Application.h              # 跨平台应用程序接口
  ├── android/
  │   └── main_android.cpp      # Android 平台入口（本文件）
  ├── mac/main_mac.mm           # macOS 平台入口
  ├── unix/main_unix.cpp        # Unix 平台入口
  └── win/main_win.cpp          # Windows 平台入口
```

Android 事件流程：
```
Android 系统 → android_app → ALooper → android_main 事件循环 →
Application::onIdle() → Skia 应用逻辑
```

## 主要类与结构体

### android_app

```cpp
struct android_app* state
```

**来源**：android_native_app_glue.h

**说明**：android_app 结构体由 Android Native App Glue 库提供，封装了原生应用程序的状态和配置信息。

**主要成员**（推断）：
- `destroyRequested`：标志应用程序是否应该退出
- `looper`：ALooper 事件循环对象
- `window`：ANativeWindow 原生窗口对象
- 生命周期回调函数指针

### android_poll_source

```cpp
struct android_poll_source* source
```

**用途**：表示轮询事件的来源，可以是输入事件、应用命令或其他系统事件。

**处理方法**：
```cpp
source->process(state, source);
```

## 公共 API 函数

### android_main

```cpp
void android_main(struct android_app* state)
```

**功能**：Android 原生应用程序的主入口点，由 android_native_app_glue 在独立线程中调用。

**参数**：
- `state`：android_app 结构体指针，包含应用程序状态和配置

**返回值**：无（void），当函数返回时应用程序终止

**执行流程**：

1. **防止库被剥离**：
   ```cpp
   app_dummy();
   ```
   确保 android_native_app_glue 库不会被链接器优化掉

2. **配置命令行参数**：
   ```cpp
   static const char* gCmdLine[] = {
       "viewer",
       "--skps",
       "/data/local/tmp/skps",
   };
   ```
   设置应用程序的默认参数，模拟命令行输入

3. **创建 Application 对象**：
   ```cpp
   std::unique_ptr<Application> vkApp(Application::Create(
       std::size(gCmdLine),
       const_cast<char**>(gCmdLine),
       state));
   ```

4. **主事件循环**：
   ```cpp
   while (!state->destroyRequested) {
       struct android_poll_source* source = nullptr;
       auto result = ALooper_pollOnce(-1, nullptr, nullptr, (void**)&source);

       if (result == ALOOPER_POLL_ERROR) {
           SkDEBUGFAIL("ALooper_pollOnce returned an error");
       }
       if (source != nullptr) {
           source->process(state, source);
       }
       vkApp->onIdle();
   }
   ```

5. **自动清理**：
   vkApp 的 unique_ptr 在作用域结束时自动释放

## 内部实现细节

### 命令行参数配置

```cpp
static const char* gCmdLine[] = {
    "viewer",
    "--skps",
    "/data/local/tmp/skps",
    // TODO: figure out how to use am start with extra params to pass in additional arguments at
    // runtime
    // "--atrace",
};
```

**设计说明**：
- 硬编码默认参数，用于 Viewer 应用程序
- `--skps` 参数指定 SKP 文件（Skia Picture 文件）的目录
- 路径 `/data/local/tmp/skps` 是 Android 设备上常用的临时文件位置
- 注释表明未来计划支持通过 `am start` 命令传递额外参数

**局限性**：
- 无法在运行时动态配置参数
- 需要通过 Intent extras 或其他机制支持动态参数（待实现）

### ALooper 事件循环

```cpp
auto result = ALooper_pollOnce(-1, nullptr, nullptr, (void**)&source);
```

**参数说明**：
- `-1`：无限超时，阻塞等待事件
- `nullptr`（第2个）：不需要返回文件描述符
- `nullptr`（第3个）：不需要返回事件标识符
- `(void**)&source`：返回事件源指针

**行为**：
- 阻塞等待直到有事件到达
- 返回事件标识符（通常是 LOOPER_ID_MAIN 或 LOOPER_ID_INPUT）
- 将事件源存储在 source 指针中

### 事件处理

```cpp
if (source != nullptr) {
    source->process(state, source);
}
```

**事件类型**：
- **输入事件**：触摸、按键等
- **应用命令**：生命周期事件（pause、resume、destroy 等）
- **窗口事件**：窗口创建、销毁、调整大小等

### 空闲处理

```cpp
vkApp->onIdle();
```

在每次事件处理后调用，允许应用程序：
- 更新动画状态
- 执行渲染
- 处理后台任务

### 错误处理

```cpp
if (result == ALOOPER_POLL_ERROR) {
    SkDEBUGFAIL("ALooper_pollOnce returned an error");
}
```

使用 Skia 的调试断言宏，在调试构建中触发断言失败。

## 依赖关系

**Android NDK 依赖**：
- `jni.h`：JNI（Java Native Interface）头文件
- `errno.h`：错误码定义
- `android_native_app_glue.h`：Native Activity 辅助库
  - `android_app` 结构体
  - `android_poll_source` 结构体
  - `app_dummy()` 函数
  - ALooper API

**Skia 内部依赖**：
- `tools/sk_app/Application.h`：应用程序抽象接口
- `tools/timer/Timer.h`：计时器工具

**依赖图**：
```
main_android.cpp
  ├── android_native_app_glue（Android NDK）
  │   └── ALooper（Android 系统库）
  ├── Application（Skia 应用框架）
  └── Timer（Skia 工具）
```

## 设计模式与设计决策

### 事件驱动架构

使用 Android 的 ALooper 机制实现事件驱动：
- **阻塞等待**：使用 `-1` 超时避免忙等待
- **事件分发**：通过 android_poll_source 处理不同类型的事件
- **空闲回调**：在事件间隙执行应用程序逻辑

### Native Activity Glue 抽象

使用 android_native_app_glue 库简化开发：
- **优点**：
  - 隐藏 JNI 复杂性
  - 提供线程化的事件循环
  - 处理生命周期管理
- **缺点**：
  - 增加一层抽象
  - 可能限制某些高级功能

### 智能指针管理

```cpp
std::unique_ptr<Application> vkApp(...)
```

使用 unique_ptr 自动管理 Application 对象生命周期，确保资源正确释放。

### 静态配置 vs 动态配置

**当前设计**：静态硬编码命令行参数
**未来计划**：通过 Intent extras 支持动态参数

**实现方案**（推测）：
```cpp
// 从 Intent extras 读取参数
std::vector<std::string> args = parseIntentExtras(state);
if (args.empty()) {
    args = {"viewer", "--skps", "/data/local/tmp/skps"};
}
```

## 性能考量

### 阻塞式事件循环

```cpp
ALooper_pollOnce(-1, ...)  // 无限超时
```

**优点**：
- 零 CPU 占用，系统完全空闲时不消耗资源
- 事件到达时立即唤醒，响应快速

**缺点**：
- 依赖 onIdle() 中的逻辑判断是否需要渲染
- 不适合需要固定帧率的场景（需要在 onIdle() 中实现定时器）

### 单线程模型

android_main 运行在独立线程（非 UI 线程）：
- **优点**：不阻塞主线程
- **注意**：与 Java 层交互需要正确的线程同步

### 内存管理

使用 unique_ptr 自动管理内存，避免泄漏：
```cpp
std::unique_ptr<Application> vkApp(...)
// 函数退出时自动清理
```

### 事件处理效率

每次循环迭代只处理一个事件，然后调用 onIdle()：
- **优点**：保证渲染有机会执行
- **缺点**：高频事件可能导致频繁的 onIdle() 调用

**优化建议**：
- 在 onIdle() 中使用时间戳判断是否需要渲染
- 批量处理输入事件

## 相关文件

**平台对应文件**：
- `tools/sk_app/mac/main_mac.mm`：macOS 平台实现
- `tools/sk_app/unix/main_unix.cpp`：Unix/Linux 平台实现
- `tools/sk_app/win/main_win.cpp`：Windows 平台实现

**Android 相关**：
- `tools/sk_app/android/Window_android.h` / `.cpp`：Android 窗口实现
- `tools/sk_app/android/surface_glue_android.h`：Surface 管理

**应用程序框架**：
- `tools/sk_app/Application.h`：跨平台应用程序接口
- `tools/viewer/Viewer.cpp`：Viewer 应用程序实现

**构建配置**：
- `tools/sk_app/android/BUILD.gn`：GN 构建文件
- Android.mk 或 CMakeLists.txt：Android NDK 构建配置

该文件展示了如何在 Android 平台上集成 Skia 的跨平台应用程序框架，是开发 Android 原生图形应用程序的起点。
