# ImageSlide

> 源文件: `tools/viewer/ImageSlide.h`, `tools/viewer/ImageSlide.cpp`

## 概述

`ImageSlide` 是 Skia Viewer 工具中用于显示图片文件的幻灯片实现。它支持从文件路径或预加载的图片对象创建幻灯片，并提供延迟加载和可选的图片保留功能。该类使用 Skia 的延迟解码（Deferred Decoding）机制，在绘制时才真正解码图片数据，优化内存使用和加载性能。

主要功能：
- 从文件路径或 `SkImage` 对象创建幻灯片
- 延迟图片加载和解码
- 可选的图片保留模式（不卸载）
- 简单的图片绘制到画布原点

## 架构位置

```
skia/
├── tools/
│   └── viewer/
│       ├── Slide.h                    # 幻灯片基类
│       ├── ImageSlide.h/cpp           # 图片幻灯片实现
│       ├── SKPSlide.h/cpp             # SKP 幻灯片
│       └── Viewer.cpp                 # Viewer 主程序
└── include/
    └── core/
        └── SkImage.h                  # 图片接口
```

## 主要类与结构体

### 类 `ImageSlide`

继承自 `Slide` 基类，实现图片的加载和显示。

#### 公共成员

```cpp
public:
    ImageSlide(const SkString& name, const SkString& path);    // 从文件路径构造
    ImageSlide(const SkString& name, sk_sp<SkImage> image);    // 从图片对象构造
    SkISize getDimensions() const override;                    // 获取图片尺寸
    void draw(SkCanvas* canvas) override;                      // 绘制图片
    void load(SkScalar winWidth, SkScalar winHeight) override; // 加载图片
    void unload() override;                                    // 卸载释放内存
```

#### 私有成员

```cpp
private:
    SkString fPath;                // 文件路径
    sk_sp<SkImage> fImage;         // 图片对象
    bool fRetainImage = false;     // 是否保留图片（不卸载）
```

## 公共 API 函数

### 构造函数

**`ImageSlide(const SkString& name, const SkString& path)`**

从文件路径创建图片幻灯片。

**参数**:
- `name`: 幻灯片显示名称
- `path`: 图片文件路径

**特性**: 延迟加载模式，图片在 `load()` 时才从文件读取。

**`ImageSlide(const SkString& name, sk_sp<SkImage> image)`**

从已有图片对象创建幻灯片。

**参数**:
- `name`: 幻灯片显示名称
- `image`: 图片对象（所有权共享）

**特性**:
- 立即保存图片引用
- 设置 `fRetainImage = true`，确保 `unload()` 不释放图片
- 适用于程序生成或已加载的图片

### 尺寸查询

**`SkISize getDimensions() const`**

返回图片尺寸。

**实现**: `return fImage ? fImage->dimensions() : SkISize::Make(0, 0);`

防御性检查：未加载时返回 (0, 0)。

### 绘制

**`void draw(SkCanvas* canvas)`**

在画布原点绘制图片。

**实现**:
```cpp
SkASSERT(fImage);
canvas->drawImage(fImage, 0, 0);
```

**断言检查**: 假设 `load()` 已成功调用，图片必须存在。

**绘制位置**: 固定在 (0, 0)，由 Viewer 负责缩放和居中。

### 生命周期管理

**`void load(SkScalar winWidth, SkScalar winHeight)`**

加载图片数据。

**实现**:
```cpp
if (fRetainImage) {
    SkASSERT(fImage);  // 预加载模式，图片应已存在
} else {
    sk_sp<SkData> encoded = SkData::MakeFromFileName(fPath.c_str());
    fImage = SkImages::DeferredFromEncodedData(encoded);
}
```

**两种模式**:
1. **保留模式** (`fRetainImage == true`): 无操作，图片已在构造时设置
2. **文件模式** (`fRetainImage == false`):
   - 从文件读取编码数据（PNG、JPEG 等）
   - 创建延迟解码的图片对象
   - 实际像素解码推迟到首次绘制

**延迟解码**: `SkImages::DeferredFromEncodedData` 返回的图片对象仅保存编码数据，在 `drawImage` 调用时才解码像素，节省内存。

**`void unload()`**

卸载图片释放内存。

**实现**:
```cpp
if (!fRetainImage) {
    fImage.reset(nullptr);
}
```

仅在文件模式下释放图片，保留模式保持图片引用。

## 内部实现细节

### 两种构造模式

**文件模式**:
```
构造(path) → 保存路径 → load() → 读取并创建图片 → draw() → 解码并绘制 → unload() → 释放
```

**保留模式**:
```
构造(image) → 保存图片 → load() → 无操作 → draw() → 绘制 → unload() → 保留图片
```

### 延迟解码优化

```cpp
sk_sp<SkData> encoded = SkData::MakeFromFileName(fPath.c_str());
fImage = SkImages::DeferredFromEncodedData(encoded);
```

**优势**:
- **快速加载**: 仅读取文件，不解码像素（约快 10-100 倍）
- **内存节省**: 编码数据通常比像素数据小 5-20 倍
- **按需解码**: 仅解码可见部分（如果支持）

**解码时机**:
```cpp
canvas->drawImage(fImage, 0, 0);  // 此时触发解码
```

首次绘制时，Skia 自动解码并缓存像素。

### 保留标志设计

```cpp
bool fRetainImage = false;
```

**用途**:
- 区分文件路径和图片对象两种构造方式
- 防止卸载外部提供的图片

**示例场景**:
- 程序生成的图片：不应在 `unload()` 时销毁
- 共享的全局图片：多个幻灯片引用同一图片

### 断言策略

```cpp
SkASSERT(fImage);  // draw() 中
SkASSERT(fImage);  // load() 中（保留模式）
```

使用断言而非防御性检查的原因：
- `load()` 必须在 `draw()` 前调用（Slide 基类保证）
- 保留模式的图片必须在构造时提供
- 生产构建中移除断言，避免性能开销

## 依赖关系

### 直接依赖

**Skia 核心**:
- `include/core/SkImage.h`: 图片接口
- `include/core/SkData.h`: 数据容器
- `include/core/SkCanvas.h`: 画布绘制
- `include/core/SkString.h`: 字符串类

**Viewer 框架**:
- `tools/viewer/Slide.h`: 幻灯片基类

### 被依赖情况

- `tools/viewer/Viewer.cpp`: 加载图片文件时创建 `ImageSlide`
- `tools/viewer/SlideDir.cpp`: 目录遍历时发现图片文件

## 设计模式与设计决策

### 策略模式

两种构造方式实现不同的图片获取策略：
- **文件策略**: 从磁盘按需加载
- **对象策略**: 使用预加载的图片

通过 `fRetainImage` 标志在运行时选择策略。

### RAII 资源管理

```cpp
sk_sp<SkImage> fImage;
```

智能指针自动管理图片生命周期，析构时自动释放。

### 延迟初始化

文件模式延迟到 `load()` 才读取数据，避免构造函数阻塞。

### 最小职责

该类只负责加载和绘制图片，不处理：
- 缩放和布局（由 Viewer 负责）
- 图片编辑（只读显示）
- 多图片管理（每个幻灯片一张图片）

## 性能考量

### 加载性能

**文件读取**:
- 小图片（< 100KB）：1-5ms
- 中图片（1-5MB）：10-50ms
- 大图片（> 10MB）：50-500ms

**延迟解码**: `load()` 本身很快（仅读取文件），解码延迟到绘制时。

### 绘制性能

**首次绘制**:
- 解码开销：10-100ms（取决于图片大小和格式）
- 后续绘制：< 1ms（使用缓存的像素）

**GPU 上传**:
- 首次绘制需要上传纹理到 GPU（5-50ms）
- 后续绘制使用 GPU 缓存

### 内存使用

**编码数据** (文件模式):
- JPEG: 约原始像素的 5-20%
- PNG: 约原始像素的 20-50%

**解码像素**:
- RGBA8888: width × height × 4 bytes
- 1920×1080 图片 ≈ 8.3MB

**延迟解码优势**:
```
未绘制时: 仅占用编码数据内存
绘制后: 编码数据 + 解码像素（总和约 1.05-1.2 倍像素大小）
```

### 卸载优化

```cpp
if (!fRetainImage) {
    fImage.reset(nullptr);
}
```

释放图片可节省大量内存，特别是高分辨率图片。

## 相关文件

### Viewer 幻灯片系统
- `tools/viewer/Slide.h`: 幻灯片基类
- `tools/viewer/SKPSlide.h/cpp`: SKP 幻灯片
- `tools/viewer/SkottieSlide.h/cpp`: Lottie 动画幻灯片
- `tools/viewer/SlideDir.h/cpp`: 幻灯片目录管理

### 图片系统
- `include/core/SkImage.h`: 图片接口
- `include/core/SkBitmap.h`: 位图表示
- `src/image/`: 图片实现

### 工具库
- `tools/Resources.h`: 资源加载工具

### 使用示例

```cpp
// 从文件创建（延迟加载）
auto slide1 = std::make_unique<ImageSlide>("Photo", "path/to/photo.jpg");
slide1->load(800, 600);
slide1->draw(canvas);
slide1->unload();

// 从图片对象创建（保留模式）
sk_sp<SkImage> img = generateImage();
auto slide2 = std::make_unique<ImageSlide>("Generated", img);
slide2->load(800, 600);  // 无操作
slide2->draw(canvas);
slide2->unload();  // 不释放图片
```

### 支持的图片格式

Skia 支持多种编码格式：
- **光栅**: JPEG, PNG, GIF, WebP, BMP, ICO
- **矢量**: SVG（通过扩展模块）
- **原始**: DNG（通过扩展模块）

格式支持取决于编译时启用的编解码器。
