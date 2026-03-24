# SkTransformShader - 变换着色器

> 源文件:
> - `src/shaders/SkTransformShader.h`
> - `src/shaders/SkTransformShader.cpp`

## 概述

SkTransformShader 是一个特殊的着色器包装类，它在着色器坐标上应用一个可动态更新的矩阵变换。与普通的 SkLocalMatrixShader 不同，SkTransformShader 的矩阵不会与逆 CTM 或其他本地矩阵合并，并且可以在管线构建后通过 `update()` 方法修改矩阵值。这使其特别适用于 `drawVertices` 和 `drawAtlas` 等操作，在这些场景中每个三角形或图集四边形需要不同的纹理坐标映射。

## 架构位置

```
Skia 着色器系统
├── SkShaderBase (内部基类)
│   └── SkTransformShader (本模块 - 可变矩阵变换)
│       ├── 矩阵管线阶段 (matrix_2x3 或 matrix_perspective)
│       └── 子着色器执行
├── SkCanvas::drawVertices() (使用场景)
├── SkCanvas::drawAtlas() (使用场景)
└── SkRasterPipeline (光栅管线)
```

## 主要类与结构体

### `SkTransformShader`
- 继承自 `SkShaderBase`，不可序列化。
- **成员变量**:
  - `fShader` (const SkShaderBase&): 被变换的子着色器的引用（不拥有所有权）。
  - `fMatrixStorage` (SkScalar[9]): 矩阵数据存储，供 SkRasterPipeline 直接读取。
  - `fAllowPerspective` (bool): 是否允许透视变换。

## 公共 API 函数

### 构造函数
```cpp
explicit SkTransformShader(const SkShaderBase& shader, bool allowPerspective);
```
- 初始化矩阵存储为单位矩阵 (`SkMatrix::I().get9(fMatrixStorage)`)。
- 不拥有子着色器的所有权，仅保持引用。

### `update`
```cpp
bool update(const SkMatrix& matrix);
```
- **功能**: 更新管线中使用的变换矩阵。
- **参数验证**: 如果 `fAllowPerspective` 为 false 且矩阵包含透视分量，返回 false。
- **实现**: 直接将矩阵的 9 个值写入 `fMatrixStorage`，由于管线引用的是同一块内存，更新立即生效。

### `appendStages`
```cpp
bool appendStages(const SkStageRec& rec, const SkShaders::MatrixRec& mRec) const override;
```
- **功能**: 向光栅管线添加矩阵变换阶段。

### 其他方法
- `type()`: 返回 `ShaderType::kTransform`。
- `isOpaque()`: 委托给子着色器的 `isOpaque()`。
- `getFactory()` / `getTypeName()`: 触发 `SkDEBUGFAIL`，因为此类不支持序列化。

## 内部实现细节

### appendStages 流程
1. **断言检查**: `SkASSERT(!mRec.hasPendingMatrix())` - 调用者通常已将父矩阵折叠到 `update()` 的矩阵中。
2. **应用父矩阵**: 调用 `mRec.apply(rec)` 处理任何待处理的矩阵（通常只是 seed 坐标）。
3. **标记总矩阵无效**: `childMRec->markTotalMatrixInvalid()` - 因为矩阵会在管线使用期间变化，子着色器不应依赖总矩阵。
4. **添加矩阵阶段**: 根据是否允许透视，选择 `matrix_perspective` 或 `matrix_2x3` 操作。矩阵数据指向 `fMatrixStorage`。
5. **执行子着色器**: 将子着色器的阶段追加到管线。

### 矩阵就地更新机制
`fMatrixStorage` 是一个固定大小的数组，其地址在 `appendStages` 时传给 SkRasterPipeline。之后通过 `update()` 直接修改同一块内存，管线在下次执行时自动使用新值。这个设计避免了重建管线的开销。

### 不可序列化
该着色器是临时性的运行时对象，不参与 SkPicture 录制或序列化。`getFactory()` 和 `getTypeName()` 方法的 `SkDEBUGFAIL` 确保在调试时能捕获错误的序列化尝试。

### 与 SkLocalMatrixShader 的区别
| 特性 | SkLocalMatrixShader | SkTransformShader |
|---|---|---|
| 矩阵合并 | 与 CTM 逆矩阵和其他本地矩阵合并 | 独立于 CTM，不合并 |
| 可变性 | 创建时固定 | 运行时可通过 update() 修改 |
| 总矩阵 | 有效 | 标记为无效 |
| 序列化 | 支持 | 不支持 |
| 用途 | 一般的本地坐标变换 | drawVertices/drawAtlas 的每图元变换 |

## 依赖关系

- `include/core/SkMatrix.h`: 矩阵操作。
- `include/core/SkScalar.h`: 标量类型。
- `src/shaders/SkShaderBase.h`: 着色器基类和 MatrixRec。
- `src/core/SkRasterPipeline.h`: 光栅管线。
- `src/core/SkRasterPipelineOpList.h`: 管线操作枚举。
- `src/core/SkEffectPriv.h`: `SkStageRec` 定义。

## 设计模式与设计决策

1. **就地修改模式**: 通过共享矩阵存储地址实现管线参数的运行时更新，无需重建管线。
2. **非拥有引用**: 对子着色器使用 const 引用而非 sk_sp，表明该着色器的生命周期由调用者管理。
3. **禁止序列化**: 明确不支持序列化，用断言防止误用。
4. **透视控制**: 通过 `fAllowPerspective` 标志控制是否接受透视矩阵，因为 2x3 矩阵管线操作比 perspective 更高效。

## 性能考量

1. **零重建更新**: `update()` 仅写入 9 个 float 值，无需重建管线或重新分配内存。
2. **管线操作选择**: 非透视情况使用 `matrix_2x3`（6 次乘加），透视使用 `matrix_perspective`（9 次乘加加除法）。
3. **断言优化**: `SkASSERT(!mRec.hasPendingMatrix())` 确认了典型使用场景中不需要额外的矩阵应用步骤。
4. **总矩阵无效化**: 通过标记总矩阵无效，避免了子着色器基于过时信息做出错误的优化决策。

## 相关文件

- `src/shaders/SkShaderBase.h/.cpp`: 着色器基类和 MatrixRec。
- `src/core/SkDraw_vertices.cpp`: drawVertices 实现，创建 SkTransformShader。
- `src/core/SkDraw_atlas.cpp`: drawAtlas 实现，创建 SkTransformShader。
- `src/core/SkRasterPipeline.h`: 光栅管线。
- `src/shaders/SkLocalMatrixShader.h`: 普通的本地矩阵着色器（对比参考）。
