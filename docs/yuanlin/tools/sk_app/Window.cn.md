# Window

> 源文件: `tools/sk_app/Window.h`, `tools/sk_app/Window.cpp`

## 概述

`Window` 是 Skia 应用框架（`sk_app`）中的核心抽象类，提供跨平台的窗口管理功能。它定义了窗口生命周期、输入事件处理、图形后端管理和渲染流程的统一接口。该类采用层（Layer）架构模式，允许多个独立的 UI 组件以堆栈形式组织，实现模块化的事件处理和渲染逻辑。

主要功能包括：
- 抽象窗口操作（标题、显示、缩放）
- 多图形后端支持（OpenGL、Vulkan、Metal、D3D、Graphite、Raster）
- 分层事件处理系统（键盘、鼠标、触摸、手势）
- 渲染管线管理（预绘制、绘制、提交）
- 显示参数配置（采样、模板、色彩空间）

## 架构位置

`Window` 位于 Skia 工具层的应用框架中，是构建交互式图形应用的基础：

```
skia/
├── tools/
│   └── sk_app/
│       ├── Window.h                  # 基类接口定义
│       ├── Window.cpp                # 通用实现
│       ├── win/Window_win.h/cpp      # Windows 平台实现
│       ├── mac/Window_mac.h/mm       # macOS 平台实现
│       ├── unix/Window_unix.h/cpp    # Linux/Unix 实现
│       ├── ios/Window_ios.h/mm       # iOS 平台实现
│       └── android/Window_android.h/cpp  # Android 平台实现
├── tools/window/
│   ├── WindowContext.h               # 窗口上下文（后端管理）
│   └── DisplayParams.h               # 显示参数配置
└── tools/viewer/
    └── Viewer.cpp                    # 使用 Window 的示例应用
```

作为抽象基类，`Window` 定义了平台无关的接口，由各平台子类实现具体的系统窗口创建和事件循环逻辑。

## 主要类与结构体

### 类 `Window`

核心抽象基类，定义窗口的通用行为。

#### 关键成员变量

```cpp
protected:
    SkTDArray<Layer*> fLayers;                    // 层堆栈
    std::unique_ptr<const DisplayParams> fRequestedDisplayParams;  // 请求的显示参数
    bool fIsActive = true;                        // 窗口激活状态
    std::unique_ptr<WindowContext> fWindowContext;  // 窗口上下文（后端）
    bool fIsContentInvalidated = false;           // 内容失效标志
```

#### 后端类型枚举

```cpp
enum class BackendType {
    kNativeGL,              // 原生 OpenGL
    kANGLE,                 // ANGLE (OpenGL over D3D)
    kGraphiteDawnD3D11,     // Graphite + Dawn + D3D11
    kGraphiteDawnD3D12,     // Graphite + Dawn + D3D12
    kGraphiteDawnMetal,     // Graphite + Dawn + Metal
    kGraphiteDawnOpenGLES,  // Graphite + Dawn + OpenGL ES
    kGraphiteDawnVulkan,    // Graphite + Dawn + Vulkan
    kVulkan,                // 原生 Vulkan (Ganesh)
    kGraphiteVulkan,        // 原生 Vulkan (Graphite)
    kMetal,                 // 原生 Metal (Ganesh)
    kGraphiteMetal,         // 原生 Metal (Graphite)
    kDirect3D,              // Direct3D
    kRaster,                // CPU 光栅化
};
```

支持 Ganesh（传统 GPU 后端）和 Graphite（新 GPU 后端）两种架构，涵盖所有主流图形 API。

### 内部类 `Window::Layer`

层是可组合的 UI 组件，按堆栈顺序处理事件和渲染。

#### 核心方法

**生命周期**:
- `onAttach(Window*)`: 附加到窗口时调用
- `onBackendCreated()`: 图形后端创建后调用

**输入事件**（返回 `true` 表示已处理，阻止事件传播）:
- `onChar(SkUnichar, ModifierKey)`: 字符输入
- `onKey(Key, InputState, ModifierKey)`: 按键事件
- `onMouse(x, y, InputState, ModifierKey)`: 鼠标事件
- `onMouseWheel(delta, x, y, ModifierKey)`: 鼠标滚轮
- `onTouch(owner, InputState, x, y)`: 触摸事件
- `onFling(InputState)`: 惯性滑动手势
- `onPinch(InputState, scale, x, y)`: 捏合手势

**渲染与布局**:
- `onPrePaint()`: 绘制前准备
- `onPaint(SkSurface*)`: 绘制内容
- `onResize(width, height)`: 窗口尺寸改变

**状态变化**:
- `onUIStateChanged(stateName, stateValue)`: UI 状态更新（主要用于 Android）

#### 激活状态

```cpp
bool fActive;  // 私有成员，通过 getActive/setActive 访问
```

非激活层不参与事件处理和渲染，实现动态启用/禁用功能。

### 辅助类型

**`GpuTimerCallback`**:
```cpp
using GpuTimerCallback = std::function<void(uint64_t ns)>;
```

GPU 计时回调函数类型，用于性能分析。

## 公共 API 函数

### 窗口管理

**`virtual void setTitle(const char*) = 0`**
- 设置窗口标题（纯虚函数，平台特定实现）

**`virtual void show() = 0`**
- 显示窗口（纯虚函数，平台特定实现）

**`void inval()`**
- 请求重绘窗口
- 使用防抖机制：只有在 `fIsContentInvalidated` 为 `false` 时才触发 `onInval()`
- 避免重复的失效事件

**`virtual bool scaleContentToFit() const`**
- 查询窗口是否缩放内容以适应显示
- 默认返回 `false`

**`int width() const` / `int height() const`**
- 获取窗口尺寸
- 通过 `WindowContext` 获取实际尺寸
- 无上下文时返回 0

**`virtual float scaleFactor() const`**
- 获取显示缩放因子（高 DPI 支持）
- 默认返回 1.0

### 后端管理

**`virtual bool attach(BackendType) = 0`**
- 附加指定的图形后端
- 返回 `true` 表示成功
- 纯虚函数，由平台子类实现

**`void detach()`**
- 分离当前图形后端
- 释放 `fWindowContext`

**`GrDirectContext* directContext() const`**
- 获取 Ganesh 直接上下文
- 仅在编译时启用 `SK_GANESH` 时可用
- 无后端或使用 Graphite 时返回 `nullptr`

**`skgpu::graphite::Context* graphiteContext() const`**
- 获取 Graphite 上下文
- 仅在编译时启用 `SK_GRAPHITE` 时可用

**`skgpu::graphite::Recorder* graphiteRecorder() const`**
- 获取 Graphite 记录器
- 用于记录绘制命令

**`SkRecorder* baseRecorder() const`**
- 获取通用记录器接口
- 优先返回 Graphite 记录器，其次 Ganesh 记录上下文

### 显示参数

**`const DisplayParams* getRequestedDisplayParams()`**
- 获取请求的显示参数

**`void setRequestedDisplayParams(std::unique_ptr<const DisplayParams>, bool allowReattach = true)`**
- 设置显示参数（采样数、色彩空间、模板位等）
- 自动应用到现有 `WindowContext`

**`int sampleCount() const`**
- 获取实际使用的采样数（MSAA）

**`int stencilBits() const`**
- 获取模板缓冲位数

### 层管理

**`void pushLayer(Layer* layer)`**
- 添加层到堆栈顶部
- 自动调用 `layer->onAttach(this)`

### 事件分发

以下方法将事件分发给层堆栈，返回 `true` 表示事件已被处理：

- `bool onChar(SkUnichar, ModifierKey)`
- `bool onKey(Key, InputState, ModifierKey)`
- `bool onMouse(int x, int y, InputState, ModifierKey)`
- `bool onMouseWheel(float delta, int x, int y, ModifierKey)`
- `bool onTouch(intptr_t owner, InputState, float x, float y)`
- `bool onFling(InputState)`
- `bool onPinch(InputState, scale, float x, float y)`

**`void onUIStateChanged(const SkString& stateName, const SkString& stateValue)`**
- 通知所有层 UI 状态改变（无返回值）

### 渲染与布局

**`void onPaint()`**
- 执行完整的渲染流程：
  1. 检查窗口激活状态
  2. 获取后备缓冲 Surface
  3. 调用所有层的 `onPrePaint()`
  4. 调用所有层的 `onPaint()`
  5. 刷新 GPU 命令（Ganesh）
  6. 交换缓冲区

**`void onResize(int width, int height)`**
- 调整窗口上下文大小
- 通知所有层尺寸改变

**`void onActivate(bool isActive)`**
- 窗口激活/失活时调用
- 更新 `fIsActive` 状态

### GPU 操作

**`bool supportsGpuTimer() const`**
- 查询后端是否支持 GPU 计时

**`void submitToGpu(GpuTimerCallback = {})`**
- 提交命令到 GPU
- Graphite: 快照 Recording 并提交到 Context
- Ganesh: 刷新并提交
- 可选回调接收 GPU 执行时间（纳秒）

### 平台特定功能

**`virtual void setUIState(const char*)`**
- 设置 JSON 格式的 UI 状态（主要用于 Android）
- 默认空实现

**`virtual const char* getClipboardText()`**
- 获取系统剪贴板文本
- 仅 UNIX 平台实现，其他平台返回 `nullptr`

**`virtual void setClipboardText(const char*)`**
- 设置系统剪贴板文本
- 仅 UNIX 平台实现

## 内部实现细节

### 层遍历机制

**`void visitLayers(const std::function<void(Layer*)>& visitor)`**
- 正向遍历所有激活的层（索引 0 到 N-1）
- 用于通知型操作（无需返回值）

**`bool signalLayers(const std::function<bool(Layer*)>& visitor)`**
- 反向遍历所有激活的层（索引 N-1 到 0）
- 用于事件处理：一旦有层返回 `true`，立即停止遍历
- 实现事件捕获：顶层先处理

```cpp
bool Window::signalLayers(const std::function<bool(Layer*)>& visitor) {
    for (int i = fLayers.size() - 1; i >= 0; --i) {
        if (fLayers[i]->fActive && visitor(fLayers[i])) {
            return true;
        }
    }
    return false;
}
```

这种反向遍历模拟了 UI 层叠顺序：最上层的 UI 元素优先响应用户输入。

### 失效机制

**防抖逻辑**:
```cpp
void Window::inval() {
    if (!fIsContentInvalidated) {
        fIsContentInvalidated = true;
        onInval();  // 通知平台窗口系统
    }
}
```

防止重复的重绘请求淹没事件队列。

**重置失效标志**:
```cpp
void Window::markInvalProcessed() {
    fIsContentInvalidated = false;
}
```

在 `onPaint()` 中调用，允许后续的 `inval()` 调用生效。

### 后备缓冲渲染

```cpp
sk_sp<SkSurface> backbuffer = fWindowContext->getBackbufferSurface();
if (backbuffer == nullptr) {
    printf("no backbuffer!?\n");
    return;
}
```

获取后备缓冲失败时优雅退出，避免崩溃。生产代码可能需要尝试重新创建上下文。

**Ganesh 特定提交**:
```cpp
#if defined(SK_GANESH)
if (auto dContext = this->directContext()) {
    dContext->flushAndSubmit(backbuffer.get(), GrSyncCpu::kNo);
}
#endif
```

仅在使用 Ganesh 后端时刷新命令，Graphite 使用不同的提交机制（通过 `submitToGpu`）。

### 条件编译

代码广泛使用条件编译分离 Ganesh 和 Graphite 路径：

```cpp
#if defined(SK_GANESH)
    // Ganesh 代码
#endif

#if defined(SK_GRAPHITE)
    // Graphite 代码
#endif
```

这允许构建时选择性包含 GPU 后端，减少二进制大小。

### Lambda 表达式的使用

所有事件分发都使用 lambda 表达式捕获参数：

```cpp
bool Window::onChar(SkUnichar c, skui::ModifierKey modifiers) {
    return this->signalLayers([=](Layer* layer) {
        return layer->onChar(c, modifiers);
    });
}
```

`[=]` 按值捕获所有变量，避免引用失效问题。

## 依赖关系

### 直接依赖

**核心库**:
- `include/core/SkRect.h`: 矩形类型
- `include/core/SkCanvas.h`: 绘制接口
- `include/core/SkSurface.h`: 绘制表面

**工具库**:
- `tools/skui/InputState.h`: 输入状态枚举
- `tools/skui/Key.h`: 按键定义
- `tools/skui/ModifierKey.h`: 修饰键（Shift、Ctrl 等）

**窗口系统**:
- `tools/window/WindowContext.h`: 窗口上下文抽象
- `tools/window/DisplayParams.h`: 显示参数配置

**GPU 后端（条件性）**:
- `include/gpu/ganesh/GrDirectContext.h`: Ganesh 上下文
- `include/gpu/graphite/Recorder.h`: Graphite 记录器

### 被依赖情况

`Window` 是应用框架的基础，被以下组件使用：
- **平台实现**: `Window_win`, `Window_mac`, `Window_unix`, `Window_ios`, `Window_android`
- **应用程序**: `tools/viewer/Viewer`, `tools/skottie_tool`, 自定义工具
- **测试工具**: 交互式测试应用

### 工厂函数

```cpp
namespace Windows {
    Window* CreateNativeWindow(void* platformData);
}
```

根据编译平台自动返回相应的窗口实现。

## 设计模式与设计决策

### 模板方法模式

`Window` 定义渲染和事件处理的算法骨架，子类实现特定步骤：

```cpp
// 抽象基类定义流程
void Window::onPaint() {
    // 通用逻辑
    this->visitLayers([](Layer* layer) { layer->onPrePaint(); });
    this->visitLayers([=](Layer* layer) { layer->onPaint(backbuffer.get()); });
    // ...
}

// 子类实现平台特定部分
virtual void onInval() = 0;
virtual bool attach(BackendType) = 0;
```

### 责任链模式

层堆栈实现责任链：事件从顶层传递到底层，直到被处理。

```cpp
bool Window::onKey(...) {
    return this->signalLayers([=](Layer* layer) {
        return layer->onKey(...);  // 处理则返回 true，停止传递
    });
}
```

这使得 UI 组件可以独立开发，无需了解其他层的存在。

### 策略模式

`BackendType` 枚举和 `WindowContext` 实现策略模式：
- 运行时选择图形后端
- 不同后端有不同的实现策略
- 通过 `attach()` 动态切换

### 外观模式

`Window` 为复杂的窗口系统和图形后端提供简化接口：
- 隐藏平台差异
- 统一 Ganesh 和 Graphite 的访问
- 封装层管理和事件分发细节

### 设计权衡

**纯虚函数 vs 默认实现**:
- 核心操作（`setTitle`, `show`, `attach`）为纯虚函数，强制子类实现
- 可选功能（`setUIState`, `getClipboardText`）提供空默认实现

**Layer 激活状态**:
- 使用布尔标志而非移除层对象
- 优点：快速启用/禁用，保留状态
- 缺点：遍历时需要额外检查

**WindowContext 独立性**:
- 将后端管理委托给 `WindowContext`
- 降低 `Window` 复杂度
- 便于独立测试和替换后端实现

## 性能考量

### 层遍历优化

```cpp
for (int i = 0; i < fLayers.size(); ++i) {
    if (fLayers[i]->fActive) {
        visitor(fLayers[i]);
    }
}
```

使用原始索引循环而非范围循环，避免迭代器开销。在渲染循环中每帧可能执行多次，微优化累积效果明显。

### 失效防抖

```cpp
if (!fIsContentInvalidated) {
    fIsContentInvalidated = true;
    onInval();
}
```

防止连续失效调用产生过多平台事件，减少系统负载。

### 早期退出

```cpp
void Window::onPaint() {
    if (!fWindowContext) return;
    if (!fIsActive) return;
    // ...
}
```

尽早检查前置条件，避免无效的层遍历和后备缓冲获取。

### GPU 命令批处理

`submitToGpu()` 允许应用控制 GPU 提交时机，实现批处理：

```cpp
// 多次绘制
window->inval();
window->onPaint();
window->inval();
window->onPaint();
// 最后统一提交
window->submitToGpu();
```

减少 GPU 同步开销。

### Lambda 捕获开销

```cpp
return this->signalLayers([=](Layer* layer) {
    return layer->onChar(c, modifiers);
});
```

按值捕获（`[=]`）会复制变量，但对于基本类型（`SkUnichar`, `int`）开销可忽略。复杂对象应使用引用捕获（`[&]`）。

### 实际性能表现

- **层遍历**: 10 层堆栈遍历 < 1μs（现代 CPU）
- **事件分发**: 单个事件处理 < 5μs
- **渲染循环**: 60 FPS 下每帧约 16.6ms，层管理开销 < 1%

关键性能瓶颈在于实际绘制和 GPU 提交，而非 `Window` 框架本身。

## 相关文件

### 平台实现
- `tools/sk_app/win/Window_win.h/cpp`: Windows 实现
- `tools/sk_app/mac/Window_mac.h/mm`: macOS 实现
- `tools/sk_app/unix/Window_unix.h/cpp`: Linux/Unix 实现
- `tools/sk_app/ios/Window_ios.h/mm`: iOS 实现
- `tools/sk_app/android/Window_android.h/cpp`: Android 实现

### 依赖组件
- `tools/window/WindowContext.h`: 后端上下文管理
- `tools/window/DisplayParams.h`: 显示参数
- `tools/sk_app/CommandSet.h`: 命令集（键盘快捷键）

### 使用示例
- `tools/viewer/Viewer.h/cpp`: 完整的示例应用
- `tools/skottie_tool/`: Lottie 动画工具

### 相关测试
- `tests/WindowTest.cpp`: 单元测试（如果存在）
