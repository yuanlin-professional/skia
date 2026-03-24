# ClickHandlerSlide

> 源文件: tools/viewer/ClickHandlerSlide.h, tools/viewer/ClickHandlerSlide.cpp

## 概述

`ClickHandlerSlide` 是 Skia Viewer 工具中为幻灯片提供高级点击处理抽象的基类。该组件将原始鼠标事件(按下、移动、抬起)封装为一个 `Click` 对象,自动跟踪点击的整个生命周期,包括起始位置、前一位置、当前位置以及修饰键状态。这使得子类可以专注于实现业务逻辑,而无需手动管理点击状态机。

该类通过 `Click` 嵌套类提供了点击状态的完整历史记录,并支持两种回调机制:虚函数重写(传统面向对象方式)和函数对象(现代C++函数式方式)。它还提供了元数据存储(`SkMetaData`),允许子类附加自定义数据到点击对象上,实现更复杂的交互模式。

## 架构位置

`ClickHandlerSlide` 位于 Skia 项目的 `tools/viewer` 目录下,作为 `Slide` 的增强基类:

```
Slide (基础幻灯片接口)
  └─> ClickHandlerSlide (点击处理增强)
      ├─> ZoomInSlide
      └─> 其他交互式幻灯片
```

## 主要类与结构体

### ClickHandlerSlide

点击处理基类:

```cpp
class ClickHandlerSlide : public Slide {
public:
    class Click {
    public:
        Click();
        Click(std::function<bool(Click*)> f);
        virtual ~Click() = default;

        SkPoint fOrig;    // 起始位置
        SkPoint fPrev;    // 前一位置
        SkPoint fCurr;    // 当前位置

        skui::InputState fState;          // 当前状态(Down/Move/Up)
        skui::ModifierKey fModifierKeys;  // 修饰键(Ctrl/Shift/Alt等)

        SkMetaData fMeta;  // 元数据存储

        std::function<bool(Click*)> fFunc;  // 可选回调函数
        bool fHasFunc;                      // 是否使用函数回调
    };

    bool onMouse(SkScalar x, SkScalar y,
                 skui::InputState clickState,
                 skui::ModifierKey modifierKeys) final;

protected:
    virtual Click* onFindClickHandler(SkScalar x, SkScalar y,
                                      skui::ModifierKey modi) = 0;
    virtual bool onClick(Click*) = 0;

private:
    std::unique_ptr<Click> fClick;  // 当前活跃的点击对象
};
```

**关键成员变量**:
- `fOrig`: 鼠标按下时的初始位置
- `fPrev`: 前一帧的鼠标位置(用于计算增量)
- `fCurr`: 当前帧的鼠标位置
- `fState`: 当前输入状态(Down/Move/Up)
- `fModifierKeys`: 修饰键状态(Ctrl/Shift/Alt组合)
- `fMeta`: 通用元数据容器,可存储任意类型的附加信息
- `fFunc` / `fHasFunc`: 函数式回调机制
- `fClick`: 当前活跃的点击对象,鼠标抬起后释放

## 公共 API 函数

### Click 构造函数

```cpp
Click()
```

默认构造函数,创建使用虚函数回调的点击对象。

```cpp
Click(std::function<bool(Click*)> f)
```

使用函数对象构造,创建使用函数回调的点击对象:
```cpp
fFunc = std::move(f);
fHasFunc = true;
```

### 鼠标事件处理

```cpp
bool onMouse(SkScalar x, SkScalar y,
             skui::InputState clickState,
             skui::ModifierKey modifierKeys) final
```

最终实现(不可重写),处理所有鼠标事件:

**Down 事件**:
```cpp
case skui::InputState::kDown:
    fClick = nullptr;  // 清除旧点击
    fClick.reset(this->onFindClickHandler(x, y, modifierKeys));
    if (!fClick) {
        return false;  // 子类不处理此点击
    }
    fClick->fPrev = fClick->fCurr = fClick->fOrig = {x, y};
    fClick->fState = skui::InputState::kDown;
    fClick->fModifierKeys = modifierKeys;
    dispatch(fClick.get());  // 调用回调
    return true;
```

**Move 事件**:
```cpp
case skui::InputState::kMove:
    if (fClick) {
        fClick->fPrev = fClick->fCurr;  // 保存前一位置
        fClick->fCurr = {x, y};
        fClick->fState = skui::InputState::kMove;
        fClick->fModifierKeys = modifierKeys;
        return dispatch(fClick.get());
    }
    return false;
```

**Up 事件**:
```cpp
case skui::InputState::kUp:
    if (fClick) {
        fClick->fPrev = fClick->fCurr;
        fClick->fCurr = {x, y};
        fClick->fState = skui::InputState::kUp;
        fClick->fModifierKeys = modifierKeys;
        bool result = dispatch(fClick.get());
        fClick = nullptr;  // 释放点击对象
        return result;
    }
    return false;
```

### 子类接口

```cpp
virtual Click* onFindClickHandler(SkScalar x, SkScalar y,
                                  skui::ModifierKey modi) = 0
```

纯虚函数,子类必须实现。鼠标按下时调用,返回 `Click` 对象开始跟踪,或返回 `nullptr` 拒绝处理。

**典型实现**:
```cpp
Click* onFindClickHandler(SkScalar x, SkScalar y, skui::ModifierKey modi) override {
    if (modi == skui::ModifierKey::kControl) {
        return new Click();  // 仅在按下 Ctrl 时处理
    }
    return nullptr;
}
```

```cpp
virtual bool onClick(Click*) = 0
```

纯虚函数,子类必须实现。每次鼠标事件(Down/Move/Up)时调用。返回 `true` 继续跟踪,返回 `false` 停止(但通常应持续到 Up 事件)。

## 内部实现细节

### 双回调机制

```cpp
auto dispatch = [this](Click* c) {
    return c->fHasFunc ? c->fFunc(c) : this->onClick(c);
};
```

- 如果 `Click` 对象构造时传入了函数,使用函数回调
- 否则调用子类的虚函数 `onClick()`

这支持两种编程风格:
```cpp
// 风格1:虚函数重写
class MySlide : public ClickHandlerSlide {
    Click* onFindClickHandler(...) override {
        return new Click();
    }
    bool onClick(Click* c) override {
        // 处理点击
        return true;
    }
};

// 风格2:函数对象
Click* onFindClickHandler(...) override {
    return new Click([](Click* c) {
        // 处理点击
        return true;
    });
}
bool onClick(Click*) override { return true; }  // 占位实现
```

### 状态跟踪

每次鼠标移动都保存前一位置:
```cpp
fClick->fPrev = fClick->fCurr;
fClick->fCurr = {x, y};
```

这使得计算拖拽增量非常简单:
```cpp
SkVector delta = c->fCurr - c->fPrev;
```

### 生命周期管理

点击对象使用 `std::unique_ptr` 管理:
```cpp
std::unique_ptr<Click> fClick;
```

- Down: 创建新点击对象
- Move: 更新现有点击对象
- Up: 调用回调后释放点击对象

### 元数据用法

`Click::fMeta` 可存储自定义数据:
```cpp
// 存储
c->fMeta.setPtr("object", someObject);
c->fMeta.setS32("index", 42);

// 读取
void* obj = c->fMeta.findPtr("object");
int idx = c->fMeta.findS32("index", -1);
```

用于跟踪点击关联的对象,如被拖拽的图形元素。

## 依赖关系

### 直接依赖

- **tools/viewer/Slide.h**: 幻灯片基类
- **tools/SkMetaData.h**: 元数据存储
- **include/core/SkPoint.h**: 点坐标

## 设计模式与设计决策

### 模板方法模式

`onMouse()` 是模板方法,定义了点击处理流程:
```cpp
bool onMouse(...) final {  // 不可重写
    switch (clickState) {
        case kDown:
            // 调用钩子 onFindClickHandler()
            // 调用钩子 onClick()
        case kMove:
            // 调用钩子 onClick()
        case kUp:
            // 调用钩子 onClick()
    }
}
```

子类通过重写钩子方法定制行为。

### 策略模式

双回调机制是策略模式的应用:
```cpp
c->fHasFunc ? c->fFunc(c) : this->onClick(c)
```

运行时选择使用哪种回调策略。

### 生命周期管理

点击对象的生命周期严格绑定到鼠标按下-抬起周期:
- 创建: kDown
- 存在: kDown -> kMove -> ... -> kMove -> kUp
- 销毁: kUp

确保不会泄漏或误用点击对象。

## 性能考量

### 单点击对象

仅存储一个活跃点击对象:
```cpp
std::unique_ptr<Click> fClick;
```

Viewer 假设单点触控,避免管理多点击的复杂性。

### 虚函数开销

每次鼠标移动都调用虚函数 `onClick()`,但开销可忽略(虚函数调用约1-2ns)。

### 元数据性能

`SkMetaData` 使用线性搜索,但对于少量元数据(通常1-3个)足够快。

## 相关文件

### 继承关系

- **tools/viewer/Slide.h**: 父类
- **tools/viewer/ZoomInSlide.h**: 使用 ClickHandlerSlide 的子类示例

### 工具

- **tools/SkMetaData.h**: 元数据存储实现

### 使用场景

该组件用于:
1. **拖拽交互**: 跟踪拖拽起始点和当前点
2. **绘制工具**: 实现画笔、橡皮擦等工具
3. **对象选择**: 点击选择场景中的对象
4. **手势识别**: 检测点击、双击、长按等手势
5. **参数调整**: 拖拽滑块或控制点

典型用法:
```cpp
class MySlide : public ClickHandlerSlide {
    Click* onFindClickHandler(SkScalar x, SkScalar y, skui::ModifierKey modi) override {
        // 检查是否点击了可交互区域
        if (hitTest(x, y)) {
            return new Click();
        }
        return nullptr;
    }

    bool onClick(Click* c) override {
        switch (c->fState) {
            case skui::InputState::kDown:
                // 开始交互
                break;
            case skui::InputState::kMove:
                // 更新状态
                SkVector delta = c->fCurr - c->fPrev;
                applyDrag(delta);
                break;
            case skui::InputState::kUp:
                // 结束交互
                break;
        }
        return true;
    }
};
```

该组件简化了交互式幻灯片的开发,是 Viewer 工具箱中的重要基础设施。
