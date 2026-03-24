# SkBidiFactory_icu_full

> 源文件: modules/skunicode/src/SkBidiFactory_icu_full.h, modules/skunicode/src/SkBidiFactory_icu_full.cpp

## 概述

`SkBidiICUFactory` 是双向文本(Bidi)处理的工厂类,使用系统完整的 ICU 库实现。该类作为 `SkBidiFactory` 接口的具体实现,将 Bidi 算法的调用桥接到系统动态链接的 ICU 库,通过 `SkGetICULib()` 获取 ICU 函数指针,为文本布局系统提供双向文本分析和重排功能。

与子集版本(SkBidiFactory_icu_subset)相比,该实现使用系统的完整 ICU 库,可以共享系统资源,但增加了外部依赖。

## 架构位置

该类位于 `skunicode` Unicode 处理模块中,作为 Bidi 功能的完整 ICU 实现:

```
skia/modules/skunicode/
├── include/
│   └── SkUnicode.h                        # Unicode抽象接口
└── src/
    ├── SkUnicode_icu_bidi.h               # Bidi工厂基类
    ├── SkBidiFactory_icu_subset.h/.cpp    # ICU子集实现
    ├── SkBidiFactory_icu_full.h/.cpp      # ICU完整版实现
    └── SkUnicode_icupriv.h                # ICU私有接口和动态加载
```

**实现选择:**
- 子集版本: Skia 内置精简 ICU,无外部依赖
- 完整版本: 动态链接系统 ICU,共享库资源

## 主要类与结构体

### SkBidiICUFactory
```cpp
class SkBidiICUFactory : public SkBidiFactory
```
Bidi 工厂的完整 ICU 实现类。

**特点:**
- 实现 `SkBidiFactory` 的所有虚函数
- 通过 `SkGetICULib()` 获取 ICU 函数指针
- 支持动态加载系统 ICU 库
- 无额外状态,纯转发实现

## 公共 API 函数

所有函数都是 `SkBidiFactory` 接口的实现,通过 ICU 库函数指针调用:

### 错误处理
```cpp
const char* errorName(UErrorCode status) const override
```
返回错误码的字符串描述,调用 `SkGetICULib()->f_u_errorName()`。

### Bidi 对象管理
```cpp
BidiCloseCallback bidi_close_callback() const override
```
返回关闭 Bidi 对象的回调函数指针 `SkGetICULib()->f_ubidi_close`。

```cpp
UBiDi* bidi_openSized(int32_t maxLength, int32_t maxRunCount,
                      UErrorCode* pErrorCode) const override
```
创建指定大小的 Bidi 对象,调用 `SkGetICULib()->f_ubidi_openSized()`。

### Bidi 分析
```cpp
void bidi_setPara(UBiDi* bidi, const UChar* text, int32_t length,
                  UBiDiLevel paraLevel, UBiDiLevel* embeddingLevels,
                  UErrorCode* status) const override
```
设置并分析段落的双向文本属性,调用 `SkGetICULib()->f_ubidi_setPara()`。

### Bidi 查询
```cpp
UBiDiDirection bidi_getDirection(const UBiDi* bidi) const override
Position bidi_getLength(const UBiDi* bidi) const override
Level bidi_getLevelAt(const UBiDi* bidi, int pos) const override
```
获取 Bidi 方向、长度和级别信息,分别调用对应的 ICU 库函数。

### 视觉重排
```cpp
void bidi_reorderVisual(const SkUnicode::BidiLevel runLevels[],
                        int levelsCount,
                        int32_t logicalFromVisual[]) const override
```
将逻辑顺序的运行级别重排为视觉顺序,调用 `SkGetICULib()->f_ubidi_reorderVisual()`。

**特殊处理:**
- `levelsCount == 0` 时直接返回,避免 ICU 内部断言失败

## 内部实现细节

### 动态函数指针调用
所有实现通过 `SkGetICULib()` 获取 ICU 库函数指针:

```cpp
const char* SkBidiICUFactory::errorName(UErrorCode status) const {
    return SkGetICULib()->f_u_errorName(status);
}

UBiDiDirection SkBidiICUFactory::bidi_getDirection(const UBiDi* bidi) const {
    return SkGetICULib()->f_ubidi_getDirection(bidi);
}

UBiDi* SkBidiICUFactory::bidi_openSized(...) const {
    return SkGetICULib()->f_ubidi_openSized(maxLength, maxRunCount, pErrorCode);
}
```

**实现特点:**
- 每次调用都通过函数指针间接调用
- `SkGetICULib()` 返回全局 ICU 库接口结构体
- 支持延迟加载和动态库版本兼容

### 边界条件处理
与子集版本相同,处理空数组的特殊情况:

```cpp
void SkBidiICUFactory::bidi_reorderVisual(...) const {
    if (levelsCount == 0) {
        // To avoid an assert in unicode
        return;
    }
    SkASSERT(runLevels != nullptr);
    SkGetICULib()->f_ubidi_reorderVisual(runLevels, levelsCount, logicalFromVisual);
}
```

### ICU 库动态加载
`SkGetICULib()` 实现(在 `SkUnicode_icupriv.cpp` 中):
- 首次调用时加载系统 ICU 动态库
- 解析所有需要的函数符号
- 缓存函数指针供后续调用
- 支持多个 ICU 版本的兼容性

## 依赖关系

### 核心依赖
- **SkBidiFactory**: Bidi 工厂抽象接口
- **SkGetICULib()**: ICU 库动态加载接口
- **系统 ICU 库**: libicuuc 动态库
- **unicode/ubidi.h**: ICU Bidi 类型定义

### 使用者
- **SkUnicode_icu**: ICU Unicode 实现
- **Paragraph**: 段落布局系统
- **TextLine**: 文本行,使用 Bidi 重排

### 依赖图
```
SkBidiICUFactory
    ↓ (calls)
SkGetICULib() → 系统 ICU 库 (libicuuc.so)
    ↓ (used by)
SkUnicode_icu → Paragraph
```

## 设计模式与设计决策

### 工厂模式
与子集版本共享相同的工厂模式设计:
- 抽象接口定义 Bidi 操作
- 具体工厂实现选择 ICU 版本
- 客户端代码不依赖具体实现

### 适配器模式
该类适配系统 ICU 库:
- 统一 Skia 的 Bidi 接口
- 隐藏动态加载细节
- 版本兼容性处理

### 延迟加载
通过 `SkGetICULib()` 实现延迟加载:
- 首次使用时才加载 ICU 库
- 减少启动开销
- 允许运行时库选择

## 性能考量

### 函数指针间接调用开销
- 每次调用都通过函数指针,无法内联
- 额外的一次内存间接访问
- 通常可以被 CPU 分支预测优化
- 相比子集版本,性能损失约 5-10%

### 动态库加载
- **优势**: 共享系统资源,减少内存占用
- **优势**: 系统级更新,安全修复自动生效
- **劣势**: 首次加载有初始化开销
- **劣势**: 符号解析可能失败

### 版本兼容性
- 支持多个 ICU 主版本
- 运行时检测和适配
- 可能有轻微的版本检测开销

### 内存占用
- 工厂对象本身无状态
- 共享系统 ICU 库的代码和数据段
- 对于多进程系统,内存共享更高效

## 与子集版本对比

| 特性 | 子集版本 | 完整版本 |
|------|---------|---------|
| 二进制大小 | 较小(内置精简ICU) | 较大(动态库依赖) |
| 依赖关系 | 自包含,无外部依赖 | 依赖系统ICU库 |
| 性能 | 直接调用,可内联 | 函数指针间接调用 |
| 内存占用 | 每个进程独立 | 多进程共享 |
| 更新机制 | 随Skia更新 | 随系统更新 |
| 版本控制 | 固定版本 | 运行时版本 |
| 兼容性 | 完全控制 | 需要版本适配 |

**选择建议:**
- **嵌入式/移动应用**: 优先选择子集版本,减少依赖
- **桌面应用**: 优先选择完整版本,共享系统资源
- **二进制大小敏感**: 选择子集版本
- **需要系统级更新**: 选择完整版本

## 相关文件

### 接口定义
- `modules/skunicode/src/SkUnicode_icu_bidi.h`: Bidi 工厂基类
- `modules/skunicode/src/SkUnicode_icupriv.h`: ICU 私有接口和动态加载

### 替代实现
- `modules/skunicode/src/SkBidiFactory_icu_subset.h/.cpp`: ICU 子集实现

### 使用方
- `modules/skunicode/src/SkUnicode_icu.cpp`: ICU Unicode 实现
- `modules/skparagraph/src/ParagraphImpl.cpp`: 段落实现
- `modules/skparagraph/src/TextLine.cpp`: 文本行实现

### ICU 头文件
- `unicode/ubidi.h`: Bidi 类型和常量定义
- `unicode/utypes.h`: ICU 基础类型定义
