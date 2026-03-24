# GrMtlVaryingHandler

> 源文件
> - src/gpu/ganesh/mtl/GrMtlVaryingHandler.h
> - src/gpu/ganesh/mtl/GrMtlVaryingHandler.mm

## 概述

`GrMtlVaryingHandler` 是 Metal 后端的 Varying 变量管理类，负责在着色器编译期间分配和管理顶点着色器输出到片段着色器输入的插值变量（Varyings）。该类继承自 `GrGLSLVaryingHandler`，复用 GLSL 接口，并实现 Metal 特定的位置索引分配和约束检查。核心功能是为每个 Varying 变量分配 `[[attribute(N)]]` 位置索引，确保不超过 Metal 的硬件限制（32 个位置，60 个分量）。

## 架构位置

- **模块层级**：`src/gpu/ganesh/mtl/` - Ganesh Metal 后端
- **继承关系**：`GrMtlVaryingHandler` -> `GrGLSLVaryingHandler`
- **使用者**：`GrMtlPipelineStateBuilder`（着色器构建器）

## 主要类与结构体

### GrMtlVaryingHandler

```cpp
class GrMtlVaryingHandler : public GrGLSLVaryingHandler
```

**构造函数**：
```cpp
GrMtlVaryingHandler(GrGLSLProgramBuilder* program) : INHERITED(program) {}
```

轻量级构造，仅调用基类构造函数。

## 公共 API 函数

继承基类所有公共接口，无额外公共 API。

## 内部实现细节

### onFinalize 实现

```cpp
void GrMtlVaryingHandler::onFinalize() override {
    finalize_helper(fVertexInputs);
    finalize_helper(fVertexOutputs);
    finalize_helper(fFragInputs);
    finalize_helper(fFragOutputs);
}
```

对四类 Varying 数组分别调用辅助函数。

### finalize_helper 辅助函数

```cpp
static void finalize_helper(VarArray& vars) {
    int locationIndex = 0;
    for (GrShaderVar& var : vars.items()) {
        // Metal 仅允许标量和向量作为 Varying
        SkASSERT(SkSLTypeVecLength(var.getType()) != -1);

        SkString location;
        location.appendf("location = %d", locationIndex);
        var.addLayoutQualifier(location.c_str());
        ++locationIndex;
    }
    SkASSERT(locationIndex <= 32);
}
```

**功能**：
1. 为每个 Varying 分配连续的位置索引
2. 添加 `[[attribute(N)]]` 布局限定符
3. 验证类型（仅标量/向量）
4. 检查硬件限制

### 硬件限制

**Metal 平台约束**：
- **iOS**：最多 60 个输入，60 个分量
- **macOS**：最多 32 个输入，128 个分量

**保守策略**：
```cpp
SkASSERT(locationIndex <= 32);    // 位置数限制
SkASSERT(componentCount <= 60);   // 分量数限制
```

统一使用最严格限制，保证跨平台兼容。

## 设计模式与设计决策

### 模板方法模式

基类定义 Varying 管理流程，子类通过 `onFinalize()` 实现平台特定逻辑。

### 懒惰初始化

位置索引在 `onFinalize()` 时分配，而非变量添加时，允许灵活重排序。

### 保守限制

使用所有平台的最小公共限制，简化代码，避免运行时平台检测。

## 性能考量

### 线性分配

位置索引线性递增，无复杂分配算法，O(n) 时间复杂度。

### 编译时验证

断言检查在调试版本生效，发布版本无开销。

## 相关文件

- `src/gpu/ganesh/glsl/GrGLSLVaryingHandler.h` - 基类
- `src/gpu/ganesh/mtl/GrMtlPipelineStateBuilder.h` - 使用者
- `src/gpu/ganesh/GrShaderVar.h` - 着色器变量表示
