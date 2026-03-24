# surface_glue_android - Android 平台窗口粘合层

> 源文件:
> - [tools/sk_app/android/surface_glue_android.h](../../../../tools/sk_app/android/surface_glue_android.h)
> - [tools/sk_app/android/surface_glue_android.cpp](../../../../tools/sk_app/android/surface_glue_android.cpp)

## 概述

surface_glue_android 是 Skia sk_app 框架在 Android 平台的粘合层，负责 Java 层与 C++ 原生层之间的通信。它通过管道（pipe）实现跨线程消息传递，处理 Surface 生命周期事件、触摸输入、键盘事件和 UI 状态变更。

## 架构位置

位于 `tools/sk_app/android/` 目录下，是 Android sk_app 实现的核心基础设施。连接 Java Activity/Surface 回调与 C++ 的 Window/Application 框架。

## 主要类与结构体

### `MessageType` 枚举
定义消息类型：SurfaceCreated/Changed/Destroyed、DestroyApp、ContentInvalidated、KeyPressed、Touched、UIStateChanged。

### `Message`
消息结构体，携带事件类型、ANativeWindow 指针、键码、触摸坐标和 UI 状态信息。

### `SkiaAndroidApp`
Android 应用管理类，负责 JNI 交互和消息循环。
- `fApp` / `fWindow` - sk_app 应用和窗口实例
- `fPipes[2]` - 管道用于线程间消息传递
- `fJavaVM` / `fPThreadEnv` - JNI 环境

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `SkiaAndroidApp(JNIEnv*, jobject, jobjectArray)` | 构造并启动 C++ 工作线程 |
| `postMessage(Message)` | 从 Java 线程发送消息到 C++ 线程 |
| `readMessage(Message*)` | 从管道读取消息 |
| `setTitle(title)` | 通过 JNI 设置 Activity 标题 |
| `setUIState(state)` | 通过 JNI 更新 UI 状态 |

## 内部实现细节

- **管道通信**：使用 POSIX pipe 在 Java UI 线程和 C++ pthread 之间传递 Message 结构。
- **JNI 线程绑定**：C++ 工作线程通过 `AttachCurrentThread` 绑定 JNI 环境。
- **消息回调**：通过 ALooper 的 `message_callback` 在事件循环中接收消息。

## 依赖关系

- **Android NDK**：ANativeWindow、JNI、ALooper
- **POSIX**：pthread、pipe
- **sk_app**：Application、Window 基类

## 设计模式与设计决策

- **消息队列模式**：使用管道实现无锁的单生产者-单消费者消息传递。
- **线程隔离**：JNI 操作必须在特定线程执行。

## 性能考量

- 管道通信是轻量级的 IPC 机制，适合低频事件传递。
- 消息结构体是固定大小的 POD 类型，避免序列化开销。

## 相关文件

- `tools/sk_app/Window.h` - 窗口抽象基类
- `tools/sk_app/Application.h` - 应用框架
