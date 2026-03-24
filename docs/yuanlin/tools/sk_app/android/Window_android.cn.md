# Window_android

> 源文件: `tools/sk_app/android/Window_android.h`, `tools/sk_app/android/Window_android.cpp`

## 概述

`Window_android` 是 Skia 应用框架中 `Window` 基类的 Android 平台实现，封装了 Android 原生窗口（ANativeWindow）的生命周期管理和事件分发逻辑。与其他平台实现不同，Android 使用异步的表面生命周期模型，窗口上下文的创建延迟到 Android 系统通知表面可用时才进行。该类通过 `SkiaAndroidApp` 粘合层与 Android 应用框架通信。

主要特点：
- 延迟的窗口上下文创建（等待表面准备）
- 通过消息队列的异步失效通知
- 自动缩放内容以适应显示
- 支持 OpenGL ES、Vulkan、Raster 和 Graphite 后端
- UI 状态同步（JSON 格式）

## 架构位置

`Window_android` 位于 Android 平台特定的实现层：

```
skia/
├── tools/
│   └── sk_app/
│       ├── Window.h/cpp                          # 跨平台基类
│       └── android/
│           ├── Window_android.h/cpp              # Android 实现
│           ├── surface_glue_android.h/cpp        # Android 粘合层
│           └── main_android.cpp                  # Android 入口
├── tools/window/
│   └── android/
│       └── WindowContextFactory_android.h/cpp    # Android 后端工厂
```

## 主要类与结构体

### 类 `Window_android`

继承自 `Window` 基类，实现 Android 平台特定功能。

#### 公共成员

```cpp
public:
    Window_android();
    ~Window_android() override;
    bool init(SkiaAndroidApp* skiaAndroidApp);      // 初始化
    void initDisplay(ANativeWindow* window);        // 初始化显示表面
    void onDisplayDestroyed();                      // 表面销毁
    void setTitle(const char*) override;            // 设置标题
    void show() override {}                         // Android 无需显式显示
    bool attach(BackendType) override;              // 附加后端
    void onInval() override;                        // 失效通知
    void setUIState(const char* state) override;    // 设置 UI 状态
    void paintIfNeeded();                           // 按需绘制
    bool scaleContentToFit() const override { return true; }  // 缩放以适应
```

#### 私有成员

```cpp
private:
    SkiaAndroidApp* fSkiaAndroidApp = nullptr;  // Android 应用对象
    BackendType fBackendType;                   // 后端类型
```

### 关联类型

**`SkiaAndroidApp`**: Android 应用粘合层（定义在 `surface_glue_android.h`）
- 管理 Android 生命周期事件
- 消息队列通信
- UI 状态同步

**`ANativeWindow`**: Android 原生窗口句柄（系统类型）

## 公共 API 函数

### 工厂函数

**`Window* Windows::CreateNativeWindow(void* platformData)`**

创建 Android 平台窗口实例。

**参数**: `platformData` - `SkiaAndroidApp*` 指针

**返回值**: 成功返回 `Window_android*`，失败返回 `nullptr`

### 初始化

**`bool init(SkiaAndroidApp* skiaAndroidApp)`**

初始化窗口并关联 Android 应用对象。

**实现**:
```cpp
fSkiaAndroidApp = skiaAndroidApp;
fSkiaAndroidApp->fWindow = this;  // 双向关联
```

**`void initDisplay(ANativeWindow* window)`**

Android 表面可用时创建窗口上下文。

**关键设计**: 延迟创建策略
```cpp
// attach() 时不创建上下文，只记录后端类型
bool attach(BackendType attachType) {
    fBackendType = attachType;
    return true;  // 延迟到 initDisplay
}

// initDisplay() 时真正创建上下文
void initDisplay(ANativeWindow* window) {
    switch (fBackendType) {
        case BackendType::kNativeGL:
            fWindowContext = MakeGLForAndroid(window, ...);
            break;
        // ... 其他后端
    }
    this->onBackendCreated();
}
```

这避免了在表面不可用时尝试创建图形上下文的错误。

**支持的后端**:
- `kNativeGL`: OpenGL ES
- `kVulkan`: Vulkan (Ganesh)
- `kGraphiteVulkan`: Vulkan (Graphite)
- `kGraphiteDawnOpenGLES`: Graphite + Dawn + OpenGL ES
- `kGraphiteDawnVulkan`: Graphite + Dawn + Vulkan
- `kRaster`: CPU 光栅化

**`void onDisplayDestroyed()`**

Android 表面销毁时清理窗口上下文。

**实现**: `detach()` - 释放 `fWindowContext`

### 窗口操作

**`void setTitle(const char* title)`**

设置窗口标题（委托给 `SkiaAndroidApp`）。

**`void show()`**

空实现。Android 窗口由系统自动管理可见性。

**`bool scaleContentToFit() const`**

返回 `true`，指示内容应缩放以适应屏幕。

**Android 特性**: 支持各种屏幕尺寸和纵横比。

### 失效与绘制

**`void onInval()`**

触发重绘请求（通过消息队列）。

**实现**:
```cpp
fSkiaAndroidApp->postMessage(Message(kContentInvalidated));
```

异步消息避免阻塞 Android 系统线程。

**`void paintIfNeeded()`**

按需绘制（检查上下文是否就绪）。

**实现**:
```cpp
if (fWindowContext) {
    onPaint();  // 执行实际绘制
} else {
    markInvalProcessed();  // 清除失效标志
}
```

这处理了表面尚未创建的情况，避免崩溃。

### UI 状态

**`void setUIState(const char* state)`**

设置 JSON 格式的 UI 状态（委托给 `SkiaAndroidApp`）。

**用途**: 与 Android UI 组件同步状态（如滑块位置、复选框状态）。

## 内部实现细节

### 延迟初始化流程

1. **`attach(BackendType)`**: 记录后端类型，不创建上下文
2. **Android 发送 `kSurfaceCreated` 事件**: 表面可用
3. **`initDisplay(ANativeWindow*)`**: 创建窗口上下文
4. **绘制**: `paintIfNeeded()` 开始工作

这种模式适应 Android 的异步生命周期模型。

### 消息驱动架构

```
Window_android::onInval()
    ↓
fSkiaAndroidApp->postMessage(kContentInvalidated)
    ↓
消息队列
    ↓
主循环处理消息
    ↓
Window_android::paintIfNeeded()
```

这避免了跨线程的直接调用，确保线程安全。

### 条件编译

```cpp
#if defined(SK_GL)
    case BackendType::kNativeGL:
        fWindowContext = MakeGLForAndroid(...);
        break;
#endif
```

与其他平台实现一致，只包含启用的后端代码。

## 依赖关系

### 直接依赖

**Skia 核心**:
- `tools/sk_app/Window.h`: 基类定义
- `tools/window/DisplayParams.h`: 显示参数
- `tools/window/WindowContext.h`: 窗口上下文抽象

**Android 特定**:
- `tools/sk_app/android/surface_glue_android.h`: Android 粘合层
- `tools/window/android/WindowContextFactory_android.h`: Android 后端工厂
- `<android/native_window.h>`: Android 原生窗口 API

### 被依赖情况

- `tools/sk_app/android/surface_glue_android.cpp`: Android 应用框架
- Android 平台的 Skia 应用（Viewer、示例程序等）

## 设计模式与设计决策

### 延迟初始化模式

**问题**: Android 表面创建是异步的，无法在窗口对象构造时立即创建图形上下文。

**解决方案**: 分离 `attach()`（记录意图）和 `initDisplay()`（执行创建）。

### 委托模式

所有 Android 特定操作委托给 `SkiaAndroidApp`：
- `setTitle()` → `fSkiaAndroidApp->setTitle()`
- `setUIState()` → `fSkiaAndroidApp->setUIState()`
- `onInval()` → `fSkiaAndroidApp->postMessage()`

这保持 `Window_android` 简洁，将复杂的 Android 逻辑隔离到粘合层。

### 自动缩放策略

```cpp
bool scaleContentToFit() const override { return true; }
```

Android 设备屏幕尺寸多样，自动缩放确保内容在所有设备上正确显示。

### 防御性绘制

```cpp
void paintIfNeeded() {
    if (fWindowContext) {
        onPaint();
    } else {
        markInvalProcessed();
    }
}
```

检查上下文存在性，避免在表面销毁后绘制。

## 性能考量

### 消息队列开销

异步失效通知增加延迟（约 1-2ms），但确保线程安全。对于 60 FPS 应用，这可以接受。

### 延迟初始化的启动时间

表面创建和上下文初始化可能需要 50-200ms（取决于后端）。这是一次性开销，不影响运行时性能。

### 内存管理

`paintIfNeeded()` 避免了在无效状态下的不必要工作，减少 CPU 和 GPU 负载。

## 相关文件

### 平台实现
- `tools/sk_app/win/Window_win.h/cpp`: Windows 实现
- `tools/sk_app/mac/Window_mac.h/mm`: macOS 实现
- `tools/sk_app/unix/Window_unix.h/cpp`: Linux 实现
- `tools/sk_app/ios/Window_ios.h/mm`: iOS 实现

### Android 粘合层
- `tools/sk_app/android/surface_glue_android.h/cpp`: Android 应用框架
- `tools/sk_app/android/main_android.cpp`: Android 入口点

### Android 后端工厂
- `tools/window/android/WindowContextFactory_android.h/cpp`: 后端创建函数
- `tools/window/android/GLWindowContext_android.cpp`: OpenGL ES 后端
- `tools/window/android/VulkanWindowContext_android.cpp`: Vulkan 后端
- `tools/window/android/RasterWindowContext_android.cpp`: Raster 后端

### 使用示例

Android 应用典型流程：
```cpp
// 1. 创建窗口
SkiaAndroidApp* app = new SkiaAndroidApp();
Window* window = Windows::CreateNativeWindow(app);

// 2. 附加后端（延迟创建）
window->attach(Window::BackendType::kNativeGL);

// 3. Android 表面创建事件
void onSurfaceCreated(ANativeWindow* nativeWindow) {
    static_cast<Window_android*>(window)->initDisplay(nativeWindow);
}

// 4. 绘制
window->inval();  // 触发重绘
app->handleMessages();  // 处理消息，调用 paintIfNeeded()

// 5. 表面销毁事件
void onSurfaceDestroyed() {
    static_cast<Window_android*>(window)->onDisplayDestroyed();
}
```
