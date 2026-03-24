# ZoomInSlide

> 源文件: tools/viewer/ZoomInSlide.h, tools/viewer/ZoomInSlide.cpp

## 概述

`ZoomInSlide` 是 Skia Viewer 工具中的一个专用实用程序类,用于可视化和检查小型路径的像素级栅格化效果。该组件将场景渲染到小尺寸离屏表面,然后将该表面放大显示在屏幕上,使开发者能够清晰地观察抗锯齿、像素覆盖和栅格化细节。这对于调试图形渲染问题、验证抗锯齿算法和理解亚像素渲染行为至关重要。

该类提供了一个抽象框架,子类可以通过实现 `drawUnderGrid()` 和 `drawOverGrid()` 方法来定制渲染内容。它自动绘制像素网格,并支持通过 Ctrl+点击进行交互式坐标操作。源文件中包含一个完整的示例实现 `ZoomInSlideDemo`,展示了如何使用该框架来检查路径渲染问题。

## 架构位置

`ZoomInSlide` 位于 Skia 项目的 `tools/viewer` 目录下,属于开发工具层。它继承自 `ClickHandlerSlide`,后者又继承自 `Slide`,形成以下继承链:

```
Slide (基础幻灯片接口)
  └─> ClickHandlerSlide (添加点击处理能力)
      └─> ZoomInSlide (添加缩放和网格可视化)
          └─> ZoomInSlideDemo (具体示例实现)
```

该组件在 Skia 工具链中的定位:

- **Viewer 框架**: 作为 Viewer 工具的一个专用幻灯片类型,用于像素级调试
- **开发辅助**: 主要服务于图形工程师和渲染算法开发者
- **教学工具**: 可用于演示和理解 Skia 的栅格化过程
- **问题复现**: 用于复现和调试特定的渲染问题(如示例中的 issues.skia.org/issues/451536363)

依赖的核心模块:
- **include/core/**: 使用 Skia 核心图形类(SkCanvas, SkPath, SkSurface 等)
- **tools/viewer/**: 依赖 Viewer 框架的 Slide 和 ClickHandlerSlide 基类

## 主要类与结构体

### ZoomInSlide

抽象基类,提供缩放可视化框架:

```cpp
class ZoomInSlide : public ClickHandlerSlide {
public:
    ZoomInSlide(size_t scale, size_t width, size_t height, SkString name);

protected:
    const size_t fScale;   // 缩放倍数
    const size_t fWidth;   // 小表面宽度(像素数)
    const size_t fHeight;  // 小表面高度(像素数)

    // 辅助方法
    void drawScaledPath(SkCanvas* canvas, const SkPath& path, const SkPaint& pathPaint);

    // 嵌套类
    class ScaledClick : public ClickHandlerSlide::Click {
    public:
        ScaledClick(size_t scale);
        SkPoint currScaled() const;  // 返回未缩放空间的坐标
    private:
        const size_t fScale;
    };

private:
    void draw(SkCanvas* canvas) override;  // 最终实现
    void drawGrid(SkCanvas* canvas);       // 绘制像素网格

    // 子类必须实现的纯虚函数
    virtual void drawUnderGrid(SkCanvas* canvas) = 0;  // 网格下层内容
    virtual void drawOverGrid(SkCanvas* canvas) = 0;   // 网格上层内容

    // 可选重写的交互回调
    virtual void handleClick(const ScaledClick* click);

    // 点击处理实现
    Click* onFindClickHandler(SkScalar x, SkScalar y, skui::ModifierKey modifiers) override;
    bool onClick(ClickHandlerSlide::Click* click) override;
};
```

**关键成员变量**:
- `fScale`: 缩放倍数,决定每个像素显示为多大(例如 32 表示每个像素放大为 32x32)
- `fWidth`, `fHeight`: 离屏表面的尺寸,以像素为单位,定义了被检查的区域大小

### ZoomInSlideDemo

示例实现类,展示如何使用框架:

```cpp
class ZoomInSlideDemo : public ZoomInSlide {
public:
    ZoomInSlideDemo();

    SkPath makePath();  // 根据控制点构造路径

    void drawUnderGrid(SkCanvas* canvas) override;    // 渲染栅格化路径
    void drawOverGrid(SkCanvas* canvas) override;     // 绘制矢量路径和控制点
    void handleClick(const ScaledClick* click) override;  // 处理控制点拖拽

private:
    static constexpr size_t kScale = 32;      // 32倍放大
    static constexpr int kMaskWidth = 20;     // 20像素宽
    static constexpr int kMaskHeight = 30;    // 30像素高
    static constexpr float kHandleRadius = 4.f;
    static constexpr int kNumPoints = 4;

    SkPoint fPts[kNumPoints];  // 路径控制点
};
```

### ScaledClick

嵌套点击数据类,提供坐标转换:

```cpp
class ScaledClick : public ClickHandlerSlide::Click {
public:
    ScaledClick(size_t scale);

    // 将屏幕坐标转换为未缩放的逻辑坐标
    SkPoint currScaled() const {
        return {fCurr.fX / fScale, fCurr.fY / fScale};
    }

private:
    const size_t fScale;
};
```

这个类简化了子类中的坐标处理,避免手动进行缩放转换。

## 公共 API 函数

### 构造函数

```cpp
ZoomInSlide(size_t scale, size_t width, size_t height, SkString name)
```

初始化缩放幻灯片:
- `scale`: 缩放倍数,例如 32 表示每个逻辑像素显示为 32x32 屏幕像素
- `width`: 离屏表面宽度(逻辑像素)
- `height`: 离屏表面高度(逻辑像素)
- `name`: 幻灯片名称,显示在 Viewer 界面中

### 辅助方法

```cpp
void drawScaledPath(SkCanvas* canvas, const SkPath& path, const SkPaint& pathPaint)
```

将路径栅格化到小表面并绘制到画布上:
1. 创建 `fWidth x fHeight` 的 N32 预乘透明表面
2. 使用 `pathPaint` 将 `path` 绘制到表面
3. 将栅格化结果作为图像绘制到主画布

该方法是可视化栅格化效果的核心,它捕获了 Skia 实际光栅化器产生的像素数据。

### 抽象接口(子类必须实现)

```cpp
virtual void drawUnderGrid(SkCanvas* canvas) = 0
```

绘制网格下层的内容,通常是需要检查栅格化效果的图形。这些内容会被像素网格覆盖,方便观察单个像素的着色情况。

```cpp
virtual void drawOverGrid(SkCanvas* canvas) = 0
```

绘制网格上层的覆盖内容,通常是:
- 理想的矢量路径(用于对比栅格化结果)
- 交互控制点(用于编辑路径)
- 参考线或标注

### 可选交互回调

```cpp
virtual void handleClick(const ScaledClick* click)
```

处理点击事件,默认实现为空。子类可重写此方法实现交互功能,如拖拽控制点。`ScaledClick` 对象已经包含了转换后的逻辑坐标。

### ScaledClick 方法

```cpp
SkPoint currScaled() const
```

返回当前点击位置的逻辑坐标(未缩放空间)。例如,如果屏幕坐标是 (128, 96),缩放倍数是 32,则返回 (4, 3)。

## 内部实现细节

### 渲染流程

`draw()` 方法定义了三层渲染架构:

```cpp
void draw(SkCanvas* canvas) override {
    canvas->scale(fScale, fScale);  // 应用缩放变换
    canvas->clear(SK_ColorWHITE);   // 白色背景

    this->drawUnderGrid(canvas);    // 层1: 栅格化内容
    this->drawGrid(canvas);         // 层2: 像素网格
    this->drawOverGrid(canvas);     // 层3: 矢量覆盖层
}
```

通过先缩放画布,所有后续绘制操作都自动按比例放大,简化了子类实现。

### 网格绘制实现

```cpp
void drawGrid(SkCanvas* canvas) {
    SkPaint gridPaint;
    gridPaint.setColor(SK_ColorDKGRAY);
    gridPaint.setStyle(SkPaint::Style::kStroke_Style);
    gridPaint.setStrokeWidth(0);  // 0表示hairline(设备像素级细线)

    for (int y = 0; y <= (int)fHeight; ++y) {
        canvas->drawLine(0, y, fWidth, y, gridPaint);  // 水平线
    }
    for (int x = 0; x <= (int)fWidth; ++x) {
        canvas->drawLine(x, 0, x, fHeight, gridPaint);  // 垂直线
    }
}
```

关键设计:
- **Hairline 笔触**: `setStrokeWidth(0)` 确保线条始终为 1 个设备像素宽,无论缩放级别如何
- **深灰色**: 使用 `SK_ColorDKGRAY` 提供足够对比度,但不会过于突兀
- **完整覆盖**: 绘制 `fWidth+1` 和 `fHeight+1` 条线,确保边界像素也有网格线

### 点击处理机制

```cpp
Click* onFindClickHandler(SkScalar x, SkScalar y, skui::ModifierKey modifiers) override {
    // 仅在按下 Ctrl 键时激活,避免干扰 Viewer 的默认平移操作
    if (modifiers != skui::ModifierKey::kControl) {
        return nullptr;
    }
    return new ScaledClick(fScale);
}

bool onClick(ClickHandlerSlide::Click* click) override {
    auto myClick = static_cast<ScaledClick*>(click);
    this->handleClick(myClick);  // 委托给子类处理
    return true;
}
```

设计考量:
- **条件激活**: 需要按住 Ctrl 键才能触发点击,避免与 Viewer 的全局手势冲突
- **类型安全转换**: 使用 `static_cast` 将基类 Click 指针转换为 ScaledClick 指针
- **委托模式**: 将具体交互逻辑委托给虚函数 `handleClick()`,保持灵活性

### 示例实现分析

`ZoomInSlideDemo` 展示了典型使用模式:

**路径构造**:
```cpp
SkPath makePath() {
    return SkPathBuilder()
        .moveTo(fPts[0])
        .lineTo(fPts[1])
        .lineTo(fPts[2])
        .lineTo(fPts[3])
        .close()
        .detach();
}
```

根据四个控制点构造闭合四边形路径。

**栅格化可视化**:
```cpp
void drawUnderGrid(SkCanvas* canvas) override {
    SkPaint paint;
    paint.setStyle(SkPaint::kStroke_Style);
    paint.setStrokeCap(SkPaint::kSquare_Cap);
    paint.setStrokeJoin(SkPaint::kMiter_Join);
    paint.setAntiAlias(true);  // 启用抗锯齿

    this->drawScaledPath(canvas, makePath(), paint);
}
```

使用方形笔帽和斜接连接绘制路径,展示实际栅格化效果。

**矢量参考和控制点**:
```cpp
void drawOverGrid(SkCanvas* canvas) override {
    // 绘制红色理想路径
    SkPaint truthPaint;
    truthPaint.setStyle(SkPaint::Style::kStroke_Style);
    truthPaint.setColor(SK_ColorRED);
    truthPaint.setStrokeWidth(2.f / fScale);  // 缩放后2像素宽
    canvas->drawPath(makePath(), truthPaint);

    // 绘制橙色控制点
    SkPaint handlePaint;
    handlePaint.setColor(SkColorSetARGB(255, 255, 70, 10));
    for (auto pt : fPts) {
        canvas->drawCircle(pt, kHandleRadius / kScale, handlePaint);
    }
}
```

红色矢量路径与栅格化结果对比,橙色圆点标记可拖拽的控制点。

**交互拖拽**:
```cpp
void handleClick(const ScaledClick* click) override {
    SkPoint pt = click->currScaled();

    // 找到最近的控制点
    int closestPointIdx = 0;
    float minDist = SkPoint::Distance(pt, fPts[0]);
    for (int i = 1; i < kNumPoints; i++) {
        float dist = SkPoint::Distance(pt, fPts[i]);
        if (dist < minDist) {
            minDist = dist;
            closestPointIdx = i;
        }
    }

    // 移动该控制点到点击位置
    fPts[closestPointIdx] = pt;
}
```

实现简单的最近邻点拖拽,允许实时调整路径形状。

## 依赖关系

### 直接依赖

- **include/core/SkCanvas.h**: 画布绘制接口,所有渲染操作的基础
- **include/core/SkSurface.h**: 离屏表面创建(`SkSurfaces::Raster`)
- **include/core/SkImage.h**: 图像对象,用于从表面生成快照
- **include/core/SkPath.h**: 路径对象,被可视化的主要内容
- **include/core/SkPaint.h**: 绘制样式,控制颜色、笔触等属性
- **include/core/SkImageInfo.h**: 图像格式描述(`MakeN32Premul`)
- **tools/viewer/ClickHandlerSlide.h**: 点击处理基类
- **tools/viewer/Slide.h**: 幻灯片基础接口

### 示例实现额外依赖

- **include/core/SkPathBuilder.h**: 便捷路径构造工具
- **include/core/SkPoint.h**: 点和距离计算

### 数据流向

```
[子类控制点数据]
    -> makePath() 构造 SkPath
    -> drawScaledPath() 栅格化到小表面
    -> SkSurface 生成 SkImage
    -> SkCanvas 绘制放大图像
    -> 屏幕显示
```

用户交互流程:
```
[鼠标点击]
    -> onFindClickHandler() 检查 Ctrl 键
    -> 创建 ScaledClick 对象
    -> onClick() 调用 handleClick()
    -> 子类更新控制点
    -> 触发重绘
```

## 设计模式与设计决策

### 模板方法模式

`ZoomInSlide` 使用模板方法模式定义渲染流程:

```cpp
void draw(SkCanvas* canvas) override {  // 模板方法
    canvas->scale(fScale, fScale);
    canvas->clear(SK_ColorWHITE);

    this->drawUnderGrid(canvas);  // 钩子方法1
    this->drawGrid(canvas);       // 固定步骤
    this->drawOverGrid(canvas);   // 钩子方法2
}
```

- **固定流程**: 缩放、清空、三层渲染的顺序不可改变
- **灵活扩展**: 子类通过重写钩子方法定制内容
- **代码复用**: 网格绘制逻辑在基类中实现,所有子类共享

### 坐标空间分离

设计明确区分两个坐标空间:

1. **逻辑空间**: `fWidth x fHeight` 的小表面空间,表示实际像素坐标
2. **显示空间**: 放大 `fScale` 倍后的屏幕空间

`ScaledClick` 类封装了坐标转换,子类无需关心缩放细节。这种设计使得子类代码更简洁,避免了到处出现的除法运算。

### 声明式配置

通过构造函数参数声明式地配置缩放行为:

```cpp
ZoomInSlideDemo() : ZoomInSlide(kScale, kMaskWidth, kMaskHeight, SkString("ZoomInDemo"))
```

所有关键参数在初始化时确定,运行时行为清晰可预测。

### 条件交互激活

使用修饰键控制交互激活:

```cpp
if (modifiers != skui::ModifierKey::kControl) {
    return nullptr;  // 不激活自定义交互
}
```

这避免了与 Viewer 全局手势(如平移、缩放)的冲突,是多层交互系统中的常见模式。

### 可视化对比策略

通过颜色编码传达信息:
- **栅格化结果**: 黑色像素(drawUnderGrid)
- **理想矢量路径**: 红色线条(drawOverGrid)
- **像素网格**: 深灰色线条(drawGrid)
- **控制点**: 橙色圆点(drawOverGrid)

这种视觉分层使用户可以直观地对比理想路径与实际栅格化结果,快速识别抗锯齿边界和像素覆盖。

## 性能考量

### 离屏渲染开销

每帧都调用 `drawScaledPath()` 创建临时表面:

```cpp
auto surface = SkSurfaces::Raster(ii);
```

**性能影响**:
- 对于小表面(如 20x30 像素),创建开销可忽略
- 栅格化操作是轻量级的,因为像素数量很少
- 没有使用缓存,因为内容通常是动态的(交互式调整)

**优化可能性**:
- 如果内容静态,可在成员变量中缓存 `SkImage`
- 但对于调试工具,实时性比性能更重要

### 网格绘制效率

绘制网格线的时间复杂度为 O(width + height):

```cpp
for (int y = 0; y <= (int)fHeight; ++y) {
    canvas->drawLine(...);
}
for (int x = 0; x <= (int)fWidth; ++x) {
    canvas->drawLine(...);
}
```

对于 20x30 的表面,只需绘制 51 条线,开销极小。使用 hairline 笔触进一步降低了绘制成本。

### 缩放变换优势

在画布级别应用缩放:

```cpp
canvas->scale(fScale, fScale);
```

**优势**:
- 所有后续绘制操作自动缩放,无需子类手动计算
- 利用 Skia 的变换管道,硬件加速可用时性能更好
- 代码简洁,减少浮点运算错误

### 内存占用分析

主要内存消耗:
- 离屏表面: `width * height * 4` 字节(N32 格式)
  - 示例: 20 * 30 * 4 = 2400 字节
- 图像快照: 相同大小,但可能共享数据
- 控制点数组: `4 * 2 * sizeof(float)` = 32 字节

总内存占用约 5KB,完全可以忽略。

### 实时交互性能

点击处理使用简单的线性搜索:

```cpp
for (int i = 1; i < kNumPoints; i++) {
    float dist = SkPoint::Distance(pt, fPts[i]);
    if (dist < minDist) {
        minDist = dist;
        closestPointIdx = i;
    }
}
```

对于 4 个点,3 次比较,开销不可测量。即使扩展到数十个点,线性搜索仍然足够快。

## 相关文件

### 框架基类

- **tools/viewer/Slide.h**: Viewer 幻灯片基类,定义 `draw()`、`load()`、`unload()` 等接口
- **tools/viewer/ClickHandlerSlide.h**: 点击处理增强基类,提供 `Click` 嵌套类和点击事件钩子

### Skia 核心图形类

- **include/core/SkCanvas.h**: 2D 绘图上下文,所有绘制操作的入口
- **include/core/SkSurface.h**: 离屏渲染表面,提供 `SkSurfaces::Raster()` 工厂方法
- **include/core/SkPath.h**: 矢量路径表示,支持线、曲线、填充规则等
- **include/core/SkPaint.h**: 绘制属性集合,控制颜色、抗锯齿、笔触等
- **include/core/SkPathBuilder.h**: 便捷路径构造工具,提供流式 API

### 使用场景

该工具在以下场景中特别有用:

1. **调试抗锯齿问题**: 可视化边缘像素的 alpha 混合效果
2. **验证栅格化算法**: 对比预期路径与实际像素结果
3. **复现渲染 bug**: 如示例中复现的 issues.skia.org/issues/451536363
4. **理解亚像素定位**: 观察 0.5 像素偏移对渲染的影响
5. **教学演示**: 向新手展示矢量图形如何转换为像素

典型工作流程:
1. 创建 `ZoomInSlide` 子类,定义要检查的图形
2. 在 Viewer 中加载该幻灯片
3. 观察栅格化结果与理想路径的差异
4. 通过 Ctrl+点击调整控制点,实时观察变化
5. 识别问题并在 Skia 渲染器中修复

该组件是 Skia 开发者工具箱中的重要诊断工具。
