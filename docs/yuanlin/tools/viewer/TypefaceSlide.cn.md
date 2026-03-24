# TypefaceSlide

## 类名
`TypefaceSlide`

## 源文件
- `tools/viewer/TypefaceSlide.cpp`

## 概述
`TypefaceSlide` 是 Skia Viewer 工具中用于展示和检查字体(Typeface)的交互式演示类。该类继承自 `Slide` 基类,提供了一个功能丰富的字体查看器,支持可变字体(Variable Fonts)的实时调整、字形(Glyph)的详细检查、字形路径的可视化以及字形度量信息的显示。用户可以通过控件面板动态调整字体的变体参数、字号、起始字形ID等属性,并可以可视化字形的轮廓方向、轮廓编号、字形边界框和前进宽度等重要信息。

这个工具主要用于字体开发者和 Skia 引擎开发者测试和调试字体渲染功能,特别是在处理可变字体、复杂字形和字体度量时。

## 架构位置
该类位于 Skia 的工具层(`tools/viewer/`)中,是 Viewer 应用程序的一个 Slide 组件。其在架构中的位置:

```
Skia Graphics Library
└── tools/                      # 工具和测试代码
    └── viewer/                 # Viewer 应用程序
        ├── Slide.h             # Slide 基类接口
        └── TypefaceSlide.cpp   # 字体查看器实现
```

`TypefaceSlide` 使用了 Skia 的核心字体API:
- `SkTypeface` - 字体表示
- `SkFont` - 字体配置和渲染
- `SkFontArguments::VariationPosition` - 可变字体参数
- `SkContourMeasure` - 路径轮廓测量
- 字体工具类 `ToolUtils::VariationSliders`

## 主要类与结构体

### TypefaceSlide 类
```cpp
class TypefaceSlide : public Slide
```

**核心成员变量:**
- `sk_sp<SkTypeface> fBaseTypeface` - 基础字体对象(从Variable.ttf加载)
- `sk_sp<SkTypeface> fCurrentTypeface` - 当前显示的字体(应用变体参数后)
- `ToolUtils::VariationSliders fVariationSliders` - 可变字体参数滑块控制器
- `SkFontArguments::VariationPosition fVariationPosition` - 当前字体变体位置
- `bool fCurrentTypefaceDirty` - 标记字体是否需要重新生成
- `SkScalar fFontSize` - 当前字号(默认80)
- `SkGlyphID fCurrentGlyphID` - 当前显示的起始字形ID
- `bool fOutline` - 是否显示字形轮廓路径
- `bool fOutlineContourNumbers` - 是否显示轮廓编号(替代方向指示器)
- `bool fGlyphNumbers` - 是否在原点显示字形编号
- `bool fDrawGlyphMetrics` - 是否绘制字形度量信息(边界框和前进宽度)
- `SkSize fWindowSize` - 窗口尺寸
- `SkISize fDrawArea` - 实际绘制区域尺寸
- `SkPath fPathDirectionIndicator` - 路径方向指示器图形(小箭头)
- `SkPaint fPathDirectionIndicatorPaint` - 方向指示器绘制样式

### Line 结构体
```cpp
struct Line {
    SkRect bounds;           // 行的边界框
    SkGlyphID firstGlyph;    // 起始字形ID(包含)
    SkGlyphID lastGlyph;     // 结束字形ID(包含)
    int number;              // 行号
}
```
用于在绘制时计算和管理每一行字形的布局信息。

## 公共 API 函数

### 生命周期管理

#### `load(SkScalar w, SkScalar h)`
```cpp
void load(SkScalar w, SkScalar h) override
```
加载 Slide 时的初始化函数:
- 记录窗口尺寸
- 从 `fonts/Variable.ttf` 资源加载可变字体
- 初始化变体参数滑块
- 创建路径方向指示器图形(红色描边三角形箭头)

#### `unload()`
```cpp
void unload() override
```
卸载 Slide 时释放资源,将字体对象指针置空。

#### `resize(SkScalar w, SkScalar h)`
```cpp
void resize(SkScalar w, SkScalar h) override
```
窗口尺寸变化时更新内部记录的窗口尺寸。

### 绘制函数

#### `draw(SkCanvas* canvas)`
```cpp
void draw(SkCanvas* canvas) override
```
主绘制函数,执行以下操作:
1. 如果字体变体参数改变,调用 `updateCurrentTypeface()` 更新字体对象
2. 创建 `SkFont` 对象并应用当前字号
3. 获取字体度量信息(`SkFontMetrics`)
4. 计算并绘制两行字形:
   - 从 `fCurrentGlyphID` 开始,依次排列字形
   - 每行根据窗口宽度自动换行
   - 字形间距为10像素
5. 对每个字形:
   - 可选绘制字形度量(红色边界框、绿色前进宽度框)
   - 绘制字形本身
   - 可选显示字形编号
   - 可选显示字形轮廓和方向指示
6. 更新 `fDrawArea` 记录实际绘制区域

**字形行布局算法:**
- 预测每个字形的绘制边界(包括边界框和前进宽度)
- 当行宽超过窗口宽度时触发换行
- 通过向上偏移确保字形顶部对齐

**轮廓方向可视化:**
使用 `SkContourMeasure` 遍历字形路径的每个轮廓:
- 获取轮廓起始点和切线方向
- 在起始点绘制方向指示器(箭头)或轮廓编号
- 通过矩阵变换使箭头指向轮廓方向

### 控件交互

#### `onGetControls(SkMetaData* controls)`
```cpp
bool onGetControls(SkMetaData* controls) override
```
向 Viewer 控制面板注册可调节的参数:
- `"Size"` - 字号滑块(0-256,当前值)
- `"Glyph"` - 起始字形ID滑块(0-字形总数,当前值)
- `"Glyph Metrics"` - 是否显示字形度量(布尔值)
- `"Glyph numbers"` - 是否显示字形编号(布尔值)
- `"Outline"` - 是否显示轮廓路径(布尔值)
- `"Outline contour numbers"` - 是否显示轮廓编号(布尔值)
- 调用 `fVariationSliders.writeControls()` 注册可变字体轴参数

#### `onSetControls(const SkMetaData& controls)`
```cpp
void onSetControls(const SkMetaData& controls) override
```
从控制面板读取用户调整的参数值并更新内部状态:
- 读取字号,如果改变则清空绘制区域缓存
- 读取起始字形ID,如果改变则清空绘制区域缓存
- 读取各种显示选项布尔值
- 调用 `fVariationSliders.readControls()` 读取变体参数,如果改变则标记 `fCurrentTypefaceDirty`

### 维度查询

#### `getDimensions()`
```cpp
SkISize getDimensions() const override
```
返回 Slide 的内容维度。如果 `fDrawArea` 为空:
- 使用 `SkNoDrawCanvas` (无绘制画布)执行一次绘制来计算维度
- 返回计算得到的 `fDrawArea`
否则直接返回缓存的 `fDrawArea`。

## 内部实现细节

### 字体更新机制

#### `updateCurrentTypeface()`
```cpp
void updateCurrentTypeface()
```
根据变体参数重新生成字体对象:
1. 从 `fVariationSliders` 获取当前坐标数组
2. 构造 `SkFontArguments::VariationPosition`
3. 创建 `SkFontArguments` 并设置变体位置
4. 调用 `fBaseTypeface->makeClone(args)` 生成新的字体实例
5. 清除 `fCurrentTypefaceDirty` 标志

这种延迟更新机制避免了频繁重建字体对象,只在实际绘制前检查并更新。

### 字形测量与布局

绘制函数使用以下API获取字形信息:
```cpp
font.getWidthsBounds({&glyph, 1}, {&advance, 1}, {&glyphBounds, 1}, nullptr);
```
- `advance` - 字形的前进宽度
- `glyphBounds` - 字形的边界框

将边界框和前进宽度合并成完整的绘制边界:
```cpp
SkRect glyphAndAdvanceBounds = glyphBounds;
glyphAndAdvanceBounds.join(advanceBounds);
```

### 轮廓方向指示器

路径方向指示器是一个简单的箭头形状:
```cpp
fPathDirectionIndicator = SkPathBuilder()
    .moveTo(0, -3)
    .lineTo(3, 0)
    .lineTo(0, 3)
    .close()
    .detach();
```

绘制时通过矩阵变换使其沿着轮廓的起始切线方向:
```cpp
SkMatrix matrix;
matrix.setSinCos(tangent.y(), tangent.x(), 0, 0);
matrix.postTranslate(contourStart.x(), contourStart.y());
canvas->concat(matrix);
```

## 依赖关系

### 直接依赖的 Skia 核心模块
- `include/core/SkCanvas.h` - 画布绘制接口
- `include/core/SkFont.h` - 字体渲染配置
- `include/core/SkFontMetrics.h` - 字体度量信息
- `include/core/SkFontMgr.h` - 字体管理器
- `include/core/SkTypeface.h` - 字体对象
- `include/core/SkPath.h` - 路径对象
- `include/core/SkContourMeasure.h` - 路径轮廓测量
- `include/utils/SkNoDrawCanvas.h` - 无绘制画布(用于测量)

### 工具类依赖
- `tools/SkMetaData.h` - 元数据容器(用于控件通信)
- `tools/ToolUtils.h` - 工具函数
- `tools/fonts/FontToolUtils.h` - 字体工具函数
- `tools/viewer/Slide.h` - Slide 基类

### 外部资源
- `fonts/Variable.ttf` - 演示用的可变字体文件

## 设计模式与设计决策

### 1. **Slide 模式**
继承自 `Slide` 基类,遵循 Viewer 应用的插件化架构。每个 Slide 是一个独立的演示单元,通过 `DEF_SLIDE` 宏注册到全局注册表。

### 2. **延迟计算模式**
- `fCurrentTypefaceDirty` 标志实现了字体对象的延迟更新
- `getDimensions()` 在需要时才计算内容尺寸
- 避免不必要的重复计算,提升性能

### 3. **元数据驱动的UI**
使用 `SkMetaData` 容器与 Viewer 的控件系统通信:
- `onGetControls()` 声明可调节参数
- `onSetControls()` 读取用户调整后的值
- 解耦了UI逻辑和渲染逻辑

### 4. **组合优于继承**
使用 `ToolUtils::VariationSliders` 组合对象管理可变字体参数,而不是在类内部重复实现滑块逻辑。

### 5. **资源管理决策**
使用智能指针 `sk_sp<SkTypeface>` 管理字体对象生命周期,确保资源自动释放。

### 6. **可视化调试设计**
提供多种可视化选项(轮廓、度量、编号等),方便开发者理解字体内部结构:
- 红色边界框显示字形实际占用空间
- 绿色框显示排版使用的前进宽度
- 轮廓方向指示器帮助理解路径绕向

## 性能考量

### 1. **绘制区域缓存**
`fDrawArea` 缓存计算结果,避免重复测量。只有在字号或起始字形改变时才清空缓存。

### 2. **有限绘制**
只绘制两行字形,而不是字体的全部字形,避免大字体文件导致的性能问题。

### 3. **条件渲染**
轮廓、度量、编号等信息只在用户启用时才绘制,减少不必要的开销。

### 4. **字体克隆开销**
每次变体参数改变都需要调用 `makeClone()` 生成新字体对象,这可能涉及字体表的重新处理。延迟更新机制减少了不必要的克隆操作。

### 5. **路径获取**
`font.getPath(gid)` 可能需要解析 `glyf` 或 CFF 表,对于复杂字形开销较大。只在 `fOutline` 启用时才执行。

### 6. **SkContourMeasure 开销**
轮廓测量涉及路径的细分和长度计算,对每个轮廓都创建 `SkContourMeasure` 对象可能影响性能,但在演示场景中可接受。

## 相关文件

### Viewer 相关 Slide
- `tools/viewer/Slide.h` - Slide 基类定义
- `tools/viewer/ClickHandlerSlide.h` - 支持点击交互的 Slide 基类
- `tools/viewer/3DSlide.cpp` - 3D 变换演示
- `tools/viewer/SGSlide.cpp` - 场景图演示
- 其他各种 Slide 实现

### 字体相关代码
- `src/core/SkFont.cpp` - 字体渲染实现
- `src/core/SkTypeface.cpp` - 字体对象实现
- `src/core/SkGlyph.cpp` - 字形对象实现
- `src/ports/SkFontMgr_*.cpp` - 各平台字体管理器实现

### 工具类
- `tools/ToolUtils.cpp` - 通用工具函数实现
- `tools/fonts/FontToolUtils.cpp` - 字体工具函数实现
- `tools/SkMetaData.cpp` - 元数据容器实现

### 测试资源
- `resources/fonts/Variable.ttf` - 可变字体测试文件
- `resources/fonts/` - 其他字体测试资源

### 相关文档
- OpenType 可变字体规范(Variable Fonts Specification)
- Skia 字体渲染文档
- Viewer 工具使用文档
