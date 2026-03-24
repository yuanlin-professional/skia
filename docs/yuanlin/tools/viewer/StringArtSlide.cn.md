# StringArtSlide

> 源文件: tools/viewer/StringArtSlide.cpp

## 概述

`StringArtSlide` 是 Skia Viewer 中的一个交互式演示幻灯片,用于渲染弦线艺术(String Art)图形。该类通过数学螺旋算法生成艺术图案,用户可以通过水平点击来调整旋转角度,从而实时改变图案形状。这个幻灯片最初用于重现 Chromium bug 279014 相关的渲染问题。

## 架构位置

`StringArtSlide` 位于 `tools/viewer` 目录下,作为 Viewer 工具的一个示例幻灯片。它继承自 `ClickHandlerSlide`,支持鼠标交互功能。

```
tools/viewer/
├── Slide (基类)
├── ClickHandlerSlide (点击处理基类)
└── StringArtSlide (弦线艺术幻灯片)
```

## 主要类与结构体

### StringArtSlide 类

```cpp
class StringArtSlide : public ClickHandlerSlide {
public:
    StringArtSlide() : fAngle(0.305f) { fName = "StringArt"; }

    void load(SkScalar w, SkScalar h) override;
    void resize(SkScalar w, SkScalar h) override;
    void draw(SkCanvas* canvas) override;

protected:
    Click* onFindClickHandler(SkScalar x, SkScalar y, skui::ModifierKey) override;
    bool onClick(ClickHandlerSlide::Click *) override;

private:
    SkScalar fAngle;  // 当前旋转角度 [0, 1]
    SkSize fSize;     // 画布尺寸
};
```

## 公共 API 函数

### 构造函数

**StringArtSlide()**
- 初始化默认角度为 0.305
- 设置幻灯片名称为 "StringArt"

### 生命周期函数

**void load(SkScalar w, SkScalar h)**
- 保存窗口尺寸到 `fSize`

**void resize(SkScalar w, SkScalar h)**
- 响应窗口大小变化
- 更新 `fSize` 成员变量

**void draw(SkCanvas* canvas)**
- 根据当前角度绘制弦线艺术图案
- 使用螺旋算法生成路径
- 应用抗锯齿和描边样式

### 交互处理

**Click* onFindClickHandler(SkScalar x, SkScalar y, skui::ModifierKey)**
- 根据水平点击位置更新角度
- `fAngle = x / fSize.width()` (归一化到 [0, 1])
- 返回 nullptr(不需要持续拖动跟踪)

**bool onClick(ClickHandlerSlide::Click*)**
- 返回 false,表示不处理持续点击事件

## 内部实现细节

### 螺旋算法

绘制算法的核心逻辑:

```cpp
SkScalar angle = fAngle * SK_ScalarPI + SkScalarHalf(SK_ScalarPI);
SkPoint center = SkPoint::Make(fSize.width()/2, fSize.height()/2);
SkScalar length = 5;
SkScalar step = angle;

SkPathBuilder path;
path.moveTo(center);

while (length < (std::min(fSize.width(), fSize.height())/2 - 10.f)) {
    SkPoint rp = SkPoint::Make(
        length * SkScalarCos(step) + center.fX,
        length * SkScalarSin(step) + center.fY
    );
    path.lineTo(rp);
    length += angle / SkScalarHalf(SK_ScalarPI);
    step += angle;
}
path.close();
```

**算法步骤**:
1. 将归一化角度 [0, 1] 转换为 [π/2, 3π/2] 弧度
2. 从画布中心开始
3. 每次迭代:
   - 计算极坐标点 (length, step)
   - 转换为笛卡尔坐标并连线
   - 增加半径: `length += angle / (π/2)`
   - 增加角度: `step += angle`
4. 当半径接近画布边界时停止
5. 闭合路径

### 绘制样式

- **抗锯齿**: 启用 (`paint.setAntiAlias(true)`)
- **样式**: 描边 (`kStroke_Style`)
- **颜色**: 深绿色 (0xFF007700)
- **线宽**: 使用默认值(1像素)

## 依赖关系

### 直接依赖

- **Skia 核心**: `SkCanvas`, `SkPath`, `SkPathBuilder`, `SkPaint`, `SkPoint`
- **交互基类**: `ClickHandlerSlide`
- **数学函数**: `SkScalarCos`, `SkScalarSin`

### 模块依赖

```
StringArtSlide
├── tools/viewer/ClickHandlerSlide (交互支持)
└── include/core (Skia核心绘图API)
```

## 设计模式与设计决策

### 设计模式

1. **Template Method**: 继承 `ClickHandlerSlide`,重写特定方法实现自定义行为
2. **Strategy Pattern**: 通过角度参数改变绘制策略,生成不同图案

### 设计决策

1. **交互式参数**: 使用水平位置控制角度,提供直观的交互体验
2. **归一化角度**: 使用 [0, 1] 范围简化计算,便于与屏幕坐标映射
3. **自适应尺寸**: 根据窗口大小自动调整图案,避免超出边界
4. **路径构建器**: 使用 `SkPathBuilder` 而非旧的 `SkPath` API,更符合现代 Skia 实践
5. **简单着色**: 使用单一颜色,突出几何形状而非色彩

## 性能考量

1. **路径复杂度**: 迭代次数取决于窗口大小,典型情况下几十到上百次
2. **三角函数调用**: 每次迭代调用 `SkScalarCos` 和 `SkScalarSin`,有一定计算开销
3. **路径绘制**: 描边路径的渲染复杂度与线段数量成正比
4. **无缓存**: 每帧重新计算和绘制,适合交互式场景
5. **内存开销**: 路径构建器动态分配内存,但总量很小

## 相关文件

- **tools/viewer/ClickHandlerSlide.h**: 交互式幻灯片基类
- **tools/viewer/Slide.h**: 幻灯片系统基类
- **include/core/SkPath.h**: 路径对象定义
- **include/core/SkPathBuilder.h**: 路径构建器
- **include/core/SkCanvas.h**: 画布绘制接口
- **Chromium Issue 279014**: 此幻灯片最初用于重现和测试该 bug
