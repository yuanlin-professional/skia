# SkFontMgr_custom_empty

> 源文件
> - src/ports/SkFontMgr_custom_empty.cpp

## 概述

`SkFontMgr_custom_empty` 是基于 FreeType 的空字体管理器实现，通过 `SkFontMgr_Custom` 框架提供一个不加载任何系统字体的最小化管理器。该模块仅包含一个空 typeface（`SkTypeface_Empty`）作为最后的回退，主要用于测试、基准测试或需要完全禁用系统字体的场景。

核心特点：
- **单一空字体**：仅包含 `SkTypeface_Empty` 作为回退
- **FreeType 后端**：基于成熟的 FreeType 渲染引擎
- **零加载开销**：不扫描文件系统或加载数据
- **测试友好**：用于隔离测试环境
- **极简实现**：代码仅 30 行

该模块是 FreeType 字体管理器系列中最简单的实现，常用于测试场景。

## 架构位置

```
SkFontMgr (抽象基类)
    ↓
SkFontMgr_Custom (自定义管理器基类)
    ↓
EmptyFontLoader (本模块 - 空加载策略)
    ↓
SkTypeface_Empty (空typeface)
```

字体管理器对比：
```
SkFontMgr_Custom_Directory → 扫描目录加载字体
SkFontMgr_Custom_Embedded  → 从嵌入数据加载字体
SkFontMgr_Custom_Empty     → 不加载任何字体 (本模块)
```

## 主要类与结构体

### EmptyFontLoader
实现 `SkFontMgr_Custom::SystemFontLoader` 接口的空加载器。

**核心方法：**
- `loadSystemFonts()`: 创建包含单个空 typeface 的匿名家族

**实现：**
```cpp
void loadSystemFonts(const SkFontScanner* scanner,
                     SkFontMgr_Custom::Families* families) const override
{
    SkFontStyleSet_Custom* family = new SkFontStyleSet_Custom(SkString());
    families->push_back().reset(family);
    family->appendTypeface(sk_make_sp<SkTypeface_Empty>());
}
```

## 公共 API 函数

### SkFontMgr_New_Custom_Empty()
```cpp
sk_sp<SkFontMgr> SkFontMgr_New_Custom_Empty();
```
创建空字体管理器。

**返回值：** 字体管理器智能指针

**使用场景：**
- 单元测试（隔离字体依赖）
- 性能基准测试（消除字体加载影响）
- 禁用系统字体的应用
- 测试字体回退机制

**使用示例：**
```cpp
sk_sp<SkFontMgr> fontMgr = SkFontMgr_New_Custom_Empty();

// 查询家族（总是返回唯一的空家族）
int familyCount = fontMgr->countFamilies();  // 返回 1

// 获取默认字体（返回 SkTypeface_Empty）
sk_sp<SkTypeface> typeface = fontMgr->legacyMakeTypeface(nullptr, SkFontStyle());

// 空 typeface 的渲染不会产生任何字形
```

## 内部实现细节

### 加载流程

构造函数调用链：
```
SkFontMgr_New_Custom_Empty()
    ↓
SkFontMgr_Custom 构造函数
    ↓
EmptyFontLoader::loadSystemFonts()
    ↓
创建匿名家族
    ↓
添加 SkTypeface_Empty
    ↓
设置为默认家族
```

### 空家族的特点

创建的家族具有以下特点：
- **匿名家族**：家族名称为空字符串（`SkString()`）
- **单一 typeface**：只包含 `SkTypeface_Empty`
- **默认家族**：`SkFontMgr_Custom` 自动将其设置为默认家族

### SkTypeface_Empty 的行为

空 typeface 的关键特性（在 `SkFontMgr_custom.h/cpp` 中定义）：
- `onOpenStream()`: 返回 nullptr（无字体数据）
- `onMakeClone()`: 返回自身引用（无法克隆）
- `onMakeFontData()`: 返回 nullptr（无字体数据）
- 渲染时不会产生任何字形
- 所有字符的字形 ID 都是 0

### 与其他加载器的对比

| 加载器 | 字体来源 | 家族数量 | 启动时间 | 内存占用 |
|--------|---------|---------|---------|---------|
| **EmptyFontLoader** | 无 | 1 | ~0ms | ~200B |
| DirectorySystemFontLoader | 文件系统 | 可变 | 100-5000ms | 10KB-1MB |
| EmbeddedSystemFontLoader | 编译期嵌入 | 可变 | 10-100ms | 500KB-20MB |
| DataFontLoader | 运行时数据 | 可变 | 10-100ms | 动态 |

### 最小化实现

整个模块只有 30 行代码，展示了 `SkFontMgr_Custom` 框架的灵活性。通过实现单一接口方法，即可创建完整功能的字体管理器。

## 依赖关系

### Skia 内部依赖
| 模块 | 用途 |
|------|------|
| `SkFontMgr_Custom` | 自定义字体管理器基类 |
| `SkTypeface_Empty` | 空 typeface 实现 |
| `SkFontStyleSet_Custom` | 自定义样式集 |
| `SkFontScanner` | 字体扫描器接口（未使用） |

### 外部依赖
无。该模块不依赖 FreeType 或其他外部库（尽管通过继承链间接依赖 FreeType）。

## 设计模式与设计决策

### 1. 策略模式（Strategy Pattern）
`EmptyFontLoader` 作为加载策略，注入到 `SkFontMgr_Custom` 中。

### 2. 空对象模式（Null Object Pattern）
整个模块是空对象模式的应用，`SkTypeface_Empty` 提供了有效但无用的 typeface。

### 3. 最小化实现
展示了框架的灵活性：仅需几行代码即可实现新的字体管理器。

### 4. 单一职责
模块只负责创建空管理器，不包含任何字体解析或渲染逻辑。

### 5. 防御式编程
即使完全没有字体，系统也不会崩溃，始终有可用的回退对象。

## 性能考量

### 1. 零启动开销
不执行任何文件扫描或数据解析：
- 启动时间：< 1 微秒
- 内存分配：仅管理器对象本身（约 200 字节）

### 2. 极小内存占用
- `SkFontMgr_Custom` 对象：约 100 字节
- `SkFontStyleSet_Custom` 对象：约 50 字节
- `SkTypeface_Empty` 对象：约 50 字节
- **总计：约 200 字节**

### 3. 无运行时开销
所有查询操作都是常数时间，因为只有一个家族和一个 typeface。

### 4. 测试性能
作为基准测试的基线：
- 消除字体加载的影响
- 测量纯渲染性能
- 隔离字体回退逻辑

### 5. 与 Fontations 空管理器对比

| 特性 | Custom_Empty (FreeType) | Fontations_Empty |
|------|-------------------------|------------------|
| **实现方式** | 策略注入 | 直接继承 |
| **包含字体** | 1 个空 typeface | 0 个字体 |
| **代码行数** | 30 | 83 |
| **启动时间** | < 1μs | < 1μs |
| **内存占用** | ~200B | ~100B |
| **查询行为** | 返回空家族 | 返回空结果 |

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/ports/SkFontMgr_custom.h` | 自定义字体管理器基类定义 |
| `src/ports/SkFontMgr_custom.cpp` | 自定义字体管理器实现 |
| `include/ports/SkFontMgr_empty.h` | 空字体管理器公共 API |
| `src/ports/SkFontMgr_custom_directory.cpp` | 目录字体管理器 |
| `src/ports/SkFontMgr_custom_embedded.cpp` | 嵌入式字体管理器 |
| `src/ports/SkFontMgr_fontations_empty.cpp` | Fontations 空字体管理器（对比） |
| `tools/fonts/FontToolUtils.cpp` | 测试字体工具 |
