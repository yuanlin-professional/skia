# SkFontMgr_custom_embedded

> 源文件
> - src/ports/SkFontMgr_custom_embedded.cpp

## 概述

`SkFontMgr_custom_embedded` 实现了从嵌入式数据加载字体的管理器，支持两种数据源：编译期嵌入的字体资源（`SkEmbeddedResource`）和运行时的 `SkData` 对象。该模块适用于需要将字体数据直接编译到可执行文件中的场景，如嵌入式系统、移动应用、独立工具等。

核心特点：
- **编译期嵌入**：通过 `SkEmbeddedResourceHeader` 嵌入字体数据
- **运行时加载**：从 `SkData` 对象加载字体
- **零文件系统依赖**：完全在内存中操作
- **TTC 和可变字体支持**：完整解析字体集合和实例
- **共享数据**：多个 typeface 可以共享同一块字体数据

该模块常用于需要确保字体可用性或减少外部依赖的场景。

## 架构位置

```
SkFontMgr (抽象基类)
    ↓
SkFontMgr_Custom (自定义管理器基类)
    ↓
┌──────────────────────┬─────────────────────┐
│                      │                     │
EmbeddedSystemFontLoader   DataFontLoader
(编译期资源加载)          (运行时数据加载)
    ↓                      ↓
SkMemoryStream          SkMemoryStream
    ↓                      ↓
SkTypeface_FreeTypeStream
```

## 主要类与结构体

### SkEmbeddedResource
描述单个嵌入式字体资源。

**成员：**
- `data`: 指向字体数据的指针（`const uint8_t*`）
- `size`: 数据大小（字节）

### SkEmbeddedResourceHeader
描述嵌入式字体资源集合的头部。

**成员：**
- `entries`: 资源数组指针（`const SkEmbeddedResource*`）
- `count`: 资源数量

### EmbeddedSystemFontLoader
从编译期嵌入资源加载字体的加载器。

**主要成员：**
- `fHeader`: 指向 `SkEmbeddedResourceHeader` 的指针

**核心方法：**
- `loadSystemFonts()`: 遍历资源头部，加载所有字体

### DataFontLoader
从运行时 `SkData` 对象加载字体的加载器。

**主要成员：**
- `fDatas`: `SkData` 智能指针数组
- `fNum`: 数据对象数量

**核心方法：**
- `loadSystemFonts()`: 遍历数据数组，加载所有字体

## 公共 API 函数

### SkFontMgr_New_Custom_Embedded()
```cpp
sk_sp<SkFontMgr> SkFontMgr_New_Custom_Embedded(const SkEmbeddedResourceHeader* header);
```
从编译期嵌入的字体资源创建字体管理器。

**参数：**
- `header`: 指向嵌入式资源头部的指针

**返回值：** 字体管理器智能指针

**使用示例：**
```cpp
// 编译期定义字体资源
static const uint8_t fontData[] = { /* 字体文件内容 */ };
static const SkEmbeddedResource resources[] = {
    { fontData, sizeof(fontData) }
};
static const SkEmbeddedResourceHeader header = { resources, 1 };

// 创建管理器
sk_sp<SkFontMgr> fontMgr = SkFontMgr_New_Custom_Embedded(&header);
```

### SkFontMgr_New_Custom_Data()
```cpp
sk_sp<SkFontMgr> SkFontMgr_New_Custom_Data(SkSpan<sk_sp<SkData>> datas);
```
从 `SkData` 对象数组创建字体管理器。

**参数：**
- `datas`: `SkData` 智能指针的 span（必须非空）

**返回值：** 字体管理器智能指针

**使用示例：**
```cpp
sk_sp<SkData> fontData = SkData::MakeFromFileName("font.ttf");
std::vector<sk_sp<SkData>> fonts = { fontData };
sk_sp<SkFontMgr> fontMgr = SkFontMgr_New_Custom_Data(SkSpan(fonts));
```

## 内部实现细节

### load_font_from_data() 核心函数
```cpp
static void load_font_from_data(const SkFontScanner* scanner,
                                std::unique_ptr<SkMemoryStream> stream, int index,
                                SkFontMgr_Custom::Families* families);
```
从内存流加载单个字体文件。

**处理流程：**
1. **扫描文件**：使用 `scanner->scanFile()` 检测 face 数量
2. **遍历 face**：对每个 face 调用 `scanner->scanFace()` 获取实例数
3. **遍历实例**：对每个实例调用 `scanner->scanInstance()` 提取元数据：
   - 家族名称（`realname`）
   - 字体样式（`style`）
   - 是否等宽（`isFixedPitch`）
4. **创建 typeface**：构建 `SkFontData` 并创建 `SkTypeface_FreeTypeStream`
5. **分组管理**：使用 `find_family()` 查找或创建家族，添加 typeface

### SkFontData 构造
```cpp
auto data = std::make_unique<SkFontData>(
    stream->duplicate(), (instanceIndex << 16) + faceIndex,
    0, nullptr, 0, nullptr, 0);
```

**参数说明：**
- 第 1 个参数：复制的内存流
- 第 2 个参数：编码的索引（实例索引 << 16 | face 索引）
- 第 3-7 个参数：可变字体轴参数（未使用，传入默认值）

### 内存流复制
每个 typeface 都获得流的独立副本：
```cpp
stream->duplicate()
```
这允许多个 typeface 并发访问字体数据而不互相干扰。

### 空数据处理
两个加载器都包含相同的回退逻辑：
```cpp
if (families->empty()) {
    SkFontStyleSet_Custom* family = new SkFontStyleSet_Custom(SkString());
    families->push_back().reset(family);
    family->appendTypeface(sk_make_sp<SkTypeface_Empty>());
}
```
确保即使没有有效字体，管理器也不会崩溃。

### find_family() 辅助函数
```cpp
static SkFontStyleSet_Custom* find_family(SkFontMgr_Custom::Families& families,
                                          const char familyName[]);
```
线性搜索现有家族，按名称匹配。返回 nullptr 表示不存在。

## 依赖关系

### Skia 内部依赖
| 模块 | 用途 |
|------|------|
| `SkFontMgr_Custom` | 自定义字体管理器基类 |
| `SkFontScanner` | 字体文件扫描接口 |
| `SkTypeface_FreeTypeStream` | 内存流字体 typeface |
| `SkTypeface_Empty` | 空 typeface 回退 |
| `SkMemoryStream` | 内存数据流 |
| `SkData` | 内存数据容器 |
| `SkFontData` | 字体数据包装 |
| `SkFontDescriptor` | 字体描述符 |

## 设计模式与设计决策

### 1. 策略模式（Strategy Pattern）
两个不同的加载器（`EmbeddedSystemFontLoader` 和 `DataFontLoader`）实现相同的接口，提供不同的数据源策略。

### 2. 工厂模式（Factory Pattern）
两个工厂函数（`SkFontMgr_New_Custom_Embedded` 和 `SkFontMgr_New_Custom_Data`）根据不同的数据源创建字体管理器。

### 3. 组合模式（Composite Pattern）
字体数据可以是单个字体文件或 TTC 集合，统一处理方式相同。

### 4. 共享数据设计
使用 `stream->duplicate()` 而非深拷贝，多个 typeface 共享底层数据，节省内存。

### 5. 零文件系统依赖
完全在内存中操作，适合无文件系统或需要沙箱隔离的环境。

### 6. 编译期嵌入支持
通过简单的结构体数组，允许在编译时将字体数据链接到可执行文件中。

## 性能考量

### 1. 内存占用
**编译期嵌入：**
- 字体数据直接占用可执行文件大小
- 单个字体：约 50KB - 2MB
- 10 个字体：约 500KB - 20MB

**运行时加载：**
- 字体数据占用堆内存
- `SkData` 使用引用计数，可以共享

### 2. 加载时间
所有字体在构造函数中一次性解析：
- 单个字体：约 1-10ms
- 10 个字体：约 10-100ms

相比文件系统加载，无 I/O 开销，速度更快。

### 3. 流复制开销
`stream->duplicate()` 创建轻量级副本：
- 只复制流对象（约 64 字节）
- 不复制底层数据（共享）

### 4. 内存优势
- **无文件缓存**：不需要操作系统页缓存
- **按需加载**：只有实际使用的字形才会解码
- **共享数据**：多个 typeface 共享字体数据

### 5. 优化建议
- **延迟解析**：只在第一次使用时解析字体元数据
- **预处理字体**：移除未使用的字形表减小数据大小
- **压缩嵌入**：嵌入压缩的字体数据，运行时解压

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/ports/SkFontMgr_custom.h` | 自定义字体管理器基类 |
| `src/ports/SkFontMgr_custom.cpp` | 自定义字体管理器实现 |
| `include/ports/SkFontMgr_data.h` | 数据字体管理器公共 API |
| `src/ports/SkTypeface_FreeType.h` | FreeType typeface 基类 |
| `include/core/SkData.h` | 数据容器接口 |
| `include/core/SkStream.h` | 流接口 |
| `src/core/SkFontDescriptor.h` | 字体描述符 |
| `src/ports/SkFontMgr_custom_directory.cpp` | 目录字体管理器 |
| `src/ports/SkFontMgr_custom_empty.cpp` | 空字体管理器 |
