# GrQuadBuffer

> 源文件: src/gpu/ganesh/geometry/GrQuadBuffer.h

## 概述

`GrQuadBuffer` 是 Ganesh GPU 后端中用于批量存储四边形的变长编码容器。它采用高效的变比特率编码方案,根据四边形的实际类型(2D 或 3D)动态调整存储空间,实现了空间和访问效率的平衡。该模块常用于批处理绘制操作,允许将多个四边形及其元数据打包在一起进行统一处理。

核心特性:
- 变长编码存储四边形(2D 四边形 8 floats,3D 四边形 12 floats)
- 支持可选的局部坐标(纹理坐标)
- 前向迭代器访问
- 类型安全的元数据关联
- 零拷贝的缓冲区拼接

## 架构位置

`GrQuadBuffer` 位于 Ganesh 几何层,作为四边形批处理的容器:

```
src/gpu/ganesh/
  └── geometry/
      ├── GrQuad.h/cpp          # 单个四边形
      ├── GrQuadBuffer.h        # 四边形批处理容器(本模块)
      └── ops/
          ├── FillRectOp.cpp    # 使用者: 批量矩形填充
          └── TextureOp.cpp     # 使用者: 批量纹理绘制
```

它为批处理操作提供了紧凑的内存表示和高效的遍历能力。

## 主要类与结构体

### GrQuadBuffer<T> 模板类

**模板参数**: `T` - 与每个四边形关联的元数据类型(需要 4 字节对齐)

**继承关系**: 无基类

**用途**: 存储四边形序列及其关联的元数据,支持变长编码和前向迭代。

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fData` | `SkTDArray<char>` | 变长编码的数据缓冲区 |
| `fCount` | `int` | 存储的四边形数量 |
| `fDeviceType` | `GrQuad::Type` | 所有设备四边形中最通用的类型 |
| `fLocalType` | `GrQuad::Type` | 所有局部四边形中最通用的类型 |

### 内存布局

每个条目的结构:

```
[ Header    ]  4 bytes - 存储类型和标志
[ Metadata  ]  sizeof(T) - 用户自定义元数据
[ Device Xs ]  16 bytes - 4 个 X 坐标
[ Device Ys ]  16 bytes - 4 个 Y 坐标
[ Device Ws ]  0/16 bytes - 仅透视四边形需要
[ Local Xs  ]  0/16 bytes - 仅有局部坐标时需要
[ Local Ys  ]  0/16 bytes - 仅有局部坐标时需要
[ Local Ws  ]  0/16 bytes - 仅局部坐标为透视时需要
```

### Header 结构体

**字段**:

| 位字段 | 位数 | 说明 |
|--------|------|------|
| `fDeviceType` | 2 | 设备四边形类型(0-3) |
| `fLocalType` | 2 | 局部四边形类型(0-3) |
| `fHasLocals` | 1 | 是否包含局部坐标 |
| `fSentinel` | 27 | 调试哨兵值(仅 Debug 模式) |

总共 32 位,与 `int32_t` 对齐。

### Iter 迭代器类

**用途**: 提供只读的前向迭代访问。

| 成员方法 | 返回类型 | 说明 |
|---------|---------|------|
| `next()` | `bool` | 移动到下一个条目,返回是否有效 |
| `deviceQuad()` | `GrQuad*` | 获取设备空间四边形(可修改) |
| `localQuad()` | `GrQuad*` | 获取局部坐标四边形(可选,可修改) |
| `metadata()` | `const T&` | 获取元数据(只读) |
| `isLocalValid()` | `bool` | 是否有局部坐标 |

注意:返回的 `GrQuad*` 指向迭代器内部的临时对象,调用 `next()` 后会被覆盖。

### MetadataIter 迭代器类

**用途**: 仅迭代元数据,跳过四边形解包。用于 Op 最终化阶段修改元数据(如颜色)。

| 成员方法 | 返回类型 | 说明 |
|---------|---------|------|
| `next()` | `bool` | 移动到下一个条目 |
| `operator*()` | `T&` | 获取当前元数据(可修改) |
| `operator->()` | `T*` | 获取当前元数据指针(可修改) |

## 公共 API 函数

### 构造函数

```cpp
GrQuadBuffer();                           // 默认构造,预留 1 个 2D 四边形空间
GrQuadBuffer(int count, bool needsLocals); // 预留指定数量的空间
```

### 容量查询

```cpp
int count() const;                        // 返回存储的四边形数量
GrQuad::Type deviceQuadType() const;      // 返回最通用的设备四边形类型
GrQuad::Type localQuadType() const;       // 返回最通用的局部四边形类型
```

### 添加四边形

```cpp
void append(const GrQuad& deviceQuad, T&& metadata, const GrQuad* localQuad = nullptr);
```

将四边形和元数据添加到缓冲区末尾。元数据通过移动语义传递以避免拷贝。

### 批量拼接

```cpp
void concat(const GrQuadBuffer<T>& that);
```

将另一个缓冲区的所有条目追加到当前缓冲区。使用 `memcpy` 进行零拷贝传输。

### 迭代器获取

```cpp
Iter iterator() const;                    // 获取完整迭代器
MetadataIter metadata();                  // 获取元数据迭代器
```

## 内部实现细节

### 变长编码方案

条目大小计算:

```cpp
inline int entrySize(GrQuad::Type deviceType, const GrQuad::Type* localType) const {
    int size = kMetaSize;  // Header + Metadata
    size += (deviceType == GrQuad::Type::kPerspective ? k3DQuadFloats  // 12
                                                      : k2DQuadFloats) // 8
            * sizeof(float);
    if (localType) {
        size += (*localType == GrQuad::Type::kPerspective ? k3DQuadFloats
                                                          : k2DQuadFloats)
                * sizeof(float);
    }
    return size;
}
```

2D 四边形节省 16 字节(4 个 W 分量),对于大批量操作可显著减少内存使用。

### 四边形打包/解包

**打包**(`packQuad`):

```cpp
float* packQuad(const GrQuad& quad, float* coords) {
    SkASSERT(quad.xs() + 4 == quad.ys() && quad.xs() + 8 == quad.ws()); // 验证连续性
    if (quad.hasPerspective()) {
        memcpy(coords, quad.xs(), k3DQuadFloats * sizeof(float));
        return coords + k3DQuadFloats;
    } else {
        memcpy(coords, quad.xs(), k2DQuadFloats * sizeof(float));
        return coords + k2DQuadFloats;
    }
}
```

利用 `GrQuad` 的连续内存布局(`fX`, `fY`, `fW` 数组相邻),使用单次 `memcpy` 高效打包。

**解包**(`unpackQuad`):

```cpp
const float* unpackQuad(GrQuad::Type type, const float* coords, GrQuad* quad) const {
    if (type == GrQuad::Type::kPerspective) {
        memcpy(quad->xs(), coords, k3DQuadFloats * sizeof(float));
        coords += k3DQuadFloats;
    } else {
        memcpy(quad->xs(), coords, k2DQuadFloats * sizeof(float));
        coords += k2DQuadFloats;
    }
    quad->setQuadType(type);  // 自动设置 W=1(如果非透视)
    return coords;
}
```

### 类型追踪

追踪最通用的类型以优化下游处理:

```cpp
void append(...) {
    // ...
    if (deviceQuad.quadType() > fDeviceType) {
        fDeviceType = deviceQuad.quadType();
    }
    if (localQuad && localQuad->quadType() > fLocalType) {
        fLocalType = localQuad->quadType();
    }
}
```

如果所有四边形都是 `kAxisAligned`,下游可以使用针对性优化路径。

### 调试验证

Debug 模式下使用哨兵值检测内存损坏:

```cpp
#ifdef SK_DEBUG
void validate(const char* entry, int expectedCount) const {
    SkASSERT(entry);  // 非空指针
    SkASSERT(entry < fData.end());  // 在缓冲区内
    SkASSERT(expectedCount == fCount);  // 计数未变
    SkASSERT(this->header(entry)->fSentinel == kSentinel);  // 哨兵值正确
}
#endif
```

防止迭代器失效和越界访问。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrQuad` | 四边形数据结构 |
| `SkTDArray` | 动态数组容器 |
| `SkRect` | 矩形类型(用于注释) |

### 被依赖的模块

| 模块 | 使用场景 |
|------|---------|
| `FillRectOp` | 批量矩形填充时缓存四边形 |
| `TextureOp` | 批量纹理绘制时缓存四边形 |
| `GrDrawOpAtlas` | 图集操作中的批处理 |

## 设计模式与设计决策

### 模板化元数据

使用模板参数 `T` 而非 `void*`:

```cpp
template<typename T>
class GrQuadBuffer { ... };
```

优势:
- 类型安全,编译期检查
- 避免类型转换开销
- 支持非平凡类型(带构造/析构函数)
- 编译器可以内联元数据访问

约束:
- `static_assert(alignof(T) == 4)` - 确保 4 字节对齐,简化指针算术

### 前向迭代器设计

仅支持前向迭代,不支持随机访问:

```cpp
class Iter {
    bool next();  // 只能前进
    // 无 prev(), operator[], at() 等
};
```

原因:
- 变长编码使得随机访问成本高(O(n) 而非 O(1))
- 实际使用场景都是顺序遍历
- 简化实现和维护

### 懒惰类型计算

不在添加时强制类型一致性检查,而是记录最通用的类型:

```cpp
fDeviceType = max(fDeviceType, newQuad.quadType());
```

这允许混合存储不同类型的四边形,下游根据 `deviceQuadType()` 选择最通用的处理路径。

### 零拷贝拼接

`concat()` 直接拼接字节流:

```cpp
void concat(const GrQuadBuffer<T>& that) {
    fData.append(that.fData.size(), that.fData.begin());
    fCount += that.fCount;
    // ...
}
```

不需要逐个解包再重新打包,充分利用变长编码的优势。

## 性能考量

### 内存密度

- **无局部坐标的 2D 四边形**: 4 + sizeof(T) + 32 = 36 + sizeof(T) 字节
- **有局部坐标的 2D 四边形**: 36 + sizeof(T) + 32 = 68 + sizeof(T) 字节
- **透视四边形**: 额外 16 字节(设备或局部)

相比固定分配透视四边形(96 字节坐标),2D 四边形节省 33%+ 空间。

### 预分配策略

构造函数支持预分配:

```cpp
GrQuadBuffer(int count, bool needsLocals) {
    int entrySize = this->entrySize(fDeviceType, needsLocals ? &fLocalType : nullptr);
    fData.reserve(count * entrySize);
}
```

假设所有四边形为 2D,可能过度或不足分配,但避免了多次重分配。

### 迭代器临时对象

迭代器使用栈上临时对象:

```cpp
class Iter {
    GrQuad fDeviceQuad;  // 栈上分配
    GrQuad fLocalQuad;   // 栈上分配
    // ...
};
```

避免堆分配,但调用者不能持有返回的指针超过 `next()` 调用。

### 元数据迭代器优化

`MetadataIter` 跳过四边形解包:

```cpp
bool MetadataIter::next() {
    if (fCurrentEntry) {
        const Header* h = fBuffer->header(fCurrentEntry);
        fCurrentEntry += fBuffer->entrySize(h);  // 跳过整个条目
    }
    // ...
}
```

当只需要修改元数据(如颜色混合)时,避免不必要的 `memcpy` 开销。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/geometry/GrQuad.h` | 依赖 | 四边形数据结构 |
| `src/gpu/ganesh/ops/FillRectOp.cpp` | 被使用 | 矩形填充批处理 |
| `src/gpu/ganesh/ops/TextureOp.cpp` | 被使用 | 纹理绘制批处理 |
| `include/private/base/SkTDArray.h` | 依赖 | 动态数组实现 |
| `tests/GrQuadBufferTest.cpp` | 测试 | 单元测试(如果存在) |
