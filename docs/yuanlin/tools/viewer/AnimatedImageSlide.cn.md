# AnimatedImageSlide

> 源文件: tools/viewer/AnimatedImageSlide.h, tools/viewer/AnimatedImageSlide.cpp

## 概述

`AnimatedImageSlide` 是 Skia Viewer 工具中用于展示和测试动画图像格式的专用幻灯片类。该组件能够加载和播放多帧图像资源(如 GIF、WebP 动画等),自动处理帧时序管理和循环播放。它提供了一个简洁的接口来验证 Skia 的动画图像解码能力,并作为动画图像渲染效果的可视化测试工具。

该类依赖于 Skia 的资源管理模块 `skresources::MultiFrameImageAsset`,能够透明地处理不同格式的多帧图像。它会自动将图像居中显示,添加轮廓框以清晰标识图像边界,并根据图像元数据中指定的持续时间循环播放动画。这使得开发者可以轻松评估 Skia 对各种动画格式的支持质量。

## 架构位置

`AnimatedImageSlide` 位于 Skia 项目的 `tools/viewer` 目录下,属于开发工具层。它继承自 `Slide` 基类,遵循 Viewer 框架的标准幻灯片接口:

```
Slide (基础幻灯片接口)
  └─> AnimatedImageSlide (动画图像展示)
```

该组件在 Skia 工具链中的定位:

- **Viewer 框架**: 作为标准幻灯片类型,集成到 Viewer 工具的幻灯片切换系统中
- **测试工具**: 用于验证动画图像解码器的正确性和性能
- **演示工具**: 可用于展示 Skia 支持的动画图像格式能力
- **资源加载测试**: 测试从资源包和文件系统加载图像的两种路径

依赖的核心模块:
- **modules/skresources/**: 使用 `MultiFrameImageAsset` 进行多帧图像管理
- **include/core/**: 使用基础图形类(SkCanvas, SkImage, SkData 等)
- **tools/Resources.h**: 使用资源加载辅助函数 `GetResourceAsData()`
- **tools/viewer/Slide.h**: 继承幻灯片基类接口

## 主要类与结构体

### AnimatedImageSlide

最终类(final),不可被继承:

```cpp
class AnimatedImageSlide final : public Slide {
public:
    AnimatedImageSlide(const SkString& name, const SkString& path);

    // Slide 接口实现
    void load(SkScalar winWidth, SkScalar winHeight) override;
    void unload() override;
    void draw(SkCanvas*) override;
    bool animate(double nanos) override;

private:
    const SkString fPath;  // 图像文件路径
    sk_sp<skresources::MultiFrameImageAsset> fImageAsset;  // 多帧图像资源
    SkSize fWinSize;  // 窗口尺寸

    double fTimeBase;  // 动画起始时间(纳秒)
    float fFrameMs;    // 当前帧时间(毫秒)
};
```

**关键成员变量**:
- `fPath`: 图像资源路径,可以是资源包中的相对路径或文件系统绝对路径
- `fImageAsset`: 智能指针,管理多帧图像资源的生命周期和帧提取
- `fWinSize`: 窗口尺寸,用于计算图像居中位置
- `fTimeBase`: 动画起始时间戳(纳秒),用于计算相对时间,初始为 0
- `fFrameMs`: 当前显示帧对应的时间(毫秒),循环范围在 [0, duration)

### 使用的外部类型

- **skresources::MultiFrameImageAsset**: 多帧图像资源抽象,提供帧提取和时长查询接口
  - `getFrame(float t)`: 获取时间 t(秒)对应的帧图像
  - `isMultiFrame()`: 判断是否为多帧图像
  - `duration()`: 获取完整动画周期时长(毫秒)
- **SkData**: 原始字节数据容器,用于存储加载的图像文件数据
- **SkImage**: 栅格图像表示,由 `getFrame()` 返回

## 公共 API 函数

### 构造函数

```cpp
AnimatedImageSlide::AnimatedImageSlide(const SkString& name, const SkString& path)
```

初始化动画图像幻灯片:
- `name`: 幻灯片显示名称,在 Viewer 界面中标识该幻灯片
- `path`: 图像文件路径,支持两种格式:
  - 资源包相对路径(如 "images/alphabetAnim.gif")
  - 文件系统绝对路径

**实现细节**:
```cpp
AnimatedImageSlide::AnimatedImageSlide(const SkString& name, const SkString& path)
    : fPath(path)
{
    fName = name;  // 设置继承自 Slide 的名称成员
}
```

注意构造函数仅存储路径,实际加载发生在 `load()` 阶段。

### 生命周期管理

```cpp
void load(SkScalar winWidth, SkScalar winHeight) override
```

加载图像资源并初始化显示参数:

```cpp
void AnimatedImageSlide::load(SkScalar w, SkScalar h) {
    fWinSize = {w, h};  // 保存窗口尺寸

    // 尝试两种加载路径
    sk_sp<SkData> data = GetResourceAsData(fPath.c_str());  // 优先从资源包加载
    if (!data) {
        data = SkData::MakeFromFileName(fPath.c_str());  // 回退到文件系统
    }

    fImageAsset = skresources::MultiFrameImageAsset::Make(std::move(data));
}
```

**加载策略**:
1. 首先尝试从资源包(resources/)加载,适用于内置测试资源
2. 如果失败,尝试从文件系统加载,支持用户指定的任意路径
3. 使用智能指针 `sk_sp` 管理数据和资源生命周期

```cpp
void unload() override
```

清理资源并重置状态:

```cpp
void AnimatedImageSlide::unload() {
    fImageAsset.reset();  // 释放图像资源
    fTimeBase = 0;        // 重置时间基准
}
```

确保切换到其他幻灯片时释放内存,下次重新加载时从头播放。

### 渲染与动画

```cpp
void draw(SkCanvas* canvas) override
```

绘制当前帧到画布:

```cpp
void AnimatedImageSlide::draw(SkCanvas* canvas) {
    if (!fImageAsset) {
        return;  // 未加载图像时跳过
    }

    sk_sp<SkImage> frame = fImageAsset->getFrame(fFrameMs * 0.001f);  // 转换为秒

    SkAutoCanvasRestore acr(canvas, true);  // 自动保存/恢复画布状态
    canvas->translate((fWinSize.width() - frame->width()) / 2,
                      (fWinSize.height() - frame->height()) / 2);  // 居中

    // 绘制轮廓框
    SkPaint outline_paint;
    outline_paint.setAntiAlias(true);
    outline_paint.setColor(0x80000000);  // 半透明黑色
    outline_paint.setStyle(SkPaint::kStroke_Style);

    const SkRect outline = SkRect::Make(frame->bounds()).makeOutset(1, 1);
    canvas->drawRect(outline, outline_paint);

    canvas->drawImage(frame, 0, 0);  // 绘制图像
}
```

**渲染流程**:
1. 获取当前时间对应的帧图像
2. 计算居中平移量
3. 绘制半透明黑色轮廓框(向外扩展1像素)
4. 绘制图像本身

```cpp
bool animate(double nanos) override
```

更新动画状态,计算当前应显示的帧:

```cpp
bool AnimatedImageSlide::animate(double nanos) {
    if (!fImageAsset || !fImageAsset->isMultiFrame()) {
        return false;  // 非多帧图像不需要动画
    }

    if (!fTimeBase) {
        fTimeBase = nanos;  // 首次调用时记录起始时间
    }

    // 计算相对时间并循环到 [0, duration) 范围
    fFrameMs = std::fmod((nanos - fTimeBase) * 0.000001f, fImageAsset->duration());

    return true;  // 需要持续重绘
}
```

**时间管理逻辑**:
- `nanos`: 系统提供的绝对时间戳(纳秒)
- `fTimeBase`: 动画开始时的时间戳(纳秒)
- `(nanos - fTimeBase) * 0.000001f`: 转换为毫秒的相对时间
- `std::fmod(..., duration())`: 模运算实现循环播放

返回 `true` 表示需要持续调用 `animate()` 和重绘,`false` 表示静态内容。

## 内部实现细节

### 双路径加载机制

加载函数实现了容错的两阶段加载:

```cpp
sk_sp<SkData> data = GetResourceAsData(fPath.c_str());
if (!data) {
    data = SkData::MakeFromFileName(fPath.c_str());
}
```

**设计考量**:
- **资源包优先**: 内置测试资源(如 "images/alphabetAnim.gif")存储在资源系统中,通过 `GetResourceAsData()` 访问,无需文件系统路径
- **文件系统回退**: 支持加载用户指定的任意文件,增强灵活性
- **失败容错**: 如果两种方式都失败,`fImageAsset` 将为空,`draw()` 和 `animate()` 会安全地跳过

### 时间计算精度

时间转换涉及多个单位:

1. **输入**: `nanos`(纳秒,int64 精度)
2. **中间**: `(nanos - fTimeBase) * 0.000001f`(毫秒,float 精度)
3. **输出**: `fFrameMs`(毫秒,float)
4. **传递**: `fFrameMs * 0.001f`(秒,传递给 `getFrame()`)

**精度分析**:
- 使用 `float` 存储毫秒级时间对于动画足够(典型帧率 24-60fps,帧间隔 16-40ms)
- `std::fmod` 使用 `double` 精度计算,避免累积误差
- 转换为秒时再次乘以 0.001,保持与 `MultiFrameImageAsset` 接口一致

### 居中对齐算法

计算平移量使图像居中:

```cpp
canvas->translate((fWinSize.width() - frame->width()) / 2,
                  (fWinSize.height() - frame->height()) / 2);
```

- 如果图像小于窗口,计算正平移量
- 如果图像大于窗口,计算负平移量(图像会被裁剪,但中心对齐)

使用 `SkAutoCanvasRestore` 确保变换不影响其他绘制操作。

### 轮廓框绘制细节

```cpp
const SkRect outline = SkRect::Make(frame->bounds()).makeOutset(1, 1);
canvas->drawRect(outline, outline_paint);
```

**设计目的**:
- 清晰标识图像边界,尤其是图像边缘透明或与背景颜色相近时
- `makeOutset(1, 1)` 向外扩展1像素,确保轮廓框完全包围图像
- 半透明黑色(0x80000000)避免过于突兀,同时保持可见性

### 动画循环逻辑

使用模运算实现无缝循环:

```cpp
fFrameMs = std::fmod((nanos - fTimeBase) * 0.000001f, fImageAsset->duration());
```

**关键特性**:
- 自动处理任意长度的动画
- `fmod` 返回范围 [0, duration),确保不会越界
- 无需手动检测循环边界,数学运算自然实现

**示例计算**(假设 duration = 1000ms):
- t = 500ms -> fFrameMs = 500ms
- t = 1500ms -> fFrameMs = 500ms (循环第二次)
- t = 2999ms -> fFrameMs = 999ms

## 依赖关系

### 直接依赖

- **modules/skresources/include/SkResources.h**: 多帧图像资源管理
  - `MultiFrameImageAsset::Make()`: 从数据创建图像资源
  - `MultiFrameImageAsset::getFrame()`: 提取指定时间的帧
  - `MultiFrameImageAsset::duration()`: 获取动画总时长
  - `MultiFrameImageAsset::isMultiFrame()`: 判断是否多帧
- **include/core/SkCanvas.h**: 画布绘制接口
- **include/core/SkData.h**: 原始数据容器
- **include/core/SkImage.h**: 栅格图像对象
- **tools/Resources.h**: 资源加载工具函数 `GetResourceAsData()`
- **tools/viewer/Slide.h**: 幻灯片基类

### 间接依赖

- **include/core/SkString.h**: 字符串类型
- **编解码器**: `MultiFrameImageAsset` 内部依赖 GIF、WebP 等编解码器

### 数据流向

```
[图像文件]
    -> GetResourceAsData() / SkData::MakeFromFileName()
    -> SkData
    -> MultiFrameImageAsset::Make()
    -> MultiFrameImageAsset
    -> getFrame(t)
    -> SkImage
    -> canvas->drawImage()
    -> 屏幕
```

时间流向:
```
[系统时钟 nanos]
    -> animate() 计算 fFrameMs
    -> draw() 查询 getFrame(fFrameMs)
    -> 返回对应帧
```

## 设计模式与设计决策

### 懒加载模式

构造函数不加载图像,延迟到 `load()` 阶段:

```cpp
AnimatedImageSlide::AnimatedImageSlide(const SkString& name, const SkString& path)
    : fPath(path)  // 仅存储路径
{
    fName = name;
}
```

**优势**:
- 允许快速构造大量幻灯片对象(Viewer 启动时)
- 仅在实际显示时才加载资源,节省内存
- 支持窗口尺寸传递(窗口尺寸在构造时可能未知)

### 资源管理最佳实践

使用智能指针自动管理生命周期:

```cpp
sk_sp<skresources::MultiFrameImageAsset> fImageAsset;
```

- `unload()` 中调用 `reset()` 立即释放资源
- 析构时自动清理,无需显式删除
- 防止内存泄漏和悬挂指针

### 容错设计

多处安全检查避免崩溃:

```cpp
if (!fImageAsset) {
    return;  // draw() 中的检查
}

if (!fImageAsset || !fImageAsset->isMultiFrame()) {
    return false;  // animate() 中的检查
}
```

即使加载失败,程序也能安全继续运行。

### 状态初始化策略

`fTimeBase` 使用 0 作为"未初始化"标记:

```cpp
double fTimeBase = 0;  // 类内初始化

if (!fTimeBase) {
    fTimeBase = nanos;  // 首次 animate() 调用时初始化
}
```

这避免了显式的布尔标志,利用 0 的特殊语义简化代码。

### 声明式幻灯片注册

使用宏注册幻灯片到 Viewer:

```cpp
DEF_SLIDE( return new AnimatedImageSlide(SkString("AnimatedImage"),
                                         SkString("images/alphabetAnim.gif")); )
```

这种声明式语法使得添加新幻灯片无需修改 Viewer 的主代码,保持松耦合。

## 性能考量

### 帧提取开销

每次 `draw()` 调用都会请求帧:

```cpp
sk_sp<SkImage> frame = fImageAsset->getFrame(fFrameMs * 0.001f);
```

**性能特性**:
- `MultiFrameImageAsset` 内部实现帧缓存
- 对于相同时间的重复请求,返回缓存的 `SkImage`
- 解码开销仅在切换到新帧时发生

**典型场景**(60fps,24fps 动画):
- 每帧显示约 2.5 次(60/24)
- 缓存命中率高,实际解码频率等于动画帧率,而非屏幕刷新率

### 内存占用

主要内存消耗:
- `fImageAsset`: 存储解码后的帧(取决于格式和实现)
  - GIF: 可能存储完整帧序列或仅当前帧+前一帧
  - WebP: 可能仅存储关键帧,按需解码增量帧
- `SkImage` 帧: N32 格式(4字节/像素)
  - 示例: 640x480 图像 = 1.2MB

**优化策略**:
- `MultiFrameImageAsset` 内部可能限制缓存大小
- 使用智能指针,未引用的帧自动释放
- `unload()` 确保切换幻灯片时释放资源

### 时间计算优化

避免每帧都调用昂贵的时间函数:

```cpp
if (!fTimeBase) {
    fTimeBase = nanos;  // 仅首次调用
}
fFrameMs = std::fmod((nanos - fTimeBase) * 0.000001f, fImageAsset->duration());
```

- 减法和乘法是廉价操作
- `std::fmod` 对于小数值也很快
- 无需查询系统时钟或日期函数

### 绘制性能

居中平移不影响性能:

```cpp
canvas->translate(...);
canvas->drawImage(frame, 0, 0);
```

- 平移变换在 GPU 路径上几乎无开销(更新变换矩阵)
- `drawImage()` 通常是硬件加速的
- 轮廓框是单个矩形,开销可忽略

### 静态图像优化

对于非动画图像,及时返回 false:

```cpp
if (!fImageAsset || !fImageAsset->isMultiFrame()) {
    return false;
}
```

Viewer 接收到 false 后可以降低刷新率或完全停止调用 `animate()`,节省 CPU。

## 相关文件

### 核心依赖文件

- **modules/skresources/include/SkResources.h**: 资源管理模块主头文件
- **modules/skresources/src/SkResources.cpp**: `MultiFrameImageAsset` 实现(推测)
- **tools/Resources.h**: 提供 `GetResourceAsData()` 函数,处理资源包加载
- **tools/Resources.cpp**: 资源加载实现

### 编解码器

- **src/codec/SkGifCodec.h**: GIF 解码器
- **src/codec/SkWebpCodec.h**: WebP 解码器
- **src/codec/SkCodec.h**: 编解码器基类

### Viewer 框架

- **tools/viewer/Slide.h**: 幻灯片基类
- **tools/viewer/Viewer.h**: Viewer 主应用程序
- **tools/viewer/Viewer.cpp**: 幻灯片管理和切换逻辑

### 测试资源

- **resources/images/alphabetAnim.gif**: 默认使用的测试动画(字母表动画)
- **resources/images/**: 其他测试图像资源目录

### 使用场景

该组件在以下场景中特别有用:

1. **编解码器验证**: 测试 GIF、WebP 等格式的解码正确性
2. **性能基准测试**: 评估动画解码和渲染的帧率
3. **视觉回归测试**: 确保动画显示效果符合预期
4. **格式兼容性**: 验证对不同编码参数(交错、透明度等)的支持
5. **内存泄漏检测**: 通过反复加载/卸载检测资源管理问题

典型工作流程:
1. 将测试动画放入 `resources/images/` 目录
2. 创建 `AnimatedImageSlide` 实例并指定路径
3. 在 Viewer 中加载该幻灯片
4. 观察动画播放是否流畅和正确
5. 使用 Viewer 的调试工具(FPS 计数器、内存监视等)评估性能

该组件是 Skia 多媒体功能测试套件的重要组成部分。
