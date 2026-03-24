# CaptureSlide

> 源文件: tools/viewer/CaptureSlide.h, tools/viewer/CaptureSlide.cpp

## 概述

`CaptureSlide` 是 Skia Viewer 工具中用于播放和检查 SkCapture 文件的专用幻灯片类。SkCapture 是 Skia 的捕获格式,用于记录一系列 SkPicture 对象及其元数据,通常用于捕获应用程序的渲染序列以进行调试、回放和分析。该组件提供了简单的键盘导航接口,允许用户通过 'N'(Next)和 'P'(Previous)键在捕获的图片序列中前后切换。

该类封装了 `SkCapture` 的加载和播放逻辑,专注于提供用户友好的检查界面。它从文件加载捕获数据,提取元数据(如图片总数),并支持逐帧查看每个 SkPicture 的渲染结果。通过裁剪到图片的边界框,确保每个图片的显示区域正确,避免相邻帧的渲染内容干扰。

## 架构位置

`CaptureSlide` 位于 Skia 项目的 `tools/viewer` 目录下,属于开发工具层:

```
Slide (基础幻灯片接口)
  └─> CaptureSlide (SkCapture 播放器)
```

依赖的核心模块:
- **src/capture/SkCapture.h**: SkCapture 格式加载和管理
- **include/core/SkPicture.h**: SkPicture 绘制接口
- **tools/viewer/Slide.h**: 幻灯片基类

## 主要类与结构体

### CaptureSlide

```cpp
class CaptureSlide : public Slide {
public:
    CaptureSlide(const SkString& name, const SkString& path);
    ~CaptureSlide() override;

    SkISize getDimensions() const override;
    void draw(SkCanvas* canvas) override;
    bool animate(double) override;
    void load(SkScalar winWidth, SkScalar winHeight) override;
    void unload() override;
    bool onChar(SkUnichar) override;

private:
    sk_sp<SkCapture> fCapture;          // 捕获对象
    int fCurrentPictureIndex;           // 当前图片索引
    bool fInvalidate;                   // 重绘标志
    SkCapture::Metadata fMetadata;      // 元数据(包含图片总数)
};
```

**关键成员变量**:
- `fCapture`: 智能指针,管理捕获数据的生命周期
- `fCurrentPictureIndex`: 当前显示的图片索引,初始为 0
- `fInvalidate`: 标记是否需要重绘,用于键盘导航后触发更新
- `fMetadata`: 包含捕获文件的元数据,主要使用 `numPictures` 字段

## 公共 API 函数

### 构造函数

```cpp
CaptureSlide::CaptureSlide(const SkString& name, const SkString& path)
```

从文件路径加载捕获:
```cpp
auto data = SkData::MakeFromFileName(path.c_str());
fCapture = SkCapture::MakeFromData(data);
if (fCapture) {
    fMetadata = fCapture->getMetadata();
} else {
    SkDebugf("Couldn't load capture %s", path.c_str());
}
```

在构造时立即加载数据,而非延迟到 `load()` 阶段。

### 渲染

```cpp
void draw(SkCanvas* canvas) override
```

绘制当前图片:
```cpp
if (fCapture) {
    auto focusPicture = fCapture->getPicture(fCurrentPictureIndex);
    auto bounds = focusPicture->cullRect().roundOut();
    canvas->clipIRect(bounds, SkClipOp::kIntersect);
    canvas->drawPicture(fCapture->getPicture(fCurrentPictureIndex));
}
```

裁剪到图片的剔除矩形(cull rect),确保不绘制超出边界的内容。

### 动画

```cpp
bool animate(double) override
```

检查并清除重绘标志:
```cpp
if (fInvalidate) {
    fInvalidate = false;
    return true;
}
return fInvalidate;  // 始终返回 false(已清除)
```

### 键盘事件

```cpp
bool onChar(SkUnichar c) override
```

处理导航键:
```cpp
switch (c) {
case 'N':  // Next
    fCurrentPictureIndex = (fCurrentPictureIndex + 1) % fMetadata.numPictures;
    fInvalidate = true;
    return true;
case 'P':  // Previous
    fCurrentPictureIndex = (fCurrentPictureIndex + fMetadata.numPictures - 1)
                           % fMetadata.numPictures;
    fInvalidate = true;
    return true;
}
```

使用模运算实现循环导航。

### 生命周期

```cpp
void load(SkScalar, SkScalar) override
```

空实现,加载在构造函数中完成。

```cpp
void unload() override
```

释放捕获对象:
```cpp
fCapture.reset(nullptr);
```

```cpp
SkISize getDimensions() const override
```

返回 {0, 0},表示使用默认尺寸。

## 内部实现细节

### 循环导航

前进和后退都使用模运算确保索引在有效范围内:
```cpp
// 前进
index = (index + 1) % total

// 后退(避免负数)
index = (index + total - 1) % total
```

### 裁剪策略

通过裁剪确保每个图片独立显示:
```cpp
auto bounds = focusPicture->cullRect().roundOut();
canvas->clipIRect(bounds, SkClipOp::kIntersect);
```

`cullRect()` 是 SkPicture 的边界矩形,`roundOut()` 向外取整到像素边界。

### 重绘触发

使用 `fInvalidate` 标志而非直接返回 true:
```cpp
bool animate(double) {
    if (fInvalidate) {
        fInvalidate = false;
        return true;  // 触发一次重绘
    }
    return false;  // 后续不重绘
}
```

这确保键盘导航后仅重绘一帧,避免持续刷新浪费资源。

## 依赖关系

### 直接依赖

- **src/capture/SkCapture.h**: 捕获格式支持
  - `SkCapture::MakeFromData()`: 从数据创建捕获对象
  - `getPicture()`: 提取指定索引的图片
  - `getMetadata()`: 获取元数据
- **include/core/SkPicture.h**: SkPicture 绘制
- **include/core/SkData.h**: 文件数据加载
- **tools/viewer/Slide.h**: 幻灯片基类

## 设计模式与设计决策

### 立即加载模式

不同于其他幻灯片,`CaptureSlide` 在构造函数中加载数据:
```cpp
CaptureSlide::CaptureSlide(...) {
    auto data = SkData::MakeFromFileName(path.c_str());
    fCapture = SkCapture::MakeFromData(data);
}
```

这简化了错误处理,但可能增加启动时间。

### 单次重绘优化

使用 `fInvalidate` 标志实现单次重绘:
```cpp
fInvalidate = true;  // 在 onChar 中设置
return fInvalidate;  // 在 animate 中返回并清除
```

避免静态内容持续刷新。

### 容错设计

加载失败时打印调试信息,但不崩溃:
```cpp
if (!fCapture) {
    SkDebugf("Couldn't load capture %s", path.c_str());
}

// draw() 中检查
if (fCapture) {
    // 绘制...
}
```

## 性能考量

### 按需获取图片

每次 `draw()` 都调用 `getPicture()`:
```cpp
auto focusPicture = fCapture->getPicture(fCurrentPictureIndex);
```

`SkCapture` 内部可能缓存图片,避免重复解析开销。

### 裁剪优化

裁剪到图片边界减少绘制区域:
```cpp
canvas->clipIRect(bounds, SkClipOp::kIntersect);
```

GPU 可以跳过裁剪区域外的像素,提升性能。

### 静态内容

除非用户按键,否则不触发重绘:
```cpp
bool animate(double) {
    return fInvalidate;  // 通常为 false
}
```

降低 CPU 和 GPU 负载。

## 相关文件

### 核心依赖

- **src/capture/SkCapture.h**: 捕获格式接口
- **src/capture/SkCapture.cpp**: 捕获格式实现
- **include/core/SkPicture.h**: SkPicture 定义

### Viewer 框架

- **tools/viewer/Slide.h**: 幻灯片基类
- **tools/viewer/Viewer.h**: Viewer 主应用

### 使用场景

该组件用于:
1. **调试捕获数据**: 检查捕获文件的内容是否正确
2. **逐帧分析**: 查看渲染序列的每一帧
3. **回归测试**: 对比不同版本的捕获输出
4. **问题复现**: 加载用户提供的捕获文件定位问题

典型工作流程:
1. 使用 Skia 捕获工具生成捕获文件
2. 在 Viewer 中加载 CaptureSlide 并指定文件路径
3. 按 'N' 和 'P' 键浏览图片序列
4. 观察每帧的渲染结果,查找异常

该组件是 Skia 捕获系统的可视化工具,简化了捕获数据的检查流程。
