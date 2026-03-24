# SkWriter32

> 源文件: src/core/SkWriter32.h, src/core/SkWriter32.cpp

## 概述

`SkWriter32` 是 Skia 中用于序列化数据的核心类，提供了一个高效的二进制数据写入器，所有写入都对齐到 4 字节边界。它支持写入各种基本类型（整数、浮点数）和 Skia 特定类型（如 `SkMatrix`、`SkPath`、`SkRegion` 等），并具有灵活的内存管理策略，可以使用外部提供的初始存储缓冲区，或在需要时自动扩展到动态分配的内存。

该类是 Skia 序列化框架的基础组件，被 `SkWriteBuffer`（高级序列化接口）和 SkPicture（绘制命令记录）等模块广泛使用。其设计目标是在保证数据对齐的前提下，最大化写入性能并最小化内存分配次数。

## 架构位置

`SkWriter32` 位于 Skia 核心序列化层，处于以下架构位置：

```
应用层 API (SkPicture, SkDrawable)
         ↓
  SkWriteBuffer (高级序列化)
         ↓
  SkWriter32 (低级二进制写入) ← 本模块
         ↓
  内存分配 (外部缓冲区/动态扩展)
```

它在序列化栈中扮演"低级写入器"角色，提供内存管理和对齐保证，而不关心具体写入的数据类型语义。

## 主要类与结构体

### SkWriter32

4 字节对齐的二进制数据写入器。

**继承关系**
- 继承自 `SkNoncopyable`（不可复制）

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fData` | `uint8_t*` | 当前数据缓冲区指针（指向 `fExternal` 或 `fInternal`） |
| `fCapacity` | `size_t` | 当前缓冲区容量（字节数） |
| `fUsed` | `size_t` | 已使用的字节数（始终是 4 的倍数） |
| `fExternal` | `void*` | 外部提供的初始存储缓冲区 |
| `fInternal` | `AutoTMalloc<uint8_t>` | 动态分配的内部缓冲区 |

### SkSWriter32<SIZE>

模板化的 `SkWriter32` 包装类，提供固定大小的栈上存储。

**继承关系**
- 继承自 `SkWriter32`

**特性**
- 使用 union 确保对齐要求（`void*` 和 `double` 对齐）
- 在栈上分配固定大小的缓冲区
- 常用于小型序列化操作，避免堆分配

## 公共 API 函数

### 构造与重置

```cpp
SkWriter32(void* external = nullptr, size_t externalBytes = 0)
```
构造写入器，可选地使用外部提供的缓冲区。

```cpp
void reset(void* external = nullptr, size_t externalBytes = 0)
```
重置写入器到初始状态，可更换外部缓冲区。外部缓冲区字节数会向下对齐到 4 的倍数。

### 基本类型写入

```cpp
void writeBool(bool value)
void writeInt(int32_t value)
void write8(int32_t value)    // 写入低 8 位，扩展为 32 位
void write16(int32_t value)   // 写入低 16 位，扩展为 32 位
void write32(int32_t value)
void writeScalar(SkScalar value)
```

### 几何类型写入

```cpp
void writePoint(const SkPoint& pt)
void writePoint3(const SkPoint3& pt)
void writeRect(const SkRect& rect)
void writeIRect(const SkIRect& rect)
void writeRRect(const SkRRect& rrect)
void writePath(const SkPath& path)
void writeMatrix(const SkMatrix& matrix)
void writeRegion(const SkRegion& rgn)
void writeSampling(const SkSamplingOptions& sampling)
```

### 原始数据写入

```cpp
void write(const void* values, size_t size)
```
写入任意数据，`size` 必须是 4 的倍数。

```cpp
void writePad(const void* src, size_t size)
```
写入数据并填充到 4 字节对齐，填充区域用零填充。

```cpp
uint32_t* reserve(size_t size)
```
预留指定大小的空间并返回指针，`size` 必须是 4 的倍数。

```cpp
uint32_t* reservePad(size_t size)
```
预留空间（不要求对齐），自动填充到 4 字节边界。

### 字符串和数据写入

```cpp
void writeString(const char* str, size_t len = (size_t)-1)
```
写入字符串，格式为：`[4 字节长度] [字符串内容] [1-4 个 '\0' 填充]`。

```cpp
void writeData(const SkData* data)
```
写入 `SkData` 对象，先写入长度，再写入内容（带填充）。

```cpp
static size_t WriteStringSize(const char* str, size_t len = (size_t)-1)
static size_t WriteDataSize(const SkData* data)
```
计算写入字符串或数据所需的对齐后大小。

### 读取与修改

```cpp
template<typename T>
const T& readTAt(size_t offset) const
```
在指定偏移量读取类型为 `T` 的值。

```cpp
template<typename T>
void overwriteTAt(size_t offset, const T& value)
```
覆写指定偏移量的值。

```cpp
void rewindToOffset(size_t offset)
```
将写入位置回退到指定偏移量（必须是 4 的倍数）。

### 查询与导出

```cpp
size_t bytesWritten() const
```
返回已写入的字节数。

```cpp
bool usingInitialStorage() const
```
返回是否仍在使用初始外部缓冲区。

```cpp
void flatten(void* dst) const
```
将所有数据复制到目标缓冲区（调用者负责分配足够空间）。

```cpp
bool writeToStream(SkWStream* stream) const
```
将数据写入流。

```cpp
sk_sp<SkData> snapshotAsData() const
```
创建当前数据的副本并封装为 `SkData`。

## 内部实现细节

### 内存管理策略

`SkWriter32` 采用两阶段内存管理：

1. **外部缓冲区阶段**
   - 初始使用调用者提供的 `external` 缓冲区
   - `fData` 指向 `fExternal`
   - 适合小型数据，避免堆分配

2. **动态扩展阶段**
   - 当数据超过外部缓冲区容量时，调用 `growToAtLeast()`
   - 分配新容量 = `max(所需大小, 旧容量 * 1.5) + 4096`
   - 复制外部数据到 `fInternal`
   - 后续扩展继续使用 `fInternal`

### growToAtLeast() 扩展逻辑

```cpp
void SkWriter32::growToAtLeast(size_t size) {
    const bool wasExternal = (fExternal != nullptr) && (fData == fExternal);

    fCapacity = 4096 + std::max(size, fCapacity + (fCapacity / 2));
    fInternal.realloc(fCapacity);
    fData = fInternal.get();

    if (wasExternal) {
        memcpy(fData, fExternal, fUsed);
    }
}
```

**扩展策略**
- 基础增量：4096 字节
- 增长因子：1.5 倍
- 一次性复制外部数据（仅在首次扩展时）

### 特殊类型序列化

#### writeSampling() 实现

```cpp
void SkWriter32::writeSampling(const SkSamplingOptions& sampling) {
    this->write32(sampling.maxAniso);
    if (!sampling.isAniso()) {
        this->writeBool(sampling.useCubic);
        if (sampling.useCubic) {
            this->writeScalar(sampling.cubic.B);
            this->writeScalar(sampling.cubic.C);
        } else {
            this->write32((unsigned)sampling.filter);
            this->write32((unsigned)sampling.mipmap);
        }
    }
}
```

采用条件序列化：
- 先写入 `maxAniso`
- 根据是否使用各向异性过滤决定后续字段
- 使用 cubic 或 filter/mipmap 模式

#### writeString() 格式

字符串序列化格式：
```
[4 字节 uint32_t 长度] [字符串字符...] [终止符 \0] [0-3 字节填充]
```

填充确保总长度对齐到 4 字节边界。

### 对齐保证

所有写入操作都确保 4 字节对齐：

1. **构造时验证**
   ```cpp
   SkASSERT(SkIsAlign4((uintptr_t)external));
   ```

2. **截断外部缓冲区大小**
   ```cpp
   externalBytes &= ~3;  // 清除低 2 位
   ```

3. **所有 `reserve()` 调用都断言对齐**
   ```cpp
   SkASSERT(SkAlign4(size) == size);
   ```

4. **`reservePad()` 自动填充**
   ```cpp
   size_t alignedSize = SkAlign4(size);
   // ... 用零填充最后一个 4 字节单元
   ```

## 依赖关系

**依赖的模块**

| 模块 | 用途 |
|------|------|
| `SkData` | 封装不可变数据块 |
| `SkPath` | 路径序列化 |
| `SkMatrix` | 矩阵序列化（通过 SkMatrixPriv） |
| `SkRRect` | 圆角矩形序列化 |
| `SkRegion` | 区域序列化 |
| `SkSamplingOptions` | 采样选项序列化 |
| `SkMalloc` | 内存分配工具 |
| `SkAlign` | 对齐宏和函数 |

**被依赖的模块**

| 模块 | 依赖原因 |
|------|----------|
| `SkBinaryWriteBuffer` | 高级序列化接口的底层实现 |
| `SkPicture` | 绘制命令记录 |
| `SkDrawable` | 可绘制对象序列化 |
| `SkImageFilter` | 图像滤镜序列化 |
| `SkShader` | 着色器序列化 |

## 设计模式与设计决策

### 设计模式

1. **缓冲区池化模式**
   - 允许重用外部缓冲区
   - 减少小对象的堆分配

2. **增量扩展模式**
   - 按需扩展容量
   - 使用增长因子避免频繁重新分配

3. **模板方法模式**
   - 提供通用的 `write()` 和类型特定的 `writeXxx()` 方法
   - 类型特定方法内部调用通用方法

4. **快照模式**
   - `snapshotAsData()` 创建当前状态的不可变副本
   - 不影响写入器继续使用

### 设计决策

1. **强制 4 字节对齐**
   - **原因**：简化反序列化，支持直接内存映射，提高 CPU 访问效率
   - **代价**：可能浪费 0-3 字节填充空间

2. **外部缓冲区优先策略**
   - **原因**：小型序列化操作（如单个对象）可完全避免堆分配
   - **适用场景**：SkPicture 的嵌套绘制、临时序列化
   - **配合 SkSWriter32 模板**：在栈上分配固定大小缓冲区

3. **不支持 seek/rewind（仅支持有限的 rewindToOffset）**
   - **原因**：简化实现，大多数序列化是顺序写入
   - **例外**：`overwriteTAt()` 允许修改已写入的值（用于回填长度等）

4. **类型特定写入方法**
   - **优点**：API 清晰，编译时类型检查
   - **缺点**：需要为每种类型提供方法
   - **权衡**：Skia 类型数量有限，可接受

5. **`write8` 和 `write16` 扩展为 32 位**
   - **原因**：保持 4 字节对齐不变
   - **空间换简洁性**：牺牲空间以简化对齐逻辑

## 性能考量

### 内存分配优化

1. **栈分配缓冲区**
   - `SkSWriter32<SIZE>` 在栈上分配缓冲区
   - 常见大小（如 256、512、1024 字节）避免大多数小对象的堆分配

2. **扩展策略**
   - 1.5 倍增长因子平衡内存使用和重新分配次数
   - 基础增量 4096 字节适合页面大小

3. **延迟分配**
   - 仅在超出外部缓冲区时才分配内部缓冲区
   - 短生命周期对象（如临时序列化）完全避免堆分配

### 写入性能

1. **直接内存写入**
   - `reserve()` 返回指针，允许直接写入
   - 避免中间缓冲区和复制

2. **批量操作**
   - `write()` 方法使用 `sk_careful_memcpy()`
   - 编译器可优化为高效的内存复制指令

3. **对齐友好**
   - 4 字节对齐利用 CPU 缓存行
   - 现代 CPU 对齐访问性能更优

### 空间效率

1. **填充开销**
   - 每个非对齐写入最多浪费 3 字节
   - 对于大型数据（如路径、图像），填充比例很小

2. **无元数据开销**
   - 不存储类型信息（由反序列化器负责）
   - 纯二进制格式，无标记开销

## 相关文件

| 文件 | 关系 | 说明 |
|------|------|------|
| `src/core/SkWriteBuffer.h/cpp` | 使用者 | 高级序列化接口，包装 SkWriter32 |
| `src/core/SkReadBuffer.h/cpp` | 对应读取器 | 反序列化对应物 |
| `src/core/SkPictureRecord.cpp` | 使用者 | 绘制命令记录 |
| `src/core/SkMatrixPriv.h` | 依赖 | 矩阵序列化辅助 |
| `include/core/SkData.h` | 依赖 | 数据块封装 |
| `include/core/SkPath.h` | 依赖 | 路径对象 |
| `include/core/SkMatrix.h` | 依赖 | 矩阵对象 |
| `include/private/base/SkMalloc.h` | 依赖 | 内存分配工具 |
| `include/private/base/SkAlign.h` | 依赖 | 对齐工具 |
