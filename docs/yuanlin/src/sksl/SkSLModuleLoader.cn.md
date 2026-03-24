# SkSL ModuleLoader（模块加载器）

> 源文件：[src/sksl/SkSLModuleLoader.h](../../src/sksl/SkSLModuleLoader.h)、[src/sksl/SkSLModuleLoader.cpp](../../src/sksl/SkSLModuleLoader.cpp)

## 概述

`ModuleLoader` 是 SkSL 编译器的模块加载和缓存管理器。它以线程安全的方式按需加载和编译 SkSL 内置模块（如 shared、fragment、vertex、compute 等），在进程生命周期内缓存已加载的模块。`ModuleLoader` 还负责构建根符号表（包含所有内置类型）和管理 Runtime Effect 的类型别名。

## 架构位置

`ModuleLoader` 位于模块系统和编译器之间，是模块的唯一入口：

```
Compiler::convertProgram(kind)
       |
       v
Compiler::moduleForProgramKind(kind)
       |
       v
ModuleLoader::loadXxxModule(compiler)
       |
       v
compile_and_shrink()  -- 首次加载时编译
       |
       v
缓存的 Module（后续直接返回）
```

模块层级结构：
```
rootModule（内置类型）
    |
    +-- sksl_shared（公共内置函数）
    |       |
    |       +-- sksl_gpu（GPU 内置函数）
    |       |       |
    |       |       +-- sksl_frag（片段着色器）
    |       |       |       +-- sksl_graphite_frag
    |       |       +-- sksl_vert（顶点着色器）
    |       |       |       +-- sksl_graphite_vert
    |       |       +-- sksl_compute（计算着色器）
    |       |
    |       +-- sksl_public（公共 Runtime Effect）
    |               +-- sksl_rt_shader（Runtime Shader）
```

## 主要类与结构体

### `class ModuleLoader`

模块加载器，通过 RAII 方式管理互斥锁：

| 成员 | 类型 | 说明 |
|------|------|------|
| `fModuleLoader` | `Impl&` | 内部实现的引用 |

### `struct ModuleLoader::Impl`（内部）

单例实现，持有所有缓存的模块：

| 成员 | 类型 | 说明 |
|------|------|------|
| `fMutex` | `SkMutex` | 线程安全互斥锁 |
| `fBuiltinTypes` | `BuiltinTypes` | 内置类型定义 |
| `fRootModule` | `unique_ptr<const Module>` | 根模块（所有内置类型） |
| `fSharedModule` | `unique_ptr<const Module>` | 共享模块 |
| `fGPUModule` | `unique_ptr<const Module>` | GPU 模块 |
| `fVertexModule` | `unique_ptr<const Module>` | 顶点着色器模块 |
| `fFragmentModule` | `unique_ptr<const Module>` | 片段着色器模块 |
| `fComputeModule` | `unique_ptr<const Module>` | 计算着色器模块 |
| `fGraphiteVertexModule` | `unique_ptr<const Module>` | Graphite 顶点模块 |
| `fGraphiteFragmentModule` | `unique_ptr<const Module>` | Graphite 片段模块 |
| `fPublicModule` | `unique_ptr<const Module>` | 公共 Runtime Effect 模块 |
| `fRuntimeShaderModule` | `unique_ptr<const Module>` | Runtime Shader 模块 |

## 公共 API 函数

### 单例访问

- **`static Get()`** —— 获取互斥锁保护的 `ModuleLoader` 实例。构造时获取锁，析构时释放锁。

### 基础类型访问

- **`builtinTypes()`** —— 获取内置类型集合
- **`rootModule()`** —— 获取根模块

### 模块加载（懒加载）

| 方法 | 父模块 | 说明 |
|------|--------|------|
| `loadSharedModule` | root | 加载共享内置函数模块 |
| `loadGPUModule` | shared | 加载 GPU 内置函数和辅助函数 |
| `loadVertexModule` | gpu | 加载顶点着色器声明 |
| `loadFragmentModule` | gpu | 加载片段着色器声明 |
| `loadComputeModule` | gpu | 加载计算着色器声明 |
| `loadGraphiteVertexModule` | vertex | 加载 Graphite 顶点辅助函数 |
| `loadGraphiteFragmentModule` | fragment | 加载 Graphite 片段辅助函数 |
| `loadPublicModule` | shared | 加载公共 Runtime Effect 模块 |
| `loadPrivateRTShaderModule` | public | 加载 Runtime Shader 私有模块 |

### 辅助功能

- **`addPublicTypeAliases(module)`** —— 为 Runtime Effect 模块添加 GLSL 风格的类型别名（如 `vec4`、`mat4`），并隐藏私有类型
- **`unloadModules()`** —— 卸载所有模块，主要用于基准测试

## 内部实现细节

### 线程安全的 RAII 锁

```cpp
ModuleLoader ModuleLoader::Get() {
    static SkNoDestructor<ModuleLoader::Impl> sModuleLoaderImpl;
    return ModuleLoader(*sModuleLoaderImpl);
}
ModuleLoader::ModuleLoader(Impl& m) : fModuleLoader(m) {
    fModuleLoader.fMutex.acquire();
}
ModuleLoader::~ModuleLoader() {
    fModuleLoader.fMutex.release();
}
```

`ModuleLoader` 对象在构造时获取互斥锁，析构时释放。这确保同一时间只有一个线程可以加载模块。

### compile_and_shrink 辅助函数

内部函数，编译模块后移除不再需要的 `FunctionPrototype` 元素（因为函数声明已在符号表中）。最后调用 `shrink_to_fit` 释放多余的向量容量。

### 根符号表构建

`makeRootSymbolTable` 将所有内置类型注册到根模块的符号表中：

- **公共类型**（`kRootTypes`）：`Void`、`Float/Half/Int/UInt` 及其向量/矩阵变体、泛型类型、着色器类型（`Shader`、`ColorFilter`、`Blender`）
- **私有类型**（`kPrivateTypes`）：采样器（`Sampler2D` 等）、子通道输入（`SubpassInput`）、纹理（`Texture2D`）、原子类型
- **特殊变量**：`sk_Caps`（编译时设置查询能力）

### 类型别名系统

`addPublicTypeAliases` 为 Runtime Effect 提供 GLSL 兼容的类型名称：
- 添加 `vec2/vec3/vec4`、`ivec2/...`、`uvec2/...`、`bvec2/...` 别名
- 添加 `mat2/mat3/mat4` 和 `mat2x2/.../mat4x4` 别名
- 将所有私有类型（如 `sampler2D`）替换为 `invalid` 类型别名，防止在 Runtime Effect 中使用

### MODULE_DATA 宏

```cpp
#define MODULE_DATA(type) ModuleType::type, GetModuleData(ModuleType::type, #type ".sksl")
```

自动构造模块类型和源文件路径，简化加载调用。

## 依赖关系

| 依赖项 | 用途 |
|--------|------|
| `SkMutex.h` | 线程安全互斥锁 |
| `SkNoDestructor.h` | 安全的静态单例 |
| `SkSLBuiltinTypes.h` | 内置类型定义 |
| `SkSLCompiler.h` | 编译模块源代码 |
| `SkSLModule.h` | 模块数据结构和 `GetModuleData` |
| `SkSLSymbolTable.h` | 符号表管理 |
| `SkSLType.h` | 类型别名创建 |

## 设计模式与设计决策

1. **单例模式 + RAII 锁**：全局唯一的 `Impl` 通过 `SkNoDestructor` 管理生命周期，`ModuleLoader` 作为锁守卫使用。
2. **懒加载模式**：每个模块仅在首次请求时编译，之后从缓存返回。
3. **模块层级结构**：模块通过父指针形成树结构，每个层级仅添加当前着色器阶段特有的声明。
4. **编译时缩减**：`compile_and_shrink` 在编译后移除冗余的 `FunctionPrototype`，减少内存占用。
5. **公私类型分离**：Runtime Effect 模块通过类型别名系统隐藏内部类型，提供安全的公共 API 表面。

## 性能考量

- 模块在进程级别缓存，每个模块最多编译一次
- 互斥锁保证线程安全，但同一时间只允许一个线程加载
- `shrink_to_fit` 在模块编译后释放多余内存
- 移除 `FunctionPrototype` 减少内存占用（声明已在符号表中可用）
- `SkNoDestructor` 避免静态析构的开销和顺序问题
- 懒加载确保只编译实际需要的模块

## 相关文件

- `src/sksl/SkSLModule.h` / `.cpp` —— 模块数据结构
- `src/sksl/SkSLBuiltinTypes.h` —— 内置类型定义
- `src/sksl/SkSLCompiler.h` / `.cpp` —— 编译器，调用模块加载
- `src/sksl/ir/SkSLSymbolTable.h` —— 符号表
- `src/sksl/ir/SkSLType.h` —— 类型系统，别名创建
