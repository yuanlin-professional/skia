# Skia SKUI 用户界面工具

## 概述

`tools/skui` 定义了 Skia 工具和示例应用共享的跨平台用户界面抽象类型。该模块提供了键盘按键、修饰键和输入状态的平台无关枚举定义，被 Viewer、sk_app 窗口系统和各种 Skia 演示应用使用。它是一个纯头文件的轻量级模块，不包含任何实现代码。

## 目录结构

```
tools/skui/
├── BUILD.bazel      # Bazel 构建配置
├── InputState.h     # 输入状态枚举
├── Key.h            # 键盘按键枚举
└── ModifierKey.h    # 修饰键枚举（支持位掩码运算）
```

## 核心类型

### InputState（输入状态）

定义鼠标和触摸事件的输入状态：

```cpp
namespace skui {
enum class InputState {
    kDown,    // 按下
    kUp,      // 释放
    kMove,    // 移动（仅鼠标有效）
    kRight,   // 向右滑动（仅 fling 手势有效）
    kLeft,    // 向左滑动（仅 fling 手势有效）
};
}
```

### Key（键盘按键）

定义完整的键盘按键映射，兼容 Android 和桌面平台：

| 按键分组 | 包含的按键 |
|---------|----------|
| 数字键 | `k0` - `k9` |
| 方向键 | `kUp`, `kDown`, `kLeft`, `kRight` |
| 功能键 | `kHome`, `kBack`, `kSend`, `kEnd` |
| 编辑键 | `kTab`, `kPageUp`, `kPageDown`, `kDelete`, `kEscape` |
| 字母键 | `kA`, `kC`, `kV`, `kX`, `kY`, `kZ`（ImGui 需要） |
| 修饰键 | `kShift`, `kCtrl`, `kOption`(Alt), `kSuper`(Command) |
| 特殊键 | `kStar`(*), `kHash`(#), `kOK`(中心键) |
| 设备键 | `kVolUp`, `kVolDown`, `kPower`, `kCamera` |

### ModifierKey（修饰键）

支持位掩码运算的修饰键枚举：

```cpp
namespace skui {
enum class ModifierKey {
    kNone       = 0,
    kShift      = 1 << 0,    // Shift 键
    kControl    = 1 << 1,    // Control 键
    kOption     = 1 << 2,    // Option/Alt 键
    kCommand    = 1 << 3,    // Command 键
    kFirstPress = 1 << 4,    // 首次按下标志
};
}
```

通过 `sknonstd::is_bitmask_enum` 特化，支持 `|`、`&` 等位运算操作：

```cpp
// 检测 Shift + Control 组合键
if ((modifiers & skui::ModifierKey::kShift) &&
    (modifiers & skui::ModifierKey::kControl)) {
    // 处理组合键
}
```

## 设计特点

- **纯头文件库**: 无 `.cpp` 实现文件，零运行时开销
- **平台无关**: 抽象了不同操作系统的输入事件差异
- **Android 兼容**: Key 枚举的设计对应 Android 的键码体系
- **ImGui 支持**: 包含 ImGui 需要的字母键和功能键
- **类型安全**: 使用 `enum class` 确保类型安全，避免隐式转换

## 使用示例

```cpp
#include "tools/skui/InputState.h"
#include "tools/skui/Key.h"
#include "tools/skui/ModifierKey.h"

// 处理键盘事件
void onKey(skui::Key key, skui::InputState state, skui::ModifierKey modifiers) {
    if (key == skui::Key::kEscape && state == skui::InputState::kDown) {
        // ESC 键按下，退出
    }
    if (key == skui::Key::kZ &&
        (modifiers & skui::ModifierKey::kCommand)) {
        // Cmd+Z 撤销
    }
}

// 处理鼠标事件
void onMouse(int x, int y, skui::InputState state, skui::ModifierKey modifiers) {
    if (state == skui::InputState::kDown) {
        // 鼠标按下
    }
}
```

## 与其他模块的关系

- **tools/sk_app/**: 窗口系统使用 skui 类型传递用户输入
- **tools/viewer/**: Viewer 应用的事件处理基于 skui 类型
- **modules/canvaskit/**: CanvasKit 的输入处理也参考了 skui 的定义
