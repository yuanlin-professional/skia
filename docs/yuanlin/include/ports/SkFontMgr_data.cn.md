# SkFontMgr_data

> 源文件: `include/ports/SkFontMgr_data.h`

## 概述

`SkFontMgr_data` 提供了一个工厂函数，用于创建基于内存数据的自定义字体管理器。该管理器直接从 `SkData` 对象(表示内存中的字体数据)加载字体，无需访问文件系统。所有字体渲染通过 FreeType 引擎完成。这是一个高度可移植的解决方案，适用于嵌入式字体、资源打包或沙盒环境。

## 架构位置

该头文件位于 `include/ports/` 目录，属于 Skia 的平台移植层(Ports Layer)。它与 `SkFontMgr_directory` 和 `SkFontMgr_empty` 并列，提供不同的字体数据源策略，是 Skia 字体架构的可选后端之一。

## 公共 API 函数

### `SkFontMgr_New_Custom_Data`

```cpp
SK_API sk_sp<SkFontMgr> SkFontMgr_New_Custom_Data(SkSpan<sk_sp<SkData>>);
```

- **功能**: 创建一个从内存数据集合加载字体的自定义字体管理器
- **参数**:
  - `SkSpan<sk_sp<SkData>>`: 字体数据的 span 视图，每个 `SkData` 对象包含一个完整字体文件的二进制数据(如 TTF、OTF、TTC 等格式)
  - Span 允许传递数组、`std::vector` 或其他连续容器
- **返回值**: `sk_sp<SkFontMgr>` 智能指针，管理新创建的字体管理器对象。如果所有字体数据无效，可能返回空管理器
- **所有权**: 字体管理器持有传入 `SkData` 对象的引用，确保数据在管理器生命周期内有效
- **线程安全**: 创建后的管理器可在多线程环境中安全使用

## 内部实现细节

### 数据解析机制

1. **FreeType 初始化**: 为每个 `SkData` 创建 FreeType 字体对象(`FT_Face`)
2. **元数据提取**: 读取字体族名(family name)、样式(style)、权重(weight)、倾斜度(slant)
3. **字体集合处理**: 对于 TTC(TrueType Collection)文件，解析所有子字体
4. **内存映射**: `SkData` 可能是内存映射文件，FreeType 直接访问底层内存，避免复制

### 数据生命周期

- **引用计数**: `sk_sp<SkData>` 确保字体数据在管理器使用期间不被释放
- **共享语义**: 多个管理器可以共享相同的 `SkData` 对象(如果从同一源创建)
- **不可变性**: `SkData` 是不可变的，保证线程安全和缓存有效性

### 字体匹配策略

管理器内部构建匹配表：
- **精确匹配**: 优先匹配字体族名和样式
- **回退机制**: 如果未找到匹配，回退到第一个可用字体(类似 `SkFontMgr_empty`)
- **样式近似**: 粗体/斜体样式可能通过算法模拟(如果原始数据不包含)

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| `SkData` | 封装不可变二进制数据，持有字体文件内容 |
| `SkFontMgr` | 字体管理器基类 |
| `SkSpan<T>` | 轻量级数组视图，避免容器类型耦合 |
| `SkRefCnt` | 引用计数基础设施 |
| FreeType 库 | 字体解析和渲染引擎 |

### 被依赖的模块

典型使用场景：
- **资源嵌入**: 字体二进制数据编译进可执行文件
- **网络加载**: 从服务器动态下载字体数据
- **加密字体**: 解密后的字体数据存储在内存中
- **跨平台分发**: 打包字体到应用资源，避免依赖系统字体
- **单元测试**: 使用预定义的字体数据集，确保测试可重现性

## 设计模式与设计决策

### 工厂模式

与 `SkFontMgr_directory` 相同，使用全局工厂函数：
- **封装**: 隐藏具体实现类
- **多态**: 返回 `SkFontMgr` 基类指针
- **一致性**: 与其他字体管理器工厂保持命名规范

### Span 参数设计

使用 `SkSpan` 而非 `std::vector` 或原始指针：
- **零拷贝**: Span 是视图，不复制数据
- **类型安全**: 避免指针+长度的传统 C 风格接口
- **灵活性**: 支持任意连续容器(数组、`std::vector`、`std::array`)

### 不可变数据源

`SkData` 是不可变的：
- **线程安全**: 多线程可并发读取字体数据
- **缓存友好**: FreeType 可安全缓存字体度量信息
- **简化**: 无需考虑数据变化的同步问题

### 延迟加载

虽然字体数据已在内存中，字形缓存仍按需构建：
- **内存效率**: 未使用的字形不占用内存
- **启动时间**: 创建管理器时只解析元数据，不渲染字形

## 性能考量

### 初始化开销

- **元数据解析**: 每个字体需要 1-10 毫秒(取决于字体复杂度)
- **大型字体集**: 数百个字体可能导致明显延迟
- **优化**: 在后台线程初始化，或延迟创建管理器

### 内存占用

- **字体数据**: 直接持有 `SkData`，现代字体通常 100KB - 10MB
- **元数据缓存**: 每个字体约 1-2 KB
- **字形缓存**: FreeType 运行时缓存，大小可配置

### 与文件系统方案对比

| 方面 | `SkFontMgr_data` | `SkFontMgr_directory` |
|------|------------------|----------------------|
| 初始化速度 | 快(数据已在内存) | 慢(需要读取文件) |
| 内存占用 | 高(持有所有数据) | 低(按需 mmap) |
| 文件系统依赖 | 无 | 需要文件系统访问 |
| 动态更新 | 不支持 | 不支持(需重建管理器) |

### 渲染性能

使用 FreeType 渲染，性能与 `SkFontMgr_directory` 相同：
- **字形缓存**: FreeType 内部缓存已渲染字形
- **无显著差异**: 数据源(内存 vs 文件)对渲染性能影响极小

## 平台相关说明

### 内存对齐

- **FreeType 要求**: 字体数据通常需要自然对齐(4 或 8 字节)
- **SkData 保证**: `SkData::MakeWithCopy` 确保适当对齐

### 大端序/小端序

- **自动处理**: FreeType 内部处理字体文件的字节序
- **跨平台兼容**: 相同的字体数据在所有平台上工作一致

### 嵌入式系统

在资源受限环境中：
- **Flash 存储**: 字体数据可以存储在 Flash 中，通过 `SkData::MakeFromMalloc` 封装
- **压缩**: 可以压缩字体数据，使用前解压到 `SkData`

## 使用示例

```cpp
// 从文件读取字体数据
sk_sp<SkData> fontData1 = SkData::MakeFromFileName("fonts/Arial.ttf");
sk_sp<SkData> fontData2 = SkData::MakeFromFileName("fonts/Times.ttf");

// 创建数据数组
std::vector<sk_sp<SkData>> fontDataArray = {fontData1, fontData2};

// 创建管理器
sk_sp<SkFontMgr> fontMgr = SkFontMgr_New_Custom_Data(SkSpan(fontDataArray));

// 使用管理器
sk_sp<SkTypeface> typeface = fontMgr->matchFamilyStyle("Arial", SkFontStyle::Normal());
```

### 嵌入式场景

```cpp
// 编译时嵌入字体(使用工具生成 C 数组)
extern const unsigned char kArialData[];
extern const size_t kArialDataSize;

sk_sp<SkData> fontData = SkData::MakeWithoutCopy(kArialData, kArialDataSize);
sk_sp<SkFontMgr> fontMgr = SkFontMgr_New_Custom_Data(SkSpan(&fontData, 1));
```

## 相关文件

| 文件 | 关系 |
|------|------|
| `include/core/SkData.h` | 数据容器，持有字体二进制 |
| `include/core/SkFontMgr.h` | 字体管理器基类 |
| `include/core/SkSpan.h` | 数组视图，用于参数传递 |
| `include/ports/SkFontMgr_directory.h` | 基于目录扫描的替代方案 |
| `include/ports/SkFontMgr_empty.h` | 空字体管理器 |
| `src/ports/SkFontMgr_custom_data.cpp` | 实现文件(源代码树) |
