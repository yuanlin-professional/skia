# editor_application - Skia 纯文本编辑器应用程序

> 源文件: `modules/skplaintexteditor/app/editor_application.cpp`

## 概述

`editor_application.cpp` 是一个基于 Skia 和 SkShaper 构建的纯文本编辑器的概念验证应用程序。它实现了一个完整的桌面文本编辑器，具备文件加载/保存、文本输入/删除、光标移动、文本选择、复制/剪切/粘贴、滚动、字体切换、字号调整以及光标闪烁等功能。该应用使用 `sk_app::Window` 框架作为窗口系统抽象层，支持 Vulkan、Metal、OpenGL 和软件光栅化等多种渲染后端。

## 架构位置

该文件是 `skplaintexteditor` 模块的应用层入口，位于 `Editor` 核心类之上。它将 `Editor` 引擎与 `sk_app` 窗口框架连接起来，处理平台事件（键盘、鼠标、窗口大小变化）并驱动编辑器的渲染循环。在 Skia 项目中，这是一个独立的演示应用，证明了使用 Skia 底层 API 构建文本编辑 UI 的可行性。

## 主要类与结构体

### `EditorLayer`
```cpp
struct EditorLayer : public sk_app::Window::Layer {
    Editor fEditor;
    Editor::TextPosition fTextPos{0, 0};
    Editor::TextPosition fMarkPos;
    std::vector<char> fClipboard;
    // ... 窗口状态
};
```
实现 `sk_app::Window::Layer` 接口，是事件处理和渲染的核心：
- 管理编辑器实例和光标/选择状态
- 内建剪贴板（`std::vector<char>`，非系统剪贴板）
- 处理所有用户输入事件

### `EditorApplication`
```cpp
struct EditorApplication : public sk_app::Application {
    std::unique_ptr<sk_app::Window> fWindow;
    EditorLayer fLayer;
    double fNextTime = -DBL_MAX;  // 光标闪烁定时器
};
```
应用程序主类，管理窗口生命周期和空闲循环。

### `Timer`（调试用）
```cpp
struct Timer {
    double fTime;
    const char* fDesc;
    Timer(const char* desc = "") : fTime(SkTime::GetNSecs()), fDesc(desc) {}
    ~Timer() { SkDebugf("%s: %5d μs\n", fDesc, (int)((SkTime::GetNSecs() - fTime) * 1e-3)); }
};
```
RAII 计时器，用于性能调试。

### `fontMgr()`
```cpp
sk_sp<SkFontMgr> fontMgr() {
    // 平台条件编译：Fontconfig/FreeType、CoreText、DirectWrite
}
```
根据编译平台选择字体管理器。

## 公共 API 函数

### EditorLayer 事件处理

| 方法 | 说明 |
|------|------|
| `void onPaint(SkSurface*) override` | 渲染编辑器内容 |
| `void onResize(int, int) override` | 处理窗口大小变化 |
| `void onAttach(sk_app::Window*) override` | 窗口附加回调 |
| `bool onMouseWheel(float, int, int, ModifierKey) override` | 鼠标滚轮滚动 |
| `bool onMouse(int, int, InputState, ModifierKey) override` | 鼠标点击和拖拽选择 |
| `bool onChar(SkUnichar, ModifierKey) override` | 字符输入和快捷键 |
| `bool onKey(skui::Key, InputState, ModifierKey) override` | 功能键处理 |

### EditorApplication

| 方法 | 说明 |
|------|------|
| `bool init(const char* path)` | 初始化窗口和加载文件 |
| `void onIdle() override` | 空闲循环，驱动光标闪烁 |
| `static Application* Create(int, char**, void*)` | 工厂方法，创建应用实例 |

## 内部实现细节

### 渲染流程 (`onPaint`)
```cpp
void onPaint(SkSurface* surface) override {
    SkCanvas* canvas = surface->getCanvas();
    canvas->clipRect({0, 0, (float)fWidth, (float)fHeight});
    canvas->translate(fMargin, (float)(fMargin - fPos));  // 滚动偏移
    Editor::PaintOpts options;
    options.fCursor = fTextPos;
    options.fCursorColor = {1, 0, 0, fBlink ? 0.0f : 1.0f};  // 闪烁
    fEditor.paint(canvas, options);
}
```

### 快捷键系统 (`onChar`)
支持 Command/Control 修饰键组合：
- `Ctrl+P`: 打印所有行到调试输出
- `Ctrl+S`: 保存文件
- `Ctrl+C`: 复制选择
- `Ctrl+X`: 剪切选择
- `Ctrl+V`: 粘贴
- `Ctrl+0`: 切换字体（sans-serif/serif/monospace）
- `Ctrl++/-`: 调整字号

### 键盘导航 (`onKey`)
```cpp
case skui::Key::kPageDown:  return this->scroll(fHeight * 4 / 5);
case skui::Key::kPageUp:    return this->scroll(-fHeight * 4 / 5);
case skui::Key::kLeft/Right/Up/Down/Home/End:  return this->moveCursor(convert(key), shift);
case skui::Key::kDelete:    // 向前删除
case skui::Key::kBack:      // 向后删除
```
支持 Ctrl+Left/Right 进行词级移动。

### 选择和光标管理
```cpp
bool move(Editor::TextPosition pos, bool shift) {
    if (shift != fShiftDown) {
        fMarkPos = shift ? fTextPos : Editor::TextPosition();
        fShiftDown = shift;
    }
    fTextPos = pos;
    // 自动滚动使光标可见
    SkIRect cursor = fEditor.getLocation(fTextPos).roundOut();
    if (fPos < cursor.bottom() - fHeight + 2 * fMargin) {
        fPos = cursor.bottom() - fHeight + 2 * fMargin;
    } else if (cursor.top() < fPos) {
        fPos = cursor.top();
    }
}
```

### 鼠标交互
- 鼠标按下：设置光标位置
- 鼠标拖拽：扩展选择区域
- Shift+点击：扩展选择
- 滚轮：基于字体行距的滚动

### 光标闪烁 (`onIdle`)
```cpp
void onIdle() override {
    double now = SkTime::GetNSecs();
    if (now >= fNextTime) {
        constexpr double kHalfPeriodNanoSeconds = 0.5 * 1e9;  // 0.5秒周期
        fNextTime = now + kHalfPeriodNanoSeconds;
        fLayer.fBlink = !fLayer.fBlink;
        fWindow->inval();
    }
}
```

### 渲染后端选择
```cpp
#if defined(SK_VULKAN)
    kBackendType = sk_app::Window::BackendType::kVulkan;
#elif defined(SK_METAL)
    kBackendType = sk_app::Window::BackendType::kMetal;
#elif defined(SK_GL)
    kBackendType = sk_app::Window::BackendType::kNativeGL;
#else
    kBackendType = sk_app::Window::BackendType::kRaster;
#endif
```

### 字体管理
```cpp
static const char* kTypefaces[3] = {"sans-serif", "serif", "monospace"};
```
通过 `Ctrl+0` 在三种字体间循环切换。

### 文件操作
- **加载**: 使用 `SkData::MakeFromFileName` 读取文件，通过 `Editor::insert` 插入
- **保存**: 使用 `std::ofstream` 逐行写出，行间插入换行符

## 依赖关系

- **直接依赖**: `editor.h`（核心编辑器）、`sk_app/Application.h`、`sk_app/Window.h`、`skui/ModifierKey.h`
- **平台依赖**: 根据编译配置选择 `SkFontMgr_fontconfig.h`（Linux）、`SkFontMgr_mac_ct.h`（macOS）、`SkTypeface_win.h`（Windows）
- **Skia 核心**: `SkCanvas.h`、`SkData.h`、`SkFontMgr.h`、`SkSurface.h`
- **运行时**: `SkTime.h` 用于计时

## 设计模式与设计决策

- **Layer 模式**: 使用 `sk_app::Window::Layer` 接口，将编辑器作为窗口层注册，实现事件处理和渲染回调的分离
- **MVC 分离**: `Editor` 类作为 Model 和部分 Controller，`EditorLayer` 作为 View 和事件处理 Controller，实现了较好的关注点分离
- **内建剪贴板**: 使用 `std::vector<char>` 作为剪贴板，而非系统剪贴板 API（代码中有 TODO 注明需要跨平台剪贴板接口）
- **平台抽象**: 通过条件编译选择字体管理器和渲染后端，实现跨平台支持
- **惰性初始化**: `fontMgr()` 使用静态变量实现单例模式（非线程安全，代码中有注释说明）
- **概念验证定位**: 作为 "proof of principle"，代码偏向简单直接，部分功能（如剪贴板、线程安全）留有 TODO

## 性能考量

- **按需重绘**: 使用 `inval()` 标记窗口需要重绘，避免不必要的渲染循环
- **滚动优化**: 滚动量基于字体行距计算 (`font().getSpacing()`)，提供自然的滚动体验
- **闪烁定时器**: 使用 0.5 秒周期的定时器驱动光标闪烁，每次闪烁都触发一次完整重绘（可优化为局部重绘）
- **调试计时**: `Timer` 结构体和 `SK_EDITOR_DEBUG_OUT` 宏用于性能分析
- **页面滚动**: PageUp/PageDown 滚动窗口高度的 4/5，保留上下文
- **shaping 预热**: `init()` 中调用 `fEditor.paint(nullptr, ...)` 触发文本 shaping，避免首次渲染时的延迟

## 相关文件

- `modules/skplaintexteditor/include/editor.h` — `Editor` 类声明
- `modules/skplaintexteditor/src/editor.cpp` — `Editor` 核心实现
- `tools/sk_app/Application.h` — 应用框架基类
- `tools/sk_app/Window.h` — 窗口抽象和 `Layer` 接口
- `tools/skui/ModifierKey.h` — 键盘修饰键定义
- `modules/skplaintexteditor/include/stringview.h` — 字符串视图类型
