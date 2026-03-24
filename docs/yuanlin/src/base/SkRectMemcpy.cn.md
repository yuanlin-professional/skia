# SkRectMemcpy

> 源文件: src/base/SkRectMemcpy.h

## 概述

`SkRectMemcpy` 是 Skia 中用于高效复制矩形区域内存数据的工具函数。它专门优化了图像处理中常见的二维数据拷贝场景，支持源和目标数据具有不同的行跨度（row stride）。该函数能够智能地选择一次性批量拷贝（当内存连续时）或逐行拷贝（当存在行间隙时），是像素数据操作的基础工具。

这个单一但重要的函数广泛应用于像素缓冲区拷贝、图像裁剪、纹理上传等需要处理二维数据块的场景。

## 架构位置

`SkRectMemcpy` 位于 Skia 基础设施层的内存操作模块中：

- **层级**: src/base（基础工具层）
- **用途**: 提供高效的矩形区域内存拷贝
- **应用场景**: 像素数据拷贝、图像操作、纹理传输

在 Skia 架构中，它是底层内存操作工具，被像素映射、位图、表面、编解码器等模块广泛使用。

## 主要类与结构体

该文件仅包含一个内联函数，无类定义。

## 公共 API 函数

### SkRectMemcpy - 矩形内存拷贝

```cpp
static inline void SkRectMemcpy(void* dst, size_t dstRB,
                                 const void* src, size_t srcRB,
                                 size_t trimRowBytes, int rowCount);
```

将矩形区域的数据从源地址复制到目标地址。

**参数**:

| 参数 | 类型 | 说明 |
|-----|------|------|
| `dst` | `void*` | 目标内存起始地址 |
| `dstRB` | `size_t` | 目标行跨度（Row Bytes，每行占用的字节数） |
| `src` | `const void*` | 源内存起始地址 |
| `srcRB` | `size_t` | 源行跨度 |
| `trimRowBytes` | `size_t` | 每行实际复制的字节数（≤ dstRB 且 ≤ srcRB） |
| `rowCount` | `int` | 要复制的行数 |

**前置条件**（通过断言检查）:
- `trimRowBytes <= dstRB`
- `trimRowBytes <= srcRB`

## 内部实现细节

### 完整实现

```cpp
static inline void SkRectMemcpy(void* dst, size_t dstRB, const void* src, size_t srcRB,
                                size_t trimRowBytes, int rowCount) {
    SkASSERT(trimRowBytes <= dstRB);
    SkASSERT(trimRowBytes <= srcRB);

    // 快速路径: 内存连续
    if (trimRowBytes == dstRB && trimRowBytes == srcRB) {
        memcpy(dst, src, trimRowBytes * rowCount);
        return;
    }

    // 慢速路径: 逐行复制
    for (int i = 0; i < rowCount; ++i) {
        memcpy(dst, src, trimRowBytes);
        dst = SkTAddOffset<void>(dst, dstRB);
        src = SkTAddOffset<const void>(src, srcRB);
    }
}
```

### 算法流程

#### 快速路径（内存连续）

**条件**: `trimRowBytes == dstRB && trimRowBytes == srcRB`

**含义**:
- 每行实际数据占满整个行跨度
- 源和目标都没有行间隙
- 数据在内存中是连续的

**优化**:
- 单次 `memcpy` 拷贝所有数据
- 总字节数: `trimRowBytes * rowCount`
- 性能最优，利用 `memcpy` 的硬件优化（如 SIMD）

**示例**:
```
源数据:   [AAAA][BBBB][CCCC]  (srcRB = 4, trimRowBytes = 4)
目标数据: [....][....][....]  (dstRB = 4)
结果:     一次性拷贝 12 字节
```

#### 慢速路径（逐行拷贝）

**条件**: `trimRowBytes < dstRB || trimRowBytes < srcRB`

**含义**:
- 存在行间隙（padding）或只复制部分列
- 源或目标的行跨度大于实际数据宽度

**实现**:
- 循环 `rowCount` 次
- 每次拷贝 `trimRowBytes` 字节
- 使用 `SkTAddOffset` 移动到下一行

**示例**:
```
源数据 (srcRB=6):   [AAA...][BBB...][CCC...]
目标数据 (dstRB=5): [.....]  [.....]  [.....]
trimRowBytes=3:      复制    复制    复制
                    [AAA..]  [BBB..]  [CCC..]
```

### SkTAddOffset 辅助函数

```cpp
template<typename T>
T* SkTAddOffset(T* ptr, size_t offset);
```

**功能**: 将指针 `ptr` 向后移动 `offset` 字节

**实现**: `reinterpret_cast<T*>(reinterpret_cast<uintptr_t>(ptr) + offset)`

**作用**: 安全地进行指针算术运算，支持 `void*` 类型

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `<cstring>` | `memcpy` 函数 |
| `SkAssert.h` | 断言宏 |
| `SkTemplates.h` | `SkTAddOffset` 模板函数 |

### 被依赖的模块

`SkRectMemcpy` 作为基础内存操作工具，被以下模块使用：

| 使用场景 | 说明 |
|---------|------|
| `SkPixmap` | 像素映射的数据拷贝 |
| `SkBitmap` | 位图的数据传输 |
| `SkImage` | 图像数据的读取和写入 |
| `SkSurface` | 表面内容的复制 |
| `SkCodec` | 解码器输出数据 |
| `GrTexture` | GPU 纹理上传/下载 |
| `SkMask` | 掩码数据操作 |

## 设计模式与设计决策

### 设计模式

1. **内联函数**:
   - 定义在头文件中，`static inline`
   - 编译器可完全内联，零函数调用开销

2. **快速路径优化**:
   - 先检查最优情况（连续内存）
   - 再回退到通用情况（逐行拷贝）

3. **模板辅助**:
   - 使用 `SkTAddOffset` 处理指针算术
   - 支持 `void*` 类型

### 设计决策

1. **支持不同的行跨度**:
   - 原因: 图像数据常有内存对齐需求（如 4 字节对齐）
   - 应用: 裁剪、ROI（感兴趣区域）操作

2. **断言前置条件**:
   - 检查 `trimRowBytes` 不超过行跨度
   - 原因: 防止内存越界，早期发现错误

3. **不检查指针有效性**:
   - 假设调用者提供有效指针
   - 原因: 性能考虑，避免每次调用都检查

4. **使用标准 memcpy**:
   - 而非自定义拷贝循环
   - 原因: `memcpy` 有高度优化的实现（SIMD、硬件加速）

5. **int 类型的 rowCount**:
   - 而非 `size_t`
   - 原因: 图像高度通常是 int，避免类型转换

6. **void* 参数类型**:
   - 支持任意数据类型
   - 调用者负责确保类型正确

7. **static inline 而非头文件内联**:
   - `static` 避免多重定义链接错误
   - `inline` 建议编译器内联

## 性能考量

### 性能特征

**快速路径**（内存连续）:
- 延迟: 取决于数据大小和 `memcpy` 实现
- 典型速度: 10-30 GB/s（现代 CPU）
- 利用: SIMD 指令、非临时存储、预取

**慢速路径**（逐行拷贝）:
- 额外开销: 循环控制 + 指针更新
- 每次循环: 约 5-10 ns（循环开销）
- 总开销: `rowCount * 循环开销 + memcpy 时间`

### 优化效果

假设复制 1920×1080 的 RGBA 像素数据：

| 场景 | 方法 | 时间估算 |
|------|------|----------|
| 连续内存 | 快速路径 | ~0.3 ms（单次 8MB 拷贝） |
| 有行间隙 | 慢速路径 | ~0.4 ms（1080 次小拷贝） |
| 朴素循环 | 逐像素拷贝 | ~5 ms（2M 次循环） |

**提升**: 相比朴素循环提升约 10-15 倍

### 行跨度对齐的影响

**对齐的行跨度**（如 4 字节对齐）:
- 优点: CPU 访问对齐地址更快
- 优点: SIMD 指令要求对齐
- 缺点: 可能需要逐行拷贝（若有 padding）

**紧凑的行跨度**（无 padding）:
- 优点: 可能触发快速路径
- 缺点: 可能不满足 GPU 对齐要求

### 使用建议

1. **尽量使用连续内存**:
   - 设计数据结构时考虑避免 padding
   - 或使用相同的行跨度

2. **批量操作**:
   - 一次拷贝整个矩形而非多次小拷贝
   - 利用快速路径

3. **注意缓存效率**:
   - 大数据量时，逐行拷贝可能更缓存友好
   - 连续拷贝可能污染缓存

4. **避免不必要的拷贝**:
   - 考虑零拷贝技术（共享内存）
   - 使用引用/指针传递数据

### 典型用例

#### 位图拷贝

```cpp
void copyBitmap(SkBitmap& dst, const SkBitmap& src) {
    SkRectMemcpy(dst.getPixels(), dst.rowBytes(),
                 src.getPixels(), src.rowBytes(),
                 src.width() * src.bytesPerPixel(),
                 src.height());
}
```

#### 裁剪区域拷贝

```cpp
void copyROI(uint8_t* dst, size_t dstStride,
             const uint8_t* src, size_t srcStride,
             int x, int y, int width, int height, int bytesPerPixel) {
    const uint8_t* srcRow = src + y * srcStride + x * bytesPerPixel;
    SkRectMemcpy(dst, dstStride,
                 srcRow, srcStride,
                 width * bytesPerPixel,
                 height);
}
```

#### 纹理上传

```cpp
void uploadTexture(void* gpuPtr, size_t gpuPitch,
                   const void* cpuData, size_t cpuPitch,
                   int width, int height, int bytesPerPixel) {
    SkRectMemcpy(gpuPtr, gpuPitch,
                 cpuData, cpuPitch,
                 width * bytesPerPixel,
                 height);
}
```

## 边界情况处理

1. **rowCount = 0**:
   - 循环不执行，快速返回
   - 无副作用

2. **trimRowBytes = 0**:
   - 技术上合法（拷贝 0 字节）
   - `memcpy(dst, src, 0)` 是无操作

3. **dst == src**:
   - `memcpy` 处理（未定义行为，但通常工作）
   - 建议使用 `memmove` 处理重叠区域（但 SkRectMemcpy 不支持）

4. **极大的 rowCount**:
   - 可能溢出 `trimRowBytes * rowCount`
   - 调用者负责确保合理的参数

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `include/private/base/SkTemplates.h` | 提供 `SkTAddOffset` 模板函数 |
| `include/private/base/SkAssert.h` | 断言宏定义 |
| `include/core/SkPixmap.h` | 像素映射类，使用 SkRectMemcpy |
| `src/core/SkBitmap.cpp` | 位图实现，使用 SkRectMemcpy |
| `src/codec/SkCodec.cpp` | 解码器，使用 SkRectMemcpy 输出数据 |
| `src/gpu/ganesh/GrTexture.cpp` | GPU 纹理操作 |
