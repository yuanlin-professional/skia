# SmallPathShapeData

> 源文件: src/gpu/ganesh/ops/SmallPathShapeData.h, src/gpu/ganesh/ops/SmallPathShapeData.cpp

## 概述

`SmallPathShapeData` 是 Skia Ganesh 渲染引擎中用于缓存和管理小路径图集数据的关键数据结构。该模块实现了一个高效的缓存机制,通过为小路径生成签名密钥(key),将路径的几何信息和其在图集纹理中的位置关联起来,从而避免重复渲染相同的小路径形状。这是一个仅在非优化大小模式下编译的性能优化特性。

## 架构位置

该模块位于 Ganesh GPU 后端的操作(ops)层,专门服务于小路径渲染优化。它处于以下架构层次:

```
Skia Graphics Library
└── GPU Backend (Ganesh)
    └── Operations (ops)
        └── SmallPathShapeData (小路径图集缓存)
```

该模块与 `SmallPathAtlasMgr` 和 `SmallPathRenderer` 协同工作,是小路径渲染优化策略的数据层。

## 主要类与结构体

### SmallPathShapeDataKey

**继承关系**: 无基类

**用途**: 为小路径形状生成唯一标识符

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fKey` | `skia_private::AutoSTArray<24, uint32_t>` | 存储形状的唯一标识符数据 |

### SmallPathShapeData

**继承关系**: 无基类,但使用 `SK_DECLARE_INTERNAL_LLIST_INTERFACE` 宏声明链表接口

**用途**: 存储小路径在图集中的位置和相关元数据

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fKey` | `const SmallPathShapeDataKey` | 路径形状的唯一标识符 |
| `fBounds` | `SkRect` | 路径的边界矩形 |
| `fAtlasLocator` | `GrAtlasLocator` | 路径在图集纹理中的位置信息 |

## 公共 API 函数

### SmallPathShapeDataKey 构造函数

```cpp
// SDF 路径密钥构造
SmallPathShapeDataKey(const GrStyledShape&, uint32_t dim);

// 位图路径密钥构造
SmallPathShapeDataKey(const GrStyledShape&, const SkMatrix& ctm);
```

**功能**: 根据路径形状和渲染参数生成唯一标识符。第一个构造函数用于 SDF(Signed Distance Field)路径,第二个用于位图路径。

### 密钥比较

```cpp
bool operator==(const SmallPathShapeDataKey& that) const;
```

**功能**: 比较两个密钥是否相等,用于缓存查找。

### 密钥数据访问

```cpp
int count32() const;
const uint32_t* data() const;
```

**功能**: 获取密钥的数据指针和长度,用于哈希计算。

### 静态辅助函数

```cpp
static inline const SmallPathShapeDataKey& GetKey(const SmallPathShapeData& data);
static inline uint32_t Hash(const SmallPathShapeDataKey& key);
```

**功能**: 提供便捷的密钥提取和哈希计算功能,支持哈希表操作。

## 内部实现细节

### 密钥生成策略

该模块实现了两种不同的密钥生成策略:

1. **SDF 路径密钥**:
   - 包含形状的几何信息(通过 `shape.writeUnstyledKey()`)
   - 包含维度信息(dim),用于指示生成的距离场分辨率(32x32、64x64 或 128x128)
   - 格式: `[dim, shape_key...]`

2. **位图路径密钥**:
   - 包含形状的几何信息
   - 包含变换矩阵的上 2x2 部分(精确匹配要求)
   - 包含亚像素定位信息(8位精度)
   - 格式: `[scaleX_bits, scaleY_bits, skewX_bits, skewY_bits, subpixel_pos, shape_key...]`

### 亚像素精度处理

对于位图路径,密钥中包含了平移分量的小数部分(8位精度):

```cpp
// 保留平移的小数部分
tx -= SkScalarFloorToScalar(tx);
ty -= SkScalarFloorToScalar(ty);
// 提取8位亚像素定位信息
SkFixed fracX = SkScalarToFixed(tx) & 0x0000FF00;
SkFixed fracY = SkScalarToFixed(ty) & 0x0000FF00;
fKey[4] = fracX | (fracY >> 8);
```

这确保了相同位置的路径能够正确匹配缓存,同时允许适度的亚像素定位。

### 内存管理

使用 `AutoSTArray<24, uint32_t>` 实现密钥存储,这是一个栈-堆混合分配策略:
- 小于等于24个元素时使用栈内存
- 超过24个元素时自动切换到堆分配
- 对于大多数路径,24个 uint32_t(96字节)足够存储完整密钥

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkRect` | 存储路径边界信息 |
| `SkMatrix` | 处理变换矩阵(位图路径) |
| `SkChecksum` | 计算密钥哈希值 |
| `GrAtlasTypes` | 图集定位器类型定义 |
| `GrStyledShape` | 路径形状的样式化表示 |
| `SkTemplates` | 栈-堆混合数组模板 |
| `SkTInternalLList` | 链表接口声明 |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|----------|
| `SmallPathAtlasMgr` | 使用本数据结构管理图集缓存 |
| `SmallPathRenderer` | 使用密钥查找和缓存路径 |
| `GrResourceCache` | 作为缓存的键值对存储 |

## 设计模式与设计决策

### 1. 值语义设计

`SmallPathShapeDataKey` 删除了赋值操作符但保留了拷贝构造函数:

```cpp
SmallPathShapeDataKey& operator=(const SmallPathShapeDataKey&) = delete;
```

这种设计强制密钥只能在构造时初始化,之后不可更改,增强了数据的不可变性保证。

### 2. 静态多态与哈希表集成

通过提供静态的 `GetKey()` 和 `Hash()` 函数,该类设计符合 Skia 的哈希表(如 `SkTDynamicHash`)要求,实现编译期多态:

```cpp
static inline const SmallPathShapeDataKey& GetKey(const SmallPathShapeData& data);
static inline uint32_t Hash(const SmallPathShapeDataKey& key);
```

### 3. 条件编译优化

整个模块被 `#if !defined(SK_ENABLE_OPTIMIZE_SIZE)` 包围,意味着在优化代码大小的构建中会被完全排除,体现了性能与代码大小的权衡策略。

### 4. 混合变换处理

对位图路径使用精确的矩阵匹配(上2x2),而对亚像素定位使用8位精度近似,这是精度与缓存命中率的平衡设计。

## 性能考量

### 缓存命中率优化

1. **维度分组**: SDF 路径按分辨率分组(dim 参数),避免不同分辨率的路径冲突
2. **亚像素容差**: 8位精度允许一定的亚像素变化仍然命中缓存
3. **快速哈希**: 使用 `SkChecksum::Hash32()` 提供高效的哈希计算

### 内存效率

1. **栈优先分配**: `AutoSTArray<24>` 对小密钥使用栈内存,减少堆分配开销
2. **紧凑存储**: 密钥以 uint32_t 数组存储,内存布局紧凑
3. **链表集成**: 通过侵入式链表节点避免额外的容器开销

### 查找性能

使用 `memcmp()` 进行密钥比较是高效的:
- 利用硬件优化的内存比较指令
- 连续内存访问对缓存友好
- 无需逐元素比较

## 相关文件

| 文件路径 | 关系 |
|---------|------|
| `src/gpu/ganesh/ops/SmallPathShapeData.h` | 接口定义 |
| `src/gpu/ganesh/ops/SmallPathShapeData.cpp` | 实现 |
| `src/gpu/ganesh/ops/SmallPathAtlasMgr.h` | 使用本数据结构的图集管理器 |
| `src/gpu/ganesh/ops/SmallPathRenderer.h` | 渲染器使用本模块进行缓存 |
| `src/gpu/ganesh/geometry/GrStyledShape.h` | 提供形状几何数据 |
| `src/gpu/ganesh/GrAtlasTypes.h` | 定义图集定位器 |
| `src/base/SkChecksum.h` | 提供哈希计算功能 |
