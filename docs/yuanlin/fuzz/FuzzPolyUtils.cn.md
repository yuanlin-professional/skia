# FuzzPolyUtils

> 源文件: fuzz/FuzzPolyUtils.cpp

## 概述

FuzzPolyUtils 是一个专门用于模糊测试多边形实用工具函数的模块。该文件测试 `SkPolyUtils` 命名空间中的各种多边形处理算法,包括卷绕方向检测、凸性判断、简单多边形判定、凸多边形内缩以及三角剖分等功能。通过生成随机多边形并对其进行各种操作,验证这些算法在处理退化情况、极端输入时的健壮性。

## 架构位置

```
skia/
  ├── fuzz/                          # 模糊测试根目录
  │   ├── FuzzPolyUtils.cpp         # 本文件:多边形工具测试
  │   ├── FuzzTriangulation.cpp     # GPU 三角剖分测试
  │   └── FuzzCommon.h              # 通用测试辅助函数
  ├── src/utils/                     # 工具函数库
  │   └── SkPolyUtils.h/cpp         # 多边形处理工具
  └── include/core/                  # 核心类型
      └── SkPoint.h                 # 点和向量定义
```

多边形处理是图形学中的基础操作,广泛应用于阴影渲染、路径填充和碰撞检测等场景。

## 主要类与结构体

### 核心依赖

**SkPolyUtils** (`src/utils/SkPolyUtils.h`)
- **关键函数**:
  - `SkGetPolygonWinding()`: 计算多边形卷绕方向(顺时针/逆时针)
  - `SkIsConvexPolygon()`: 判断是否为凸多边形
  - `SkIsSimplePolygon()`: 判断是否为简单多边形(无自交)
  - `SkInsetConvexPolygon()`: 对凸多边形进行内缩
  - `SkOffsetSimplePolygon()`: 对简单多边形进行偏移
  - `SkTriangulateSimplePolygon()`: 将简单多边形三角剖分

### 辅助函数

**sanitize_point**
```cpp
static SkPoint sanitize_point(const SkPoint& in)
```
- **作用**: 将点坐标钳制到最近的 1/16 像素
- **目的**: 避免浮点精度问题导致的不稳定行为
- **实现**: 四舍五入到 0.0625 的倍数

**ignoreResult**
```cpp
void inline ignoreResult(bool)
```
- **作用**: 显式忽略函数返回值
- **目的**: 避免编译器警告,表明测试只关心"不崩溃"

## 公共 API 函数

### DEF_FUZZ(PolyUtils, fuzz)

```cpp
DEF_FUZZ(PolyUtils, fuzz)
```

**功能**: 模糊测试多边形工具函数的健壮性

**实现流程**:

1. **生成随机多边形**
   ```cpp
   int count;
   fuzz->nextRange(&count, 0, 512);  // 0-512 个顶点
   AutoSTMalloc<64, SkPoint> polygon(count);
   for (int index = 0; index < count; ++index) {
       fuzz->next(&polygon[index].fX, &polygon[index].fY);
       polygon[index] = sanitize_point(polygon[index]);
   }
   ```

2. **计算边界框**
   ```cpp
   const auto bounds = SkRect::BoundsOrEmpty({polygon.data(), (size_t)count});
   ```

3. **测试基本属性**
   ```cpp
   ignoreResult(SkGetPolygonWinding(polygon, count));
   bool isConvex = SkIsConvexPolygon(polygon, count);
   bool isSimple = SkIsSimplePolygon(polygon, count);
   ```

4. **条件性测试高级操作**
   - 凸多边形 → 测试内缩
   - 简单多边形 → 测试偏移和三角剖分

**测试覆盖范围**:
- 空多边形(0 个顶点)
- 退化情况(1-2 个顶点)
- 常规多边形(3-100 个顶点)
- 大型多边形(100-512 个顶点)
- 凸/凹/自交多边形
- 共线点、重复点

## 内部实现细节

### 点坐标量化

```cpp
static SkPoint sanitize_point(const SkPoint& in) {
    SkPoint out;
    out.fX = SkScalarRoundToScalar(16.f*in.fX)*0.0625f;
    out.fY = SkScalarRoundToScalar(16.f*in.fY)*0.0625f;
    return out;
}
```

**设计理由**:
- **减少浮点误差**: 避免极小的坐标差异导致不可预测的行为
- **提高稳定性**: 量化后的坐标更容易复现问题
- **保持精度**: 1/16 像素对于图形渲染足够精确

### 凸多边形内缩测试

```cpp
if (isConvex) {
    SkScalar inset;
    fuzz->next(&inset);
    ignoreResult(SkInsetConvexPolygon(polygon, count, inset, &output));
}
```

**测试场景**:
- 正内缩(缩小多边形)
- 负内缩(扩大多边形,可能变为非凸)
- 极大内缩(可能导致多边形退化)
- NaN/Inf 内缩值

### 简单多边形偏移测试

```cpp
if (isSimple) {
    SkScalar offset;
    fuzz->nextRange(&offset, -1000, 1000);  // 限制范围防止超时
    ignoreResult(SkOffsetSimplePolygon(polygon, count, bounds, offset, &output));
}
```

**关键优化**:
- **范围限制**: 偏移量限制在 [-1000, 1000] 防止算法超时
- **边界框传递**: 提供边界框加速计算
- **注释说明**: 明确指出范围来自阴影算法的实际需求

### 三角剖分测试

```cpp
AutoSTMalloc<64, uint16_t> indexMap(count);
for (int index = 0; index < count; ++index) {
    fuzz->next(&indexMap[index]);
}
SkTDArray<uint16_t> outputIndices;
ignoreResult(SkTriangulateSimplePolygon(polygon, indexMap, count, &outputIndices));
```

**索引映射的作用**:
- 允许重用顶点(减少内存占用)
- 支持复杂的顶点拓扑
- 测试索引越界处理

### 编译条件保护

```cpp
#if !defined(SK_ENABLE_OPTIMIZE_SIZE)
DEF_FUZZ(PolyUtils, fuzz) {
    // ... 实际测试代码
}
#else
DEF_FUZZ(PolyUtils, fuzz) {}  // 空实现
#endif
```

**设计理由**:
- 优化尺寸构建时禁用复杂的多边形算法
- 避免在嵌入式环境中增加二进制体积
- 保持构建系统的一致性

## 依赖关系

### 直接依赖

- **SkPolyUtils** (`src/utils/SkPolyUtils.h`)
  - 核心测试目标
  - 提供所有多边形处理函数

- **Fuzz** (`fuzz/Fuzz.h`)
  - 模糊测试框架
  - 提供随机数生成接口

- **SkPoint** (`include/core/SkPoint.h`)
  - 点和向量的基础类型

### 间接依赖

- **SkTDArray** (`include/private/base/SkTDArray.h`)
  - 动态数组容器
  - 存储输出结果

- **AutoSTMalloc** (`include/private/base/SkTemplates.h`)
  - 自动内存管理模板
  - 栈优先的动态内存分配

- **skia_private 命名空间**
  - 私有实现细节的命名空间隔离

## 设计模式与设计决策

### 设计模式

1. **策略测试模式**
   - 根据多边形类型(凸/简单)选择不同测试路径
   - 避免对不适用的情况进行无效测试

2. **渐进式测试**
   - 先测试基本属性(卷绕、凸性)
   - 再测试复杂操作(内缩、三角剖分)
   - 逐步增加测试难度

### 设计决策

1. **顶点数量限制**
   ```cpp
   fuzz->nextRange(&count, 0, 512);
   ```
   - 512 是经验值,平衡测试覆盖和性能
   - 避免过大多边形导致超时

2. **偏移范围限制**
   ```cpp
   fuzz->nextRange(&offset, -1000, 1000);
   ```
   - 防止极端偏移值导致算法超时
   - 反映阴影算法的实际使用范围

3. **点坐标量化**
   - 牺牲少量精度换取稳定性
   - 1/16 像素对渲染质量无影响

4. **栈优先内存分配**
   ```cpp
   AutoSTMalloc<64, SkPoint> polygon(count);
   ```
   - 小多边形(≤64 个顶点)使用栈分配
   - 大多边形自动切换到堆分配
   - 提高常见情况的性能

## 性能考量

### 测试效率

1. **早期退出**
   - 非凸多边形跳过内缩测试
   - 非简单多边形跳过偏移和三角剖分
   - 避免无效计算

2. **内存管理**
   - 栈优先分配减少堆操作
   - 动态数组复用减少分配次数

3. **超时预防**
   - 偏移范围限制
   - 顶点数量上限
   - 注释明确说明防超时措施

### 算法复杂度

各操作的时间复杂度:
- **卷绕检测**: O(n)
- **凸性判断**: O(n)
- **简单性判断**: O(n log n)(扫描线算法)
- **凸多边形内缩**: O(n)
- **简单多边形偏移**: O(n log n)
- **三角剖分**: O(n log n)(耳切法或分治法)

## 相关文件

### 核心实现
- `src/utils/SkPolyUtils.h` - 多边形工具函数声明
- `src/utils/SkPolyUtils.cpp` - 算法实现
- `src/utils/SkShadowUtils.cpp` - 阴影渲染(使用多边形偏移)

### 相关测试
- `fuzz/oss_fuzz/FuzzPolyUtils.cpp` - OSS-Fuzz 版本
- `fuzz/FuzzTriangulation.cpp` - GPU 三角剖分测试
- `tests/PolyUtilsTest.cpp` - 单元测试

### 使用场景
- `src/utils/SkShadowTessellator.cpp` - 阴影网格生成
- `src/core/SkPath.cpp` - 路径填充算法
- `src/gpu/ganesh/geometry/GrTriangulator.cpp` - GPU 三角剖分

### 测试基础设施
- `fuzz/Fuzz.h` - 模糊测试工具类
- `fuzz/FuzzCommon.h` - 通用辅助函数
- `include/private/base/SkTemplates.h` - 内存管理模板

### 文档
- `site/dev/testing/fuzz.md` - 模糊测试指南
- `docs/dev/design/shadows.md` - 阴影渲染设计(使用多边形偏移)
