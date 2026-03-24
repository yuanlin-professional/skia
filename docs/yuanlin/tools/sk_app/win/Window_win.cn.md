# Window_win

> 源文件: `tools/sk_app/win/Window_win.h`, `tools/sk_app/win/Window_win.cpp`

## 概述

`Window_win` 是 Skia 应用框架中 `Window` 基类的 Windows 平台实现，封装了 Win32 API 的窗口创建、消息处理和事件分发逻辑。该类负责创建原生 Windows 窗口（HWND），处理 Windows 消息循环，并将系统事件转换为 Skia 的跨平台事件接口。它支持多种图形后端（OpenGL、Vulkan、D3D、ANGLE、Raster）和完整的输入设备处理（键盘、鼠标、触摸）。

主要功能包括：
- Win32 窗口创建和生命周期管理
- Windows 消息循环处理（WndProc）
- 虚拟键码到 Skia 按键枚举的转换
- 修饰键状态提取（Shift、Ctrl、Alt）
- 多点触摸输入支持
- MSAA 参数变更时的窗口重建
- 窗口位置和尺寸的记忆功能

## 架构位置

`Window_win` 位于 Windows 平台特定的实现层：

```
skia/
├── tools/
│   └── sk_app/
│       ├── Window.h/cpp                      # 跨平台基类
│       └── win/
│           ├── Window_win.h                  # Windows 实现头文件
│           ├── Window_win.cpp                # Windows 实现
│           └── main_win.cpp                  # Windows 程序入口
├── tools/window/
│   └── win/
│       ├── WindowContextFactory_win.h/cpp    # Windows 后端工厂
│       └── [各后端实现]
└── include/
    └── core/
        └── SkTypes.h                          # 平台宏定义
```

作为平台适配层，`Window_win` 桥接了 Win32 API 和 Skia 的跨平台窗口抽象。

## 主要类与结构体

### 类 `Window_win`

继承自 `Window` 基类，实现 Windows 平台特定功能。

#### 公共成员

```cpp
public:
    Window_win();
    ~Window_win() override;
    bool init(HINSTANCE instance);                     // 初始化窗口
    void setTitle(const char*) override;               // 设置标题
    void show() override;                              // 显示窗口
    bool attach(BackendType) override;                 // 附加图形后端
    void onInval() override;                           // 失效通知
    void setRequestedDisplayParams(                     // 设置显示参数
        std::unique_ptr<const DisplayParams>,
        bool allowReattach) override;
```

#### 私有成员

```cpp
private:
    void closeWindow();                      // 关闭窗口

    HINSTANCE fHInstance;                    // 应用程序实例句柄
    HWND fHWnd;                              // 窗口句柄
    BackendType fBackend;                    // 当前图形后端类型
    bool fInitializedBackend = false;        // 后端初始化标志
```

### 全局辅助函数

**`LRESULT CALLBACK WndProc(HWND, UINT, WPARAM, LPARAM)`**
- Windows 消息处理函数（窗口过程）
- 将 Win32 消息转换为 Skia 事件调用

**`static skui::Key get_key(WPARAM vk)`**
- 将 Windows 虚拟键码转换为 Skia 按键枚举

**`static skui::ModifierKey get_modifiers(UINT, WPARAM, LPARAM)`**
- 从消息参数提取修饰键状态

### 全局状态变量

```cpp
static int gWindowX = CW_USEDEFAULT;       // 窗口 X 位置（记忆上次位置）
static int gWindowY = 0;                   // 窗口 Y 位置
static int gWindowWidth = CW_USEDEFAULT;   // 窗口宽度
static int gWindowHeight = 0;              // 窗口高度
```

这些静态变量在窗口销毁时保存位置，重新创建时恢复，实现窗口位置记忆功能。

## 公共 API 函数

### 工厂函数

**`Window* Windows::CreateNativeWindow(void* platformData)`**

创建 Windows 平台的窗口实例。

**参数**:
- `platformData`: `HINSTANCE` 句柄（转换为 `void*`）

**返回值**:
- 成功：指向 `Window_win` 对象的指针
- 失败：`nullptr`

### 生命周期管理

**`bool init(HINSTANCE instance)`**

初始化 Windows 窗口。

**流程**:
1. 保存或获取 `HINSTANCE`
2. 注册窗口类（`WNDCLASSEX`，仅首次）
3. 创建窗口（`CreateWindow`）
4. 关联窗口与对象（`SetWindowLongPtr`）
5. 注册触摸支持（`RegisterTouchWindow`）

**窗口类属性**:
- 类名: "SkiaApp"
- 样式: `CS_HREDRAW | CS_VREDRAW | CS_OWNDC`（重绘时刷新、拥有设备上下文）
- 窗口过程: `WndProc`
- 背景: `COLOR_WINDOW + 1`

**`~Window_win()`**

析构函数，保存窗口位置并销毁窗口。

**`void closeWindow()`**

关闭窗口并保存位置/尺寸。

**行为**:
```cpp
RECT r;
if (GetWindowRect(fHWnd, &r)) {
    gWindowX = r.left;
    gWindowY = r.top;
    gWindowWidth = r.right - r.left;
    gWindowHeight = r.bottom - r.top;
}
DestroyWindow(fHWnd);
```

这使得下次创建窗口时能恢复到上次的位置和大小。

### 窗口操作

**`void setTitle(const char* title)`**

设置窗口标题。

**实现**: `SetWindowTextA(fHWnd, title)`

**`void show()`**

显示窗口。

**实现**: `ShowWindow(fHWnd, SW_SHOW)`

**`void onInval()`**

触发窗口重绘。

**实现**: `InvalidateRect(fHWnd, nullptr, false)`
- `nullptr`: 失效整个客户区
- `false`: 不擦除背景（由渲染器负责）

### 图形后端管理

**`bool attach(BackendType attachType)`**

附加指定的图形后端。

**支持的后端**:
- `kNativeGL`: 原生 OpenGL（通过 `MakeGLForWin`）
- `kANGLE`: ANGLE（OpenGL over D3D）
- `kGraphiteDawnD3D11/D3D12`: Graphite + Dawn + D3D
- `kVulkan`: Vulkan（Ganesh）
- `kGraphiteVulkan`: Vulkan（Graphite）
- `kDirect3D`: Direct3D 12
- `kRaster`: CPU 光栅化

**实现**:
```cpp
switch (attachType) {
#if defined(SK_GL)
    case BackendType::kNativeGL:
        fWindowContext = skwindow::MakeGLForWin(fHWnd, fRequestedDisplayParams->clone());
        break;
#endif
    // ... 其他后端
}
this->onBackendCreated();
return SkToBool(fWindowContext);
```

条件编译确保只包含启用的后端。

### 显示参数设置

**`void setRequestedDisplayParams(std::unique_ptr<const DisplayParams> params, bool allowReattach)`**

设置显示参数，必要时重建窗口。

**特殊处理**:
```cpp
// Windows OpenGL 不允许在窗口创建后更改 MSAA
if (params->msaaSampleCount() != this->getRequestedDisplayParams()->msaaSampleCount() &&
    allowReattach) {
    fRequestedDisplayParams = params->clone();
    fWindowContext = nullptr;
    this->closeWindow();
    this->init(fHInstance);
    if (fInitializedBackend) {
        this->attach(fBackend);
    }
}
```

MSAA 参数变更需要完全重建窗口，这是 Windows OpenGL 的限制。

## 内部实现细节

### Windows 消息处理（WndProc）

**消息分发表**:

| Windows 消息 | Skia 事件处理 | 说明 |
|-------------|-------------|------|
| `WM_PAINT` | `window->onPaint()` | 绘制窗口 |
| `WM_CLOSE` | `PostQuitMessage(0)` | 退出应用 |
| `WM_SIZE` | `window->onResize(w, h)` | 尺寸变化 |
| `WM_UNICHAR` | `window->onChar()` | Unicode 字符输入 |
| `WM_CHAR` | `window->onChar()` | 字符输入（UTF-16） |
| `WM_KEYDOWN/SYSKEYDOWN` | `window->onKey(..., kDown)` | 按键按下 |
| `WM_KEYUP/SYSKEYUP` | `window->onKey(..., kUp)` | 按键释放 |
| `WM_LBUTTONDOWN/UP` | `window->onMouse()` | 鼠标左键 |
| `WM_MOUSEMOVE` | `window->onMouse(..., kMove)` | 鼠标移动 |
| `WM_MOUSEWHEEL` | `window->onMouseWheel()` | 鼠标滚轮 |
| `WM_TOUCH` | `window->onTouch()` | 触摸输入 |

**事件处理返回值**:
```cpp
return eventHandled ? 0 : 1;
```

返回 0 表示事件已处理，1 表示未处理（传递给 `DefWindowProc`）。

### 虚拟键码转换

**`get_key` 映射表**:
```cpp
static const struct {
    WPARAM fVK;
    skui::Key fKey;
} gPair[] = {
    { VK_BACK,    skui::Key::kBack   },
    { VK_RETURN,  skui::Key::kOK     },
    { VK_UP,      skui::Key::kUp     },
    { VK_DOWN,    skui::Key::kDown   },
    // ... 22 个映射
};
```

使用线性搜索查找对应的 Skia 按键枚举。未映射的键返回 `skui::Key::kNONE`。

### 修饰键提取

**`get_modifiers` 逻辑**:

**键盘消息**（`WM_CHAR`, `WM_KEYDOWN` 等）:
```cpp
if (0 == (lParam & (1 << 30))) {
    modifiers |= skui::ModifierKey::kFirstPress;  // 首次按下（非重复）
}
if (lParam & (1 << 29)) {
    modifiers |= skui::ModifierKey::kOption;      // Alt 键
}
```

**鼠标消息**（`WM_LBUTTONDOWN`, `WM_MOUSEMOVE` 等）:
```cpp
if (wParam & MK_CONTROL) {
    modifiers |= skui::ModifierKey::kControl;
}
if (wParam & MK_SHIFT) {
    modifiers |= skui::ModifierKey::kShift;
}
```

不同消息类型使用不同的参数位提取修饰键状态。

### 字符输入处理

**UTF-16 解码**（`WM_CHAR`）:
```cpp
const uint16_t* cPtr = reinterpret_cast<uint16_t*>(&wParam);
SkUnichar c = SkUTF::NextUTF16(&cPtr, cPtr + 2);
eventHandled = window->onChar(c, get_modifiers(message, wParam, lParam));
```

Windows 的 `WM_CHAR` 消息使用 UTF-16 编码，需要转换为 Unicode 码点（`SkUnichar`）。

**Unicode 消息**（`WM_UNICHAR`）:
```cpp
eventHandled = window->onChar((SkUnichar)wParam, get_modifiers(message, wParam, lParam));
```

`WM_UNICHAR` 直接传递 Unicode 码点，无需解码。

### 触摸输入处理

**多点触摸支持**:
```cpp
uint16_t numInputs = LOWORD(wParam);
std::unique_ptr<TOUCHINPUT[]> inputs(new TOUCHINPUT[numInputs]);
if (GetTouchInputInfo((HTOUCHINPUT)lParam, numInputs, inputs.get(), sizeof(TOUCHINPUT))) {
    for (uint16_t i = 0; i < numInputs; ++i) {
        TOUCHINPUT ti = inputs[i];
        // 转换状态
        skui::InputState state = (ti.dwFlags & TOUCHEVENTF_DOWN) ? skui::InputState::kDown
                               : (ti.dwFlags & TOUCHEVENTF_MOVE) ? skui::InputState::kMove
                               : (ti.dwFlags & TOUCHEVENTF_UP)   ? skui::InputState::kUp
                               : continue;
        // 坐标转换：100ths of pixels → window relative
        LONG tx = (ti.x / 100) - topLeft.x;
        LONG ty = (ti.y / 100) - topLeft.y;
        eventHandled = window->onTouch(ti.dwID, state, tx, ty) || eventHandled;
    }
}
```

关键细节：
- **触摸坐标单位**: Windows 使用百分之一像素（1/100 pixel）
- **坐标系转换**: 从屏幕坐标转换为窗口客户区坐标
- **触摸 ID**: `ti.dwID` 用于跟踪多个触摸点

### 鼠标滚轮处理

```cpp
float delta = GET_WHEEL_DELTA_WPARAM(wParam) > 0 ? +1.0f : -1.0f;
window->onMouseWheel(delta, xPos, yPos, get_modifiers(message, wParam, lParam));
```

Windows 的滚轮增量（通常是 120 的倍数）被规范化为 +1.0 或 -1.0。

### 窗口用户数据关联

```cpp
// 初始化时关联
SetWindowLongPtr(fHWnd, GWLP_USERDATA, (LONG_PTR)this);

// WndProc 中检索
Window_win* window = (Window_win*) GetWindowLongPtr(hWnd, GWLP_USERDATA);
```

这种技术使得全局的 `WndProc` 函数可以访问特定窗口对象，实现对象化的消息处理。

## 依赖关系

### 直接依赖

**Windows API**:
- `<windows.h>`: 核心 Win32 API
- `<tchar.h>`: 字符类型（支持 Unicode/ANSI）
- `<windowsx.h>`: 消息处理宏（`GET_X_LPARAM` 等）

**Skia 核心**:
- `tools/sk_app/Window.h`: 基类定义
- `src/base/SkUTF.h`: UTF-16 解码
- `tools/skui/ModifierKey.h`: 修饰键枚举
- `tools/window/DisplayParams.h`: 显示参数
- `tools/window/WindowContext.h`: 窗口上下文抽象

**后端工厂**:
- `tools/window/win/WindowContextFactory_win.h`: Windows 后端创建函数
  - `MakeGLForWin`
  - `MakeANGLEForWin`
  - `MakeVulkanForWin`
  - `MakeD3D12ForWin`
  - `MakeRasterForWin`
  - 等

### 平台宏依赖

```cpp
#if defined(SK_GL)        // OpenGL 支持
#if defined(SK_ANGLE)     // ANGLE 支持
#if defined(SK_DAWN)      // Dawn 支持
#if defined(SK_GRAPHITE)  // Graphite 支持
#if defined(SK_VULKAN)    // Vulkan 支持
#ifdef SK_DIRECT3D        // Direct3D 支持
```

这些宏在构建时定义，控制哪些后端被编译。

### 被依赖情况

- `tools/sk_app/win/main_win.cpp`: 应用程序入口点
- Windows 平台的 Skia 应用（Viewer、示例程序等）

## 设计模式与设计决策

### 单例窗口类注册

```cpp
static WNDCLASSEX wcex;
static bool wcexInit = false;
if (!wcexInit) {
    // 注册窗口类
    RegisterClassEx(&wcex);
    wcexInit = true;
}
```

窗口类只注册一次，所有窗口实例共享。这是 Win32 编程的标准模式。

### 全局状态与对象状态的分离

**全局状态**: 窗口位置/尺寸（跨窗口实例保留）
**对象状态**: `HWND`、后端类型（每个窗口独立）

这种设计使得窗口重建时能保持用户偏好的位置。

### 消息处理的委托模式

```cpp
// WndProc（全局函数）→ Window_win（成员函数）
Window_win* window = (Window_win*) GetWindowLongPtr(hWnd, GWLP_USERDATA);
window->onPaint();
```

全局的 `WndProc` 作为适配器，将消息委托给对象方法，实现面向对象的事件处理。

### 条件编译的图形后端选择

使用 `#if defined(SK_GL)` 而非运行时检查的原因：
- **减少二进制大小**: 未启用的后端代码完全不包含
- **避免链接错误**: 未构建的后端库不会被引用
- **编译时安全**: 不可能尝试使用未构建的后端

### MSAA 重建窗口的必要性

Windows OpenGL 的限制：
- 像素格式（包括 MSAA 采样数）在窗口创建时固定
- 更改需要销毁并重新创建窗口和 OpenGL 上下文

Vulkan 和 D3D 没有此限制，但为了一致性，所有后端都采用相同的重建逻辑。

### 触摸坐标的奇怪单位

Windows 使用 1/100 像素单位的历史原因：
- 支持高精度触摸设备
- 兼容不同 DPI 设置

Skia 需要转换为标准像素单位。

## 性能考量

### 消息循环性能

**WndProc 执行频率**:
- `WM_PAINT`: 通常 60 Hz（V-Sync）
- `WM_MOUSEMOVE`: 高达 1000 Hz（高轮询率鼠标）
- `WM_TOUCH`: 高达 240 Hz（高刷新率触摸屏）

**优化措施**:
- 早期返回：未处理的消息立即交给 `DefWindowProc`
- 轻量级转换：`get_key` 和 `get_modifiers` 都是 O(1) 或 O(n)（n 很小）
- 无动态分配：除触摸输入外，所有处理都在栈上完成

### 触摸输入的动态分配

```cpp
std::unique_ptr<TOUCHINPUT[]> inputs(new TOUCHINPUT[numInputs]);
```

每次触摸事件都分配数组的原因：
- 触摸点数量不定（1-10 个常见）
- 触摸事件频率相对较低（< 240 Hz）

优化可能性：使用对象池或栈上小数组 + 动态分配的混合策略。

### 字符串转换开销

```cpp
SkUnichar c = SkUTF::NextUTF16(&cPtr, cPtr + 2);
```

UTF-16 到 Unicode 的转换开销：
- 单次转换约 10-20ns
- 对于文本输入场景（< 10 次/秒）可忽略

### 窗口重建的开销

MSAA 参数变更触发完整的窗口重建：
- 窗口销毁和创建：约 10-50ms
- 图形上下文重建：约 50-200ms（取决于后端）

这是罕见操作（用户手动调整设置），延迟可接受。

## 相关文件

### 平台特定实现
- `tools/sk_app/mac/Window_mac.h/mm`: macOS 实现
- `tools/sk_app/unix/Window_unix.h/cpp`: Linux 实现
- `tools/sk_app/ios/Window_ios.h/mm`: iOS 实现
- `tools/sk_app/android/Window_android.h/cpp`: Android 实现

### Windows 后端工厂
- `tools/window/win/WindowContextFactory_win.h/cpp`: 后端创建函数
- `tools/window/win/GLWindowContext_win.cpp`: OpenGL 后端
- `tools/window/win/ANGLEWindowContext_win.cpp`: ANGLE 后端
- `tools/window/win/VulkanWindowContext_win.cpp`: Vulkan 后端
- `tools/window/win/D3D12WindowContext_win.cpp`: Direct3D 后端

### 应用程序入口
- `tools/sk_app/win/main_win.cpp`: `WinMain` 函数

### 使用示例
```cpp
// main_win.cpp
int APIENTRY wWinMain(HINSTANCE hInstance, ...) {
    Window* window = Windows::CreateNativeWindow(hInstance);
    window->setTitle("My Skia App");
    window->attach(Window::BackendType::kNativeGL);
    window->show();

    // 消息循环
    MSG msg;
    while (GetMessage(&msg, nullptr, 0, 0)) {
        TranslateMessage(&msg);
        DispatchMessage(&msg);
    }

    delete window;
    return 0;
}
```
