# SkVerticesPriv

> 源文件: src/core/SkVerticesPriv.h

## 概述

`SkVerticesPriv` 是 Skia 中用于访问 `SkVertices` 私有成员和内部方法的特权类（privileged class）。它提供了一个受控的窗口，允许 Skia 内部代码（特别是序列化和渲染相关模块）访问 `SkVertices` 的内部数据，同时保持公共 API 的简洁性和封装性。该类遵循"特权访问者"设计模式，不添加额外的数据成员或虚函数，纯粹作为访问桥梁存在。

此类的主要用途包括顶点数据的序列化/反序列化、设备层渲染时直接访问数组指针、以及调试和测试时检查内部状态。它的设计体现了 Skia 在保持 API 清洁与提供内部灵活性之间的平衡。

## 架构位置

`SkVerticesPriv` 在 Skia 架构中扮演"内部访问桥梁"角色：

```
公共 API (SkVertices)
         ↓
  SkVerticesPriv (特权访问) ← 本模块
         ↓
  内部使用者:
  - SkWriteBuffer/SkReadBuffer (序列化)
  - SkDevice (渲染实现)
  - SkGpuDevice (GPU 顶点缓冲区)
```

它位于公共 API 和内部实现之间的中间层，通过友元机制控制访问权限。

## 主要类与结构体

### SkVerticesPriv

`SkVertices` 的特权访问类。

**继承关系**
- 无继承（纯特权类）

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fVertices` | `SkVertices*` | 指向被访问的 `SkVertices` 对象 |

**特殊约束**
- 禁止获取地址（`operator&` 被删除）
- 禁止赋值（`operator=` 被删除）
- 默认复制构造函数（但因 RVO 实际不调用）

### SkVertices_DeprecatedBone

历史遗留的骨骼结构体（已弃用）。

```cpp
struct SkVertices_DeprecatedBone {
    float values[6];  // 仿射变换参数
};
```

**用途**：用于旧版本的骨骼动画支持（已移除），保留定义以支持旧版序列化格式。

## 公共 API 函数

### 查询方法

```cpp
SkVertices::VertexMode mode() const
```
返回顶点模式（三角形/三角形带/三角形扇）。

```cpp
int vertexCount() const
int indexCount() const
```
返回顶点数量和索引数量。

```cpp
bool hasColors() const
bool hasTexCoords() const
bool hasIndices() const
```
检查是否包含颜色、纹理坐标或索引数组。

### 数据访问方法

```cpp
const SkPoint* positions() const
const SkPoint* texCoords() const
const SkColor* colors() const
const uint16_t* indices() const
```
返回各数组的只读指针。如果对应数组不存在，返回 `nullptr`。

**安全性**：返回 `const` 指针，防止外部修改不可变对象。

### 序列化方法

```cpp
void encode(SkWriteBuffer& buffer) const
```
将 `SkVertices` 对象序列化到写入缓冲区。

**序列化格式**
```
[packed: mode + flags]
[vertexCount]
[indexCount]
[positions 数组]
[texs 数组]      (如果有)
[colors 数组]    (如果有)
[indices 数组]   (如果有)
```

**标志位**
- `kHasTexs_Mask` (0x100)：包含纹理坐标
- `kHasColors_Mask` (0x200)：包含颜色

```cpp
static sk_sp<SkVertices> Decode(SkReadBuffer& buffer)
```
从读取缓冲区反序列化 `SkVertices` 对象。

**验证检查**
- 顶点数和索引数非负
- 索引值在 `[0, vertexCount)` 范围内
- 数组大小不超过可用缓冲区
- 拒绝三角形扇格式（已弃用）
- 拒绝包含自定义属性的旧版本数据

## 内部实现细节

### 特权访问机制

`SkVerticesPriv` 使用友元机制访问 `SkVertices` 的私有成员：

```cpp
// SkVertices.h
class SkVertices {
    // ...
    SkVerticesPriv priv();
    const SkVerticesPriv priv() const;
private:
    SkPoint*  fPositions;
    uint16_t* fIndices;
    // ...
    friend class SkVerticesPriv;
};

// SkVerticesPriv.h
class SkVerticesPriv {
public:
    const SkPoint* positions() const { return fVertices->fPositions; }
    // ...
private:
    explicit SkVerticesPriv(SkVertices* vertices) : fVertices(vertices) {}
    SkVertices* fVertices;
    friend class SkVertices;
};

// 内联实现
inline SkVerticesPriv SkVertices::priv() {
    return SkVerticesPriv(this);
}
```

**访问流程**
1. 调用者获取 `SkVertices` 对象
2. 调用 `vertices->priv()` 获取 `SkVerticesPriv` 对象
3. 通过 `SkVerticesPriv` 的方法访问私有成员
4. `SkVerticesPriv` 对象是临时的，超出作用域后自动销毁

### 序列化实现

#### encode() 实现

```cpp
void SkVerticesPriv::encode(SkWriteBuffer& buffer) const {
    uint32_t packed = static_cast<uint32_t>(fVertices->fMode);
    if (fVertices->fTexs) {
        packed |= kHasTexs_Mask;
    }
    if (fVertices->fColors) {
        packed |= kHasColors_Mask;
    }

    SkVertices::Sizes sizes = fVertices->getSizes();

    buffer.writeUInt(packed);
    buffer.writeInt(fVertices->fVertexCount);
    buffer.writeInt(fVertices->fIndexCount);

    buffer.writeByteArray(fVertices->fPositions, sizes.fVSize);
    buffer.writeByteArray(fVertices->fTexs, sizes.fTSize);
    buffer.writeByteArray(fVertices->fColors, sizes.fCSize);
    buffer.writeByteArray(fVertices->fIndices, sizes.fISize);
}
```

**关键点**
- 使用位掩码压缩标志位
- 模式值占用低 8 位 (`kMode_Mask = 0x0FF`)
- 直接写入原始数组字节

#### Decode() 实现

```cpp
sk_sp<SkVertices> SkVerticesPriv::Decode(SkReadBuffer& buffer) {
    const uint32_t packed = buffer.readUInt();
    const int vertexCount = safe.checkGE(buffer.readInt(), 0);
    const int indexCount = safe.checkGE(buffer.readInt(), 0);

    const SkVertices::VertexMode mode = safe.checkLE<SkVertices::VertexMode>(
        packed & kMode_Mask, SkVertices::kLast_VertexMode);
    const bool hasTexs = SkToBool(packed & kHasTexs_Mask);
    const bool hasColors = SkToBool(packed & kHasColors_Mask);

    // 验证数据有效性
    if (mode == SkVertices::kTriangleFan_VertexMode) {
        return nullptr;  // 不支持反序列化三角形扇
    }

    // 创建 Builder 并读取数组
    SkVertices::Builder builder(desc);
    buffer.readByteArray(builder.positions(), sizes.fVSize);
    buffer.readByteArray(builder.texCoords(), sizes.fTSize);
    buffer.readByteArray(builder.colors(), sizes.fCSize);
    buffer.readByteArray(builder.indices(), sizes.fISize);

    // 验证索引范围
    if (indexCount > 0) {
        const uint16_t* indices = builder.indices();
        for (int i = 0; i < indexCount; ++i) {
            if (indices[i] >= (unsigned)vertexCount) {
                return nullptr;
            }
        }
    }

    return builder.detach();
}
```

**验证策略**
- **安全检查**：使用 `SkSafeRange` 验证范围
- **缓冲区溢出保护**：检查数组大小不超过 `buffer.available()`
- **索引越界保护**：验证每个索引值
- **版本兼容性**：处理包含自定义属性的旧版本数据（跳过）

### 防止地址获取

```cpp
const SkVerticesPriv* operator&() const = delete;
SkVerticesPriv* operator&() = delete;
```

**目的**
- 防止创建 `SkVerticesPriv*` 指针
- 强制使用临时对象模式
- 避免生命周期管理问题

**示例**
```cpp
// 正确用法
vertices->priv().positions();

// 禁止用法（编译错误）
SkVerticesPriv* priv = &vertices->priv();
```

### 返回值优化（RVO）

```cpp
// 注释说明
SkVerticesPriv(const SkVerticesPriv&) = default;
// Never called due to RVO in priv(), but must exist for MSVC 2017.
```

**背景**
- `priv()` 返回 `SkVerticesPriv` 值对象
- 现代编译器使用 RVO（返回值优化），无需复制
- MSVC 2017 要求复制构造函数存在（即使不调用）

## 依赖关系

**依赖的模块**

| 模块 | 用途 |
|------|------|
| `SkVertices` | 被访问的目标类 |
| `SkWriteBuffer` | 序列化接口 |
| `SkReadBuffer` | 反序列化接口 |
| `SkToBool` | 位掩码转布尔值 |

**被依赖的模块**

| 模块 | 依赖原因 |
|------|----------|
| `SkWriteBuffer` | 调用 `encode()` 序列化顶点数据 |
| `SkReadBuffer` | 调用 `Decode()` 反序列化顶点数据 |
| `SkDevice` | 访问顶点数组进行渲染 |
| `SkGpuDevice` | 创建 GPU 顶点缓冲区 |
| `SkDebugCanvas` | 调试时检查顶点数据 |

## 设计模式与设计决策

### 设计模式

1. **特权类模式（Privileged Class）**
   - 提供受控的私有成员访问
   - 不添加数据成员或虚函数
   - 通过友元机制实现

2. **代理模式（Proxy）**
   - `SkVerticesPriv` 作为 `SkVertices` 的代理
   - 提供额外的访问方法
   - 不改变原对象

3. **临时对象模式**
   - `priv()` 返回临时对象
   - 禁止获取地址
   - 强制正确使用方式

### 设计决策

#### 1. 为什么使用特权类而非公开成员

**设计选择**：使用 `SkVerticesPriv` 而非将成员设为 public

**优点**
- **清晰的 API 边界**：公共 API 仅包含应用层需要的方法
- **受控访问**：通过 `priv()` 明确标识内部使用
- **文档友好**：公共 API 文档不包含内部方法
- **向后兼容**：可在不影响公共 API 的情况下修改内部接口

**缺点**
- 稍微复杂的访问语法（需调用 `priv()`）
- 需要友元声明

#### 2. 为什么返回 const 指针

**设计**：所有数据访问方法返回 `const` 指针

```cpp
const SkPoint* positions() const { return fVertices->fPositions; }
```

**原因**
- `SkVertices` 是不可变对象
- 防止通过特权类破坏不可变性
- 即使内部代码也不应修改已创建的对象

#### 3. 为什么禁止地址获取

**设计**：删除 `operator&`

**原因**
- 防止创建长生命周期的 `SkVerticesPriv` 对象
- 避免悬空指针（如果 `SkVertices` 被销毁）
- 强制使用临时对象模式

**强制的使用模式**
```cpp
// 推荐：临时对象
int count = vertices->priv().vertexCount();

// 禁止：持有指针（编译错误）
SkVerticesPriv* priv = &vertices->priv();
```

#### 4. Decode() 为静态方法

**设计**：`Decode()` 是静态方法，不需要现有对象

**原因**
- 反序列化创建新对象
- 无需现有 `SkVertices` 实例
- 与序列化（成员方法）形成对称

**调用方式**
```cpp
// 序列化
vertices->priv().encode(buffer);

// 反序列化
sk_sp<SkVertices> vertices = SkVerticesPriv::Decode(buffer);
```

#### 5. 拒绝三角形扇序列化

**设计**：`Decode()` 拒绝 `kTriangleFan_VertexMode`

**原因**
- Skia 已停止写入三角形扇格式（转换为三角形）
- 旧版本序列化数据应该不包含三角形扇
- 简化反序列化逻辑

**向前兼容性**：如果真的遇到旧数据，返回 `nullptr` 比崩溃更好。

## 性能考量

### 零开销抽象

1. **内联方法**
   - 所有访问方法都定义在头文件中
   - 编译器可内联，零函数调用开销
   - 等价于直接访问成员（如果允许）

2. **无额外存储**
   - `SkVerticesPriv` 仅包含一个指针
   - 临时对象通常被优化掉（RVO）
   - 不增加 `SkVertices` 对象大小

3. **编译时检查**
   - 类型安全由编译器保证
   - 无运行时检查开销

### 序列化性能

1. **直接数组写入**
   - `encode()` 使用 `writeByteArray()` 批量写入
   - 避免逐元素序列化
   - 适合大型顶点数组

2. **最小化元数据**
   - 仅写入 3 个整数头部（packed, vertexCount, indexCount）
   - 标志位压缩在 packed 字段中

3. **反序列化验证成本**
   - 索引验证需遍历所有索引（O(n)）
   - 但这是安全性必需的
   - 相比渲染崩溃，验证开销可接受

## 相关文件

| 文件 | 关系 | 说明 |
|------|------|------|
| `include/core/SkVertices.h` | 目标类 | 被访问的 SkVertices 定义 |
| `src/core/SkVertices.cpp` | 实现 | SkVertices 实现，包含 priv() 定义 |
| `src/core/SkWriteBuffer.h` | 使用者 | 序列化接口 |
| `src/core/SkReadBuffer.h` | 使用者 | 反序列化接口 |
| `src/core/SkDevice.cpp` | 使用者 | 设备层渲染 |
| `src/gpu/ganesh/Device.cpp` | 使用者 | GPU 顶点缓冲区创建 |
| `src/core/SkPictureRecord.cpp` | 使用者 | SkPicture 录制 |
| `include/private/base/SkTo.h` | 依赖 | SkToBool 工具 |
