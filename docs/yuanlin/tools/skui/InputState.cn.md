# InputState.h

> 源文件: tools/skui/InputState.h

## 概述

`InputState.h` 定义了 Skia 用户界面框架（skui）中的输入状态枚举类型。该文件声明了 `InputState` 枚举，用于表示各种用户输入动作的状态，包括鼠标和触摸事件的按下、释放、移动，以及手势操作（如 fling 手势）的方向。这是一个轻量级的头文件，为跨平台的输入事件处理提供了统一的状态表示。

## 架构位置

在 Skia 应用程序框架中的位置：

```
tools/
  └── skui/                      # Skia UI 工具库
      ├── InputState.h          # 输入状态枚举（本文件）
      ├── Key.h                 # 键盘按键枚举
      └── ModifierKey.h         # 修饰键枚举
```

使用场景：
```
平台输入事件 → Window 抽象层 → InputState + Key + ModifierKey →
应用程序事件处理器
```

## 主要类与结构体

### InputState 枚举

```cpp
namespace skui {
enum class InputState {
    kDown,   // 按下
    kUp,     // 释放
    kMove,   // 移动（仅用于鼠标）
    kRight,  // 向右（仅用于 fling）
    kLeft,   // 向左（仅用于 fling）
};
}
```

**成员说明**：

#### kDown
**用途**：表示鼠标按钮或触摸点按下事件
**适用场景**：
- 鼠标左键/右键/中键按下
- 触摸屏幕开始触摸
- 触控笔接触屏幕

#### kUp
**用途**：表示鼠标按钮或触摸点释放事件
**适用场景**：
- 鼠标按钮释放
- 触摸结束
- 触控笔离开屏幕

#### kMove
**用途**：表示鼠标移动事件
**限制**：仅用于鼠标输入，不适用于触摸或其他输入类型
**适用场景**：
- 鼠标指针在窗口内移动
- 可能带有或不带有按钮按下状态

#### kRight
**用途**：表示向右的 fling（快速滑动）手势
**限制**：仅用于 fling 手势
**适用场景**：
- 用户在触摸屏上快速向右滑动
- 手势识别后的方向指示

#### kLeft
**用途**：表示向左的 fling 手势
**限制**：仅用于 fling 手势
**适用场景**：
- 用户在触摸屏上快速向左滑动
- 手势识别后的方向指示

## 公共 API 函数

本文件仅定义枚举类型，不包含函数。

**使用示例**（推断）：
```cpp
// 在事件处理函数中使用
void Window::onMouse(int x, int y, skui::InputState state, skui::ModifierKey modifiers) {
    switch (state) {
        case skui::InputState::kDown:
            handleMouseDown(x, y, modifiers);
            break;
        case skui::InputState::kUp:
            handleMouseUp(x, y, modifiers);
            break;
        case skui::InputState::kMove:
            handleMouseMove(x, y, modifiers);
            break;
        default:
            break;
    }
}

// 处理 fling 手势
void Window::onFling(skui::InputState direction) {
    if (direction == skui::InputState::kLeft) {
        navigateToNextPage();
    } else if (direction == skui::InputState::kRight) {
        navigateToPreviousPage();
    }
}
```

## 内部实现细节

### 枚举类（enum class）设计

使用 C++11 的强类型枚举：
```cpp
enum class InputState { ... }
```

**优点**：
- 类型安全：不会隐式转换为整数
- 作用域隔离：需要使用 `skui::InputState::kDown` 完整限定
- 避免命名冲突：不会污染全局命名空间

### 命名约定

- 使用 `k` 前缀：遵循 Skia 的枚举值命名风格
- 驼峰命名：`kDown`、`kMove` 等
- 语义明确：直接描述输入状态

### 注释说明

```cpp
kMove,   // only valid for mouse
kRight,  // only valid for fling
kLeft,   // only valid for fling
```

明确指出某些状态仅适用于特定输入类型，避免误用。

## 依赖关系

**无外部依赖**：该文件是独立的头文件，仅依赖标准 C++ 语言特性。

**被依赖者**：
- `tools/sk_app/Window.h`：窗口类使用 InputState 定义事件回调
- `tools/viewer/Viewer.cpp`：Viewer 应用程序处理输入事件
- 各平台的 Window 实现（Window_mac、Window_unix、Window_win 等）

## 设计模式与设计决策

### 统一输入抽象

**问题**：不同平台的输入事件模型差异很大
- Windows：WM_LBUTTONDOWN、WM_MOUSEMOVE 等
- macOS：NSEvent 的不同类型
- Linux：X11 事件结构
- Android：MotionEvent

**解决方案**：定义跨平台的 InputState 枚举，统一表示所有平台的基本输入状态

### 最小化设计

仅定义最基本的状态：
- 按下/释放（通用）
- 移动（鼠标特有）
- 方向（手势特有）

**理由**：
- 简化跨平台实现
- 覆盖大多数应用场景
- 复杂交互由上层应用处理

### 多用途枚举

同一枚举同时服务于：
- 鼠标事件（kDown、kUp、kMove）
- 触摸事件（kDown、kUp）
- 手势事件（kLeft、kRight）

**优点**：
- 减少类型数量
- 统一事件处理接口

**缺点**：
- 某些值仅对特定输入类型有效（通过注释说明）

### 扩展性考虑

**当前限制**：
- 仅支持左右 fling，不支持上下
- 不包含双击、长按等复杂手势

**扩展方案**（如需要）：
```cpp
enum class InputState {
    // ... 现有值 ...
    kUp,     // 向上 fling
    kDown,   // 向下 fling（与 kDown 冲突，需重命名）
    kDoubleClick,
    kLongPress,
};
```

## 性能考量

### 内存占用

枚举类型通常占用一个整数大小（4 字节），开销极小。

### 运行时效率

- 枚举值比较是整数比较，速度极快
- 编译器可优化 switch 语句为跳转表或二分查找

### 编译时类型检查

使用 enum class 提供编译时类型安全，避免运行时错误。

## 相关文件

**同模块文件**：
- `tools/skui/Key.h`：键盘按键枚举
- `tools/skui/ModifierKey.h`：修饰键（Shift、Ctrl 等）枚举

**使用者**：
- `tools/sk_app/Window.h`：定义输入事件回调接口
- `tools/sk_app/mac/Window_mac.h` / `.mm`：macOS 窗口实现
- `tools/sk_app/unix/Window_unix.h` / `.cpp`：Unix 窗口实现
- `tools/sk_app/win/Window_win.h` / `.cpp`：Windows 窗口实现
- `tools/sk_app/android/Window_android.h` / `.cpp`：Android 窗口实现

**应用示例**：
- `tools/viewer/Viewer.cpp`：Skia Viewer 应用程序的输入处理

该文件虽然简单，但在 Skia 应用程序框架的输入处理体系中扮演着基础性角色，为跨平台输入事件提供了统一的抽象。
