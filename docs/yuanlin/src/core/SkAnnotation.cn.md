# SkAnnotation

> 源文件
> - include/core/SkAnnotation.h
> - src/core/SkAnnotation.cpp

## 概述

`SkAnnotation` 是 Skia 图形库中用于在画布上添加元数据注解的接口模块。它支持将 URL 链接、命名目标点等语义信息与绘制内容关联，主要用于 PDF 等支持交互式元数据的输出格式。注解不影响视觉渲染，仅在特定后端中生效。

## 架构位置

`SkAnnotation` 位于 Skia 的高层绘制接口层，通过 `SkCanvas::drawAnnotation` 方法将注解信息传递给后端。它是 PDF、SVG 等矢量格式的元数据桥梁。

```
Skia Core
  └── Drawing API
      ├── SkCanvas (绘制接口)
      │   └── drawAnnotation() (注解入口)
      ├── SkAnnotation (公共 API)
      │   └── 注解辅助函数
      └── SkAnnotationKeys (键常量)
          └── 预定义注解类型键
```

## 主要类与结构体

### SkAnnotation 模块

这是一个函数集合模块，而非类。提供三个便利函数用于常见注解操作。

**核心函数**

| 函数 | 说明 |
|------|------|
| `SkAnnotateRectWithURL` | 将矩形区域与 URL 关联 |
| `SkAnnotateNamedDestination` | 定义命名目标点 |
| `SkAnnotateLinkToDestination` | 创建到命名目标的链接 |

### SkAnnotationKeys 类

**设计**
- 纯静态类（只有静态方法）
- 提供预定义的注解键常量

**键常量方法**

| 方法 | 返回值 | 用途 |
|------|-------|------|
| `URL_Key()` | `"SkAnnotationKey_URL"` | URL 链接注解 |
| `Define_Named_Dest_Key()` | `"SkAnnotationKey_Define_Named_Dest"` | 定义命名目标 |
| `Link_Named_Dest_Key()` | `"SkAnnotationKey_Link_Named_Dest"` | 链接到命名目标 |

## 公共 API 函数

### SkAnnotateRectWithURL

**签名**
```cpp
void SkAnnotateRectWithURL(SkCanvas* canvas, const SkRect& rect, SkData* value)
```

**功能**
- 在画布上标注一个可点击的矩形区域，关联指定 URL
- 类似 HTML 中的 `<a href="url">` 标签

**参数**
- `canvas`: 目标画布指针
- `rect`: 矩形区域（本地坐标系）
- `value`: URL 字符串（`SkData` 包装，预期为 7 位 ASCII，已转义）

**行为**
- 如果 `value` 为 `nullptr`，安全忽略
- 调用 `canvas->drawAnnotation(rect, URL_Key(), value)`
- 不支持注解的后端会忽略此调用

**典型用途**
```cpp
// PDF 输出中创建可点击链接
sk_sp<SkData> url = SkData::MakeWithCString("https://example.com");
SkRect linkRect = SkRect::MakeXYWH(10, 10, 100, 20);
SkAnnotateRectWithURL(canvas, linkRect, url.get());
```

### SkAnnotateNamedDestination

**签名**
```cpp
void SkAnnotateNamedDestination(SkCanvas* canvas, const SkPoint& point, SkData* name)
```

**功能**
- 在指定位置定义一个命名目标点
- 类似 HTML 中的 `<a name="target">` 或 `id="target"`

**参数**
- `canvas`: 目标画布指针
- `point`: 目标点位置
- `name`: 目标名称（`SkData` 包装）

**实现细节**
- 创建零尺寸矩形：`SkRect::MakeXYWH(point.x(), point.y(), 0, 0)`
- 调用 `canvas->drawAnnotation(rect, Define_Named_Dest_Key(), name)`

**典型用途**
```cpp
// 定义 PDF 书签目标
sk_sp<SkData> destName = SkData::MakeWithCString("chapter1");
SkAnnotateNamedDestination(canvas, SkPoint::Make(0, 100), destName.get());
```

### SkAnnotateLinkToDestination

**签名**
```cpp
void SkAnnotateLinkToDestination(SkCanvas* canvas, const SkRect& rect, SkData* name)
```

**功能**
- 创建一个链接到内部命名目标的可点击矩形
- 类似 HTML 中的 `<a href="#target">`

**参数**
- `canvas`: 目标画布指针
- `rect`: 可点击矩形区域
- `name`: 目标名称（引用已定义的命名目标）

**行为**
- 如果 `name` 为 `nullptr`，安全忽略
- 调用 `canvas->drawAnnotation(rect, Link_Named_Dest_Key(), name)`

**典型用途**
```cpp
// 创建到目录的内部链接
sk_sp<SkData> destName = SkData::MakeWithCString("chapter1");
SkRect tocRect = SkRect::MakeXYWH(10, 50, 150, 20);
SkAnnotateLinkToDestination(canvas, tocRect, destName.get());
```

## 内部实现细节

### 空指针安全检查

所有函数都首先检查 `value/name` 是否为 `nullptr`：
```cpp
if (nullptr == value) {
    return;
}
```

**原因**:
- 避免无效注解传递到后端
- 简化调用者逻辑（无需预检查）

### 零尺寸矩形技巧

`SkAnnotateNamedDestination` 使用零尺寸矩形：
```cpp
const SkRect rect = SkRect::MakeXYWH(point.x(), point.y(), 0, 0);
```

**优势**:
- 统一使用 `drawAnnotation` 接口
- 后端可区分点注解和区域注解
- 不影响视觉渲染边界

### 键常量实现

```cpp
const char* SkAnnotationKeys::URL_Key() {
    return "SkAnnotationKey_URL";
}
```

**设计选择**:
- 使用函数而非 `constexpr` 变量
- 返回字符串字面量（编译期常量）
- 避免静态初始化顺序问题

### URL 格式约定

API 文档要求：
- **编码**: 有效的 7 位 ASCII
- **转义**: 调用者负责 URL 转义
- **验证**: Skia 不验证 URL 有效性

**示例**:
```cpp
// 正确：已转义的 URL
"https://example.com/path?query=value%20with%20spaces"

// 错误：未转义的空格
"https://example.com/path?query=value with spaces"
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `include/core/SkCanvas.h` | 画布接口，`drawAnnotation` 方法 |
| `include/core/SkRect.h` | 矩形类型 |
| `include/core/SkPoint.h` | 点坐标类型 |
| `include/core/SkData.h` | 二进制数据容器 |
| `src/core/SkAnnotationKeys.h` | 注解键常量 |

### 被依赖的模块

| 模块 | 使用场景 |
|------|---------|
| `SkPDFDevice` | PDF 输出中生成链接和书签 |
| `SkSVGDevice` | SVG 输出中生成元数据 |
| 应用层代码 | 创建交互式文档 |
| 测试代码 | 验证注解功能 |

## 设计模式与设计决策

### 便利函数模式（Convenience Functions）
- **模式**: 封装常见的 `drawAnnotation` 调用
- **优势**:
  - 简化客户端代码
  - 隐藏键字符串细节
  - 提供类型安全的接口

### 键值对注解系统
- **设计**: 使用字符串键和 `SkData` 值
- **灵活性**:
  - 可扩展新注解类型
  - 后端可选择性支持
  - 无需修改核心接口

### 安全忽略模式
- **体现**: 空指针检查和后端选择性支持
- **优势**:
  - 调用者无需关心后端能力
  - 跨平台代码统一
  - 退化到无操作而非错误

### 字符串键常量
- **选择**: 使用字符串而非枚举
- **原因**:
  - 易于扩展（无需修改枚举）
  - 支持自定义注解类型
  - 后端友好（直接存储/传递）

## 性能考量

### 性能特征

1. **零渲染开销**
   - 注解不参与实际绘制
   - 不影响像素操作
   - 仅记录元数据

2. **数据传递**
   - `SkData` 使用引用计数，无拷贝
   - 字符串比较开销可忽略
   - 后端存储由具体实现决定

3. **内存占用**
   - 注解存储在 Picture/Command buffer
   - 典型 URL 注解：~50-200 字节
   - 命名目标：~20-50 字节

### 性能建议

| 场景 | 建议 | 原因 |
|------|------|------|
| 大量注解 | 重用 `SkData` 对象 | 减少分配 |
| 不支持注解的后端 | 无需避免调用 | 开销极小，安全忽略 |
| PDF 输出 | 预计算注解位置 | 避免重复布局计算 |

### 典型使用开销

| 操作 | 时间 | 说明 |
|------|------|------|
| `SkAnnotateRectWithURL` | ~50ns | 一次虚函数调用 + 参数传递 |
| 键常量获取 | ~1ns | 返回字符串字面量 |
| `SkData` 创建 | ~100-500ns | 取决于字符串长度 |

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/core/SkAnnotationKeys.h` | 协作 | 注解键常量定义 |
| `include/core/SkCanvas.h` | 依赖 | 画布接口，`drawAnnotation` 方法 |
| `src/pdf/SkPDFDevice.h` | 使用者 | PDF 后端实现注解 |
| `src/svg/SkSVGDevice.h` | 使用者 | SVG 后端实现注解 |
| `include/core/SkData.h` | 依赖 | 数据容器 |
| `tests/AnnotationTest.cpp` | 测试 | 注解功能单元测试 |
