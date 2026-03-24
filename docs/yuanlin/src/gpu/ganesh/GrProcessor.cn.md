# GrProcessor

> 源文件: src/gpu/ganesh/GrProcessor.h, src/gpu/ganesh/GrProcessor.cpp

## 概述

`GrProcessor` 是 Ganesh 渲染管线中所有处理器的抽象基类，为 Ganesh 着色管线提供自定义着色器代码。它是片段处理器（Fragment Processor）、几何处理器（Geometry Processor）和传输处理器（Xfer Processor）的共同基础。

核心特性：
- **不可变性**：处理器对象构造后字段不可更改
- **线程池内存管理**：使用每线程内存池进行动态分配
- **类型标识**：通过 ClassID 枚举支持运行时类型识别
- **着色器生成**：子类实现具体的着色器代码生成逻辑

该类使用自定义的 new/delete 运算符，确保处理器在正确的内存池中分配和释放，支持高性能的对象生命周期管理。

## 架构位置

`GrProcessor` 是 Ganesh 处理器体系的根基类，位于渲染管线的核心：

```
GrProcessor (抽象基类)
    ↓
    ├── GrGeometryProcessor (几何处理器)
    │       - 顶点着色器生成
    │       - 顶点属性处理
    │
    ├── GrFragmentProcessor (片段处理器)
    │       - 片段着色器效果
    │       - 纹理采样和混合
    │
    └── GrXferProcessor (传输处理器)
            - 颜色混合逻辑
            - 目标缓冲区交互
```

在渲染流程中的位置：

```
GrPaint → GrProcessorSet → GrPipeline → Shader Generation
                                             ↑
                                      GrProcessor 子类
```

## 主要类与结构体

### GrProcessor

处理器抽象基类，定义所有处理器的公共接口。

**继承关系**:
- 基类：无
- 派生类：`GrGeometryProcessor`, `GrFragmentProcessor`, `GrXferProcessor`

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fClassID` | `ClassID` | 处理器的类型标识符 |

### ClassID 枚举

包含超过 90 个处理器类型的枚举值，用于运行时类型识别和调试。部分重要类型：

| ClassID | 说明 |
|---------|------|
| `kNull_ClassID` | 空处理器保留 ID |
| `kGrTextureEffect_ClassID` | 纹理效果 |
| `kGrSkSLFP_ClassID` | SkSL 自定义片段处理器 |
| `kPorterDuffXferProcessor_ClassID` | Porter-Duff 混合 |
| `kGrBitmapTextGeoProc_ClassID` | 位图文本几何处理器 |

完整列表包含各种内置效果、测试处理器和优化变体。

#### ClassID 的分配方式

每个具体子类在构造函数中硬编码传入自己的 ClassID，这是**编译期确定**的，不存在运行时注册机制。以 `GrMatrixEffect` 为例：

```cpp
// src/gpu/ganesh/effects/GrMatrixEffect.h:35-41
GrMatrixEffect(SkMatrix matrix, std::unique_ptr<GrFragmentProcessor> child)
        : INHERITED(kGrMatrixEffect_ClassID, ProcessorOptimizationFlags(child.get()))
        , fMatrix(matrix) {
    SkASSERT(child);
    this->registerChild(std::move(child),
                        SkSL::SampleUsage::UniformMatrix(matrix.hasPerspective()));
}
```

`INHERITED` 即 `GrFragmentProcessor`，其构造函数再将 ClassID 向上传递给 `GrProcessor(ClassID classID)`。整条链路中 ClassID 始终是编译期常量。

#### ClassID 的三大核心用途

**用途一：类型识别与安全向下转型**

ClassID 最直接的用途是替代 `dynamic_cast` 进行类型判断。`GrFragmentProcessor::asTextureEffect()` 通过比较 ClassID 实现安全转型：

```cpp
// src/gpu/ganesh/GrFragmentProcessor.cpp:92-96
GrTextureEffect* GrFragmentProcessor::asTextureEffect() {
    if (this->classID() == kGrTextureEffect_ClassID) {
        return static_cast<GrTextureEffect*>(this);
    }
    return nullptr;
}
```

更精妙的是利用 ClassID 进行**跨实例优化**。`GrMatrixEffect::Make()` 检测子节点是否也是 `GrMatrixEffect`，如果是则合并矩阵，避免创建嵌套节点：

```cpp
// src/gpu/ganesh/effects/GrMatrixEffect.cpp:21-33
std::unique_ptr<GrFragmentProcessor> GrMatrixEffect::Make(
        const SkMatrix& matrix, std::unique_ptr<GrFragmentProcessor> child) {
    if (child->classID() == kGrMatrixEffect_ClassID) {
        auto me = static_cast<GrMatrixEffect*>(child.get());
        if (me->fMatrix.hasPerspective() || !matrix.hasPerspective()) {
            me->fMatrix.preConcat(matrix);
            return child;
        }
    }
    return std::unique_ptr<GrFragmentProcessor>(new GrMatrixEffect(matrix, std::move(child)));
}
```

**用途二：相等性比较的快速前置检查**

两个处理器相等的必要条件是 ClassID 相同。在 `isEqual()` 中，ClassID 比较作为第一道检查，可以在 O(1) 时间内排除绝大多数不相等的情况，避免进入昂贵的 `onIsEqual()` 虚函数调用：

```cpp
// src/gpu/ganesh/GrFragmentProcessor.cpp:36-41
bool GrFragmentProcessor::isEqual(const GrFragmentProcessor& that) const {
    if (this->classID() != that.classID()) {
        return false;
    }
    if (this->sampleUsage() != that.sampleUsage()) {
        return false;
    }
    if (!this->onIsEqual(that)) {  // 只有 ClassID 相同才调用虚函数
        return false;
    }
    // ... 继续比较子处理器
}
```

`GrXferProcessor` 也采用相同模式：

```cpp
// src/gpu/ganesh/GrXferProcessor.h:125-136
bool isEqual(const GrXferProcessor& that) const {
    if (this->classID() != that.classID()) {
        return false;
    }
    if (this->fWillReadDstColor != that.fWillReadDstColor) {
        return false;
    }
    if (fIsLCD != that.fIsLCD) {
        return false;
    }
    return this->onIsEqual(that);
}
```

**用途三：Shader 程序缓存键**

ClassID 被编码进 `GrProgramDesc`（shader 程序描述符），作为 GPU shader 缓存键的一部分。系统为此固定了 8 bit 的位宽：

```cpp
// src/gpu/ganesh/GrProgramDesc.cpp:28-29
static constexpr uint32_t kClassIDBits = 8;
```

三种处理器类型（几何、片段、传输）各自将 ClassID 写入缓存键：

```cpp
// src/gpu/ganesh/GrProgramDesc.cpp:87
b->addBits(kClassIDBits, geomProc.classID(), "geomProcClassID");

// src/gpu/ganesh/GrProgramDesc.cpp:101
b->addBits(kClassIDBits, xp.classID(), "xpClassID");

// src/gpu/ganesh/GrProgramDesc.cpp:109
b->addBits(kClassIDBits, fp.classID(), "fpClassID");
```

这意味着**同一 ClassID 的不同实例共享编译后的 shader 代码**。例如两个 `GrTextureEffect` 实例可能采样不同纹理（不同 uniform 值），但它们的着色器代码结构相同，可以复用同一编译结果。ClassID 作为整数可以直接按位编码，这是 `std::type_info` 做不到的。

## 公共 API 函数

### name()

```cpp
virtual const char* name() const = 0;
```

返回人类可读的处理器名称，必须是合法的 SkSL 标识符前缀。用于：
- 着色器代码生成
- 调试信息输出
- 日志记录

### cast()

```cpp
template <typename T>
const T& cast() const { return *static_cast<const T*>(this); }
```

类型安全的向下转型辅助函数，将基类指针转换为子类引用。

### classID()

```cpp
ClassID classID() const { return fClassID; }
```

返回处理器的类型标识符，用于类型匹配和分发。

### dumpInfo()

```cpp
#if defined(GPU_TEST_UTILS)
SkString dumpInfo() const;
virtual SkString onDumpInfo() const { return SkString(); }
#endif
```

在测试模式下输出处理器的详细信息，包括名称和子类特定的调试数据。

### 内存管理运算符

```cpp
void* operator new(size_t size);
void* operator new(size_t object_size, size_t footer_size);
void operator delete(void* target);
```

自定义的内存分配和释放运算符，使用线程局部的内存池。

## 内部实现细节

### 线程池内存管理

使用 `MemoryPoolAccessor` 封装线程安全的内存池访问：

```cpp
class MemoryPoolAccessor {
public:
    #if defined(SK_BUILD_FOR_ANDROID_FRAMEWORK)
        // Android 框架只有一个 GrContext，无需锁
        MemoryPoolAccessor() {}
        ~MemoryPoolAccessor() {}
    #else
        // 其他平台使用自旋锁保护
        MemoryPoolAccessor() { gProcessorSpinlock.acquire(); }
        ~MemoryPoolAccessor() { gProcessorSpinlock.release(); }
    #endif

    GrMemoryPool* pool() const {
        static GrMemoryPool* gPool = GrMemoryPool::Make(4096, 4096).release();
        return gPool;
    }
};
```

**设计要点**：
- Android 框架优化：已知单 GrContext，跳过锁开销
- 全局静态池：生命周期贯穿整个进程
- 块大小：4KB 起始块和增长块

### 内存分配实现

```cpp
void* GrProcessor::operator new(size_t size) {
    return MemoryPoolAccessor().pool()->allocate(size);
}

void* GrProcessor::operator new(size_t object_size, size_t footer_size) {
    return MemoryPoolAccessor().pool()->allocate(object_size + footer_size);
}
```

第二个重载支持在对象后附加额外内存（如变长数组）。

### 子类型的内存管理继承

**核心结论**：所有 GrProcessor 子类型——`GrFragmentProcessor`、`GrGeometryProcessor`、`GrXferProcessor` 及其 90+ 个具体子类——都继承基类的 `operator new` / `operator delete`，没有任何子类覆盖这些运算符。

**C++ 继承机制**：当一个类定义了类成员 `operator new` / `operator delete` 时，这些运算符会被所有派生类自动继承，除非派生类显式覆盖。因此 `GrProcessor` 中定义的自定义内存分配逻辑对整个处理器继承树生效。

**实例化模式**：所有具体子类通过工厂方法 `Make()` 创建实例，工厂方法内部的 `new` 表达式会调用继承来的 `GrProcessor::operator new`，从而将对象分配在线程局部内存池中。以 `ColorTableEffect` 为例：

```cpp
// src/gpu/ganesh/effects/GrColorTableEffect.cpp:76-92
std::unique_ptr<GrFragmentProcessor> ColorTableEffect::Make(
        std::unique_ptr<GrFragmentProcessor> inputFP,
        GrRecordingContext* context,
        const GrMippedBitmap& bitmap) {
    // ...（省略纹理视图创建）
    return std::unique_ptr<GrFragmentProcessor>(
            new ColorTableEffect(std::move(inputFP), std::move(view)));
    //  ^^^
    //  这里的 new 调用的是继承自 GrProcessor 的 operator new
    //  → MemoryPoolAccessor().pool()->allocate(size)
    //  → 内存池分配，而非全局 malloc
}
```

这一模式在所有具体处理器中保持一致（如 `GrMatrixEffect::Make()`、`GrTextureEffect::Make()` 等）。

**placement new 例外**：`GrProcessor.h` 中还定义了 placement new/delete，它们直接委托给全局 `::operator new`，绕过内存池：

```cpp
// src/gpu/ganesh/GrProcessor.h:119-124
void* operator new(size_t size, void* placement) {
    return ::operator new(size, placement);
}
void operator delete(void* target, void* placement) {
    ::operator delete(target, placement);
}
```

这是为已有内存地址上的就地构造保留的标准用法，不经过内存池路径。

**无栈分配**：整个代码库中未发现任何 GrProcessor 子类实例在栈上分配的用例。所有实例均通过 `Make()` 工厂方法在堆（内存池）上创建，并由 `std::unique_ptr` 管理生命周期。

### 不可变性保证

```cpp
GrProcessor(const GrProcessor&) = delete;
GrProcessor& operator=(const GrProcessor&) = delete;
```

禁用拷贝和赋值，强制不可变性语义。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrMemoryPool` | 提供对象池内存分配 |
| `SkSpinlock` | 线程安全的内存池访问 |
| `SkString` | 调试信息字符串 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| `GrFragmentProcessor` | 继承基类实现片段效果 |
| `GrGeometryProcessor` | 继承基类实现几何处理 |
| `GrXferProcessor` | 继承基类实现传输逻辑 |
| `GrPipeline` | 持有处理器实例 |
| `GrProcessorSet` | 管理处理器集合 |
| 所有内置效果 | 90+ 个具体处理器类型 |

## 设计模式与设计决策

### 对象池模式

使用全局内存池管理处理器生命周期：

**优点**：
- 减少内存碎片
- 提高分配/释放性能
- 更好的缓存局部性
- 批量释放支持

**权衡**：
- 需要确保线程结束前释放所有对象
- 全局状态管理复杂性

### 类型标识策略

使用 ClassID 枚举而非 C++ RTTI（`dynamic_cast` / `typeid`）：

**Skia 禁用了 RTTI**：Skia 默认以 `-fno-rtti` 编译（见 `gn/skia/BUILD.gn`），这意味着 `dynamic_cast` 和 `typeid` 在编译期就不可用。这是 Skia 在所有平台上的通用策略，并非偶然遗漏。

**性能优势**：ClassID 是简单的整数比较（一条 CPU 指令），而 `dynamic_cast` 即使在启用 RTTI 的情况下也需要遍历类型继承链，在深继承层次中代价显著。在 `isEqual()` 这类高频调用路径上，这一差距被放大。

**可嵌入缓存键**：ClassID 是 8 bit 整数，可以直接通过 `addBits()` 按位编码进 `GrProgramDesc` 缓存键（见 `GrProgramDesc.cpp`）。`std::type_info` 是一个不透明对象，无法以确定性的方式序列化为固定宽度的位字段。

**跨平台一致性**：不同编译器和平台对 RTTI 的实现细节（name mangling、type_info 布局）各不相同。ClassID 是 Skia 自行定义的枚举值，在所有平台上保证行为一致。

**实现**：
```cpp
GrProcessor(ClassID classID) : fClassID(classID) {}
```

每个子类在构造时传入唯一的 ClassID，这是编译期硬编码的常量值。

### 不可变性设计

处理器构造后不可修改的原因：
- **线程安全**：多线程读取无需同步
- **缓存友好**：可安全缓存分析结果
- **语义清晰**：处理器表示固定的着色逻辑
- **优化机会**：编译器可进行更激进优化

### 平台特定优化

Android 框架特殊处理：
```cpp
#if defined(SK_BUILD_FOR_ANDROID_FRAMEWORK)
    // 无锁实现
#else
    // 带锁实现
#endif
```

基于运行环境特性的条件编译优化。

## 性能考量

### 内存池优势

传统 malloc/free vs 对象池：

| 指标 | malloc/free | 对象池 |
|------|-------------|--------|
| 分配速度 | 慢（系统调用） | 快（指针移动） |
| 释放速度 | 慢（系统调用） | 快（指针回退） |
| 内存碎片 | 高 | 低 |
| 缓存性能 | 差（分散） | 好（连续） |

### 块大小选择

4KB 的块大小平衡了：
- **内存开销**：避免过多未使用空间
- **分配频率**：减少块分配次数
- **页对齐**：大多数系统页大小为 4KB

### ClassID 性能

相比虚函数或 dynamic_cast：
- **类型检查**：O(1) 整数比较 vs O(n) vtable 查找
- **内存占用**：4 字节 vs 8 字节指针
- **缓存行使用**：更紧凑的对象布局

### 不可变性收益

- **编译器优化**：常量折叠、内联
- **并发性能**：无锁读取
- **指令缓存**：更好的代码局部性

## 相关文件

| 文件路径 | 关系 |
|---------|------|
| `src/gpu/ganesh/GrFragmentProcessor.h` | 重要派生类 |
| `src/gpu/ganesh/GrGeometryProcessor.h` | 重要派生类 |
| `src/gpu/ganesh/GrXferProcessor.h` | 重要派生类 |
| `src/gpu/ganesh/GrMemoryPool.h` | 提供内存池实现 |
| `src/base/SkSpinlock.h` | 提供自旋锁 |
| `src/gpu/ganesh/GrPipeline.h` | 使用处理器的主要类 |
| `src/gpu/ganesh/GrProcessorSet.h` | 处理器集合管理 |
| `src/gpu/ganesh/effects/*.h` | 大量具体处理器实现 |
