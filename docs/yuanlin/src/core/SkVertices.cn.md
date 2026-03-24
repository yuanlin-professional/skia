# SkVertices

> 源文件: include/core/SkVertices.h, src/core/SkVertices.cpp

## 概述

`SkVertices` 是 Skia 中用于表示顶点数据的不可变对象，可直接用于 `SkCanvas::drawVertices()` 绘制三角形网格。它封装了位置、纹理坐标、颜色和索引数组，支持三角形、三角形带和三角形扇三种顶点模式。该类采用引用计数管理内存，使用自定义内存布局将所有数组数据紧凑存储在对象后面，实现了高效的内存使用和缓存友好性。

`SkVertices` 是 Skia 中直接暴露底层图形硬件能力的少数 API 之一，允许开发者使用原始三角形网格进行高性能渲染，常用于 3D 模型、粒子系统、地形渲染等场景。

## 架构位置

`SkVertices` 在 Skia 渲染架构中处于应用层和设备层之间：

```
应用层 (游戏引擎, 3D 渲染器)
         ↓
  SkCanvas::drawVertices()
         ↓
  SkVertices (顶点数据容器) ← 本模块
         ↓
  SkDevice (GPU/CPU 设备)
         ↓
  GPU API (OpenGL, Vulkan, Metal, D3D)
  或 CPU 光栅化
```

它作为平台无关的顶点数据抽象，由设备层负责将其转换为具体的图形 API 调用。

## 主要类与结构体

### SkVertices

不可变的顶点数据集合。

**继承关系**
- 继承自 `SkNVRefCnt<SkVertices>`（非虚函数引用计数）

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fUniqueID` | `uint32_t` | 唯一标识符（用于缓存失效） |
| `fPositions` | `SkPoint*` | 顶点位置数组 [vertexCount] |
| `fIndices` | `uint16_t*` | 索引数组 [indexCount] 或 null |
| `fTexs` | `SkPoint*` | 纹理坐标数组 [vertexCount] 或 null |
| `fColors` | `SkColor*` | 顶点颜色数组 [vertexCount] 或 null |
| `fBounds` | `SkRect` | 所有位置的边界矩形 |
| `fVertexCount` | `int` | 顶点数量 |
| `fIndexCount` | `int` | 索引数量 |
| `fMode` | `VertexMode` | 顶点模式（三角形/三角形带/三角形扇） |

**内存布局**
```
[SkVertices 对象] [位置数组] [纹理坐标数组] [颜色数组] [索引数组]
                  └────────── 连续分配 ──────────┘
```

### SkVertices::Builder

用于构造 `SkVertices` 对象的构建器。

**继承关系**
- 无继承

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fVertices` | `sk_sp<SkVertices>` | 部分完成的顶点对象 |
| `fIntermediateFanIndices` | `std::unique_ptr<uint8_t[]>` | 三角形扇临时索引存储 |

**设计理念**
- 提供可写指针，允许应用层直接填充数组
- 延迟计算边界和 ID，直到 `detach()` 调用
- 自动转换三角形扇为索引三角形

### VertexMode 枚举

```cpp
enum VertexMode {
    kTriangles_VertexMode,       // 独立三角形（每 3 个顶点一个三角形）
    kTriangleStrip_VertexMode,   // 三角形带（共享边）
    kTriangleFan_VertexMode,     // 三角形扇（共享中心顶点）
};
```

**注意**：三角形扇在序列化时会自动转换为三角形模式。

## 公共 API 函数

### 静态工厂方法

```cpp
static sk_sp<SkVertices> MakeCopy(VertexMode mode,
                                   int vertexCount,
                                   const SkPoint positions[],
                                   const SkPoint texs[],
                                   const SkColor colors[],
                                   int indexCount,
                                   const uint16_t indices[])
```
复制提供的数组创建顶点对象。

**参数说明**
- `mode`: 顶点模式
- `vertexCount`: 顶点数量
- `positions`: 位置数组（必需）
- `texs`: 纹理坐标数组（可选，传 nullptr）
- `colors`: 颜色数组（可选，传 nullptr）
- `indexCount`: 索引数量（0 表示无索引）
- `indices`: 索引数组（可选）

**索引验证**
- 自动钳制索引到 `[0, vertexCount-1]` 范围
- 使用 SIMD 向量化加速（处理 8/4/2 个索引）

### Builder 构造器

```cpp
Builder(VertexMode mode, int vertexCount, int indexCount, uint32_t flags)
```
创建顶点构建器。

**标志位**
- `kHasTexCoords_BuilderFlag` (1 << 0): 包含纹理坐标
- `kHasColors_BuilderFlag` (1 << 1): 包含颜色

**示例用法**
```cpp
SkVertices::Builder builder(SkVertices::kTriangles_VertexMode,
                             100, 0,
                             SkVertices::kHasColors_BuilderFlag);
if (builder.isValid()) {
    SkPoint* positions = builder.positions();
    SkColor* colors = builder.colors();
    // 填充数据...
    sk_sp<SkVertices> vertices = builder.detach();
}
```

### Builder 方法

```cpp
bool isValid() const
```
检查构建器是否有效（分配成功）。

```cpp
SkPoint* positions()
SkPoint* texCoords()
SkColor* colors()
uint16_t* indices()
```
返回可写数组指针，供填充数据。

```cpp
sk_sp<SkVertices> detach()
```
完成构建并返回不可变的 `SkVertices` 对象。完成以下操作：
- 计算边界矩形
- 转换三角形扇为索引三角形
- 分配唯一 ID
- 将 `fVertices` 置空（仅可调用一次）

### 查询方法

```cpp
uint32_t uniqueID() const
```
返回唯一标识符（用于 GPU 缓存键）。

```cpp
const SkRect& bounds() const
```
返回所有顶点位置的边界矩形。

```cpp
size_t approximateSize() const
```
返回对象及其数组的近似内存大小。

```cpp
SkVerticesPriv priv()
```
返回特权访问接口（用于序列化等内部操作）。

## 内部实现细节

### 自定义内存布局

`SkVertices` 使用单次分配策略：

```cpp
void SkVertices::Builder::init(const Desc& desc) {
    Sizes sizes(desc);  // 计算各数组大小
    void* storage = ::operator new (sizes.fTotal);  // 单次分配
    fVertices.reset(new (storage) SkVertices);      // placement new

    char* ptr = (char*)storage + sizeof(SkVertices);
    fVertices->fPositions = (SkPoint*) ptr; ptr += sizes.fVSize;
    fVertices->fTexs      = (SkPoint*) ptr; ptr += sizes.fTSize;
    fVertices->fColors    = (SkColor*) ptr; ptr += sizes.fCSize;
    fVertices->fIndices   = (uint16_t*)ptr; ptr += sizes.fISize;
}
```

**优点**
- 单次分配减少堆碎片
- 缓存友好（数据连续存储）
- 单次释放简化内存管理

**自定义 delete 操作符**
```cpp
void SkVertices::operator delete(void* p) {
    ::operator delete(p);
}
```
与 placement new 配对使用。

### 三角形扇转换

三角形扇在 `detach()` 时自动转换为索引三角形：

```cpp
if (fVertices->fMode == kTriangleFan_VertexMode) {
    if (fIntermediateFanIndices) {
        // 有索引的三角形扇
        auto tempIndices = this->indices();
        for (int t = 0; t < fVertices->fIndexCount - 2; ++t) {
            fVertices->fIndices[3 * t + 0] = tempIndices[0];
            fVertices->fIndices[3 * t + 1] = tempIndices[t + 1];
            fVertices->fIndices[3 * t + 2] = tempIndices[t + 2];
        }
        fVertices->fIndexCount = 3 * (fVertices->fIndexCount - 2);
    } else {
        // 无索引的三角形扇
        for (int t = 0; t < fVertices->fVertexCount - 2; ++t) {
            fVertices->fIndices[3 * t + 0] = 0;
            fVertices->fIndices[3 * t + 1] = SkToU16(t + 1);
            fVertices->fIndices[3 * t + 2] = SkToU16(t + 2);
        }
        fVertices->fIndexCount = 3 * (fVertices->fVertexCount - 2);
    }
    fVertices->fMode = kTriangles_VertexMode;
}
```

**转换公式**
- N 个顶点的三角形扇 → (N-2) 个三角形
- 每个三角形使用索引 `[0, t+1, t+2]`

**原因**
- GPU 不一定支持三角形扇原语
- 统一内部表示简化渲染管线

### 索引钳制（MakeCopy）

`MakeCopy()` 使用 SIMD 向量化钳制索引：

```cpp
const uint16_t max_index = SkToU16(vertexCount - 1);

size_t i = 0;
for (; i + 8 <= icount; i += 8) {
    const skvx::ushort8 ind8 = skvx::ushort8::Load(indices + i),
                clamped_ind8 = skvx::min(ind8, max_index);
    clamped_ind8.store(builder.indices() + i);
}
// 处理剩余 4/2/1 个索引...
```

**安全性**
- 防止越界访问导致的崩溃或安全漏洞
- 渲染结果可能不正确，但不会崩溃

### 序列化格式

`SkVerticesPriv::encode()` 实现序列化：

```cpp
void SkVerticesPriv::encode(SkWriteBuffer& buffer) const {
    uint32_t packed = static_cast<uint32_t>(fVertices->fMode);
    if (fVertices->fTexs)   packed |= kHasTexs_Mask;
    if (fVertices->fColors) packed |= kHasColors_Mask;

    buffer.writeUInt(packed);
    buffer.writeInt(fVertices->fVertexCount);
    buffer.writeInt(fVertices->fIndexCount);

    buffer.writeByteArray(fVertices->fPositions, sizes.fVSize);
    buffer.writeByteArray(fVertices->fTexs, sizes.fTSize);
    buffer.writeByteArray(fVertices->fColors, sizes.fCSize);
    buffer.writeByteArray(fVertices->fIndices, sizes.fISize);
}
```

**格式**
```
[packed: mode + flags]
[vertexCount]
[indexCount]
[positions 数组]
[texs 数组]      (如果有)
[colors 数组]    (如果有)
[indices 数组]   (如果有)
```

**反序列化验证**
- 检查顶点数/索引数非负
- 验证模式值合法
- 不支持反序列化三角形扇（已弃用）
- 验证索引在 `[0, vertexCount)` 范围内

## 依赖关系

**依赖的模块**

| 模块 | 用途 |
|------|------|
| `SkPoint` | 顶点位置和纹理坐标 |
| `SkColor` | 顶点颜色 |
| `SkRect` | 边界矩形 |
| `SkRefCnt` | 引用计数基类 |
| `SkVx` | SIMD 向量运算 |
| `SkWriteBuffer/SkReadBuffer` | 序列化支持 |
| `SkSafeMath` | 安全的整数运算 |

**被依赖的模块**

| 模块 | 依赖原因 |
|------|----------|
| `SkCanvas` | 通过 `drawVertices()` 使用 |
| `SkDevice` | 设备特定的顶点渲染 |
| `SkGpuDevice` | GPU 顶点缓冲区管理 |
| `SkRasterDevice` | CPU 光栅化顶点 |
| `SkPicture` | 录制顶点绘制命令 |

## 设计模式与设计决策

### 设计模式

1. **不可变对象模式**
   - 创建后无法修改
   - 线程安全（读取无需锁）
   - 可安全共享和缓存

2. **构建器模式**
   - `Builder` 类提供可变接口
   - `detach()` 返回不可变对象
   - 分离构造和使用阶段

3. **引用计数模式**
   - 使用 `sk_sp<SkVertices>` 智能指针
   - 自动内存管理
   - 支持共享所有权

4. **享元模式**
   - 通过 `uniqueID` 支持 GPU 缓存
   - 多次绘制同一顶点集无需重新上传

5. **特权类模式**
   - `SkVerticesPriv` 提供内部访问
   - 避免污染公共 API
   - 控制访问权限

### 设计决策

#### 1. 单次分配策略

**优点**
- 减少堆碎片
- 提高缓存局部性
- 简化内存管理（单次 delete）

**缺点**
- 不能调整大小
- 需要预先知道所有尺寸

**权衡**：顶点对象通常创建一次后不变，适合此策略。

#### 2. 三角形扇转换为三角形

**原因**
- GPU API 支持不一致（部分 API 已弃用三角形扇）
- 简化设备层实现
- 索引数组增加，但可重用顶点

**时机**
- 在 `Builder::detach()` 时转换
- 序列化格式不包含三角形扇
- 反序列化拒绝三角形扇数据

#### 3. 索引钳制而非验证失败

**设计选择**
- `MakeCopy()` 钳制非法索引到有效范围
- 不抛出异常或返回 null

**原因**
- 防御性编程：渲染错误优于崩溃
- 兼容性：处理来自不可信源的数据
- 性能：使用 SIMD 加速

**替代方案**：严格验证并拒绝非法数据（更安全但不灵活）

#### 4. 位置数组必需，其他可选

**设计理念**
- 位置是几何的核心，必需
- 纹理坐标、颜色可通过着色器提供
- 灵活性：支持纯色三角形、顶点色插值、纹理映射等多种用法

**内存影响**
- 最小对象：仅位置数组
- 最大对象：位置+纹理+颜色+索引

#### 5. 边界矩形延迟计算

**时机**
- 在 `Builder::detach()` 时计算
- 使用 `SkRect::BoundsOrEmpty()`

**原因**
- 避免构建期间多次计算
- 仅在需要时（绘制时）才有用

#### 6. uniqueID 的作用

**用途**
- GPU 顶点缓冲区缓存键
- 图像缓存失效标识
- SkPicture 中的对象引用

**生成策略**
```cpp
static uint32_t next_id() {
    static std::atomic<uint32_t> nextID{1};
    uint32_t id;
    do {
        id = nextID.fetch_add(1, std::memory_order_relaxed);
    } while (id == SK_InvalidGenID);
    return id;
}
```

使用原子操作确保唯一性，跳过无效 ID。

## 性能考量

### 内存效率

1. **紧凑布局**
   - 单次分配，无指针开销
   - 对象大小 = `sizeof(SkVertices)` + 数组总大小
   - 对齐到 4/8 字节（取决于平台）

2. **零拷贝构建**
   - `Builder` 直接返回可写指针
   - 应用层填充数据无需中间缓冲区

3. **可选数组**
   - 不需要纹理坐标或颜色时节省内存
   - 灵活适应不同使用场景

### 渲染性能

1. **GPU 缓存友好**
   - 通过 `uniqueID` 缓存顶点缓冲区
   - 重复绘制无需重新上传

2. **索引绘制优化**
   - 支持索引数组，减少顶点重复
   - 适合共享顶点的网格（如立方体）

3. **SIMD 索引验证**
   - 向量化钳制操作
   - 一次处理 8 个索引（AVX2）或 4 个（SSE）

### 构建性能

1. **栈友好**
   - `Builder` 对象小巧
   - 不持有大数组，仅持有 `sk_sp`

2. **延迟计算**
   - 边界和 ID 在 `detach()` 时计算
   - 避免构建期间的冗余计算

3. **移动语义**
   - `detach()` 返回 `sk_sp<SkVertices>`
   - 使用移动语义避免引用计数增减

## 相关文件

| 文件 | 关系 | 说明 |
|------|------|------|
| `src/core/SkVerticesPriv.h` | 特权接口 | 内部访问和序列化 |
| `include/core/SkCanvas.h` | 使用者 | `drawVertices()` API |
| `src/core/SkDevice.cpp` | 使用者 | 设备层渲染实现 |
| `src/gpu/ganesh/Device.cpp` | 使用者 | GPU 顶点渲染 |
| `src/core/SkReadBuffer.h/cpp` | 序列化 | 反序列化实现 |
| `src/core/SkWriteBuffer.h/cpp` | 序列化 | 序列化实现 |
| `src/base/SkVx.h` | 依赖 | SIMD 向量运算 |
| `include/core/SkPoint.h` | 依赖 | 顶点位置和纹理坐标 |
| `include/core/SkColor.h` | 依赖 | 顶点颜色 |
