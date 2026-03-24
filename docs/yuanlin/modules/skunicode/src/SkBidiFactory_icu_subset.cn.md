# SkBidiFactory_icu_subset

> 源文件: modules/skunicode/src/SkBidiFactory_icu_subset.h, modules/skunicode/src/SkBidiFactory_icu_subset.cpp

## 概述

`SkBidiSubsetFactory` 是双向文本(Bidi)处理的工厂类,使用 Skia 内置的 ICU 子集实现。该类作为 `SkBidiFactory` 接口的具体实现,将 Bidi 算法的调用桥接到 Skia 编译进的精简版 ICU 库(ICU subset),为文本布局系统提供双向文本分析和重排功能。

与完整 ICU 版本(SkBidiFactory_icu_full)相比,该实现使用 Skia 定制的 ICU 子集,具有更小的二进制体积,但功能完整,适合对二进制大小敏感的应用场景。

## 架构位置

该类位于 `skunicode` Unicode 处理模块中,作为 Bidi 功能的子集实现:

```
skia/modules/skunicode/
├── include/
│   └── SkUnicode.h                        # Unicode抽象接口
└── src/
    ├── SkUnicode_icu_bidi.h               # Bidi工厂基类
    ├── SkBidiFactory_icu_subset.h/.cpp    # ICU子集实现
    └── SkBidiFactory_icu_full.h/.cpp      # ICU完整版实现
```

**实现选择:**
- 编译时选择使用子集版本或完整版本
- 子集版本: 更小的二进制,Skia 自包含
- 完整版本: 动态链接系统 ICU,共享库依赖

## 主要类与结构体

### SkBidiSubsetFactory
```cpp
class SkBidiSubsetFactory : public SkBidiFactory
```
Bidi 工厂的 ICU 子集实现类。

**特点:**
- 实现 `SkBidiFactory` 的所有虚函数
- 调用 Skia 内置的 ICU 子集函数(后缀 `_skia`)
- 无额外状态,纯转发实现

## 公共 API 函数

所有函数都是 `SkBidiFactory` 接口的实现,直接转发到 ICU 子集函数:

### 错误处理
```cpp
const char* errorName(UErrorCode status) const override
```
返回错误码的字符串描述,调用 `u_errorName_skia()`。

### Bidi 对象管理
```cpp
BidiCloseCallback bidi_close_callback() const override
```
返回关闭 Bidi 对象的回调函数指针 `ubidi_close_skia`。

```cpp
UBiDi* bidi_openSized(int32_t maxLength, int32_t maxRunCount,
                      UErrorCode* pErrorCode) const override
```
创建指定大小的 Bidi 对象,调用 `ubidi_openSized_skia()`。

### Bidi 分析
```cpp
void bidi_setPara(UBiDi* bidi, const UChar* text, int32_t length,
                  UBiDiLevel paraLevel, UBiDiLevel* embeddingLevels,
                  UErrorCode* status) const override
```
设置并分析段落的双向文本属性,调用 `ubidi_setPara_skia()`。

**参数:**
- `bidi`: Bidi 对象
- `text`: UTF-16 文本
- `length`: 文本长度
- `paraLevel`: 段落级别(LTR/RTL)
- `embeddingLevels`: 可选的嵌入级别数组
- `status`: 错误状态输出

### Bidi 查询
```cpp
UBiDiDirection bidi_getDirection(const UBiDi* bidi) const override
```
获取文本的整体方向,调用 `ubidi_getDirection_skia()`。

```cpp
Position bidi_getLength(const UBiDi* bidi) const override
```
获取文本长度,调用 `ubidi_getLength_skia()`。

```cpp
Level bidi_getLevelAt(const UBiDi* bidi, int pos) const override
```
获取指定位置的 Bidi 级别,调用 `ubidi_getLevelAt_skia()`。

### 视觉重排
```cpp
void bidi_reorderVisual(const SkUnicode::BidiLevel runLevels[],
                        int levelsCount,
                        int32_t logicalFromVisual[]) const override
```
将逻辑顺序的运行级别重排为视觉顺序,调用 `ubidi_reorderVisual_skia()`。

**特殊处理:**
- `levelsCount == 0` 时直接返回,避免 ICU 内部断言失败

## 内部实现细节

### 纯转发实现
所有实现都是简单的函数调用转发:

```cpp
const char* SkBidiSubsetFactory::errorName(UErrorCode status) const {
    return u_errorName_skia(status);
}

UBiDiDirection SkBidiSubsetFactory::bidi_getDirection(const UBiDi* bidi) const {
    return ubidi_getDirection_skia(bidi);
}

// ... 其他函数类似
```

**设计优势:**
- 最小化适配层开销
- 编译器可以内联调用
- 易于维护和理解

### 边界条件处理
`bidi_reorderVisual()` 中的特殊处理:

```cpp
void SkBidiSubsetFactory::bidi_reorderVisual(...) const {
    if (levelsCount == 0) {
        // To avoid an assert in unicode
        return;
    }
    SkASSERT(runLevels != nullptr);
    ubidi_reorderVisual_skia(runLevels, levelsCount, logicalFromVisual);
}
```

避免空数组触发 ICU 库的断言失败。

### ICU 子集函数命名
所有调用的函数都有 `_skia` 后缀:
- `u_errorName_skia()`
- `ubidi_close_skia()`
- `ubidi_openSized_skia()`
- 等等

这些函数来自 Skia 编译进的 ICU 子集,与系统 ICU 库隔离。

## 依赖关系

### 核心依赖
- **SkBidiFactory**: Bidi 工厂抽象接口
- **ICU Bidi 子集**: Skia 内置的精简 ICU 库
- **unicode/ubidi.h**: ICU Bidi 类型定义

### 使用者
- **SkUnicode_icu**: ICU Unicode 实现
- **Paragraph**: 段落布局系统
- **TextLine**: 文本行,使用 Bidi 重排

### 依赖图
```
SkBidiSubsetFactory
    ↓ (calls)
ICU 子集函数 (ubidi_*_skia)
    ↓ (used by)
SkUnicode_icu → Paragraph
```

## 设计模式与设计决策

### 工厂模式
`SkBidiFactory` 使用工厂模式:
- 抽象接口定义 Bidi 操作
- 具体工厂实现选择 ICU 版本
- 客户端代码不依赖具体实现

### 适配器模式
该类是 ICU Bidi API 的适配器:
- 统一 Skia 的 Bidi 接口
- 隐藏 ICU 实现细节
- 支持未来切换到其他 Bidi 实现

### 编译时选择
通过编译配置选择使用子集或完整版本:
- 无运行时开销
- 二进制体积优化
- 功能完全一致

## 性能考量

### 零开销抽象
- 纯转发实现,编译器可以完全内联
- 无虚函数调用开销(已通过 vtable 解析)
- 与直接调用 ICU 函数性能相同

### 内存占用
- 工厂对象本身无状态,仅占用 vtable 指针大小
- Bidi 对象内存由 ICU 管理
- 子集版本: 减少二进制体积约 50-70%

### ICU 子集优势
- 更小的代码段
- 更好的缓存局部性
- 减少动态库加载开销
- Skia 自包含,无外部依赖

## 相关文件

### 接口定义
- `modules/skunicode/src/SkUnicode_icu_bidi.h`: Bidi 工厂基类

### 替代实现
- `modules/skunicode/src/SkBidiFactory_icu_full.h/.cpp`: ICU 完整版实现

### 使用方
- `modules/skunicode/src/SkUnicode_icu.cpp`: ICU Unicode 实现
- `modules/skparagraph/src/ParagraphImpl.cpp`: 段落实现
- `modules/skparagraph/src/TextLine.cpp`: 文本行实现

### ICU 头文件
- `unicode/ubidi.h`: Bidi 类型和常量定义
