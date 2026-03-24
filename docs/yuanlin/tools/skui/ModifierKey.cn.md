# ModifierKey.h

> 源文件: tools/skui/ModifierKey.h

## 概述

`ModifierKey.h` 定义了 Skia 用户界面框架中的修饰键（Modifier Key）枚举类型。修饰键是指在按键事件中同时按下的辅助按键，如 Shift、Ctrl、Alt（Option）和 Command 等。该文件使用位掩码（bitmask）枚举实现，允许通过位运算组合多个修饰键状态，为跨平台应用程序提供统一的修饰键抽象。

该枚举还包含 `kFirstPress` 标志，用于区分按键的首次按下和持续按住状态，这对于实现按键重复延迟等功能至关重要。

## 架构位置

在 Skia UI 工具库中的位置：

```
tools/skui/
  ├── ModifierKey.h      # 修饰键枚举（本文件）
  ├── Key.h              # 键盘按键枚举
  └── InputState.h       # 输入状态枚举

src/base/
  └── SkBitmaskEnum.h    # 位掩码枚举支持
```

使用场景：
```
键盘事件 → 修饰键状态（ModifierKey 组合） →
应用程序处理（区分 Ctrl+C vs C）
```

## 主要类与结构体

### ModifierKey 枚举

```cpp
namespace skui {
enum class ModifierKey {
    kNone       = 0,        // 无修饰键
    kShift      = 1 << 0,   // Shift 键（位 0）
    kControl    = 1 << 1,   // Control/Ctrl 键（位 1）
    kOption     = 1 << 2,   // Option/Alt 键（位 2）
    kCommand    = 1 << 3,   // Command/Windows/Super 键（位 3）
    kFirstPress = 1 << 4,   // 首次按下标志（位 4）
};
}
```

**位掩码设计**：
每个修饰键占用一个独立的位，允许通过位运算组合：
- `kShift`：0001（二进制）= 1
- `kControl`：0010 = 2
- `kOption`：0100 = 4
- `kCommand`：1000 = 8
- `kFirstPress`：10000 = 16

**成员说明**：

#### kNone
**值**：0
**用途**：表示没有任何修饰键被按下
**使用场景**：普通按键事件，不带修饰键

#### kShift
**值**：1 << 0 = 1
**用途**：Shift 键被按下
**跨平台映射**：
- Windows：VK_SHIFT
- macOS：NSEventModifierFlagShift
- Linux：ShiftMask（X11）

#### kControl
**值**：1 << 1 = 2
**用途**：Control/Ctrl 键被按下
**跨平台映射**：
- Windows：VK_CONTROL
- macOS：NSEventModifierFlagControl
- Linux：ControlMask（X11）

#### kOption
**值**：1 << 2 = 4
**用途**：Option（macOS）/ Alt（Windows/Linux）键被按下
**跨平台映射**：
- Windows：VK_MENU（Alt 键）
- macOS：NSEventModifierFlagOption
- Linux：Mod1Mask（X11，通常是 Alt）
**别名**：也称为 ALT 键

#### kCommand
**值**：1 << 3 = 8
**用途**：Command（macOS）/ Windows（Windows）/ Super（Linux）键被按下
**跨平台映射**：
- Windows：VK_LWIN / VK_RWIN（Windows 键）
- macOS：NSEventModifierFlagCommand（⌘ 键）
- Linux：Mod4Mask（X11，通常是 Super/Meta）

#### kFirstPress
**值**：1 << 4 = 16
**用途**：标识按键的首次按下事件
**使用场景**：
- 实现按键重复延迟（首次按下后延迟，然后快速重复）
- 区分首次按下和持续按住
- 实现单次触发的快捷键

### 位掩码枚举特性

```cpp
namespace sknonstd {
template <> struct is_bitmask_enum<skui::ModifierKey> : std::true_type {};
}
```

**作用**：声明 `ModifierKey` 为位掩码枚举，启用位运算符重载。

**支持的运算**：
```cpp
ModifierKey mods = ModifierKey::kShift | ModifierKey::kControl;  // 按位或
if (mods & ModifierKey::kShift) { ... }                          // 按位与
mods |= ModifierKey::kOption;                                    // 复合赋值
mods &= ~ModifierKey::kControl;                                  // 清除标志
```

## 公共 API 函数

本文件仅定义枚举类型，不包含函数。但通过位掩码特性支持运算符。

**使用示例**：
```cpp
// 检查单个修饰键
void onKey(skui::Key key, skui::ModifierKey modifiers) {
    if (modifiers & skui::ModifierKey::kControl) {
        // Ctrl 键被按下
    }
}

// 检查多个修饰键组合
if ((modifiers & (skui::ModifierKey::kControl | skui::ModifierKey::kShift))
    == (skui::ModifierKey::kControl | skui::ModifierKey::kShift)) {
    // Ctrl+Shift 同时按下
}

// 检查是否为首次按下
if (modifiers & skui::ModifierKey::kFirstPress) {
    // 首次按下，不是持续按住
}

// 组合修饰键
skui::ModifierKey mods = skui::ModifierKey::kNone;
if (shiftPressed) mods |= skui::ModifierKey::kShift;
if (ctrlPressed) mods |= skui::ModifierKey::kControl;

// 平台特定快捷键
#ifdef SK_BUILD_FOR_MAC
    const auto cmdKey = skui::ModifierKey::kCommand;  // Mac 使用 Cmd
#else
    const auto cmdKey = skui::ModifierKey::kControl;  // 其他平台使用 Ctrl
#endif
if ((modifiers & cmdKey) && key == skui::Key::kC) {
    copyToClipboard();
}
```

## 内部实现细节

### 位运算优化

位掩码设计使用单个整数存储多个布尔状态：
```
位 4: kFirstPress
位 3: kCommand
位 2: kOption
位 1: kControl
位 0: kShift

例如：Ctrl+Shift = 0011 (二进制) = 3 (十进制)
```

**优点**：
- 紧凑存储：5 个标志只占用 1 个字节
- 快速检查：位运算比多个布尔值比较更快
- 原子操作：单个整数可原子读写

### is_bitmask_enum 特性

```cpp
namespace sknonstd {
template <> struct is_bitmask_enum<skui::ModifierKey> : std::true_type {};
}
```

这个模板特化启用了 `SkBitmaskEnum.h` 中定义的位运算符重载：
- `operator|`：按位或
- `operator&`：按位与
- `operator^`：按位异或
- `operator~`：按位取反
- `operator|=`、`operator&=`、`operator^=`：复合赋值

### 平台映射策略

各平台的 Window 实现负责将平台修饰键状态映射到 `ModifierKey`：

**macOS 示例**（推断）：
```objective-c
skui::ModifierKey mapModifiers(NSEventModifierFlags flags) {
    skui::ModifierKey mods = skui::ModifierKey::kNone;
    if (flags & NSEventModifierFlagShift) mods |= skui::ModifierKey::kShift;
    if (flags & NSEventModifierFlagControl) mods |= skui::ModifierKey::kControl;
    if (flags & NSEventModifierFlagOption) mods |= skui::ModifierKey::kOption;
    if (flags & NSEventModifierFlagCommand) mods |= skui::ModifierKey::kCommand;
    return mods;
}
```

## 依赖关系

**Skia 内部依赖**：
- `src/base/SkBitmaskEnum.h`：提供位掩码枚举支持

**被依赖者**：
- `tools/sk_app/Window.h`：窗口事件回调接口
- `tools/viewer/Viewer.cpp`：应用程序快捷键处理
- 各平台 Window 实现：修饰键状态转换

**相关枚举**：
- `tools/skui/Key.h`：键盘按键枚举
- `tools/skui/InputState.h`：输入状态枚举

## 设计模式与设计决策

### 位掩码模式

**优点**：
- 高效存储和传递多个布尔状态
- 自然的组合语义（`Shift | Control`）
- 快速的位运算检查

**缺点**：
- 不如结构体直观
- 需要理解位运算

### 平台抽象策略

不同平台的"主要"修饰键不同：
- **macOS**：Command（⌘）用于大多数快捷键
- **Windows/Linux**：Control（Ctrl）用于大多数快捷键

**解决方案**：
应用程序可根据平台选择：
```cpp
#ifdef SK_BUILD_FOR_MAC
    const auto mainModifier = skui::ModifierKey::kCommand;
#else
    const auto mainModifier = skui::ModifierKey::kControl;
#endif
```

### kFirstPress 设计

**问题**：按键持续按住时会产生重复事件
**解决方案**：使用 `kFirstPress` 标志区分首次按下和重复

**应用场景**：
```cpp
void onKey(skui::Key key, skui::InputState state, skui::ModifierKey mods) {
    if (state == skui::InputState::kDown && (mods & skui::ModifierKey::kFirstPress)) {
        // 仅在首次按下时触发
        triggerOneTimeAction();
    }
}
```

### 最小化设计

仅包含最常用的修饰键：
- ✅ Shift、Control、Option、Command
- ❌ CapsLock、NumLock、ScrollLock、Fn

**理由**：
- 覆盖 99% 的使用场景
- 简化跨平台实现
- 减少复杂性

## 性能考量

### 内存效率

位掩码使用单个整数（4 字节）存储 5 个状态，比 5 个布尔值（5 字节 + 对齐填充）更紧凑。

### 运行时性能

**位运算速度**：
- 检查标志：`mods & kShift`（一次位与运算）
- 设置标志：`mods |= kShift`（一次位或运算）
- 清除标志：`mods &= ~kShift`（一次位与和位取反）

这些操作通常编译为单条 CPU 指令，极快。

### 比较效率

```cpp
// 快速：单次比较
if (mods == (kControl | kShift)) { ... }

// 慢：多次比较
if ((mods & kControl) && (mods & kShift) &&
    !(mods & kOption) && !(mods & kCommand)) { ... }
```

### 传递开销

枚举值按值传递，开销等同于传递一个整数，无需指针或引用。

## 相关文件

**核心依赖**：
- `src/base/SkBitmaskEnum.h`：位掩码枚举基础设施

**同模块文件**：
- `tools/skui/Key.h`：键盘按键枚举
- `tools/skui/InputState.h`：输入状态枚举

**使用者**：
- `tools/sk_app/Window.h`：定义键盘事件回调
- `tools/sk_app/*/Window_*.cpp`：平台特定的修饰键映射
- `tools/viewer/Viewer.cpp`：快捷键处理

**ImGui 集成**：
- `tools/viewer/ImGuiLayer.cpp`：ImGui 修饰键状态同步

该文件提供的位掩码枚举设计是一种经典且高效的多标志表示方法，广泛应用于系统编程和 GUI 框架中。
