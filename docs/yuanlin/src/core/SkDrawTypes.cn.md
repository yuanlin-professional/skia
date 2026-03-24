# SkDrawTypes

> 源文件
> - src/core/SkDrawTypes.h

## 概述

`SkDrawTypes` 是一个轻量级的类型定义头文件，为 Skia 核心绘制系统提供共享的枚举类型和常量。它定义了绘制覆盖类型（`SkDrawCoverage`）和着色器上下文的标准栈大小常量（`kSkBlitterContextSize`）。该文件的设计目标是集中管理跨多个绘制模块使用的基础类型，避免重复定义并提高代码可维护性。

## 架构位置

该头文件位于 `src/core` 核心层，是私有实现细节（不在 `include/` 公共目录中）。它被绘制系统的多个模块包含，包括 `SkDraw`、`SkBlitter`、`SkScan` 等。作为类型定义文件，它处于依赖树的底层，不依赖其他Skia类，只依赖C++标准库的 `<cstddef>`。

## 主要类与结构体

该文件不定义类或结构体，仅定义枚举类型和常量。

### SkDrawCoverage 枚举

```cpp
enum class SkDrawCoverage : bool {
    kNo = false,
    kYes = true,
};
```

用于指示绘制操作是否需要计算覆盖率（coverage）。

| 枚举值 | 底层值 | 说明 |
|--------|--------|------|
| `kNo` | `false` | 不需要覆盖率（全覆盖或二值覆盖） |
| `kYes` | `true` | 需要覆盖率计算（抗锯齿、部分覆盖） |

**设计特点：**
- 使用 `bool` 作为底层类型，在内存中仅占1字节
- 枚举类（enum class）提供类型安全，防止隐式转换
- 语义明确，比直接使用 `bool` 更具可读性

### kSkBlitterContextSize 常量

```cpp
constexpr size_t kSkBlitterContextSize = 3332;
```

定义用于在栈上创建着色器上下文的推荐缓冲区大小。

**用途：**
- 为 `SkSTArenaAlloc<kSkBlitterContextSize>` 提供模板参数
- 避免堆分配，提高小型绘制操作的性能
- 值（3332字节）基于实际测量的典型着色器上下文大小

**相关使用场景：**
```cpp
SkSTArenaAlloc<kSkBlitterContextSize> alloc;
SkBlitter* blitter = SkBlitter::Choose(fDst, *fCTM, paint, &alloc, ...);
```

## 公共 API 函数

该文件不包含函数定义。

## 内部实现细节

### SkDrawCoverage 的使用场景

**抗锯齿判断：**
在 `SkBlitter::Choose()` 中，根据 `SkDrawCoverage` 参数选择不同的blitter实现：
- `kNo`：使用 `SkARGB32_Blitter`（快速路径，无alpha混合）
- `kYes`：使用 `SkARGB32_Shader_Blitter`（计算部分覆盖）

**路径填充：**
扫描线填充器根据抗锯齿设置传递相应的覆盖类型：
```cpp
SkDrawCoverage coverage = paint.isAntiAlias() ? SkDrawCoverage::kYes : SkDrawCoverage::kNo;
```

### kSkBlitterContextSize 的计算依据

该值是经验常量，基于以下考虑：

1. **典型着色器大小：**
   - `SkBitmapProcShader` 上下文：约1200字节
   - `SkGradientShaderBase` 上下文：约800字节
   - `SkPictureShader` 上下文：约1500字节

2. **组合着色器：**
   - `SkComposeShader` 可能嵌套多个子着色器
   - 3332字节足以容纳2-3个复杂着色器的组合

3. **栈限制：**
   - 在大多数平台上，默认线程栈为1-8MB
   - 3332字节（约3.3KB）是安全的栈分配大小

4. **性能权衡：**
   - 更大的值可以处理更复杂的场景
   - 更小的值节省栈空间
   - 3332是实测的平衡点

如果实际需要超过此大小，`SkSTArenaAlloc` 会自动回退到堆分配。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `<cstddef>` | `size_t` 类型定义 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| `src/core/SkBlitter.cpp` | 使用 `SkDrawCoverage` 选择blitter |
| `src/core/SkDraw_text.cpp` | 使用 `kSkBlitterContextSize` 分配上下文 |
| `src/core/SkScan.cpp` | 使用 `SkDrawCoverage` 判断扫描方式 |
| `src/core/SkCoreBlitters.h` | 在blitter构造函数中使用覆盖类型 |

## 设计模式与设计决策

**集中定义原则：** 将跨模块共享的类型集中在一个头文件中，遵循DRY（Don't Repeat Yourself）原则。这避免了循环依赖和重复定义的问题。

**类型安全：** 使用 `enum class` 而非 `#define` 或原始 `bool`，提供编译期类型检查。与C风格枚举不同，`enum class` 不会隐式转换为整数。

**布尔底层类型：** `SkDrawCoverage` 使用 `bool` 作为底层类型是罕见但合理的设计：
- 内存高效（1字节）
- 语义匹配（二值选择）
- 可以直接用于条件判断（需显式转换）

**constexpr常量：** `kSkBlitterContextSize` 使用 `constexpr` 而非 `#define`：
- 有类型信息（`size_t`）
- 遵守作用域规则
- 可以在模板参数中使用

**最小化依赖：** 仅包含 `<cstddef>`，避免引入不必要的头文件，减少编译时间。

**命名约定：**
- 枚举使用 `k` 前缀（如 `kYes`）遵循Skia风格
- 常量使用 `k` 前缀和驼峰命名（如 `kSkBlitterContextSize`）
- 类型名使用 `Sk` 前缀

## 性能考量

**内存布局：** `SkDrawCoverage` 占用1字节，通常会因对齐而占用4-8字节。在结构体中放置多个 `SkDrawCoverage` 时，编译器可能紧密打包它们。

**分支预测：** `SkDrawCoverage` 的二值特性使得基于它的条件分支易于预测。在循环中，分支通常是稳定的（全部抗锯齿或全部非抗锯齿）。

**栈分配优势：** `kSkBlitterContextSize` 启用的栈分配避免了以下开销：
- `malloc/free` 调用（通常数百个CPU周期）
- 内存碎片
- 缓存失效（栈数据通常在L1缓存中）

**编译期计算：** `constexpr` 保证 `kSkBlitterContextSize` 在编译期已知，模板实例化不会产生运行时开销。

**内联友好：** 类型定义不包含代码，包含此头文件不会增加二进制大小。所有使用都会被编译器内联。

## 相关文件

| 文件路径 | 关系说明 |
|---------|---------|
| `src/core/SkBlitter.h` | 主要消费者，使用 `SkDrawCoverage` |
| `src/core/SkDraw.h` | 使用 `kSkBlitterContextSize` |
| `src/base/SkArenaAlloc.h` | 定义 `SkSTArenaAlloc` 模板类 |
| `src/core/SkCoreBlitters.h` | Blitter实现，依赖覆盖类型 |
| `src/core/SkScan.cpp` | 扫描线填充，使用覆盖标志 |
