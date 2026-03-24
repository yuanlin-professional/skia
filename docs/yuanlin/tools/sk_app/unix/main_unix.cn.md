# main_unix.cpp

> 源文件: tools/sk_app/unix/main_unix.cpp

## 概述

`main_unix.cpp` 是 Skia 应用程序框架在 Unix/Linux 平台上的主入口点实现。该文件负责初始化 X11 窗口系统、管理事件循环、处理窗口事件，并与 Skia 的跨平台应用程序框架集成。它实现了一个高效的事件驱动架构，使用 select() 系统调用来避免忙等待，并通过事件批处理和合并机制来优化性能。

核心功能包括：
- 初始化 X11 Display 连接和线程支持
- 实现非阻塞的事件循环，使用 select() 等待 X11 事件
- 合并多个连续的 Expose（重绘）和 ConfigureNotify（调整大小）事件
- 管理窗口映射和事件分发
- 处理应用程序空闲回调

## 架构位置

在 Skia 应用程序框架中的位置：

```
tools/sk_app/
  ├── Application.h              # 跨平台应用程序抽象接口
  ├── unix/
  │   ├── main_unix.cpp         # Unix 平台主入口（本文件）
  │   ├── Window_unix.h/.cpp    # X11 窗口实现
  │   └── keysym2ucs.h          # 键盘符号转换
  ├── mac/main_mac.mm
  ├── win/main_win.cpp
  └── android/main_android.cpp
```

事件处理流程：
```
X11 事件 → select() 监听 → XPending() 检查 →
事件循环处理 → Window_unix → Application
```

## 主要类与结构体

### THashSet<sk_app::Window_unix*>

```cpp
THashSet<sk_app::Window_unix*> pendingWindows;
```

**用途**：使用 Skia 的哈希集合类型存储待处理的窗口指针，用于合并多个重绘和调整大小事件。

**设计理由**：
- 避免同一窗口的重复处理
- 高效的查找和插入操作（O(1)平均复杂度）
- 自动去重

### fd_set

```cpp
fd_set in_fds;
```

**用途**：POSIX 文件描述符集合，用于 select() 系统调用监听 X11 连接的文件描述符。

### timeval

```cpp
struct timeval tv;
tv.tv_usec = 10;
tv.tv_sec = 0;
```

**用途**：指定 select() 的超时时间（10 微秒），实现非阻塞轮询。

## 公共 API 函数

### main

```cpp
int main(int argc, char**argv)
```

**功能**：Unix/Linux 平台的程序入口点，初始化 X11 环境并运行主事件循环。

**参数**：
- `argc`：命令行参数数量
- `argv`：命令行参数数组

**返回值**：
- `0`：正常退出

**执行流程**：

1. **初始化 X11 线程支持**：
   ```cpp
   XInitThreads();
   ```
   允许多线程访问 X11 显示连接

2. **打开 Display 连接**：
   ```cpp
   Display* display = XOpenDisplay(nullptr);
   ```
   连接到默认的 X11 显示服务器

3. **创建 Skia 应用程序**：
   ```cpp
   sk_app::Application* app = sk_app::Application::Create(argc, argv, (void*)display);
   ```

4. **获取 X11 文件描述符**：
   ```cpp
   const int x11_fd = ConnectionNumber(display);
   ```

5. **主事件循环**：
   ```cpp
   while (!done) {
       // 使用 select() 等待事件或超时
       // 处理所有待处理的 X11 事件
       // 合并重绘和调整大小事件
       // 调用应用程序空闲回调
   }
   ```

6. **清理资源**：
   ```cpp
   delete app;
   XCloseDisplay(display);
   ```

## 内部实现细节

### 非阻塞事件循环

```cpp
if (0 == XPending(display)) {
    fd_set in_fds;
    FD_ZERO(&in_fds);
    FD_SET(x11_fd, &in_fds);

    struct timeval tv;
    tv.tv_usec = 10;
    tv.tv_sec = 0;

    (void)select(1, &in_fds, nullptr, nullptr, &tv);
}
```

**设计要点**：
- 仅在无待处理事件时调用 select()
- 使用短超时（10 微秒）避免长时间阻塞
- 允许快速响应渲染需求

### 事件批处理与合并

```cpp
if (int count = XPending(display)) {
    THashSet<sk_app::Window_unix*> pendingWindows;
    while (count-- && !done) {
        XEvent event;
        XNextEvent(display, &event);

        sk_app::Window_unix* win = sk_app::Window_unix::gWindowMap.find(event.xany.window);
        if (!win) {
            continue;
        }

        switch (event.type) {
        case Expose:
            win->markPendingPaint();
            pendingWindows.add(win);
            break;
        case ConfigureNotify:
            win->markPendingResize(event.xconfigurerequest.width,
                                   event.xconfigurerequest.height);
            pendingWindows.add(win);
            break;
        default:
            if (win->handleEvent(event)) {
                done = true;
            }
            break;
        }
    }
    pendingWindows.foreach([](sk_app::Window_unix* win) {
        win->finishResize();
        win->finishPaint();
    });
}
```

**优化策略**：
1. **限制单次处理的事件数量**：处理 `XPending()` 返回的事件数量，避免无限循环
2. **合并重绘事件**：多个 Expose 事件只触发一次绘制
3. **合并调整大小事件**：多个 ConfigureNotify 事件只执行一次调整
4. **延迟处理**：标记需要重绘/调整的窗口，批量处理完成后统一执行

### 窗口查找机制

```cpp
sk_app::Window_unix* win = sk_app::Window_unix::gWindowMap.find(event.xany.window);
```

使用全局窗口映射表（在 Window_unix 中定义）快速查找事件对应的窗口对象。

### 空闲处理

```cpp
} else {
    // We are only really "idle" when the timer went off with zero events.
    app->onIdle();
}
```

仅在 select() 超时且无事件时才视为真正的空闲状态，避免在事件处理期间误调用空闲回调。

### 显示刷新

```cpp
XFlush(display);
```

在每次循环迭代后刷新 X11 命令缓冲区，确保所有绘制命令发送到服务器。

## 依赖关系

**系统库依赖**：
- X11 库：
  - `XInitThreads()`：线程支持
  - `XOpenDisplay()`、`XCloseDisplay()`：连接管理
  - `XPending()`、`XNextEvent()`：事件处理
  - `XFlush()`：显示刷新
  - `ConnectionNumber()`：获取文件描述符
- POSIX 库：
  - `select()`：I/O 多路复用
  - `fd_set`、`FD_ZERO`、`FD_SET`：文件描述符集操作

**Skia 内部依赖**：
- `include/core/SkTypes.h`：核心类型定义
- `src/core/SkTHash.h`：哈希集合
- `tools/sk_app/Application.h`：应用程序抽象
- `tools/sk_app/unix/Window_unix.h`：Unix 窗口实现
- `tools/timer/Timer.h`：计时器工具

## 设计模式与设计决策

### 事件驱动架构

使用事件循环模式，响应式处理 X11 事件和应用程序回调。

### I/O 多路复用

使用 select() 系统调用避免忙等待：
- **优点**：低 CPU 占用，响应快速
- **替代方案**：poll()、epoll()（Linux 特定）

### 事件合并优化

**问题**：窗口调整时可能产生大量连续的 Expose 和 ConfigureNotify 事件
**解决方案**：使用哈希集合收集需要处理的窗口，批量处理后统一执行
**效果**：大幅减少重复的重绘和布局计算

### 有限事件处理

```cpp
if (int count = XPending(display)) {
    while (count-- && !done) {
        // ...
    }
}
```

**设计理由**：
- 防止无限循环：限制单次处理的事件数量
- 保证响应性：定期返回空闲处理
- 避免饥饿：确保渲染有机会执行

## 性能考量

### select() 超时时间选择

```cpp
tv.tv_usec = 10;  // 10 微秒
```

**权衡**：
- 更短的超时：更快的响应，但更高的 CPU 占用
- 更长的超时：更低的 CPU 占用，但响应延迟增加
- 10 微秒是一个平衡点，满足实时渲染需求

### 事件批处理性能

```cpp
pendingWindows.foreach([](sk_app::Window_unix* win) {
    win->finishResize();
    win->finishPaint();
});
```

**优势**：
- 减少重复的布局计算
- 减少重复的 OpenGL/Vulkan 命令提交
- 提高窗口调整时的流畅度

### 哈希集合性能

使用 THashSet 而非 vector 或 set：
- O(1) 平均插入和查找时间
- 自动去重，无需手动检查
- 对于少量窗口（通常 < 10），性能差异不明显

### XFlush 位置

在循环末尾调用 XFlush()，而非每个事件后：
- 批量发送命令，减少网络往返（对于远程 X11）
- 减少系统调用开销

## 相关文件

**直接依赖**：
- `tools/sk_app/unix/Window_unix.h` / `.cpp`：窗口实现和事件处理
- `tools/sk_app/Application.h`：应用程序接口定义

**平台对应文件**：
- `tools/sk_app/mac/main_mac.mm`：macOS 实现
- `tools/sk_app/win/main_win.cpp`：Windows 实现
- `tools/sk_app/android/main_android.cpp`：Android 实现

**相关工具**：
- `tools/skui/Key.h`、`ModifierKey.h`：键盘输入抽象
- `tools/timer/Timer.h`：性能计时
- `tools/sk_app/unix/keysym2ucs.h`：键盘符号转换

该文件是 Unix/Linux 平台上 Skia 应用程序的基础，提供了高效的事件处理和窗口管理机制。
