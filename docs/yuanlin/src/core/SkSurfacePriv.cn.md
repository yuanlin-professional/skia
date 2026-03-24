# SkSurfacePriv

> 源文件: src/core/SkSurfacePriv.h

## 概述

`SkSurfacePriv` 是 Skia 图形库中 `SkSurface` 的私有辅助工具头文件。它提供了 Surface 创建和验证过程中使用的内部工具函数和常量定义。主要包括 Surface 属性的默认值处理、光栅化 Surface 参数验证等功能。这是一个轻量级的工具模块,为 Surface 相关的内部实现提供通用功能。

## 架构位置

`SkSurfacePriv` 位于 Surface 模块的内部实现层,为 Surface 的各种实现(光栅、GPU、图像等)提供共享的私有工具。

```
Surface 架构:
  公共 API
    SkSurface (include/core/SkSurface.h)
    ↓
  私有工具层
    SkSurfacePriv (src/core/SkSurfacePriv.h) ← 本文件
    ↓
  具体实现
    ├─ SkSurface_Raster
    ├─ SkSurface_Gpu
    └─ SkSurface_Image
```

## 主要类与结构体

### 常量定义

| 常量名 | 值 | 说明 |
|-------|---|------|
| `kIgnoreRowBytesValue` | `static_cast<size_t>(~0)` | 表示"忽略行字节数"的特殊值 |

**用途:**
在某些 Surface 创建函数中,如果不关心行字节数(rowBytes)的具体值,可以传入此常量。实现会自动计算合适的行字节数。

**示例场景:**
```cpp
// 用户不指定 rowBytes,系统自动计算
SkSurfaceValidateRasterInfo(imageInfo, kIgnoreRowBytesValue);
```

## 公共 API 函数

### SkSurfacePropsCopyOrDefault

```cpp
static inline SkSurfaceProps SkSurfacePropsCopyOrDefault(const SkSurfaceProps* props) {
    return props ? *props : SkSurfaceProps();
}
```

**功能:**
- 如果提供了 `props` 指针,返回其副本
- 如果 `props` 为 `nullptr`,返回默认构造的 `SkSurfaceProps`

**参数:**
- `props`: 指向 `SkSurfaceProps` 的指针(可为 null)

**返回值:**
- `SkSurfaceProps` 对象(按值返回)

**使用场景:**
在 Surface 创建函数中处理可选的 Surface 属性参数:
```cpp
SkSurface::MakeRaster(const SkImageInfo& info, const SkSurfaceProps* props) {
    SkSurfaceProps finalProps = SkSurfacePropsCopyOrDefault(props);
    // 使用 finalProps
}
```

**设计优势:**
- 简化调用方代码:避免重复的空指针检查
- 统一默认值处理:确保所有地方使用相同的默认值
- 性能友好:内联函数,无额外开销

### SkSurfaceValidateRasterInfo

```cpp
bool SkSurfaceValidateRasterInfo(const SkImageInfo& info, size_t rb = kIgnoreRowBytesValue);
```

**功能:**
验证光栅化 Surface 的图像信息和行字节数是否有效。

**参数:**
- `info`: 图像信息(宽度、高度、颜色类型、alpha 类型等)
- `rb`: 行字节数(可选,默认为 `kIgnoreRowBytesValue`)

**返回值:**
- `true`: 参数有效,可以创建 Surface
- `false`: 参数无效,不应创建 Surface

**验证内容:**
1. **宽度和高度**: 必须大于 0 且在合理范围内
2. **颜色类型**: 必须是支持的颜色类型
3. **Alpha 类型**: 必须与颜色类型兼容
4. **行字节数**: 如果指定,必须足够大且对齐正确

**使用场景:**
```cpp
bool createRasterSurface(const SkImageInfo& info, size_t rowBytes) {
    if (!SkSurfaceValidateRasterInfo(info, rowBytes)) {
        return false;  // 参数无效
    }
    // 继续创建 Surface
}
```

**错误检测示例:**
- 宽度或高度为 0 或负数
- 行字节数小于图像宽度所需的最小值
- 行字节数导致总内存大小溢出
- 颜色类型不支持光栅化渲染

## 内部实现细节

### kIgnoreRowBytesValue 的设计

```cpp
constexpr size_t kIgnoreRowBytesValue = static_cast<size_t>(~0);
```

**为何使用 `~0`?**
- **最大值**: `size_t` 类型的所有位都是 1,表示最大可能值
- **不可能的值**: 实际行字节数不可能是最大 `size_t` 值
- **易于识别**: 调试时容易发现未正确处理的情况

**替代方案为何不适用:**
- `0`: 可能是有效值(宽度为 0 的图像)
- `-1`: `size_t` 是无符号类型,会转换为最大值(实际等价)
- 特殊枚举: 引入额外类型复杂度

### SkSurfaceProps 的角色

`SkSurfaceProps` 封装了影响渲染质量的属性:
- **像素几何**: LCD 子像素布局(RGB/BGR/无)
- **抗锯齿**: 是否使用子像素抗锯齿
- **字体渲染**: 文本渲染提示

**默认构造:**
```cpp
SkSurfaceProps() {
    // 使用平台默认设置
    // 通常禁用子像素渲染
}
```

### 光栅化验证的重要性

**为何需要验证?**
1. **防止崩溃**: 无效参数可能导致内存访问越界
2. **防止溢出**: 计算总内存大小时避免整数溢出
3. **资源保护**: 避免分配不合理的巨大内存
4. **早期失败**: 在创建 Surface 前而非使用时失败

**典型验证逻辑:**
```cpp
// 伪代码
bool validate(width, height, colorType, rowBytes) {
    if (width <= 0 || height <= 0) return false;
    if (!isSupportedColorType(colorType)) return false;

    size_t minRowBytes = width * bytesPerPixel(colorType);
    if (rowBytes != kIgnoreRowBytesValue) {
        if (rowBytes < minRowBytes) return false;
        if (rowBytes * height > kMaxAllocationSize) return false;
    }
    return true;
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkSurfaceProps` | Surface 属性定义 |
| `SkImageInfo` | 图像信息描述 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| `SkSurface_Raster` | 验证光栅化参数 |
| `SkSurface_Gpu` | 可能使用属性处理工具 |
| Surface 创建函数 | 使用默认属性处理 |
| 单元测试 | 测试参数验证逻辑 |

## 设计模式与设计决策

### 设计模式

1. **工具类模式**: 提供静态工具函数
2. **默认值模式**: 简化可选参数处理
3. **验证模式**: 早期参数验证,快速失败

### 设计决策

**1. 为何使用内联函数?**
- 函数体极小(1-2 行)
- 避免函数调用开销
- 便于编译器优化

**2. 为何返回 SkSurfaceProps 副本而非指针?**
- 避免生命周期管理问题
- 调用方不需要关心内存所有权
- 值语义更安全

**3. 为何 rowBytes 参数有默认值?**
- 大多数情况不需要指定
- 保持 API 简洁
- 向后兼容性

**4. 为何不使用 std::optional?**
- Skia 需要支持 C++14(较老的编译器)
- 使用 `nullptr` 和特殊值更轻量
- 避免引入额外的模板复杂度

**5. 为何是私有头文件?**
- 这些工具只在 Skia 内部使用
- 不作为公共 API 的一部分
- 允许未来修改而不影响用户代码

## 性能考量

### 性能特点

1. **零开销内联**: 所有函数都是内联的,编译后无函数调用
2. **按值返回优化**: 编译器可以应用 RVO (返回值优化)
3. **验证成本**: `SkSurfaceValidateRasterInfo` 主要是简单的整数比较

### 性能影响

- **SkSurfacePropsCopyOrDefault**: ~0 ns (完全内联)
- **SkSurfaceValidateRasterInfo**: ~5-10 ns (几个条件检查)

**权衡:**
验证的少量开销换取了安全性和正确性,对于 Surface 创建这种非热路径操作,完全可以接受。

### 内存考量

- **SkSurfaceProps 大小**: 通常 8-16 字节(取决于成员)
- **按值返回**: 小对象按值返回通常比指针更高效(寄存器传递)

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `include/core/SkSurface.h` | Surface 公共 API |
| `include/core/SkSurfaceProps.h` | Surface 属性定义 |
| `include/core/SkImageInfo.h` | 图像信息描述 |
| `src/core/SkSurface_Base.h` | Surface 基类 |
| `src/image/SkSurface_Raster.cpp` | 光栅 Surface 实现 |
| `src/image/SkSurface_Gpu.cpp` | GPU Surface 实现 |
| `tests/SurfaceTest.cpp` | Surface 单元测试 |

## 使用示例

### 示例 1: 创建 Surface 时处理可选属性

```cpp
sk_sp<SkSurface> createSurface(const SkImageInfo& info,
                                const SkSurfaceProps* props) {
    // 使用工具函数处理可选属性
    SkSurfaceProps finalProps = SkSurfacePropsCopyOrDefault(props);

    // 验证参数
    if (!SkSurfaceValidateRasterInfo(info)) {
        return nullptr;
    }

    // 创建 Surface
    return SkSurfaces::Raster(info, &finalProps);
}
```

### 示例 2: 验证自定义 rowBytes

```cpp
bool tryCreateWithRowBytes(const SkImageInfo& info, size_t rowBytes) {
    // 验证指定的 rowBytes 是否有效
    if (!SkSurfaceValidateRasterInfo(info, rowBytes)) {
        SkDebugf("Invalid parameters: %d x %d, rowBytes: %zu\n",
                 info.width(), info.height(), rowBytes);
        return false;
    }

    // 参数有效,继续处理
    return true;
}
```

### 示例 3: 忽略 rowBytes

```cpp
void quickValidation(const SkImageInfo& info) {
    // 只验证 ImageInfo,不关心 rowBytes
    if (SkSurfaceValidateRasterInfo(info)) {
        SkDebugf("ImageInfo is valid\n");
    }
}
```
