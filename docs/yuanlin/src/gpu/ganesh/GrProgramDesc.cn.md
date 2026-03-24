# GrProgramDesc

> 源文件
> - src/gpu/ganesh/GrProgramDesc.h
> - src/gpu/ganesh/GrProgramDesc.cpp

## 概述

`GrProgramDesc` 是 Ganesh GPU 后端中用于生成和管理程序缓存键的核心类。它将渲染程序的配置信息编码为一个紧凑的二进制键,用于在程序缓存中查找和存储已编译的 GPU 程序。

主要功能包括:
- 将 `GrProgramInfo` 编码为唯一的键值
- 支持快速的程序缓存查找和比较
- 提供平台无关的基础键生成
- 支持后端特定扩展(Dawn、Metal、Vulkan、D3D 等)
- 生成人类可读的程序描述(调试用)

该类使用位打包技术高效编码程序信息,确保相同配置生成相同的键,不同配置生成不同的键。这对于避免重复编译 GPU 程序至关重要,可以显著提升渲染性能。

## 架构位置

`GrProgramDesc` 在程序缓存系统中的位置:

```
GrProgramInfo (程序配置)
    ↓
GrProgramDesc::Build() (生成描述符)
    ↓
GrProgramDesc (程序描述符/缓存键)
    ↓
ProgramCache (程序缓存)
    ├── 命中 -> 返回已编译程序
    └── 未命中 -> 编译新程序并缓存
```

它是连接程序配置和程序缓存的桥梁。

## 主要类与结构体

### GrProgramDesc 类

**继承关系**:
- 无继承关系,独立的值类型
- 派生类:后端特定的描述符类(如 `GrVkProgramDesc`)

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fKey | STArray<kPreAllocSize, uint32_t, true> | 键数据(uint32_t 数组) |
| fInitialKeyLength | uint32_t | 初始键长度(通用部分) |

**常量定义**:

| 常量 | 值 | 说明 |
|------|-----|------|
| kHeaderSize | 1 | 头部大小(uint32_t 单位) |
| kMaxPreallocProcessors | 8 | 预分配处理器数量 |
| kIntsPerProcessor | 4 | 每个处理器平均占用 uint32_t 数 |
| kPreAllocSize | 33 | 预分配大小(避免堆分配) |
| kClassIDBits | 8 | 类 ID 位数 |
| kSamplerOrImageTypeKeyBits | 4 | 采样器/图像类型键位数 |

## 公共 API 函数

### 构造和复制

```cpp
GrProgramDesc(const GrProgramDesc& other) = default;
GrProgramDesc& operator=(const GrProgramDesc& other) = default;
```

支持默认的拷贝构造和赋值。

### 状态查询

```cpp
bool isValid() const;  // 键是否有效
void reset();  // 重置为空
```

### 键访问

```cpp
const uint32_t* asKey() const;  // 获取键数据
uint32_t keyLength() const;  // 获取键长度(字节)
uint32_t initialKeyLength() const;  // 获取初始键长度
```

### 比较操作

```cpp
bool operator==(const GrProgramDesc& that) const;
bool operator!=(const GrProgramDesc& other) const;
```

基于键数据的逐位比较。

### 静态方法

```cpp
static SkString Describe(const GrProgramInfo&, const GrCaps&);
```

生成人类可读的程序描述(调试用)。

## 内部实现细节

### 键生成主流程

`Build` 方法是核心,编码所有程序信息:

```cpp
void GrProgramDesc::Build(GrProgramDesc* desc,
                          const GrProgramInfo& programInfo,
                          const GrCaps& caps) {
    desc->reset();
    skgpu::KeyBuilder b(desc->key());
    gen_key(&b, programInfo, caps);
    desc->fInitialKeyLength = desc->keyLength();
}
```

### 键生成详细流程

`gen_key` 函数按顺序编码:

1. **几何处理器**: 类 ID、配置、属性、采样器
2. **目标纹理**: 采样器键、原点、是否使用输入附件
3. **片段处理器**: 数量、每个处理器的递归编码
4. **传输处理器**: 类 ID、配置
5. **管线状态**: 写入混合、顶点对齐、图元类型

### 几何处理器编码

```cpp
static void gen_geomproc_key(const GrGeometryProcessor& geomProc,
                             const GrCaps& caps,
                             skgpu::KeyBuilder* b) {
    b->appendComment(geomProc.name());
    b->addBits(kClassIDBits, geomProc.classID(), "geomProcClassID");
    geomProc.addToKey(*caps.shaderCaps(), b);
    geomProc.getAttributeKey(b);
    add_geomproc_sampler_keys(b, geomProc, caps);
}
```

编码内容:
- 类 ID(8 位)
- 处理器特定键(由子类生成)
- 顶点属性配置
- 纹理采样器配置

### 片段处理器编码

```cpp
static void gen_fp_key(const GrFragmentProcessor& fp,
                       const GrCaps& caps,
                       skgpu::KeyBuilder* b) {
    b->addBits(kClassIDBits, fp.classID(), "fpClassID");
    b->addBits(GrGeometryProcessor::kCoordTransformKeyBits,
               GrGeometryProcessor::ComputeCoordTransformsKey(fp),
               "fpTransforms");

    if (auto* te = fp.asTextureEffect()) {
        // 编码纹理采样器
        uint32_t samplerKey = sampler_key(...);
        b->add32(samplerKey, "fpSamplerKey");
        caps.addExtraSamplerKey(b, te->samplerState(), backendFormat);
    }

    fp.addToKey(*caps.shaderCaps(), b);
    b->add32(fp.numChildProcessors(), "fpNumChildren");

    // 递归编码子处理器
    for (int i = 0; i < fp.numChildProcessors(); ++i) {
        if (auto child = fp.childProcessor(i)) {
            gen_fp_key(*child, caps, b);
        } else {
            b->addBits(kClassIDBits, GrProcessor::ClassID::kNull_ClassID, "fpClassID");
        }
    }
}
```

支持处理器树的递归编码,包括 null 子处理器的哨兵值。

### 采样器键生成

```cpp
static uint32_t sampler_key(GrTextureType textureType,
                            const skgpu::Swizzle& swizzle,
                            const GrCaps& caps) {
    int samplerTypeKey = texture_type_key(textureType);
    uint16_t swizzleKey = swizzle.asKey();
    return SkToU32(samplerTypeKey | swizzleKey << kSamplerOrImageTypeKeyBits);
}
```

将纹理类型和混合打包到 32 位:
- 低 4 位:纹理类型
- 高位:混合键

### 图元类型编码

```cpp
// 基础描述符仅存储是否为点图元
b->addBool((programInfo.primitiveType() == GrPrimitiveType::kPoints),
           "isPoints");
```

后端特定版本(如 Vulkan)可能需要更详细的图元类型信息。

### 键对齐和刷新

```cpp
b->flush();  // 确保 4 字节对齐
```

在通用部分结束后刷新,为后端特定数据提供清晰边界。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| GrProgramInfo | 程序配置信息源 |
| GrCaps | GPU 能力查询 |
| GrGeometryProcessor | 几何处理器 |
| GrFragmentProcessor | 片段处理器 |
| GrXferProcessor | 传输处理器 |
| GrPipeline | 管线配置 |
| skgpu::KeyBuilder | 键构建工具 |
| skgpu::StringKeyBuilder | 字符串键构建(调试) |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| GrGLGpu | 使用描述符查找 OpenGL 程序 |
| GrVkGpu | 使用描述符查找 Vulkan 管线 |
| GrMtlResourceProvider | 使用描述符查找 Metal 管线 |
| GrD3DGpu | 使用描述符查找 D3D 管线 |
| 程序缓存 | 使用描述符作为缓存键 |

## 设计模式与设计决策

### 值语义

`GrProgramDesc` 是可拷贝的值类型,适合用作 map 的键。

### 位打包优化

使用位级编码最小化键大小:
- 类 ID:8 位(支持 256 个类)
- 纹理类型:4 位
- 混合:16 位

### 预分配优化

使用 `STArray` 预分配 33 个 uint32_t(132 字节),避免大多数情况的堆分配。

### 平台扩展设计

基类生成通用部分,派生类可追加平台特定信息:
- `fInitialKeyLength` 标记通用部分结束
- 后端代码可使用 `key()->add32(...)` 追加数据

### 调试友好

`StringKeyBuilder` 生成带注释的键描述:

```
geomProcClassID: 123
ppNumSamplers: 2
fpClassID: 45
...
```

### 哨兵值处理

使用 `kNull_ClassID` 标记 null 子处理器,确保键的唯一性。

## 性能考量

### 预分配避免堆分配

132 字节的预分配足以覆盖大多数程序,避免动态分配开销。

### 位打包减少键大小

更小的键意味着:
- 更快的比较
- 更好的缓存局部性
- 更少的内存占用

### 4 字节对齐

键使用 `uint32_t` 数组,确保对齐,支持快速比较。

### 避免字符串操作

生产代码中键是二进制,不涉及字符串操作。`Describe` 仅用于调试。

### 缓存友好

键的顺序编码确保常见部分(几何处理器、主要片段处理器)在键的开头,提高比较效率。

### 递归深度限制

片段处理器树的深度通常有限,递归开销可控。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| src/gpu/ganesh/GrProgramInfo.h/cpp | 输入 | 程序配置信息 |
| src/gpu/ganesh/GrCaps.h | 依赖 | GPU 能力 |
| src/gpu/KeyBuilder.h | 工具 | 键构建器 |
| src/gpu/ganesh/GrGeometryProcessor.h | 编码 | 几何处理器 |
| src/gpu/ganesh/GrFragmentProcessor.h | 编码 | 片段处理器 |
| src/gpu/ganesh/GrXferProcessor.h | 编码 | 传输处理器 |
| src/gpu/ganesh/GrPipeline.h | 编码 | 管线状态 |
| src/gpu/ganesh/gl/GrGLGpu.h | 使用者 | OpenGL 程序缓存 |
| src/gpu/ganesh/vk/GrVkCaps.h | 派生 | Vulkan 描述符 |
| src/gpu/ganesh/mtl/GrMtlCaps.h | 派生 | Metal 描述符 |
| src/gpu/ganesh/d3d/GrD3DCaps.h | 派生 | D3D 描述符 |
