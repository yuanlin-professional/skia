# GrMtlPipelineStateDataManager

> 源文件
> - `src/gpu/ganesh/mtl/GrMtlPipelineStateDataManager.h`
> - `src/gpu/ganesh/mtl/GrMtlPipelineStateDataManager.mm`

## 概述

`GrMtlPipelineStateDataManager` 是 Ganesh 图形后端中 Metal 实现的管道状态数据管理器类,负责管理和更新着色器的 uniform 变量数据。该类作为 CPU 端 uniform 数据与 GPU 端着色器变量的桥梁,提供类型安全的 uniform 设置接口,并优化数据上传策略。支持标量、向量、矩阵等多种类型的 uniform,并通过脏位追踪避免不必要的数据传输,还能根据数据大小智能选择推送常量(push constants)或缓冲区绑定方式。

## 架构位置

`GrMtlPipelineStateDataManager` 位于 Skia 图形库的 GPU 后端 uniform 数据管理层次结构中:

```
Skia 图形库
└── GPU 后端 (src/gpu)
    └── Ganesh 渲染引擎 (ganesh)
        ├── GrUniformDataManager (Uniform 数据管理基类)
        │   └── GrMtlPipelineStateDataManager (Metal 数据管理器) ← 当前类
        └── Metal 后端实现 (mtl)
            ├── GrMtlPipelineState (管道状态)
            ├── GrMtlUniformHandler (Uniform 处理器)
            ├── GrMtlRenderCommandEncoder (渲染编码器)
            └── GrMtlBuffer (缓冲对象)
```

该类与管道状态和渲染编码器协作,实现 uniform 数据的管理和绑定。

## 主要类与结构体

### GrMtlPipelineStateDataManager 类

Metal 管道状态数据管理器。

**继承关系:**
- 继承: `GrUniformDataManager` (Uniform 数据管理基类)

**关键类型定义:**

```cpp
typedef GrMtlUniformHandler::UniformInfoArray UniformInfoArray;
```

**关键继承成员:**

| 成员变量 (继承自基类) | 类型 | 说明 |
|---------------------|------|------|
| `fUniforms` | `Uniform[]` | Uniform 变量数组 |
| `fUniformData` | `SkAutoMalloc` | Uniform 数据缓冲区 |
| `fUniformSize` | `uint32_t` | Uniform 数据总大小 |
| `fUniformsDirty` | `mutable bool` | 脏位标记 |
| `fWrite16BitUniforms` | `bool` | 是否写入 16 位 uniform |

## 公共 API 函数

### 构造函数

```cpp
GrMtlPipelineStateDataManager(
    const UniformInfoArray& uniforms,
    uint32_t uniformSize)
```
从 uniform 信息数组构造数据管理器,分配指定大小的数据缓冲区。

### Uniform 设置函数

```cpp
void set1iv(UniformHandle u, int arrayCount, const int32_t v[]) const override
```
设置整型标量或数组。

```cpp
void set1fv(UniformHandle u, int arrayCount, const float v[]) const override
```
设置浮点标量或数组。

```cpp
void set2iv(UniformHandle u, int arrayCount, const int32_t v[]) const override
```
设置 2D 整型向量或数组。

```cpp
void set2fv(UniformHandle u, int arrayCount, const float v[]) const override
```
设置 2D 浮点向量或数组。

```cpp
void setMatrix2f(UniformHandle u, const float matrix[]) const override
```
设置单个 2x2 矩阵。

```cpp
void setMatrix2fv(UniformHandle u, int arrayCount, const float matrices[]) const override
```
设置 2x2 矩阵数组。

### 数据上传与绑定

```cpp
void uploadAndBindUniformBuffers(
    GrMtlGpu* gpu,
    GrMtlRenderCommandEncoder* renderCmdEncoder) const
```
将 uniform 数据上传到 GPU 并绑定到渲染编码器。智能选择推送常量或缓冲区方式。

```cpp
void resetDirtyBits()
```
重置脏位标记,强制下次上传 uniform 数据。

## 内部实现细节

### 构造时初始化

构造函数遍历 uniform 信息数组,初始化内部 uniform 结构:

```cpp
for (const auto& uniformInfo : uniforms.items()) {
    Uniform& uniform = fUniforms[i];
    uniform.fOffset = uniformInfo.fUBOffset;        // 偏移量
    uniform.setType(uniformInfo.fVariable.getType()); // 类型
    SkDEBUGCODE(uniform.fArrayCount = ...);         // 数组大小(调试)
}
```

设置 `fWrite16BitUniforms = true` 启用 16 位 uniform 支持(half/short 类型)。

### Uniform 设置流程

所有 `set*` 方法遵循相同流程:

1. **类型验证**: 检查 uniform 类型匹配
   ```cpp
   SkASSERT(uni.type() == SkSLType::kFloat2 || uni.type() == SkSLType::kHalf2);
   ```

2. **数组大小验证**: 检查数组边界
   ```cpp
   SkASSERT(arrayCount <= uni.fArrayCount || ...);
   ```

3. **获取缓冲指针并标记脏位**:
   ```cpp
   void* buffer = this->getBufferPtrAndMarkDirty(uni);
   ```

4. **复制数据**: 使用基类的 `copyUniforms()` 处理类型转换
   ```cpp
   this->copyUniforms(buffer, v, arrayCount, uni.type());
   ```

### 类型支持

每个设置函数支持全精度和半精度类型:

| 函数 | 支持的类型 |
|-----|-----------|
| `set1iv` | `kInt`, `kShort` |
| `set1fv` | `kFloat`, `kHalf` |
| `set2iv` | `kInt2`, `kShort2` |
| `set2fv` | `kFloat2`, `kHalf2` |
| `setMatrix2fv` | `kFloat2x2`, `kHalf2x2` |

基类的 `copyUniforms()` 处理全精度到半精度的自动转换。

### 数据上传策略

`uploadAndBindUniformBuffers()` 实现两级上传策略:

#### 策略一: 推送常量(Push Constants)

适用于小数据量:

```cpp
if (fUniformSize <= gpu->caps()->maxPushConstantsSize()) {
    renderCmdEncoder->setVertexBytes(fUniformData.get(), fUniformSize, binding);
    renderCmdEncoder->setFragmentBytes(fUniformData.get(), fUniformSize, binding);
    return;
}
```

**优点:**
- 无需缓冲区分配
- 数据直接嵌入命令流
- 延迟更低

**限制:**
- 仅支持 macOS 10.11+, iOS 8.3+
- 大小限制(通常 4KB)

#### 策略二: 缓冲区绑定

适用于大数据量:

```cpp
// 从环形缓冲区分配
GrRingBuffer::Slice slice = gpu->uniformsRingBuffer()->suballocate(fUniformSize);
GrMtlBuffer* buffer = (GrMtlBuffer*) slice.fBuffer;

// 映射并复制数据
char* destPtr = static_cast<char*>(slice.fBuffer->map()) + slice.fOffset;
memcpy(destPtr, fUniformData.get(), fUniformSize);

// 绑定缓冲区
renderCmdEncoder->setVertexBuffer(buffer->mtlBuffer(), slice.fOffset, binding);
renderCmdEncoder->setFragmentBuffer(buffer->mtlBuffer(), slice.fOffset, binding);
```

**优点:**
- 支持大数据量
- 环形缓冲区高效复用

### 脏位追踪

通过 `fUniformsDirty` 标志避免重复上传:

```cpp
if (fUniformSize && fUniformsDirty) {
    fUniformsDirty = false;
    // 执行上传
}
```

- 任何 `set*` 调用通过 `getBufferPtrAndMarkDirty()` 设置脏位
- 上传后清除脏位
- `resetDirtyBits()` 强制下次上传

### 矩阵处理

矩阵按列主序(column-major)存储:

```cpp
void setMatrix2f(UniformHandle u, const float matrix[]) {
    this->setMatrix2fv(u, 1, matrix);
}
```

单矩阵设置转发到数组版本,统一处理逻辑。

### 数组计数转换

向量和矩阵数组需要计数转换:

```cpp
// 2D 向量: 每个元素 2 个分量
this->copyUniforms(buffer, v, arrayCount * 2, uni.type());

// 2x2 矩阵: 每个矩阵 4 个分量
this->copyUniforms(buffer, m, arrayCount * 4, uni.type());
```

### 绑定位置

Uniform 缓冲区绑定到固定槽位:

```cpp
GrMtlUniformHandler::kUniformBinding
```

顶点和片段着色器使用相同绑定点,共享 uniform 数据。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrUniformDataManager` | Uniform 数据管理基类 |
| `GrMtlUniformHandler` | Uniform 信息和绑定定义 |
| `GrMtlGpu` | GPU 接口,访问环形缓冲区 |
| `GrMtlRenderCommandEncoder` | 渲染编码器,绑定 uniform |
| `GrMtlBuffer` | Metal 缓冲对象 |
| `GrRingBuffer` | 环形缓冲区分配器 |
| `SkAutoMalloc` | 自动内存管理 |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|----------|
| `GrMtlPipelineState` | 拥有数据管理器,更新 uniform |
| `GrMtlOpsRenderPass` | 通过管道状态访问数据管理器 |

## 设计模式与设计决策

### 1. 策略模式 (Strategy Pattern)

根据数据大小自动选择上传策略:
- 小数据 → 推送常量
- 大数据 → 缓冲区绑定

```cpp
if (fUniformSize <= maxPushConstantsSize()) {
    // 策略 A
} else {
    // 策略 B
}
```

### 2. 脏标记模式 (Dirty Flag Pattern)

使用脏位追踪避免冗余上传:

```cpp
void* getBufferPtrAndMarkDirty(const Uniform& uni) {
    fUniformsDirty = true;  // 标记脏
    return ...;
}
```

### 3. 模板方法模式 (Template Method)

继承基类并重写关键方法:

```cpp
void set1fv(...) const override {
    // Metal 特定实现
}
```

### 4. 享元模式 (Flyweight)

环形缓冲区复用内存,避免频繁分配:

```cpp
GrRingBuffer::Slice slice = gpu->uniformsRingBuffer()->suballocate(...);
```

### 5. 统一接口 (Uniform Interface)

所有 uniform 类型通过统一的 `UniformHandle` 访问,隐藏底层细节。

### 6. 类型安全

编译时和运行时检查确保类型匹配:

```cpp
SkASSERT(uni.type() == SkSLType::kFloat2 || uni.type() == SkSLType::kHalf2);
```

## 性能考量

### 1. 推送常量优化

小 uniform 数据使用推送常量:
- 避免缓冲区分配开销
- 减少内存带宽
- 降低延迟

典型阈值 4KB,覆盖大多数简单着色器。

### 2. 脏位追踪

只在数据变化时上传:
- 避免冗余传输
- 减少 GPU 同步点
- 提升多次绘制性能

### 3. 环形缓冲区

使用环形缓冲区池化内存:
- 避免每帧分配
- 减少内存碎片
- 提升分配速度

### 4. 批量上传

单次调用同时绑定顶点和片段着色器:

```cpp
renderCmdEncoder->setVertexBytes(...);
renderCmdEncoder->setFragmentBytes(...);
```

减少 API 调用开销。

### 5. 16 位 Uniform 支持

启用 `fWrite16BitUniforms`:
- 支持 half/short 类型
- 减少带宽和存储
- 移动设备性能提升

### 6. 内联小函数

`setMatrix2f()` 等简单函数适合内联:

```cpp
void setMatrix2f(...) const {
    this->setMatrix2fv(u, 1, matrix);  // 内联友好
}
```

### 7. 平台检查优化

推送常量的平台检查仅执行一次:

```cpp
if (@available(macOS 10.11, iOS 8.3, tvOS 9.0, *)) {
    // 检查结果可能被缓存
}
```

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/GrUniformDataManager.h` | 继承关系 | Uniform 数据管理基类 |
| `src/gpu/ganesh/mtl/GrMtlUniformHandler.h/mm` | 使用关系 | Uniform 信息定义 |
| `src/gpu/ganesh/mtl/GrMtlGpu.h/mm` | 使用关系 | GPU 接口 |
| `src/gpu/ganesh/mtl/GrMtlPipelineState.h/mm` | 被使用关系 | 管道状态拥有数据管理器 |
| `src/gpu/ganesh/mtl/GrMtlRenderCommandEncoder.h` | 使用关系 | 渲染编码器 |
| `src/gpu/ganesh/mtl/GrMtlBuffer.h/mm` | 使用关系 | 缓冲对象 |
| `src/gpu/ganesh/GrRingBuffer.h` | 使用关系 | 环形缓冲区 |
| `src/base/SkAutoMalloc.h` | 使用关系 | 自动内存管理 |
