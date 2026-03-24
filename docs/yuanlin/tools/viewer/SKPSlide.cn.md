# SKPSlide

> 源文件: `tools/viewer/SKPSlide.h`, `tools/viewer/SKPSlide.cpp`

## 概述

`SKPSlide` 是 Skia Viewer 工具中用于显示 SKP（Skia Picture）文件的幻灯片实现。SKP 是 Skia 的序列化绘制命令格式，用于记录和回放图形操作。该类从文件或流中加载 SKP 数据，反序列化为 `SkPicture` 对象，并在画布上绘制。它支持自动偏移调整以确保内容正确居中显示。

主要功能：
- 从文件路径或流加载 SKP 文件
- 反序列化 SkPicture 对象
- 处理 cull rect 偏移以正确显示内容
- 提供 Picture 的尺寸信息
- 支持延迟加载和卸载

## 架构位置

`SKPSlide` 位于 Viewer 工具的幻灯片系统中：

```
skia/
├── tools/
│   └── viewer/
│       ├── Slide.h                    # 幻灯片基类
│       ├── SKPSlide.h/cpp             # SKP 幻灯片实现
│       ├── ImageSlide.h/cpp           # 图片幻灯片
│       ├── SlideDir.h/cpp             # 幻灯片目录
│       └── Viewer.cpp                 # Viewer 主程序
├── include/
│   └── core/
│       ├── SkPicture.h                # Picture 接口
│       ├── SkSerialProcs.h            # 序列化过程定义
│       └── SkStream.h                 # 流接口
└── tools/
    └── DeserialProcsUtils.h           # 默认反序列化配置
```

## 主要类与结构体

### 类 `SKPSlide`

继承自 `Slide` 基类，实现 SKP 文件的加载和显示。

#### 公共成员

```cpp
public:
    SKPSlide(const SkString& name, const SkString& path);          // 从文件路径构造
    SKPSlide(const SkString& name, std::unique_ptr<SkStream>);     // 从流构造
    ~SKPSlide() override;

    SkISize getDimensions() const override;        // 获取 Picture 尺寸
    void draw(SkCanvas* canvas) override;          // 绘制 Picture
    void load(SkScalar winWidth, SkScalar winHeight) override;  // 加载 SKP 数据
    void unload() override;                        // 卸载释放内存
```

#### 私有成员

```cpp
private:
    std::unique_ptr<SkStream> fStream;    // SKP 数据流
    sk_sp<const SkPicture> fPic;          // 反序列化的 Picture 对象
    SkIRect fCullRect;                     // Picture 的剔除矩形
```

### 关键类型

**`SkPicture`**: Skia 的录制绘制命令对象
- 不可变的绘制操作序列
- 支持序列化和反序列化
- 包含 cull rect（绘制边界）

**`SkStream`**: Skia 流接口
- 抽象的数据源
- 支持文件、内存、网络等

**`SkSerialProcs`**: 序列化/反序列化配置
- 自定义图片、字体等的序列化方式

## 公共 API 函数

### 构造函数

**`SKPSlide(const SkString& name, const SkString& path)`**

从文件路径创建 SKP 幻灯片。

**实现**:
```cpp
SKPSlide::SKPSlide(const SkString& name, const SkString& path)
    : SKPSlide(name, SkStream::MakeFromFile(path.c_str())) {
}
```

委托到流构造函数，使用 `SkStream::MakeFromFile` 打开文件。

**`SKPSlide(const SkString& name, std::unique_ptr<SkStream> stream)`**

从流创建 SKP 幻灯片。

**参数**:
- `name`: 幻灯片显示名称
- `stream`: SKP 数据流（所有权转移）

**实现**:
```cpp
fStream(std::move(stream)) {
    fName = name;  // 设置基类的名称字段
}
```

流在构造时保存，延迟到 `load()` 时才反序列化。

### 尺寸查询

**`SkISize getDimensions() const`**

返回 Picture 的尺寸。

**实现**: `return fCullRect.size();`

Cull rect 定义了 Picture 的绘制边界，其尺寸即为内容尺寸。

### 绘制

**`void draw(SkCanvas* canvas)`**

在画布上绘制 Picture。

**实现**:
```cpp
if (fPic) {
    bool isOffset = SkToBool(fCullRect.left() | fCullRect.top());
    if (isOffset) {
        canvas->save();
        canvas->translate(SkIntToScalar(-fCullRect.left()),
                         SkIntToScalar(-fCullRect.top()));
    }

    canvas->drawPicture(fPic.get());

    if (isOffset) {
        canvas->restore();
    }
}
```

**偏移处理**:
- 如果 cull rect 的左上角不在原点 (0, 0)，应用平移变换
- 这确保 Picture 内容正确显示在画布上
- 例如：cull rect 为 (100, 50, 500, 400) 时，平移 (-100, -50)

**防御性检查**: 仅在 Picture 已加载时绘制，避免空指针访问。

### 生命周期管理

**`void load(SkScalar winWidth, SkScalar winHeight)`**

加载并反序列化 SKP 文件。

**参数**: 窗口尺寸（此实现未使用，但基类接口需要）

**流程**:
1. **检查流**: 如果 `fStream` 为空，输出错误并返回
2. **重置流位置**: `fStream->rewind()` - 允许重复加载
3. **获取反序列化配置**: `ToolUtils::get_default_skp_deserial_procs()`
4. **反序列化**: `SkPicture::MakeFromStream(fStream.get(), &procs)`
5. **提取 cull rect**: `fPic->cullRect().roundOut()` - 取整为整数矩形

**错误处理**:
```cpp
if (!fStream) {
    SkDebugf("No skp stream for slide %s.\n", fName.c_str());
    return;
}
if (!fPic) {
    SkDebugf("Could not parse SkPicture from skp stream for slide %s.\n", fName.c_str());
    return;
}
```

输出调试信息但不崩溃，允许 Viewer 继续运行。

**`void unload()`**

卸载 Picture 释放内存。

**实现**: `fPic.reset(nullptr);`

智能指针自动释放 Picture 对象及其引用的所有资源。

## 内部实现细节

### 延迟加载策略

```
构造时: 仅保存流，不反序列化
    ↓
load(): 反序列化 Picture，提取 cull rect
    ↓
draw(): 使用已加载的 Picture
    ↓
unload(): 释放 Picture，保留流
    ↓
可再次 load(): 重复加载
```

这种设计允许：
- 快速创建幻灯片对象（不阻塞）
- 按需加载内容（节省内存）
- 重复加载（如重新加载功能）

### Cull Rect 处理

**Cull rect（剔除矩形）**:
- Picture 的逻辑绘制边界
- 用于优化：超出边界的内容可能被跳过
- 可能不从原点 (0, 0) 开始

**偏移检查**:
```cpp
bool isOffset = SkToBool(fCullRect.left() | fCullRect.top());
```

位或运算检查左上角是否为非零，比两次比较稍快。

**平移变换**:
```cpp
canvas->translate(-fCullRect.left(), -fCullRect.top());
```

将 Picture 的逻辑坐标系对齐到画布原点。

**示例**:
- Cull rect: (100, 50, 600, 450)
- 不平移: Picture 绘制在 (100, 50) 开始的位置，可能超出视口
- 平移: Picture 对齐到 (0, 0)，完整显示

### 流的可重用性

```cpp
fStream->rewind();
```

流在 `load()` 时重置位置，支持多次加载：
- 用户切换到其他幻灯片并返回
- 编辑 SKP 文件后重新加载
- 测试不同的反序列化配置

### 默认反序列化配置

```cpp
SkDeserialProcs procs = ToolUtils::get_default_skp_deserial_procs();
```

`get_default_skp_deserial_procs` 提供：
- 图片反序列化器（加载嵌入的 PNG/JPEG）
- 字体反序列化器（恢复字体引用）
- 其他资源处理器

这确保 SKP 文件中的所有资源正确恢复。

## 依赖关系

### 直接依赖

**Skia 核心**:
- `include/core/SkCanvas.h`: 画布绘制
- `include/core/SkPicture.h`: Picture 类
- `include/core/SkSerialProcs.h`: 序列化过程
- `include/core/SkStream.h`: 流接口
- `include/core/SkString.h`: 字符串类

**Viewer 框架**:
- `tools/viewer/Slide.h`: 幻灯片基类

**工具库**:
- `tools/DeserialProcsUtils.h`: 反序列化工具
- `include/private/base/SkDebug.h`: 调试输出
- `include/private/base/SkTo.h`: 类型转换工具

### 被依赖情况

- `tools/viewer/Viewer.cpp`: 加载 SKP 文件时创建 `SKPSlide` 对象
- `tools/viewer/SlideDir.cpp`: 目录遍历时发现 SKP 文件

## 设计模式与设计决策

### 资源获取即初始化（RAII）

```cpp
std::unique_ptr<SkStream> fStream;
sk_sp<const SkPicture> fPic;
```

使用智能指针自动管理内存，析构函数无需显式清理。

### 两阶段初始化

**阶段 1（构造）**: 轻量级初始化
- 保存名称和流
- 不执行 I/O 或解析

**阶段 2（load）**: 重量级初始化
- 反序列化 SKP 文件
- 构建 Picture 对象

这避免了构造函数抛出异常或长时间阻塞。

### 委托构造函数

```cpp
SKPSlide(const SkString& name, const SkString& path)
    : SKPSlide(name, SkStream::MakeFromFile(path.c_str())) {
}
```

路径构造函数委托到流构造函数，减少代码重复。

### 防御性编程

```cpp
if (fPic) {
    canvas->drawPicture(fPic.get());
}
```

始终检查 Picture 是否已加载，避免在加载失败时崩溃。

### 不可变 Picture

```cpp
sk_sp<const SkPicture> fPic;
```

使用 `const SkPicture` 强调 Picture 的不可变性，防止意外修改。

## 性能考量

### 加载性能

**SKP 反序列化开销**:
- 小型 SKP（< 100KB）：1-10ms
- 中型 SKP（1-10MB）：10-100ms
- 大型 SKP（> 10MB）：100-1000ms

延迟加载避免了应用启动时的长时间阻塞。

### 绘制性能

**Picture 回放开销**:
```cpp
canvas->drawPicture(fPic.get());
```

- Picture 回放经过高度优化
- 绘制命令直接执行，无中间转换
- 对于复杂 Picture（数千条命令），可能需要数毫秒

**偏移变换**:
```cpp
canvas->save();
canvas->translate(...);
canvas->drawPicture(...);
canvas->restore();
```

Save/restore 开销约 1-2μs，可忽略。

### 内存使用

**Picture 内存占用**:
- 基础开销：约 100 bytes
- 绘制命令：每条约 10-50 bytes
- 嵌入资源：图片、字体等的原始大小

典型的 SKP 文件占用 100KB - 10MB 内存。

**卸载优化**:
```cpp
void unload() {
    fPic.reset(nullptr);
}
```

释放 Picture 可以显著减少内存使用，特别是处理大量幻灯片时。

### 优化建议

1. **异步加载**: 在后台线程反序列化 SKP
2. **预加载**: 提前加载相邻幻灯片
3. **LRU 缓存**: 自动卸载最少使用的幻灯片

## 相关文件

### Viewer 幻灯片系统
- `tools/viewer/Slide.h`: 幻灯片基类
- `tools/viewer/ImageSlide.h/cpp`: 图片幻灯片
- `tools/viewer/SkottieSlide.h/cpp`: Lottie 动画幻灯片
- `tools/viewer/SlideDir.h/cpp`: 幻灯片目录管理

### Picture 系统
- `include/core/SkPicture.h`: Picture 接口
- `src/core/SkPictureRecorder.h`: Picture 录制器
- `src/core/SkPicturePlayback.h`: Picture 回放引擎

### 工具库
- `tools/DeserialProcsUtils.h`: 反序列化工具
- `tools/Resources.h`: 资源加载工具

### 使用示例

```cpp
// 加载单个 SKP 文件
auto slide = std::make_unique<SKPSlide>("MySketch", "path/to/sketch.skp");
slide->load(800, 600);
slide->draw(canvas);
slide->unload();

// 从内存流加载
auto memStream = std::make_unique<SkMemoryStream>(data, size);
auto slide = std::make_unique<SKPSlide>("MemorySketch", std::move(memStream));
slide->load(800, 600);
slide->draw(canvas);
```

### SKP 文件创建

```cpp
// 录制 SKP 文件
SkPictureRecorder recorder;
SkCanvas* canvas = recorder.beginRecording(SkRect::MakeWH(800, 600));
// ... 绘制操作 ...
sk_sp<SkPicture> pic = recorder.finishRecordingAsPicture();

// 序列化到文件
SkFILEWStream stream("output.skp");
pic->serialize(&stream);
```
