# MSKPSlide

> 源文件: tools/viewer/MSKPSlide.h, tools/viewer/MSKPSlide.cpp

## 概述

`MSKPSlide` 是 Skia Viewer 工具中用于播放和调试 MSKP(Multi-frame Skia Picture)文件的专用幻灯片类。MSKP 是 Skia 的多帧图形记录格式,通常用于捕获 Android 应用的完整渲染序列,包含多个绘制帧和离屏图层。该组件提供了丰富的交互式控制界面,允许开发者逐帧检查渲染内容、调整播放速度、可视化离屏图层、控制背景颜色,并显示帧边界框。

该类依赖于 `MSKPPlayer` 进行实际的 MSKP 解析和播放,自身专注于用户交互和可视化控制。它使用 ImGui 构建了完整的调试界面,支持播放/暂停控制、帧率选择(1/15/30/60/120 FPS 或 1:1 模式)、手动帧导航、离屏图层检查等功能。这使得 MSKP 成为强大的渲染调试和性能分析工具。

## 架构位置

`MSKPSlide` 位于 Skia 项目的 `tools/viewer` 目录下,属于开发工具层。它继承自 `Slide` 基类:

```
Slide (基础幻灯片接口)
  └─> MSKPSlide (MSKP 播放器)
```

该组件在 Skia 工具链中的定位:

- **Viewer 框架**: 集成到 Viewer 工具,作为标准幻灯片类型
- **调试工具**: 用于调试 Android 应用的 Skia 渲染管线
- **性能分析**: 支持离屏图层性能评估和基准测试
- **回归测试**: 用于验证渲染输出的正确性

依赖的核心模块:
- **tools/MSKPPlayer.h**: MSKP 文件解析和播放引擎
- **include/core/**: 使用基础图形类(SkCanvas, SkImage, SkStream 等)
- **imgui.h**: ImGui 界面库,构建所有交互控件
- **tools/viewer/Slide.h**: 继承幻灯片基类接口

## 主要类与结构体

### MSKPSlide

MSKP 播放器幻灯片类:

```cpp
class MSKPSlide : public Slide {
public:
    MSKPSlide(const SkString& name, const SkString& path);
    MSKPSlide(const SkString& name, std::unique_ptr<SkStreamSeekable>);

    // Slide 接口实现
    SkISize getDimensions() const override;
    void draw(SkCanvas* canvas) override;
    bool animate(double nanos) override;
    void load(SkScalar winWidth, SkScalar winHeight) override;
    void unload() override;
    void gpuTeardown() override;

private:
    void redrawLayers();  // 重绘图层

    // 核心数据
    std::unique_ptr<SkStreamSeekable> fStream;
    std::unique_ptr<MSKPPlayer> fPlayer;

    // 播放控制
    int fFrame;           // 当前帧索引
    int fFPS;             // 帧率设置
    bool fPaused;         // 暂停状态
    double fLastFrameTime;  // 上次帧时间戳

    // 可视化控制
    bool fShowFrameBounds;       // 显示帧边界
    float fBackgroundColor[4];   // 背景颜色(RGBA)

    // 图层管理
    std::vector<int> fAllLayerIDs;                // 所有图层 ID
    std::vector<std::vector<int>> fFrameLayerIDs; // 每帧的图层 ID
    std::vector<SkString> fLayerIDStrings;        // 图层 ID 字符串
    int fDrawLayerID;                             // 当前显示图层
    bool fListAllLayers;                          // 列出所有图层或仅当前帧
};
```

**关键成员变量**:
- `fStream`: 可查找流,存储 MSKP 文件数据
- `fPlayer`: MSKP 播放器,处理解析和帧提取
- `fFrame`: 当前显示帧,范围 [0, numFrames-1]
- `fFPS`: 帧率,-1 表示 1:1 模式(每次 animate 前进一帧)
- `fPaused`: 暂停标志
- `fLastFrameTime`: 上次更新时间戳(纳秒),-1 表示需要重新初始化
- `fShowFrameBounds`: 是否绘制红色边界框
- `fBackgroundColor`: RGBA 背景颜色,默认透明黑色 [0,0,0,0](适用于 Android MSKP)
- `fDrawLayerID`: -1 表示显示根图层,>=0 表示显示指定离屏图层
- `fListAllLayers`: true 列出所有图层,false 仅列出当前帧涉及的图层

## 公共 API 函数

### 构造函数

```cpp
MSKPSlide::MSKPSlide(const SkString& name, const SkString& path)
```

从文件路径构造,内部调用 `SkStream::MakeFromFile()` 创建流。

```cpp
MSKPSlide::MSKPSlide(const SkString& name, std::unique_ptr<SkStreamSeekable> stream)
```

从已有流构造,提供更灵活的数据源(如内存流、网络流等)。

### 尺寸查询

```cpp
SkISize getDimensions() const override
```

返回 MSKP 的最大尺寸:
```cpp
return fPlayer ? fPlayer->maxDimensions() : SkISize{0, 0};
```

MSKP 每帧可能有不同尺寸,该方法返回所有帧的最大宽度和最大高度。

### 生命周期管理

```cpp
void load(SkScalar winWidth, SkScalar winHeight) override
```

加载 MSKP 文件并初始化图层信息:
```cpp
fStream->rewind();
fPlayer = MSKPPlayer::Make(fStream.get());
fAllLayerIDs = fPlayer->layerIDs();
fFrameLayerIDs.resize(fPlayer->numFrames());
for (int i = 0; i < fPlayer->numFrames(); ++i) {
    fFrameLayerIDs[i] = fPlayer->layerIDs(i);
}
```

构建所有图层 ID 列表和每帧图层 ID 映射。

```cpp
void unload() override
```

释放播放器资源:
```cpp
fPlayer.reset();
```

```cpp
void gpuTeardown() override
```

GPU 资源清理,重置图层缓存:
```cpp
if (fPlayer) {
    fPlayer->resetLayers();
}
```

### 渲染与动画

```cpp
void draw(SkCanvas* canvas) override
```

绘制当前帧和 ImGui 控制界面,详见实现细节部分。

```cpp
bool animate(double nanos) override
```

更新动画状态,根据 FPS 设置前进帧:
- 如果暂停或未加载,返回 false
- 如果 `fFPS < 0`,每次前进一帧(1:1 模式)
- 否则根据经过时间和帧率计算应前进的帧数

返回 true 表示需要持续重绘。

## 内部实现细节

### ImGui 控制界面

`draw()` 函数构建了复杂的 ImGui 界面:

**播放控制**:
```cpp
if (ImGui::Button(fPaused ? "Play " : "Pause")) {
    fPaused = !fPaused;
    if (fPaused) {
        fLastFrameTime = -1;  // 确保取消暂停时从当前帧开始
    }
}
```

**帧率选择**:
```cpp
ImGui::RadioButton(  "1", &fFPS,    1);
ImGui::RadioButton( "15", &fFPS,   15);
ImGui::RadioButton( "30", &fFPS,   30);
ImGui::RadioButton( "60", &fFPS,   60);
ImGui::RadioButton("120", &fFPS,  120);
ImGui::RadioButton("1:1", &fFPS,   -1);  // 每帧一次
```

**帧导航**:
```cpp
if (ImGui::ArrowButton("-mksp_frame", ImGuiDir_Left)) {
    fFrame = (fFrame + fPlayer->numFrames() - 1) % fPlayer->numFrames();  // 循环后退
}
if (ImGui::SliderInt("##msk_frameslider", &fFrame, 0, fPlayer->numFrames()-1, "% 3d")) {
    fFrame = SkTPin(fFrame, 0, fPlayer->numFrames() - 1);  // 限制范围
}
if (ImGui::ArrowButton("+mskp_frame", ImGuiDir_Right)) {
    fFrame = (fFrame + 1) % fPlayer->numFrames();  // 循环前进
}
if (fFrame != oldFrame) {
    this->redrawLayers();  // 手动调整时强制重绘图层
}
```

**可视化选项**:
```cpp
ImGui::Checkbox("Show Frame Bounds", &fShowFrameBounds);
ImGui::ColorPicker4("background", fBackgroundColor, ImGuiColorEditFlags_AlphaBar);
for (float& component : fBackgroundColor) {
    component = SkTPin(component, 0.f, 1.f);  // 限制 [0,1]
}
```

**离屏图层选择**:
```cpp
ImGui::Checkbox("List All Layers", &fListAllLayers);
ImGui::RadioButton("root", &fDrawLayerID, -1);
const std::vector<int>& layerIDs = fListAllLayers ? fAllLayerIDs : fFrameLayerIDs[fFrame];
for (size_t i = 0; i < layerIDs.size(); ++i) {
    fLayerIDStrings[i] = SkStringPrintf("%d", layerIDs[i]);
    ImGui::RadioButton(fLayerIDStrings[i].c_str(), &fDrawLayerID, layerIDs[i]);
}
```

### 渲染逻辑

绘制根图层或选定图层:

```cpp
auto bounds = SkIRect::MakeSize(fPlayer->frameDimensions(fFrame));

if (fShowFrameBounds) {
    // 绘制红色边界框
    SkPaint boundsPaint;
    boundsPaint.setStyle(SkPaint::kStroke_Style);
    boundsPaint.setColor(SK_ColorRED);
    boundsPaint.setStrokeWidth(0.f);  // hairline
    canvas->drawRect(SkRect::Make(bounds).makeOutset(0.5f, 0.5f), boundsPaint);
}

canvas->save();
if (fDrawLayerID >= 0) {
    bounds = SkIRect::MakeEmpty();  // 裁剪掉根图层
}
canvas->clipIRect(bounds);
canvas->clear(SkColor4f{fBackgroundColor[0], ...});
fPlayer->playFrame(canvas, fFrame);  // 播放当前帧
canvas->restore();

if (fDrawLayerID >= 0) {
    // 绘制选定的离屏图层
    if (sk_sp<SkImage> layerImage = fPlayer->layerSnapshot(fDrawLayerID)) {
        canvas->save();
        canvas->clipIRect(SkIRect::MakeSize(layerImage->dimensions()));
        canvas->clear(...);
        canvas->drawImage(std::move(layerImage), 0, 0);
        canvas->restore();
    }
}
```

**关键设计**:
- 即使显示图层,仍然调用 `playFrame()` 更新所有图层状态
- 通过裁剪区域为空避免绘制根图层内容
- 单独绘制选定图层的快照

### 动画时间管理

```cpp
bool MSKPSlide::animate(double nanos) {
    if (!fPlayer || fPaused) {
        return false;
    }

    if (fLastFrameTime < 0) {
        // 从暂停或 1:1 模式恢复
        fFrame = (fFrame + 1) % fPlayer->numFrames();
        fLastFrameTime = nanos;
        return fPlayer->numFrames() > 1;
    }

    if (fFPS < 0) {
        // 1:1 模式:每次 animate 前进一帧
        fFrame = (fFrame + 1) % fPlayer->numFrames();
        return fPlayer->numFrames() > 1;
    }

    // 稳定帧率模式
    double elapsed = nanos - fLastFrameTime;
    double frameTime = 1E9 / fFPS;  // 纳秒
    int framesToAdvance = elapsed / frameTime;
    fFrame = fFrame + framesToAdvance;

    if (fFrame >= fPlayer->numFrames()) {
        this->redrawLayers();  // 循环时重绘图层
    }
    fFrame %= fPlayer->numFrames();

    // 更新时间基准(不是 += elapsed,而是 += 实际帧数 * 帧时间)
    fLastFrameTime += framesToAdvance * frameTime;

    return framesToAdvance > 0;
}
```

**时间计算策略**:
- 使用 `framesToAdvance * frameTime` 而非 `elapsed` 更新时间基准,避免累积误差
- 允许跳帧:如果系统卡顿,一次可能前进多帧

### 图层管理

```cpp
void MSKPSlide::redrawLayers() {
    if (fDrawLayerID >= 0) {
        // 完全重置图层,确保不会看到后续帧的内容
        fPlayer->resetLayers();
    } else {
        // 仅倒回图层,保留后端存储,用于基准测试
        fPlayer->rewindLayers();
    }
}
```

**设计考量**:
- `resetLayers()`: 释放并重新分配图层存储,用于图层检查模式
- `rewindLayers()`: 保留存储但标记为需要重绘,用于性能测试(避免重复分配开销)

## 依赖关系

### 直接依赖

- **tools/MSKPPlayer.h**: MSKP 播放引擎
  - `MSKPPlayer::Make()`: 从流创建播放器
  - `playFrame()`: 播放指定帧
  - `layerSnapshot()`: 获取图层快照
  - `resetLayers()` / `rewindLayers()`: 图层管理
- **include/core/SkCanvas.h**: 画布绘制接口
- **include/core/SkStream.h**: 流抽象
- **imgui.h**: ImGui 界面库
- **tools/viewer/Slide.h**: 幻灯片基类

### 间接依赖

- **include/core/SkPicture.h**: SkPicture 格式(MSKP 基础)
- **include/private/base/SkTPin.h**: 范围限制工具

### 数据流向

```
[MSKP 文件]
    -> SkStreamSeekable
    -> MSKPPlayer::Make()
    -> MSKPPlayer
    -> playFrame(canvas, frameIdx)
    -> SkCanvas
    -> 屏幕
```

图层流向:
```
[MSKP 图层数据]
    -> MSKPPlayer 内部缓存
    -> layerSnapshot(layerID)
    -> SkImage
    -> canvas->drawImage()
    -> 屏幕
```

## 设计模式与设计决策

### 双构造函数模式

提供路径和流两种构造方式:
```cpp
MSKPSlide::MSKPSlide(const SkString& name, const SkString& path)
    : MSKPSlide(name, SkStream::MakeFromFile(path.c_str())) {}
```

委托构造简化实现,同时支持文件和内存数据源。

### 懒加载与流复用

构造函数仅存储流,`load()` 时才解析:
```cpp
void load(...) {
    fStream->rewind();  // 复用流
    fPlayer = MSKPPlayer::Make(fStream.get());
}
```

支持 reload 场景,无需重新读取文件。

### 状态标记优化

使用 `fLastFrameTime < 0` 作为"需要重新初始化"标记:
```cpp
if (fLastFrameTime < 0) {
    fFrame = (fFrame + 1) % fPlayer->numFrames();
    fLastFrameTime = nanos;
}
```

避免额外的布尔标志,利用非法值表示特殊状态。

### 图层可视化策略

通过裁剪控制根图层显示:
```cpp
if (fDrawLayerID >= 0) {
    bounds = SkIRect::MakeEmpty();  // 空裁剪区域
}
canvas->clipIRect(bounds);
fPlayer->playFrame(canvas, fFrame);  // 仍然调用,更新图层状态
```

确保图层状态正确,即使不显示根内容。

### 循环播放设计

所有帧导航使用模运算:
```cpp
fFrame = (fFrame + 1) % fPlayer->numFrames();
```

自然实现无缝循环,无需边界检查。

## 性能考量

### 帧跳跃机制

允许跳帧保持时间同步:
```cpp
int framesToAdvance = elapsed / frameTime;
fFrame = fFrame + framesToAdvance;
```

如果渲染慢于目标帧率,自动跳过中间帧,避免越来越慢。

### 图层缓存管理

```cpp
void rewindLayers() {
    // 不释放存储,仅标记需要重绘
}
```

对于基准测试,避免重复分配/释放图层内存,更准确测量渲染性能。

### 1:1 模式优化

```cpp
if (fFPS < 0) {
    fFrame = (fFrame + 1) % fPlayer->numFrames();
    return fPlayer->numFrames() > 1;
}
```

跳过所有时间计算,每次 animate 简单前进一帧,适用于手动逐帧检查。

### 背景颜色默认值

```cpp
float fBackgroundColor[4] = {0, 0, 0, 0};  // 透明黑色
```

Android MSKP 通常期望透明背景,默认值避免了大多数情况下的手动调整。

## 相关文件

### 核心依赖文件

- **tools/MSKPPlayer.h**: MSKP 播放器接口
- **tools/MSKPPlayer.cpp**: MSKP 解析和播放实现
- **include/core/SkPicture.h**: SkPicture 格式定义

### Viewer 框架

- **tools/viewer/Slide.h**: 幻灯片基类
- **tools/viewer/Viewer.h**: Viewer 主应用程序

### 界面库

- **imgui.h**: Dear ImGui 库

### 使用场景

该组件在以下场景中特别有用:

1. **Android 渲染调试**: 捕获 Android 应用的 Skia 渲染序列,逐帧分析问题
2. **离屏图层优化**: 可视化哪些内容被渲染到离屏图层,评估性能影响
3. **动画性能分析**: 以不同帧率播放,测量渲染瓶颈
4. **回归测试**: 对比不同 Skia 版本的 MSKP 输出
5. **教学演示**: 展示 Skia 的图层系统和渲染管线

典型工作流程:
1. 使用 Android Skia 工具捕获 MSKP 文件
2. 在 Viewer 中加载 MSKP 幻灯片
3. 逐帧检查渲染内容,查找异常
4. 检查离屏图层,评估图层策略
5. 调整背景颜色,测试透明度处理
6. 使用不同帧率评估性能

该组件是 Skia 生产环境渲染调试的关键工具。
