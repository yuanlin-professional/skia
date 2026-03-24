# tools/sk_app/android/ - Android 平台应用实现

## 概述

`tools/sk_app/android/` 目录实现了 Skia 应用框架在 Android 平台上的适配层。与其他平台不同，Android 的实现需要通过 JNI（Java Native Interface）粘合层来桥接 Java/Kotlin 应用层和 C++ 原生代码。该目录包含了完整的 JNI 粘合代码（`surface_glue_android.h/cpp`），处理 Activity 生命周期、Surface 创建/销毁、触摸事件和 UI 状态变更等平台交互。

`Window_android` 类是该实现的核心，它接收来自 `SkiaAndroidApp` 粘合对象的事件通知。与桌面平台不同，Android 的 Surface 可能在运行时被创建和销毁（例如应用切到后台再恢复），因此 `initDisplay()` 和 `onDisplayDestroyed()` 方法处理了这种动态生命周期。

另一个 Android 特有的功能是 `setUIState()`，它接收 JSON 格式的 UI 状态字符串，使 Java 层可以向 Skia Viewer 传递 UI 变更（如当前选择的 Slide 名称、后端类型等）。`scaleContentToFit()` 返回 `true` 表示内容会被自动缩放以适配屏幕尺寸，这是因为 Android 设备的屏幕分辨率差异巨大。

入口文件 `main_android.cpp` 通过 `android_main` 函数（NativeActivity 入口）或 JNI 调用启动 Skia 应用。粘合层使用 Android 的 ALooper 消息队列实现原生线程和 Java UI 线程之间的通信。

## 架构图

```
+----------------------------------------------------------+
|                 Android 应用流程                            |
|                                                           |
|  Java 层 (SkiaAndroidActivity)                             |
|    |                                                      |
|    +-- Surface 创建/销毁通知                               |
|    +-- 触摸事件转发                                        |
|    +-- UI 状态变更 (JSON)                                  |
|    |                                                      |
|    v  (JNI 调用)                                           |
|                                                           |
|  SkiaAndroidApp (surface_glue_android)                     |
|    |  Java/C++ 粘合层，管理:                                |
|    |  - ANativeWindow 生命周期                              |
|    |  - ALooper 消息队列                                    |
|    |  - JNI 回调注册                                        |
|    |  - 触摸事件队列                                        |
|    |                                                      |
|    v                                                      |
|                                                           |
|  Window_android                                            |
|    |                                                      |
|    +-- init(SkiaAndroidApp*)                               |
|    |     绑定粘合层对象                                     |
|    |                                                      |
|    +-- initDisplay(ANativeWindow*)                         |
|    |     Surface 可用时创建 WindowContext                    |
|    |     attach(BackendType)                               |
|    |                                                      |
|    +-- onDisplayDestroyed()                                |
|    |     Surface 销毁时清理 WindowContext                    |
|    |     detach()                                          |
|    |                                                      |
|    +-- setUIState(const char*)                             |
|    |     接收 JSON 格式 UI 状态                             |
|    |     转发给 Layer 栈                                    |
|    |                                                      |
|    +-- paintIfNeeded()                                     |
|          由 ALooper 消息驱动                                |
|          onPaint() --> 遍历 Layer 栈                        |
|                                                           |
|  ANativeWindow (Android NDK)                               |
|    Surface 创建 --> initDisplay()                          |
|    Surface 销毁 --> onDisplayDestroyed()                   |
+----------------------------------------------------------+
```

## 目录结构

```
tools/sk_app/android/
|-- main_android.cpp          # Android 入口点（android_main 或 JNI 入口）
|-- Window_android.h          # Android 窗口类声明
|-- Window_android.cpp        # Android 窗口类实现
|-- surface_glue_android.h    # JNI 粘合层头文件（SkiaAndroidApp 类）
+-- surface_glue_android.cpp  # JNI 粘合层实现（JNI 函数、ALooper 集成）
```

## 关键类与函数

### Window_android 类

```cpp
// tools/sk_app/android/Window_android.h
namespace sk_app {
class Window_android : public Window {
public:
    bool init(SkiaAndroidApp* skiaAndroidApp);  // 绑定 JNI 粘合层
    void initDisplay(ANativeWindow* window);     // Surface 可用时初始化
    void onDisplayDestroyed();                   // Surface 销毁时清理

    void setTitle(const char*) override;         // 通过 JNI 回调设置标题
    void show() override {}                      // Android 无需显式 show
    bool attach(BackendType) override;           // 附着 GL/Vulkan/Dawn 后端
    void onInval() override;                     // 通过 ALooper 消息请求重绘
    void setUIState(const char* state) override; // 接收 JSON UI 状态

    void paintIfNeeded();                        // 由消息循环驱动的绘制

    bool scaleContentToFit() const override { return true; }

private:
    SkiaAndroidApp* fSkiaAndroidApp;  // JNI 粘合对象
    BackendType     fBackendType;     // 当前后端
};
}
```

### SkiaAndroidApp (JNI 粘合层)

```cpp
// tools/sk_app/android/surface_glue_android.h
// 核心职责：
// 1. 管理 ANativeWindow 指针（来自 Java Surface）
// 2. 通过 ALooper 实现线程间消息传递
// 3. 将 Java 触摸事件转发给 Window_android
// 4. 将 Java UI 状态变更通知转发给应用
// 5. 反向通知 Java 层（如标题变更、状态更新）

// JNI 导出函数:
// Java_org_skia_viewer_ViewerActivity_onSurfaceCreated
// Java_org_skia_viewer_ViewerActivity_onSurfaceChanged
// Java_org_skia_viewer_ViewerActivity_onSurfaceDestroyed
// Java_org_skia_viewer_ViewerActivity_onTouched
// Java_org_skia_viewer_ViewerActivity_onUIStateChanged
```

## 依赖关系

```
Window_android
    |
    +---> Android NDK
    |       +---> ANativeWindow (native_window.h)
    |       +---> ALooper (looper.h) - 线程间消息队列
    |       +---> JNI (jni.h) - Java 交互
    |
    +---> sk_app::Window (基类)
    |
    +---> SkiaAndroidApp (JNI 粘合层)
    |       +---> Java SkiaAndroidActivity
    |       +---> 触摸事件队列
    |       +---> UI 状态 JSON
    |
    +---> tools/window/android/
    |       +---> MakeGLForAndroid(ANativeWindow*, DisplayParams*)
    |       +---> MakeVulkanForAndroid(ANativeWindow*, DisplayParams*)
    |       +---> MakeGraphiteDawnForAndroid(ANativeWindow*, DisplayParams*)
    |       +---> MakeGraphiteVulkanForAndroid(ANativeWindow*, DisplayParams*)
    |       +---> MakeRasterForAndroid(ANativeWindow*, DisplayParams*)
    |
    +---> tools/skui/
            +---> skui::InputState, Key, ModifierKey
```

## 设计模式分析

### 中介者模式 (Mediator)

`SkiaAndroidApp` 作为中介者协调 Java 层（Activity/Surface）、Window_android 和 WindowContext 之间的交互。所有跨层通信都通过 `SkiaAndroidApp` 路由，避免了组件间的直接耦合。

### 状态机模式 (State Machine)

Android Surface 的动态生命周期形成了一个状态机：
```
无 Surface --> initDisplay() --> 有活跃 Surface --> onDisplayDestroyed() --> 无 Surface
                                      ^                                       |
                                      +---------------------------------------+
```
Window_android 在每次状态转换时正确管理 WindowContext 的创建和销毁。

### 生产者-消费者模式

JNI 粘合层使用 ALooper 消息队列实现生产者-消费者模式。Java UI 线程作为生产者发送触摸事件和状态变更消息，原生渲染线程作为消费者处理这些消息并执行相应的 Skia 操作。

## 相关文档与参考

- **sk_app 框架**: `tools/sk_app/README.md`
- **Android 窗口上下文**: `tools/window/android/README.md`
- **Android NDK NativeActivity**: https://developer.android.com/ndk/reference/group/native-activity
- **Android JNI**: https://developer.android.com/training/articles/perf-jni
- **ALooper**: https://developer.android.com/ndk/reference/group/looper
