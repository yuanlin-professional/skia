# Slide

> 源文件: `tools/viewer/Slide.h`

## 概述

Slide 是 Skia Viewer 应用程序中所有演示幻灯片的抽象基类。它定义了幻灯片生命周期管理、绘制、动画、输入处理和控件交互的统一接口。所有 Viewer 中的演示内容都继承自此类。

## 架构位置

Slide 是 `tools/viewer` 模块的核心抽象，位于 Viewer 应用的幻灯片框架层。通过 `SlideRegistry`（基于 `sk_tools::Registry` 模板）实现幻灯片的自动注册。

## 主要类与结构体

### Slide
- 继承自 `SkRefCnt`（引用计数基类）
- 保护成员: `fName`（`SkString` 类型，幻灯片名称）

### SlideFactory
类型别名: `Slide* (*)()`，幻灯片工厂函数指针。

### SlideRegistry
类型别名: `sk_tools::Registry<SlideFactory>`，全局幻灯片注册表。

### DEF_SLIDE 宏
注册宏，生成唯一的工厂函数和注册表条目：
```cpp
#define DEF_SLIDE(code)
    static Slide* F_##__LINE__() { code }
    static SlideRegistry R_##__LINE__(F_##__LINE__);
```

## 公共 API 函数

- `getDimensions()`: 返回幻灯片的内容尺寸（空尺寸表示使用窗口尺寸）
- `gpuTeardown()`: GPU 资源清理回调
- `setSurfaceProps(SkSurfaceProps*)`: 设置表面属性
- `draw(SkCanvas*)`: **纯虚函数**，绘制幻灯片内容
- `animate(double nanos)`: 动画更新（返回 true 表示需要重绘）
- `load(SkScalar, SkScalar)`: 加载时初始化（接收窗口尺寸）
- `resize(SkScalar, SkScalar)`: 窗口大小变化通知
- `unload()`: 卸载清理
- `onChar(SkUnichar)`: 字符输入处理
- `onMouse(...)`: 鼠标事件处理
- `onGetControls/onSetControls(SkMetaData)`: 控件数据读写
- `getName()`: 返回幻灯片名称引用

## 依赖关系

- `include/core/SkRefCnt.h`: 引用计数基类
- `include/core/SkSize.h`: 尺寸类型
- `include/core/SkString.h`: 字符串类型
- `tools/Registry.h`: 注册表模板
- `tools/skui/InputState.h`: 输入状态枚举
- `tools/skui/ModifierKey.h`: 修饰键枚举

## 设计模式与设计决策

- **模板方法模式**: 定义幻灯片生命周期的虚函数框架
- **注册表模式**: `DEF_SLIDE` 宏实现编译时自动注册
- **引用计数**: 继承 `SkRefCnt` 支持 `sk_sp` 智能指针管理

## 性能考量

- 所有虚函数都有默认空实现，子类只需覆盖需要的函数
- `draw()` 是唯一的纯虚函数，确保每个幻灯片都实现绘制逻辑

## 相关文件

- `tools/viewer/ClickHandlerSlide.h`: 带点击处理的 Slide 子类
- `tools/Registry.h`: 通用注册表模板
- `tools/viewer/Viewer.cpp`: 幻灯片管理器
