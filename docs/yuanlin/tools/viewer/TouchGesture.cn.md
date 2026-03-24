# TouchGesture

> 源文件: tools/viewer/TouchGesture.h, tools/viewer/TouchGesture.cpp

## 概述

`TouchGesture` 是 Skia Viewer 工具中的触摸手势识别和处理引擎,负责将原始触摸输入转换为平移、缩放和惯性滑动等高级手势操作。该组件支持单指平移、双指缩放(pinch-to-zoom)、惯性滑动(fling)和双击重置等常见触摸交互模式,并提供了内容边界限制机制,确保内容不会完全移出视口。

该类维护了一个变换矩阵管道,将触摸手势转换为局部和全局变换矩阵,供渲染系统应用到画布上。它实现了复杂的状态机来管理不同的手势模式,处理多点触控的开始、移动和结束事件,并提供了平滑的惯性滑动效果,包括指数衰减和轴对齐优化。该组件是构建流畅触摸交互界面的基础设施。

## 架构位置

`TouchGesture` 位于 Skia 项目的 `tools/viewer` 目录下,属于开发工具层的交互支持模块。它不继承任何基类,是一个独立的实用程序类:

```
TouchGesture (独立手势处理器)
  ├─> Viewer (使用手势处理用户输入)
  └─> Slide (某些幻灯片可能直接使用)
```

该组件在 Skia 工具链中的定位:

- **输入层**: 处理底层触摸事件,转换为高级手势
- **变换管理**: 维护视图变换矩阵
- **交互支持**: 为 Viewer 和幻灯片提供触摸交互能力
- **跨平台**: 抽象触摸输入,支持不同操作系统的触摸 API

依赖的核心模块:
- **include/core/SkMatrix.h**: 变换矩阵计算
- **include/core/SkPoint.h**: 点和向量运算
- **include/core/SkRect.h**: 矩形和边界
- **include/private/base/SkTDArray.h**: 动态数组存储触摸点
- **src/base/SkTime.h**: 时间戳获取

## 主要类与结构体

### TouchGesture

主手势识别器类:

```cpp
class TouchGesture {
public:
    TouchGesture();
    ~TouchGesture();

    // 触摸事件接口
    void touchBegin(void* owner, float x, float y);
    void touchMoved(void* owner, float x, float y);
    void touchEnd(void* owner);

    // 状态管理
    void reset();
    void resetTouchState();

    // 状态查询
    bool isActive() { return fFlinger.isActive(); }
    void stop() { fFlinger.stop(); }
    bool isBeingTouched() { return kEmpty_State != fState; }
    bool isFling(SkPoint* dir);

    // 缩放控制
    void startZoom();
    void updateZoom(float scale, float startX, float startY, float lastX, float lastY);
    void endZoom();

    // 变换矩阵访问
    const SkMatrix& localM();
    const SkMatrix& globalM() const { return fGlobalM; }

    // 平移限制
    void setTransLimit(const SkRect& contentRect, const SkRect& windowRect,
                       const SkMatrix& preTouchM);

private:
    enum State {
        kEmpty_State,       // 无触摸
        kTranslate_State,   // 单指平移
        kZoom_State,        // 双指缩放
    };

    struct Rec {
        void* fOwner;       // 触摸点标识符
        float fStartX, fStartY;  // 起始位置
        float fPrevX, fPrevY;    // 前一位置
        float fLastX, fLastY;    // 当前位置
        float fPrevT, fLastT;    // 时间戳
    };
    SkTDArray<Rec> fTouches;  // 活跃触摸点列表

    State fState;
    SkMatrix fLocalM, fGlobalM, fPreTouchM;

    struct FlingState {
        bool isActive() const { return fActive; }
        void stop() { fActive = false; }
        void reset(float sx, float sy);
        bool evaluateMatrix(SkMatrix* matrix);
        void get(SkPoint* dir, SkScalar* speed);

    private:
        SkPoint fDirection;   // 惯性方向
        SkScalar fSpeed0;     // 初始速度
        double fTime0;        // 起始时间
        bool fActive;
    };
    FlingState fFlinger;
    double fLastUpMillis;     // 上次抬起时间
    SkPoint fLastUpP;         // 上次抬起位置

    // 平移限制
    SkRect fContentRect, fWindowRect;
    bool fIsTransLimited;

    // 辅助方法
    void limitTrans();
    void flushLocalM();
    int findRec(void* owner) const;
    void appendNewRec(void* owner, float x, float y);
    float computePinch(const Rec&, const Rec&);
    bool handleDblTap(float, float);
};
```

**关键成员变量**:
- `fTouches`: 存储当前所有活跃触摸点的信息,支持多点触控
- `fState`: 当前手势状态(空闲/平移/缩放)
- `fLocalM`: 局部变换矩阵,存储当前手势产生的临时变换
- `fGlobalM`: 全局变换矩阵,累积所有已完成的手势变换
- `fPreTouchM`: 触摸前的变换矩阵,用于平移限制计算
- `fFlinger`: 惯性滑动状态管理器
- `fLastUpMillis`, `fLastUpP`: 用于双击检测

### Rec 结构体

存储单个触摸点的完整历史:

```cpp
struct Rec {
    void* fOwner;           // 触摸标识符(通常是指针)
    float fStartX, fStartY; // 触摸开始位置
    float fPrevX, fPrevY;   // 前一帧位置
    float fLastX, fLastY;   // 当前位置
    float fPrevT, fLastT;   // 前一帧和当前时间戳(秒)
};
```

存储三个时间点的位置,用于速度计算和手势识别。

### FlingState 结构体

管理惯性滑动状态:

```cpp
struct FlingState {
    SkPoint fDirection;   // 归一化方向向量
    SkScalar fSpeed0;     // 初始速度(像素/秒)
    double fTime0;        // 惯性开始时间
    bool fActive;         // 是否活跃
};
```

使用指数衰减模型计算惯性滑动距离。

## 公共 API 函数

### 构造与析构

```cpp
TouchGesture::TouchGesture()
```

初始化并调用 `reset()` 清空所有状态。

```cpp
TouchGesture::~TouchGesture()
```

默认析构函数。

### 触摸事件处理

```cpp
void touchBegin(void* owner, float x, float y)
```

触摸开始事件:
- 如果 `owner` 已存在,移除旧记录(处理异常情况)
- 如果已有 2 个触摸点,忽略新触摸
- 刷新局部矩阵,停止惯性滑动
- 添加新触摸点记录
- 根据触摸点数量切换状态:
  - 1 个点: 进入 `kTranslate_State`
  - 2 个点: 进入 `kZoom_State`

```cpp
void touchMoved(void* owner, float x, float y)
```

触摸移动事件:
- 查找对应的触摸点记录
- 检测抖动(jitter),小于 2 像素的移动忽略(双指时)
- 更新位置和时间戳
- 根据状态更新变换:
  - 单指: 计算平移量,更新 `fLocalM`
  - 双指: 计算缩放比例和中心,调用 `updateZoom()`

```cpp
void touchEnd(void* owner)
```

触摸结束事件:
- 查找并移除触摸点记录
- 检测双击(时间 < 300ms,距离 < 100px)
- 根据剩余触摸点数量处理:
  - 从 1 到 0: 计算速度,启动惯性滑动,进入 `kEmpty_State`
  - 从 2 到 1: 结束缩放
- 应用平移限制

### 状态管理

```cpp
void reset()
```

完全重置,清空全局矩阵和触摸状态。

```cpp
void resetTouchState()
```

仅重置触摸状态,保留全局矩阵:
```cpp
fIsTransLimited = false;
fTouches.reset();
fState = kEmpty_State;
fLocalM.reset();
fLastUpMillis = SkTime::GetMSecs() - 2 * MAX_DBL_TAP_INTERVAL;
```

### 状态查询

```cpp
bool isActive()
```

返回惯性滑动是否活跃。

```cpp
bool isBeingTouched()
```

返回当前是否有触摸输入。

```cpp
bool isFling(SkPoint* dir)
```

判断是否为快速滑动(fling),阈值 1000 像素/秒。

### 缩放控制

```cpp
void startZoom()
```

切换到缩放状态。

```cpp
void updateZoom(float scale, float startX, float startY, float lastX, float lastY)
```

更新缩放变换:
```cpp
fLocalM.setTranslate(-startX, -startY);  // 移到原点
fLocalM.postScale(scale, scale);          // 缩放
fLocalM.postTranslate(lastX, lastY);      // 移回当前中心
```

围绕初始中心点缩放,跟随当前中心点移动。

```cpp
void endZoom()
```

刷新局部矩阵,结束缩放状态。

### 变换矩阵访问

```cpp
const SkMatrix& localM()
```

获取局部变换矩阵,如果惯性滑动活跃,先评估并更新:
```cpp
if (fFlinger.isActive()) {
    if (!fFlinger.evaluateMatrix(&fLocalM)) {
        this->flushLocalM();  // 惯性结束,刷新到全局
    }
}
return fLocalM;
```

```cpp
const SkMatrix& globalM() const
```

获取全局变换矩阵,只读访问。

### 平移限制

```cpp
void setTransLimit(const SkRect& contentRect, const SkRect& windowRect,
                   const SkMatrix& preTouchM)
```

设置平移限制,确保内容不会完全离开窗口:
- `contentRect`: 内容原始边界
- `windowRect`: 窗口边界
- `preTouchM`: 触摸前的变换矩阵

## 内部实现细节

### 状态机管理

手势识别的核心是状态机:

```
kEmpty_State
  ↓ touchBegin (1指)
kTranslate_State
  ↓ touchBegin (2指)
kZoom_State
  ↓ touchEnd (剩1指)
kTranslate_State
  ↓ touchEnd (0指)
kEmpty_State → 启动 fling
```

### 双指缩放算法

```cpp
float TouchGesture::computePinch(const Rec& rec0, const Rec& rec1) {
    // 计算初始距离
    double dx = rec0.fStartX - rec1.fStartX;
    double dy = rec0.fStartY - rec1.fStartY;
    double dist0 = sqrt(dx*dx + dy*dy);

    // 计算当前距离
    dx = rec0.fLastX - rec1.fLastX;
    dy = rec0.fLastY - rec1.fLastY;
    double dist1 = sqrt(dx*dx + dy*dy);

    return (float)(dist1 / dist0);  // 缩放比例
}
```

使用两指间距离比例作为缩放因子,简单且直观。

### 惯性滑动物理模型

```cpp
bool FlingState::evaluateMatrix(SkMatrix* matrix) {
    const float t = (float)(getseconds() - fTime0);
    const float K0 = 5;       // 衰减系数
    const float K1 = 0.02f;   // 最小速度系数
    const float speed = fSpeed0 * (std::exp(-K0 * t) - K1);

    if (speed <= MIN_SPEED) {
        fActive = false;
        return false;
    }

    float dist = (fSpeed0 - speed) / K0;  // 积分距离
    matrix->setTranslate(fDirection.fX * dist, fDirection.fY * dist);
    return true;
}
```

**物理公式**:
- 速度: `v(t) = v0 * (e^(-K0*t) - K1)`
- 距离: `s = (v0 - v(t)) / K0`

指数衰减确保平滑减速,K1 确保速度不会变负。

### 轴对齐优化

```cpp
static void unit_axis_align(SkVector* unit) {
    const SkScalar TOLERANCE = 0.15;
    if (SkScalarAbs(unit->fX) < TOLERANCE) {
        unit->fX = 0;
        unit->fY = SkScalarSignNonZero(unit->fY);  // 垂直滑动
    } else if (SkScalarAbs(unit->fY) < TOLERANCE) {
        unit->fX = SkScalarSignNonZero(unit->fX);  // 水平滑动
        unit->fY = 0;
    }
}
```

如果滑动方向接近水平或垂直(15% 容差),则对齐到轴,提供更自然的列表滚动体验。

### 抖动过滤

```cpp
static bool close_enough_for_jitter(float x0, float y0, float x1, float y1) {
    return std::fabs(x0 - x1) <= MAX_JITTER_RADIUS &&
           std::fabs(y0 - y1) <= MAX_JITTER_RADIUS;
}
```

双指缩放时,忽略小于 2 像素的移动,减少手指微小抖动导致的意外缩放。

### 双击检测

```cpp
bool TouchGesture::handleDblTap(float x, float y) {
    double now = SkTime::GetMSecs();
    if (now - fLastUpMillis <= MAX_DBL_TAP_INTERVAL) {  // 300ms 内
        if (SkPoint::Length(fLastUpP.fX - x, fLastUpP.fY - y) <= MAX_DBL_TAP_DISTANCE) {  // 100px 内
            // 双击:重置所有变换
            fFlinger.stop();
            fLocalM.reset();
            fGlobalM.reset();
            fTouches.reset();
            fState = kEmpty_State;
            return true;
        }
    }
    fLastUpMillis = now;
    fLastUpP.set(x, y);
    return false;
}
```

记录上次抬起的时间和位置,检测快速连续点击。

### 平移限制算法

```cpp
void TouchGesture::limitTrans() {
    if (!fIsTransLimited) return;

    SkRect scaledContent = fContentRect;
    fPreTouchM.mapRect(&scaledContent);  // 应用触摸前变换
    fGlobalM.mapRect(&scaledContent);    // 应用当前变换

    // 确保内容不会完全移出窗口
    fGlobalM.postTranslate(0, std::min(0.f, fWindowRect.fBottom - scaledContent.fTop));
    fGlobalM.postTranslate(0, std::max(0.f, fWindowRect.fTop - scaledContent.fBottom));
    fGlobalM.postTranslate(std::min(0.f, fWindowRect.fRight - scaledContent.fLeft), 0);
    fGlobalM.postTranslate(std::max(0.f, fWindowRect.fLeft - scaledContent.fRight), 0);
}
```

**限制逻辑**:
- 内容顶部 > 窗口底部: 向下平移
- 内容底部 < 窗口顶部: 向上平移
- 类似处理左右边界

确保至少有一部分内容始终可见。

### 矩阵管道

变换分为两个矩阵:
- **fLocalM**: 当前手势或惯性的临时变换
- **fGlobalM**: 所有已完成手势的累积变换

每次手势结束时,调用 `flushLocalM()`:
```cpp
void TouchGesture::flushLocalM() {
    fGlobalM.postConcat(fLocalM);  // 合并到全局
    fLocalM.reset();                // 清空局部
}
```

使用者通常将两个矩阵相乘应用到画布:
```cpp
canvas->concat(gesture.globalM());
canvas->concat(gesture.localM());
```

### 离散化优化

```cpp
#define DISCRETIZE_TRANSLATE_TO_AVOID_FLICKER true

if (DISCRETIZE_TRANSLATE_TO_AVOID_FLICKER) {
    tx = (float)sk_float_round2int(tx);
    ty = (float)sk_float_round2int(ty);
}
```

将平移量舍入到整数像素,避免亚像素渲染导致的闪烁,特别是对于像素艺术或文本。

## 依赖关系

### 直接依赖

- **include/core/SkMatrix.h**: 2D 变换矩阵
- **include/core/SkPoint.h**: 点和向量运算
- **include/core/SkRect.h**: 矩形和边界
- **include/private/base/SkTDArray.h**: 动态数组模板
- **src/base/SkTime.h**: 时间戳获取(`SkTime::GetMSecs()`, `SkTime::GetSecs()`)
- **tools/timer/TimeUtils.h**: 时间工具

### 间接依赖

- **include/private/base/SkFloatingPoint.h**: 浮点工具
- **include/core/SkTypes.h**: 基础类型定义

### 数据流向

```
[触摸事件]
    -> touchBegin/Moved/End()
    -> 更新 fTouches
    -> 计算 fLocalM
    -> flushLocalM() 合并到 fGlobalM
    -> localM() / globalM() 供外部访问
    -> 应用到画布变换
```

惯性流向:
```
[touchEnd 计算速度]
    -> fFlinger.reset(vx, vy)
    -> localM() 调用 evaluateMatrix()
    -> 根据时间更新 fLocalM
    -> 持续更新直到速度衰减到阈值
```

## 设计模式与设计决策

### 所有者标识模式

使用 `void* owner` 标识触摸点,而非整数 ID:
```cpp
void touchBegin(void* owner, float x, float y)
```

提供更大灵活性,调用者可以使用任何指针作为标识符(如窗口句柄)。

### 双缓冲矩阵策略

局部和全局矩阵分离:
- **局部矩阵**: 快速变化,每帧更新(手势或惯性)
- **全局矩阵**: 稳定累积,仅在手势结束时更新

这避免了频繁的矩阵乘法,提高性能。

### 状态封装

`FlingState` 封装惯性逻辑:
```cpp
struct FlingState {
    void reset(float sx, float sy);
    bool evaluateMatrix(SkMatrix* matrix);
    bool isActive() const;
    void stop();
};
```

清晰分离惯性管理,便于独立测试和修改物理模型。

### 容差设计

多处使用容差值:
- 抖动半径: 2 像素
- 双击间隔: 300 毫秒
- 双击距离: 100 像素
- 轴对齐容差: 15%

这些值基于人体工程学研究,提供自然的交互体验。

## 性能考量

### 触摸点线性搜索

```cpp
int TouchGesture::findRec(void* owner) const {
    for (int i = 0; i < fTouches.size(); i++) {
        if (owner == fTouches[i].fOwner) return i;
    }
    return -1;
}
```

最多支持 2 个触摸点,线性搜索足够高效,无需哈希表。

### 矩阵缓存

惯性滑动时,每帧调用 `evaluateMatrix()` 计算新矩阵,但不累积到全局矩阵,避免精度损失。

### 避免不必要的计算

```cpp
if (close_enough_for_jitter(...)) {
    return;  // 跳过微小移动
}
```

减少不必要的矩阵计算和重绘。

### 速度限制

```cpp
static const SkScalar MAX_FLING_SPEED = SkIntToScalar(1500);

static SkScalar pin_max_fling(SkScalar speed) {
    if (speed > MAX_FLING_SPEED) {
        speed = MAX_FLING_SPEED;
    }
    return speed;
}
```

限制惯性最大速度,避免异常输入导致的过度滚动。

## 相关文件

### Skia 核心

- **include/core/SkMatrix.h**: 矩阵运算
- **include/core/SkPoint.h**: 点和向量
- **include/core/SkRect.h**: 矩形

### 时间工具

- **src/base/SkTime.h**: 时间戳
- **tools/timer/TimeUtils.h**: 时间工具

### Viewer 集成

- **tools/viewer/Viewer.h**: Viewer 主应用程序,使用 TouchGesture 处理输入
- **tools/sk_app/Window.h**: 窗口抽象,提供触摸事件

### 使用场景

该组件在以下场景中使用:

1. **Viewer 主应用**: 处理所有触摸输入,实现平移和缩放
2. **移动设备适配**: 提供触摸屏友好的交互
3. **幻灯片导航**: 滑动切换幻灯片
4. **内容检查**: 放大查看渲染细节
5. **演示模式**: 流畅的手势交互增强演示效果

典型集成代码:
```cpp
TouchGesture gesture;

void onTouchDown(void* id, float x, float y) {
    gesture.touchBegin(id, x, y);
}

void onTouchMove(void* id, float x, float y) {
    gesture.touchMoved(id, x, y);
}

void onTouchUp(void* id) {
    gesture.touchEnd(id);
}

void draw(SkCanvas* canvas) {
    canvas->concat(gesture.globalM());
    canvas->concat(gesture.localM());
    // 绘制内容...
}
```

该组件是构建触摸友好应用的基础,提供了生产级的手势识别能力。
