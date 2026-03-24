# tools/sk_app/wasm/ - WebAssembly 平台应用实现

## 概述

`tools/sk_app/wasm/` 目录实现了 Skia 应用框架在 WebAssembly (WASM) 平台上的适配层。这是所有平台实现中最精简的一个，仅包含一个入口文件 `main_wasm.cpp`。该实现基于 Emscripten 工具链，使用 `emscripten_set_main_loop` 注册主循环回调，将浏览器的 `requestAnimationFrame` 机制适配为 Skia 的 `onIdle()` 调用。

由于 WebAssembly 环境的特殊性，WASM 实现没有专门的 `Window_wasm` 类。窗口管理和渲染上下文的创建依赖于 Emscripten 提供的 HTML5 Canvas API 和 WebGL/WebGPU 绑定。事件处理（键盘、鼠标、触摸）通过 Emscripten 的事件回调 API 实现。

WebAssembly 平台的主要约束包括：单线程执行模型（Web Workers 除外）、浏览器安全沙箱限制、无法直接访问文件系统（需要通过虚拟文件系统或 fetch API）。这些约束决定了 WASM 实现相比原生平台有更多的功能省略。

该实现主要用于 Skia 的 Web 演示和 CanvasKit（Skia 的 WebAssembly 封装模块）的测试验证。CanvasKit 提供了完整的 JavaScript API，而 `main_wasm.cpp` 则为传统的 C++ Skia 应用提供了 Web 运行时环境。

## 架构图

```
+----------------------------------------------------------+
|                 WASM 应用流程                               |
|                                                           |
|  浏览器环境                                                |
|    |                                                      |
|    v                                                      |
|  Emscripten Runtime                                       |
|    |                                                      |
|    v                                                      |
|  main() (main_wasm.cpp)                                   |
|    |                                                      |
|    +-- Application::Create(argc, argv, nullptr)           |
|    |     创建 Viewer 或其他应用实例                         |
|    |                                                      |
|    +-- 注册事件回调                                        |
|    |     emscripten_set_keydown_callback(...)              |
|    |     emscripten_set_mousedown_callback(...)            |
|    |     emscripten_set_resize_callback(...)               |
|    |                                                      |
|    +-- emscripten_set_main_loop(main_loop, 0, true)       |
|          |                                                |
|          v                                                |
|        main_loop() {                                      |
|          app->onIdle();  // 每帧调用                       |
|        }                                                  |
|          ^                                                |
|          | requestAnimationFrame 驱动                      |
|          |                                                |
|  HTML5 Canvas                                             |
|    WebGL 2.0 上下文 或 WebGPU 上下文                        |
+----------------------------------------------------------+
```

## 目录结构

```
tools/sk_app/wasm/
+-- main_wasm.cpp    # WASM 入口点（Emscripten 主循环注册、事件绑定）
```

## 关键函数

### main_wasm.cpp 核心逻辑

```cpp
// 全局应用实例
static Application* app = nullptr;

// 每帧回调（由 requestAnimationFrame 驱动）
void main_loop() {
    app->onIdle();
}

// Emscripten 事件回调
EM_BOOL key_callback(int eventType, const EmscriptenKeyboardEvent* e, void* userData) {
    // 将 Emscripten 键盘事件转换为 sk_app 事件
    // e->key, e->code --> skui::Key
    // eventType (KEYDOWN/KEYUP) --> skui::InputState
    return EM_TRUE;
}

EM_BOOL mouse_callback(int eventType, const EmscriptenMouseEvent* e, void* userData) {
    // 将 Emscripten 鼠标事件转换为 sk_app 事件
    return EM_TRUE;
}

int main(int argc, char** argv) {
    // 创建应用
    app = Application::Create(argc, argv, nullptr);

    // 注册事件回调
    emscripten_set_keydown_callback("#canvas", nullptr, true, key_callback);
    emscripten_set_keyup_callback("#canvas", nullptr, true, key_callback);
    emscripten_set_mousedown_callback("#canvas", nullptr, true, mouse_callback);
    emscripten_set_mousemove_callback("#canvas", nullptr, true, mouse_callback);
    emscripten_set_mouseup_callback("#canvas", nullptr, true, mouse_callback);

    // 启动主循环（不返回）
    // 参数 0 表示使用 requestAnimationFrame 的帧率
    // 参数 true 表示模拟无限循环
    emscripten_set_main_loop(main_loop, 0, true);

    return 0;
}
```

## 依赖关系

```
main_wasm.cpp
    |
    +---> Emscripten SDK
    |       +---> emscripten.h
    |       |       emscripten_set_main_loop()
    |       |
    |       +---> emscripten/html5.h
    |       |       emscripten_set_keydown_callback()
    |       |       emscripten_set_mousedown_callback()
    |       |       emscripten_set_resize_callback()
    |       |       EmscriptenKeyboardEvent
    |       |       EmscriptenMouseEvent
    |       |
    |       +---> emscripten/html5_webgpu.h (可选)
    |               WebGPU/Dawn 绑定
    |
    +---> sk_app::Application (基类)
    |
    +---> WebGL 2.0 / WebGPU
    |       通过 Emscripten 自动绑定到 HTML5 Canvas
    |
    +---> CanvasKit (modules/canvaskit/)
            Skia 的完整 WASM 封装（更常用的 Web 集成方式）
```

## 设计模式分析

### 适配器模式 (Adapter)

WASM 实现的核心适配是将浏览器的异步事件驱动模型适配为 Skia 的同步主循环模型。`emscripten_set_main_loop` 在内部使用 `requestAnimationFrame`，但对应用代码呈现为同步的 `main_loop()` 回调，使得 C++ 应用无需感知浏览器的异步本质。

### 最小接口实现

WASM 是所有平台中功能最精简的。没有 `Window_wasm` 类，没有平台特定的窗口管理，大部分功能直接由 Emscripten 运行时和浏览器提供。这体现了 **接口隔离原则** -- 只实现平台确实需要的最小功能集。

### 与 CanvasKit 的关系

虽然 `main_wasm.cpp` 提供了传统 C++ 应用在 Web 上运行的基础，但 Skia 的主要 Web 集成方式是通过 `modules/canvaskit/`。CanvasKit 提供了完整的 JavaScript API，而 `main_wasm.cpp` 更多用于内部测试和验证。

## 相关文档与参考

- **sk_app 框架**: `tools/sk_app/README.md`
- **Emscripten 文档**: https://emscripten.org/docs/api_reference/
- **Emscripten HTML5 API**: https://emscripten.org/docs/api_reference/html5.h.html
- **CanvasKit**: `modules/canvaskit/README.md`
- **WebGPU 标准**: https://www.w3.org/TR/webgpu/
