# StrokeVerbSlide

> 源文件: tools/viewer/StrokeVerbSlide.cpp

## 概述

`StrokeVerbSlide` 是 Skia Viewer 中用于可视化和测试路径描边的交互式幻灯片。它支持展示不同类型的路径图元(直线、二次曲线、三次曲线、圆锥曲线)的描边效果,用户可以交互式地调整控制点、描边宽度、连接样式和端点样式,用于调试和演示 Skia 的描边渲染能力。

## 架构位置

`StrokeVerbSlide` 位于 `tools/viewer` 目录,作为 Viewer 工具的高级调试幻灯片。它依赖 Ganesh GPU 后端,仅在定义了 `SK_GANESH` 宏时编译。

```
tools/viewer/
├── Slide (基类)
├── ClickHandlerSlide (交互基类)
└── StrokeVerbSlide (描边测试幻灯片)
    ├── 支持的图元类型
    │   ├── kTriangles (三角形)
    │   ├── kQuadratics (二次曲线)
    │   ├── kCubics (三次曲线)
    │   └── kConics (圆锥曲线)
    └── 交互控制
        ├── 控制点拖动
        ├── 描边宽度调整
        ├── 连接样式切换
        └── 端点样式切换
```

## 主要类与结构体

### VerbType 枚举

```cpp
enum class VerbType {
    kTriangles,   // 三角形(两条直线)
    kQuadratics,  // 二次贝塞尔曲线
    kCubics,      // 三次贝塞尔曲线
    kConics       // 圆锥曲线
};
```

### StrokeVerbSlide 类

```cpp
class StrokeVerbSlide : public ClickHandlerSlide {
public:
    StrokeVerbSlide() { fName = "StrokeVerb"; }

    void load(SkScalar w, SkScalar h) override;
    void draw(SkCanvas*) override;
    bool onChar(SkUnichar) override;

protected:
    class Click;
    ClickHandlerSlide::Click* onFindClickHandler(SkScalar x, SkScalar y,
                                                 skui::ModifierKey) override;
    bool onClick(ClickHandlerSlide::Click*) override;

private:
    void updateAndInval();
    void updatePath();

    VerbType fVerbType = VerbType::kCubics;
    SkPoint fPoints[4] = {
        {100.05f, 100.05f}, {400.75f, 100.05f},
        {400.75f, 300.95f}, {100.05f, 300.95f}
    };
    float fConicWeight = 0.5f;
    float fStrokeWidth = 40;
    SkPaint::Join fStrokeJoin = SkPaint::kMiter_Join;
    SkPaint::Cap fStrokeCap = SkPaint::kButt_Cap;
    SkPath fPath;
};
```

### Click 嵌套类

```cpp
class StrokeVerbSlide::Click : public ClickHandlerSlide::Click {
public:
    Click(int ptIdx) : fPtIdx(ptIdx) {}
    void doClick(SkPoint points[]);
private:
    int fPtIdx;  // -1表示移动所有点,否则移动特定点
};
```

## 公共 API 函数

### 生命周期函数

**void load(SkScalar w, SkScalar h)**
- 初始化路径,调用 `updatePath()`

**void draw(SkCanvas* canvas)**
- 清空画布为黑色
- 绘制描边路径(灰色)
- 绘制控制点(蓝色圆点)
- 显示信息文本(类型、权重、描边宽度)

### 交互处理

**ClickHandlerSlide::Click* onFindClickHandler(SkScalar x, SkScalar y, skui::ModifierKey)**
- 检测点击位置是否靠近控制点(20像素容差)
- 返回 `Click` 对象,包含点击的控制点索引
- 如果未击中控制点,返回移动所有点的 Click 对象

**bool onClick(ClickHandlerSlide::Click* click)**
- 根据拖动偏移更新控制点位置
- 调用 `updateAndInval()` 刷新显示

**bool onChar(SkUnichar unichar)**
- 处理键盘输入,支持以下操作:
  - `'1'` - `'4'`: 切换图元类型
  - `'+'`: 描边宽度或圆锥权重 × 2
  - `'='`: 描边宽度或圆锥权重 × 5/4
  - `'-'`: 描边宽度或圆锥权重 × 4/5
  - `'_'`: 描边宽度或圆锥权重 × 0.5
  - `'D'`: 打印当前控制点坐标(调试用)
  - `'J'`: 循环切换连接样式(Miter/Round/Bevel)
  - `'C'`: 循环切换端点样式(Butt/Round/Square)

### 内部函数

**void updatePath()**
- 根据当前图元类型和控制点重新构建路径
- 使用 `SkPathBuilder` 构建路径

**void updateAndInval()**
- 调用 `updatePath()` 更新路径

## 内部实现细节

### 路径构建逻辑

根据 `fVerbType` 构建不同类型的路径:

```cpp
void StrokeVerbSlide::updatePath() {
    SkPathBuilder builder;
    builder.moveTo(fPoints[0]);
    switch (fVerbType) {
        case VerbType::kCubics:
            builder.cubicTo(fPoints[1], fPoints[2], fPoints[3]);
            break;
        case VerbType::kQuadratics:
            builder.quadTo(fPoints[1], fPoints[3]);
            break;
        case VerbType::kConics:
            builder.conicTo(fPoints[1], fPoints[3], fConicWeight);
            break;
        case VerbType::kTriangles:
            builder.lineTo(fPoints[1]);
            builder.lineTo(fPoints[3]);
            builder.close();
            break;
    }
    fPath = builder.detach();
}
```

### 绘制细节

1. **描边路径绘制**:
   - 颜色: 0xff808080 (灰色)
   - 样式: kStroke_Style
   - 使用当前描边宽度、连接样式和端点样式
   - 启用抗锯齿

2. **控制点绘制**:
   - 颜色: SK_ColorBLUE
   - 大小: 8 像素
   - 三次曲线显示 4 个点,其他类型显示 2 个点和第 4 个点

3. **信息文本**:
   - 字体大小: 20
   - 显示内容:
     - 图元类型名称
     - 三次曲线显示分类 (`SkClassifyCubic`)
     - 圆锥曲线显示权重
     - 描边宽度

### 控制点布局

默认控制点位置精心选择,包含亚像素偏移(0.05, 0.75)用于测试亚像素渲染:
- P0: (100.05, 100.05) - 起点
- P1: (400.75, 100.05) - 控制点1
- P2: (400.75, 300.95) - 控制点2
- P3: (100.05, 300.95) - 终点

## 依赖关系

### 直接依赖

- **Skia 核心**: `SkCanvas`, `SkPaint`, `SkPath`, `SkPathBuilder`, `SkFont`
- **几何工具**: `SkGeometry` (用于 `SkClassifyCubic` 分类三次曲线)
- **字体工具**: `FontToolUtils` (默认字体)
- **交互基类**: `ClickHandlerSlide`

### 条件依赖

- 仅在 `SK_GANESH` 定义时编译
- 需要 Ganesh GPU 后端支持

## 设计模式与设计决策

### 设计模式

1. **State Pattern**: 通过 `VerbType` 枚举表示不同的路径类型状态
2. **Command Pattern**: 键盘输入映射到不同的操作命令
3. **Builder Pattern**: 使用 `SkPathBuilder` 构建路径对象

### 设计决策

1. **交互式调试**: 支持实时拖动控制点,便于观察描边算法在不同几何形状下的表现
2. **亚像素精度**: 使用非整数坐标测试亚像素渲染
3. **多种图元支持**: 覆盖所有常见路径图元,全面测试描边系统
4. **可调参数**: 描边宽度、连接样式、端点样式、圆锥权重均可调节
5. **视觉反馈**: 蓝色控制点、灰色路径、白色文本提供清晰的视觉层次
6. **调试输出**: 'D' 键打印坐标,方便复现特定配置

## 性能考量

1. **实时更新**: 每次交互后重新构建路径,开销可忽略(路径复杂度低)
2. **描边渲染**: 性能取决于描边宽度和路径复杂度,是测试的重点
3. **GPU 加速**: 依赖 Ganesh 后端,利用 GPU 加速描边光栅化
4. **控制点检测**: 简单的距离计算,O(4) 时间复杂度
5. **文本渲染**: 每帧格式化字符串有轻微开销

## 相关文件

- **tools/viewer/ClickHandlerSlide.h**: 交互式幻灯片基类
- **src/core/SkGeometry.h**: 几何工具,包括 `SkClassifyCubic`
- **tools/fonts/FontToolUtils.h**: 字体工具
- **include/core/SkPathBuilder.h**: 路径构建器
- **include/core/SkPaint.h**: 绘制样式定义(Join/Cap枚举)
