# Key.h

> 源文件: tools/skui/Key.h

## 概述

`Key.h` 定义了 Skia 用户界面框架中的键盘按键枚举类型。该文件声明了 `Key` 枚举，为跨平台应用程序提供了统一的键盘按键标识符。枚举涵盖了从数字键、方向键、功能键到移动设备特有的硬件按键（如音量键、相机键），特别包含了 ImGui（即时模式图形用户界面库）所需的关键按键。

该枚举设计考虑了多平台兼容性，特别是 Android 平台的特殊按键，为 Skia 的跨平台应用程序框架提供了统一的键盘输入抽象层。

## 架构位置

在 Skia UI 工具库中的位置：

```
tools/skui/
  ├── Key.h              # 键盘按键枚举（本文件）
  ├── InputState.h       # 输入状态枚举
  └── ModifierKey.h      # 修饰键枚举

tools/sk_app/            # 应用程序框架
  └── Window.h           # 使用 Key 枚举处理键盘事件
```

## 主要类与结构体

### Key 枚举

```cpp
namespace skui {
enum class Key {
    kNONE,    // 未知键（对应 Android 的 UNKNOWN）

    // 移动设备软键
    kLeftSoftKey,
    kRightSoftKey,

    // 导航和功能键
    kHome,    // 主屏幕键
    kBack,    // 返回键（CLR）
    kSend,    // 绿色通话键
    kEnd,     // 红色挂断键

    // 数字键
    k0, k1, k2, k3, k4, k5, k6, k7, k8, k9,
    kStar,    // * 键
    kHash,    // # 键

    // 方向键
    kUp, kDown, kLeft, kRight,

    // ImGui 需要的键
    kTab, kPageUp, kPageDown, kDelete, kEscape,
    kShift, kCtrl,
    kOption, // 也称为 Alt
    kSuper,  // 也称为 Command
    kA, kC, kV, kX, kY, kZ,

    // 其他功能键
    kOK,      // 中心确认键

    // 移动设备硬件键（匹配 Android）
    kVolUp,   // 音量增加
    kVolDown, // 音量减少
    kPower,   // 电源键
    kCamera,  // 相机键
};
}
```

**枚举值分类**：

#### 特殊键
- `kNONE`：未识别或无效的键

#### 移动设备软键（功能键）
- `kLeftSoftKey`、`kRightSoftKey`：屏幕下方的软件功能键

#### 系统导航键
- `kHome`：返回主屏幕
- `kBack`：返回上一级（Android 标准导航）
- `kSend`：拨号/发送（绿色通话键）
- `kEnd`：挂断/结束（红色挂断键）

#### 数字和符号键
- `k0` ~ `k9`：数字键
- `kStar`：星号键（*）
- `kHash`：井号键（#）

#### 方向键
- `kUp`、`kDown`、`kLeft`、`kRight`：四向方向键

#### ImGui 集成键
支持 ImGui 文本编辑和快捷键：
- `kTab`：制表符
- `kPageUp`、`kPageDown`：翻页
- `kDelete`：删除
- `kEscape`：取消/退出
- `kShift`、`kCtrl`、`kOption`（Alt）、`kSuper`（Cmd）：修饰键
- `kA`、`kC`、`kV`、`kX`、`kY`、`kZ`：常用快捷键字母

#### 确认键
- `kOK`：中心确认键（D-pad 中心）

#### 移动硬件键
- `kVolUp`、`kVolDown`：音量控制
- `kPower`：电源/锁屏键
- `kCamera`：相机快门键

## 公共 API 函数

本文件仅定义枚举类型，不包含函数。

**典型使用示例**：
```cpp
// 键盘事件处理
void Window::onKey(skui::Key key, skui::InputState state, skui::ModifierKey modifiers) {
    if (state == skui::InputState::kDown) {
        switch (key) {
            case skui::Key::kEscape:
                quitApplication();
                break;
            case skui::Key::kLeft:
                navigateLeft();
                break;
            case skui::Key::kRight:
                navigateRight();
                break;
            case skui::Key::kC:
                if (modifiers & skui::ModifierKey::kControl) {
                    copyToClipboard();
                }
                break;
            default:
                break;
        }
    }
}

// ImGui 集成
bool processImGuiKey(skui::Key key) {
    switch (key) {
        case skui::Key::kA: return ImGuiKey_A;
        case skui::Key::kTab: return ImGuiKey_Tab;
        // ... 更多映射
    }
}
```

## 内部实现细节

### 平台兼容性设计

**Android 特有键**：
```cpp
kHome,    // 对应 KEYCODE_HOME
kBack,    // 对应 KEYCODE_BACK
kVolUp,   // 对应 KEYCODE_VOLUME_UP
kCamera,  // 对应 KEYCODE_CAMERA
```

**桌面平台映射**：
- `kOption` ↔ Alt（Windows/Linux）、Option（macOS）
- `kSuper` ↔ Windows 键（Windows）、Command（macOS）、Super（Linux）

### ImGui 支持

专门包含 ImGui 所需的键：
```cpp
// Keys needed by ImGui
kTab, kPageUp, kPageDown, kDelete, kEscape,
kShift, kCtrl, kOption, kSuper,
kA, kC, kV, kX, kY, kZ,
```

这些键支持：
- 文本导航（Tab、方向键）
- 编辑操作（Delete、复制粘贴）
- 快捷键（Ctrl+C、Ctrl+V 等）

### 命名约定

- `k` 前缀：遵循 Skia 的枚举命名风格
- 描述性名称：`kVolUp` 而非 `kVolumeIncrease`
- 缩写说明：通过注释标注（如 `kOption // AKA Alt`）

## 依赖关系

**无外部依赖**：该文件是独立的头文件，仅使用标准 C++ 特性。

**被依赖者**：
- `tools/sk_app/Window.h`：定义键盘事件回调
- `tools/viewer/Viewer.cpp`：处理键盘快捷键
- 各平台 Window 实现：将平台键码映射到 `Key` 枚举

**相关枚举**：
- `tools/skui/InputState.h`：键盘事件状态（按下/释放）
- `tools/skui/ModifierKey.h`：修饰键状态（Shift、Ctrl 等）

## 设计模式与设计决策

### 跨平台抽象

**挑战**：不同平台的键码系统差异巨大
- Windows：VK_* 虚拟键码
- macOS：NSEvent.keyCode
- Linux：X11 KeySym
- Android：KeyEvent.KEYCODE_*

**解决方案**：定义平台无关的 `Key` 枚举，各平台实现负责映射

### 完整性 vs 简洁性

**当前设计**：有选择性地包含按键
- ✅ 包含：常用键、ImGui 需要的键、移动设备特有键
- ❌ 不包含：完整的字母表、所有功能键（F1-F12）、小键盘键

**理由**：
- 减少枚举值数量
- 覆盖实际使用场景
- 需要时可扩展

### 移动优先设计

包含大量移动设备特有的键：
```cpp
kLeftSoftKey, kRightSoftKey,
kHome, kBack, kSend, kEnd,
kVolUp, kVolDown, kPower, kCamera,
```

体现 Skia 对移动平台的重视。

### ImGui 集成优先

专门标注 ImGui 需要的键：
```cpp
// Keys needed by ImGui
kTab, kPageUp, kPageDown, kDelete, kEscape,
kShift, kCtrl, kOption, kSuper,
kA, kC, kV, kX, kY, kZ,
```

简化 ImGui 与 Skia 应用框架的集成。

### 扩展性考虑

**当前缺失但可能需要的键**：
- 完整的字母键（B、D、E、F 等）
- 功能键（F1-F12）
- 小键盘键
- 媒体控制键（播放、暂停、下一曲）

**扩展方案**：
```cpp
enum class Key {
    // ... 现有值 ...
    kF1, kF2, kF3, // ... F12
    kB, kD, kE, kF, // ... 其他字母
    kNumpad0, kNumpad1, // ... 小键盘
    kMediaPlay, kMediaPause, kMediaNext,
};
```

## 性能考量

### 内存占用

枚举类型占用一个整数大小（通常 4 字节），开销极小。

### 运行时性能

- 枚举比较是整数比较，非常快速
- switch 语句可被编译器优化为跳转表

### 平台键码映射

各平台需要维护键码映射表：
```cpp
// 伪代码：Windows 平台
skui::Key mapVirtualKey(WPARAM vk) {
    switch (vk) {
        case VK_ESCAPE: return skui::Key::kEscape;
        case VK_LEFT: return skui::Key::kLeft;
        case 'A': return skui::Key::kA;
        // ...
    }
}
```

映射开销通常很小，每次按键事件只执行一次。

## 相关文件

**同模块文件**：
- `tools/skui/InputState.h`：输入状态枚举
- `tools/skui/ModifierKey.h`：修饰键枚举

**使用者**：
- `tools/sk_app/Window.h`：窗口接口定义
- `tools/sk_app/mac/Window_mac.mm`：macOS 键码映射
- `tools/sk_app/unix/Window_unix.cpp`：X11 键码映射
- `tools/sk_app/win/Window_win.cpp`：Windows 键码映射
- `tools/sk_app/android/Window_android.cpp`：Android 键码映射

**ImGui 集成**：
- `tools/viewer/ImGuiLayer.cpp`：ImGui 输入处理

**应用示例**：
- `tools/viewer/Viewer.cpp`：Viewer 应用的键盘快捷键

该枚举是 Skia 应用程序框架中键盘输入处理的核心抽象，为跨平台应用提供了统一的按键标识符。
