# SkDocument

> 源文件: include/core/SkDocument.h, src/core/SkDocument.cpp

## 概述

`SkDocument` 是 Skia 中用于创建基于文档的多页面渲染的高层抽象类。它提供了一个统一的接口来生成 PDF、XPS 等文档格式，允许开发者以页面为单位组织内容。通过 `SkDocument`，用户可以顺序创建多个页面，在每个页面上使用 `SkCanvas` 进行绘制，然后将整个文档输出到流中。

该类采用状态机设计，管理文档的生命周期（页面间、页面内、已关闭）。它是一个抽象基类，具体的文档格式（如 `SkPDFDocument`）需要实现其虚函数。默认的光栅 DPI 设置为 72.0f。

## 架构位置

`SkDocument` 位于文档生成管道的顶层：

```
用户代码
    ↓
SkDocument（文档抽象）← 当前模块
    ↓
SkCanvas（页面绘制）
    ↓
具体实现（SkPDFDocument / SkXPSDocument）
    ↓
SkWStream（输出流）
```

- 上游：接收用户的页面创建和绘制请求
- 下游：协调 `SkCanvas` 进行页面绘制，通过 `SkWStream` 输出数据
- 子类：`SkPDFDocument`、`SkXPSDocument` 等具体实现

## 主要类与结构体

### SkDocument 类

**继承关系：**
```
SkRefCnt
    ↑
SkDocument
```

**关键成员变量：**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fStream` | `SkWStream*` | 输出流，不拥有所有权 |
| `fState` | `State` | 当前文档状态 |

### State 枚举

文档的内部状态机：

| 状态 | 说明 |
|------|------|
| `kBetweenPages_State` | 页面间状态（初始状态） |
| `kInPage_State` | 页面内状态（正在绘制） |
| `kClosed_State` | 已关闭状态（终态） |

### 常量定义

| 常量 | 值 | 说明 |
|------|------|------|
| `SK_ScalarDefaultRasterDPI` | 72.0f | 默认光栅 DPI（每英寸点数） |

## 公共 API 函数

### 生命周期管理

| 函数 | 说明 |
|------|------|
| `beginPage(SkScalar width, SkScalar height, const SkRect* content = nullptr)` | 开始新页面，返回用于绘制的 Canvas |
| `endPage()` | 结束当前页面，使 Canvas 失效 |
| `close()` | 关闭文档，完成输出流写入 |
| `abort()` | 中止文档生成，输出内容不可信 |

**参数说明：**
- `width, height`：页面尺寸（单位：标量）
- `content`：可选的内容矩形，用于裁剪和偏移

### 使用流程

典型的使用模式：

```cpp
// 1. 创建文档
sk_sp<SkDocument> doc = MakePDF(stream);

// 2. 对每个页面
for (int i = 0; i < pageCount; ++i) {
    // a. 开始页面
    SkCanvas* canvas = doc->beginPage(width, height);

    // b. 绘制内容
    draw_my_content(canvas);

    // c. 结束页面
    doc->endPage();
}

// 3. 关闭文档
doc->close();
```

## 内部实现细节

### 状态转换逻辑

**beginPage()：**
```
kClosed_State → 返回 nullptr（错误）
kInPage_State → 自动调用 endPage()，转到 kBetweenPages_State
kBetweenPages_State → 转到 kInPage_State，返回 Canvas
```

**endPage()：**
```
kInPage_State → 转到 kBetweenPages_State，调用 onEndPage()
其他状态 → 无操作
```

**close()：**
```
kInPage_State → 先调用 endPage()，再递归调用 close()
kBetweenPages_State → 转到 kClosed_State，调用 onClose()，清空 fStream
kClosed_State → 直接返回（幂等性）
```

**abort()：**
```
任何状态 → 调用 onAbort()，转到 kClosed_State，清空 fStream
```

### 内容裁剪与偏移

`trim` 静态函数处理内容矩形：

```cpp
if (content && canvas) {
    SkRect inner = *content;
    if (!inner.intersect({0, 0, width, height})) {
        return nullptr;  // 内容完全在页面外
    }
    canvas->clipRect(inner);
    canvas->translate(inner.x(), inner.y());
}
```

**作用：**
- 将绘制区域限制在内容矩形内
- 将坐标系原点移至内容矩形左上角

### 输入验证

`beginPage` 检查参数有效性：

```cpp
if (width <= 0 || height <= 0 || fState == kClosed_State) {
    return nullptr;
}
```

### 资源管理

- **流所有权**：`SkDocument` 不拥有 `fStream`，由用户管理生命周期
- **Canvas 所有权**：由子类实现通过 `onBeginPage()` 返回，文档负责销毁
- **析构函数**：自动调用 `close()` 确保资源释放

### 虚函数接口

子类必须实现的纯虚函数：

| 虚函数 | 职责 |
|--------|------|
| `onBeginPage(SkScalar width, SkScalar height)` | 创建并返回页面 Canvas |
| `onEndPage()` | 完成页面绘制，释放 Canvas |
| `onClose(SkWStream*)` | 写入文档尾部，关闭流 |
| `onAbort()` | 清理资源，放弃输出 |

### 受保护的辅助方法

| 方法 | 说明 |
|------|------|
| `getStream()` | 返回输出流，供子类在页面写入时使用 |
| `getState()` | 返回当前状态，供子类判断 |

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkRefCnt` | 引用计数基类 |
| `SkCanvas` | 页面绘制接口 |
| `SkWStream` | 输出流抽象 |
| `SkRect` | 矩形区域 |
| `SkScalar` | 标量类型 |
| `SkAssert` | 断言宏 |

### 被依赖的模块

| 模块 | 依赖方式 |
|------|----------|
| `SkPDFDocument` | 继承 `SkDocument` 实现 PDF 生成 |
| `SkXPSDocument` | 继承 `SkDocument` 实现 XPS 生成 |
| 用户应用代码 | 调用 `MakePDF()` 等工厂函数 |

## 设计模式与设计决策

### 模板方法模式

`SkDocument` 定义文档生成的骨架算法（状态管理、参数验证），子类实现具体步骤（`onBeginPage`、`onEndPage` 等）。

### 状态模式

使用枚举 `State` 管理文档生命周期，通过状态转换确保 API 调用顺序正确。

### RAII 资源管理

虽然 `SkDocument` 本身不拥有流，但通过引用计数（`SkRefCnt`）确保文档对象正确销毁。析构函数自动调用 `close()` 防止资源泄漏。

### 非拥有性指针

`fStream` 使用原始指针而非智能指针，因为：
- 流的生命周期由调用者管理
- 文档只是临时使用流，不应影响其生命周期
- `close()` 后将 `fStream` 设为 `nullptr` 防止悬空访问

### 幂等性保证

`close()` 可多次调用，第二次及以后直接返回。`abort()` 也是幂等的。

### 内容矩形可选性

`content` 参数为可选：
- `nullptr`：使用整个页面区域
- 非 `nullptr`：裁剪并偏移绘制区域

### 自动状态修正

`beginPage()` 检测到 `kInPage_State` 时自动调用 `endPage()`，容错设计简化用户代码。

### 子类实现责任

基类注释明确指出：
```cpp
// note: subclasses must call close() in their destructor
```

子类析构函数必须调用 `close()` 确保虚函数正确调用。

## 性能考量

### 轻量级状态管理

`State` 枚举仅 4 字节，状态转换为简单的赋值操作。

### 惰性流操作

流只在 `onClose()` 时完成最终写入，页面数据可能被缓冲以优化 I/O。

### 引用计数开销

继承 `SkRefCnt` 引入原子操作，但对于文档级对象可忽略（创建和销毁次数极少）。

### 虚函数调用

每个页面的开始和结束各触发一次虚函数调用，开销可接受。

### 内容矩形优化

`trim` 函数通过提前交集检查避免无效页面的绘制：
```cpp
if (!inner.intersect(...)) return nullptr;
```

### 内存占用

`SkDocument` 本身仅两个指针（16 字节），不存储页面数据。

## 相关文件

| 文件路径 | 关系 |
|----------|------|
| `src/pdf/SkPDFDocument.h/.cpp` | PDF 格式实现 |
| `include/docs/SkPDFDocument.h` | PDF 文档工厂函数 |
| `include/core/SkCanvas.h` | 页面绘制接口 |
| `include/core/SkStream.h` | 输出流基类 |
| `include/core/SkRefCnt.h` | 引用计数基类 |
| `include/core/SkRect.h` | 矩形数据结构 |
| `tests/DocumentTest.cpp` | 单元测试 |
