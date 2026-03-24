# 概述

SkSL（"Skia 着色语言，Skia Shading Language"）是 GLSL 的一个变体，用作 Skia 的内部着色语言。从本质上讲，SkSL 是一个单一的标准化版本的 GLSL，它避免了在"野外"GLSL 中发现的各种版本和方言差异，但它也带来了一些自己的变化。

Skia 使用 SkSL 编译器将 SkSL 代码转换为 GLSL、GLSL ES、SPIR-V 或 MSL，然后交给图形驱动程序处理。


# 与 GLSL 的区别

* 不使用精度修饰符 (Precision Modifier)。'float'、'int' 和 'uint' 始终为高精度。新类型 'half'、'short' 和 'ushort' 为中精度（我们不使用低精度）。
* 向量类型命名为 <基本类型><列数>，因此用 float2 代替 vec2，用 bool4 代替 bvec4
* 矩阵类型命名为 <基本类型><列数>x<行数>，因此用 float2x3 代替 mat2x3，用 double4x4 代替 dmat4
* GLSL 能力可以通过语法 'sk_Caps.<name>' 引用，例如 sk_Caps.integerSupport。该值将是适当的常量布尔值或整数。由于 SkSL 支持常量折叠 (Constant Folding) 和分支消除 (Branch Elimination)，这意味着静态查询能力的 'if' 语句将折叠为所选分支，即：

    if (sk_Caps.integerSupport)
        do_something();
    else
        do_something_else();

  将编译为好像你只写了 'do_something();' 或 'do_something_else();'，取决于该能力是否启用。
* 不需要 #version 语句，如果存在也会被忽略
* 输出颜色为 sk_FragColor（不要声明它）
* 使用 sk_Position 代替 gl_Position。sk_Position 使用设备坐标而非归一化坐标。
* 使用 sk_PointSize 代替 gl_PointSize
* 使用 sk_VertexID 代替 gl_VertexID
* 使用 sk_InstanceID 代替 gl_InstanceID
* 片段坐标为 sk_FragCoord，始终相对于左上角。
* 使用 sk_Clockwise 代替 gl_FrontFacing。它始终相对于左上角原点。
* 你不需要包含 ".0" 来使数字成为浮点数（这意味着 "float2(x, y) * 4" 在 SkSL 中是完全合法的，而在 GLSL 中通常必须表示为 "float2(x, y) * 4.0"。这不会有性能损失，因为数字在编译时被转换为浮点数）
* 数字上的类型后缀（1.0f、0xFFu）既不必要也不受支持
* 从较大的向量创建较小的向量（例如 float2(float3(1))）被有意禁止，因为这只是执行混合 (Swizzle) 的更冗长方式。请改用混合操作。
* 混合分量除了正常的 rgba / xyzw 分量外，还可以是 LTRB（意为"左/上/右/下"，用于在向量中存储矩形），也可以是常量 '0' 或 '1'，以在该通道中产生常量 0 或 1，而不是从源向量中选择任何内容。foo.rgb1 等价于 float4(foo.rgb, 1)。
* 所有纹理函数都命名为 "sample"，例如 sample(sampler2D, float3) 等价于 GLSL 的 textureProj(sampler2D, float3)。
* 函数支持 'inline' 修饰符，它使编译器忽略其正常的内联启发式规则，并尽可能地内联该函数
* 一些内置函数和一两个很少使用的语言特性尚未支持（抱歉！）


# 同步原语 (Synchronization Primitives)

SkSL 提供面向 GPU 计算程序的原子操作和同步原语。这些原语旨在抽象 MSL、SPIR-V 和 WGSL 提供的功能，与 GLSL 中的对应原语有所不同。

## 原子操作 (Atomics)

SkSL 提供 `atomicUint` 类型。这是一个不透明类型，需要使用原子内在函数 (Atomic Intrinsic)（如 `atomicLoad`、`atomicStore` 和 `atomicAdd`）来操作其值（类型为 `uint`）。

`atomicUint` 类型的变量必须在可写存储缓冲区块 (Storage Buffer Block) 内声明，或作为工作组共享变量 (Workgroup-shared Variable) 声明。当在缓冲区块内声明时，它保证与 `uint` 具有相同的大小和步长。

```
workgroup atomicUint myLocalAtomicUint;

layout(set = 0, binding = 0) buffer mySSBO {
    atomicUint myGlobalAtomicUint;
};

```

`atomicUint` 可以声明为结构体成员或数组的元素类型，前提是该结构体/数组类型仅在工作组共享变量或存储缓冲区块变量中实例化。

### 后端注意事项及与 GLSL 的区别

`atomicUint` 不应与 GLSL 的 [`atomic_uint`（即原子计数器，Atomic Counter）](https://www.khronos.org/opengl/wiki/Atomic_Counter) 类型混淆。`atomicUint` 提供的语义更类似于 GLSL 的["原子内存函数"](https://www.khronos.org/opengl/wiki/Atomic_Variable_Operations)（参见 GLSL 规范 v4.3，8.11 "Atomic Memory Functions"）。关键区别在于 SkSL 原子操作仅对 `atomicUint` 类型的变量操作，而 GLSL 原子内存函数可以对任意内存位置操作（例如向量的一个分量）。

* `atomicUint` 的语义类似于 Metal 的 `atomic<uint>` 和 WGSL 的 `atomic<u32>`。当目标为 Metal 和 WGSL 时，`atomicUint` 会被翻译为这些类型。
* 当翻译为 Metal 时，原子内在函数使用宽松内存顺序 (Relaxed Memory Order) 语义。
* 当翻译为 SPIR-V 时，原子内在函数使用宽松[内存语义](https://registry.khronos.org/SPIR-V/specs/unified1/SPIRV.html#Memory_Semantics_-id-)（即 `0x0 None`）。[内存作用域](https://registry.khronos.org/SPIR-V/specs/unified1/SPIRV.html#Scope_-id-)为 `1 Device` 或 `2 Workgroup`，取决于 `atomicUint` 是在缓冲区块中还是工作组变量中声明。

## 屏障 (Barriers)

SkSL 提供两个屏障内在函数：`workgroupBarrier()` 和 `storageBarrier()`。这些函数仅在计算程序中可用，用于同步同一工作组内调用之间对工作组共享和存储缓冲区内存的访问。它们提供与等效的 [WGSL 同步内置函数](https://www.w3.org/TR/WGSL/#sync-builtin-functions)相同的语义。更具体地说：

* 两个函数都执行具有获取/释放 (Acquire/Release) 内存排序的控制屏障 (Control Barrier)。
* 两个函数都使用 `Workgroup` 执行和内存作用域。这意味着一致的内存视图仅在同一工作组内的调用之间保证，而不是在给定计算管线分派 (Dispatch) 中的跨工作组之间。如果多个工作组需要对相同的共享可变状态进行_同步的_一致视图，则必须通过其他方式（例如多次分派之间的管线屏障）同步其访问。

### 后端注意事项

* `workgroupBarrier()` 在 GLSL 中最接近的等价函数是 [`barrier()`](https://registry.khronos.org/OpenGL-Refpages/gl4/html/barrier.xhtml) 内在函数。`workgroupBarrier()` 和 `storageBarrier()` 都可以定义为 [GL_KHR_memory_scope_semantics](https://github.com/KhronosGroup/GLSL/blob/master/extensions/khr/GL_KHR_memory_scope_semantics.txt) 中定义的 `controlBarrier` 内在函数的以下调用：

```
// workgroupBarrier():
controlBarrier(gl_ScopeWorkgroup,
               gl_ScopeWorkgroup,
               gl_StorageSemanticsShared,
               gl_SemanticsAcquireRelease);

// storageBarrier():
controlBarrier(gl_ScopeWorkgroup,
               gl_ScopeWorkgroup,
               gl_StorageSemanticsBuffer,
               gl_SemanticsAcquireRelease);
```

* 在 Metal 中，`workgroupBarrier()` 等价于 `threadgroup_barrier(mem_flags::mem_threadgroup)`。`storageBarrier()` 等价于 `threadgroup_barrier(mem_flags::mem_device)`。

* 在 Vulkan SPIR-V 中，`workgroupBarrier()` 等价于具有 `Workgroup` 执行和内存作用域以及 `AcquireRelease | WorkgroupMemory` 内存语义的 `OpControlBarrier`。

  `storageBarrier()` 等价于具有 `Workgroup` 执行和内存作用域以及 `AcquireRelease | UniformMemory` 内存语义的 `OpControlBarrier`。
