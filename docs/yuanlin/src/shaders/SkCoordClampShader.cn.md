# SkCoordClampShader

> 源文件
> - src/shaders/SkCoordClampShader.h
> - src/shaders/SkCoordClampShader.cpp

## 概述

`SkCoordClampShader` 是一个装饰器着色器,用于将子着色器的采样坐标限制在指定的矩形范围内。它通过在光栅管线中插入坐标钳制操作,确保着色器评估时使用的坐标不会超出定义的边界矩形。这在需要严格控制图像采样区域或防止坐标溢出时非常有用。

该着色器本身不产生颜色,而是修改传递给内部着色器的坐标,从而间接控制最终的着色结果。它是 Skia 着色器组合系统中的一个辅助工具。

## 架构位置

`SkCoordClampShader` 位于 Skia 的着色器模块中:

- **模块路径**: `src/shaders/`
- **基类**: `SkShaderBase` (位于 `src/shaders/SkShaderBase.h`)
- **公共接口**: 通过 `SkShaders::CoordClamp()` 工厂函数创建
- **设计模式**: 装饰器模式 (Decorator Pattern)

该类在着色器层次结构中作为一个包装器,修改子着色器的行为而不改变其核心逻辑。它通常与 `SkImageShader` 等需要坐标约束的着色器一起使用。

## 主要类与结构体

### SkCoordClampShader

核心装饰器类,将子着色器的坐标限制在矩形范围内。

**关键成员**:
```cpp
sk_sp<SkShader> fShader;  // 被包装的子着色器
SkRect fSubset;           // 坐标限制的矩形范围
```

**主要方法**:
- `SkCoordClampShader(sk_sp<SkShader> shader, const SkRect& subset)`: 构造函数
- `ShaderType type() const`: 返回 `ShaderType::kCoordClamp`
- `sk_sp<SkShader> shader() const`: 获取被包装的着色器
- `SkRect subset() const`: 获取限制矩形

### SkRasterPipelineContexts::CoordClampCtx

光栅管线上下文结构,用于存储钳制边界:
```cpp
struct CoordClampCtx {
    float left, top, right, bottom;
};
```

### 工厂函数

```cpp
namespace SkShaders {
    sk_sp<SkShader> CoordClamp(sk_sp<SkShader> shader, const SkRect& subset);
}
```

## 公共 API 函数

### SkShaders::CoordClamp()

```cpp
sk_sp<SkShader> CoordClamp(sk_sp<SkShader> shader, const SkRect& subset)
```

创建一个坐标钳制着色器,将子着色器的采样坐标限制在指定矩形内。

**参数**:
- `shader`: 要被包装的子着色器,不能为空
- `subset`: 坐标限制的矩形范围,必须是已排序的 (左<=右, 上<=下)

**返回值**:
- 成功时返回新创建的 `SkCoordClampShader` 智能指针
- 如果 `shader` 为空或 `subset` 未排序,返回 `nullptr`

**验证逻辑**:
```cpp
if (!shader) return nullptr;           // 子着色器必须存在
if (!subset.isSorted()) return nullptr; // 矩形必须已排序
```

**使用场景**:
- 限制图像着色器的采样区域
- 防止纹理坐标溢出
- 实现图像子区域渲染
- 配合硬件边界约束优化

## 内部实现细节

### 坐标钳制机制

`appendStages()` 方法实现了坐标钳制的核心逻辑:

```cpp
bool appendStages(const SkStageRec& rec, const SkShaders::MatrixRec& mRec) const
```

**实现步骤**:

1. **应用矩阵变换**:
   ```cpp
   std::optional<SkShaders::MatrixRec> childMRec = mRec.apply(rec);
   if (!childMRec.has_value()) {
       return false;
   }
   ```
   将父级矩阵应用到当前上下文,生成子着色器的矩阵记录。

2. **创建钳制上下文**:
   ```cpp
   auto clampCtx = rec.fAlloc->make<SkRasterPipelineContexts::CoordClampCtx>();
   *clampCtx = {fSubset.fLeft, fSubset.fTop, fSubset.fRight, fSubset.fBottom};
   ```
   在竞技场分配器中创建钳制上下文,存储矩形边界。

3. **插入钳制操作**:
   ```cpp
   rec.fPipeline->append(SkRasterPipelineOp::clamp_x_and_y, clampCtx);
   ```
   在管线中添加 `clamp_x_and_y` 操作,这会将坐标限制在指定范围内。

4. **追加子着色器阶段**:
   ```cpp
   return as_SB(fShader)->appendStages(rec, *childMRec);
   ```
   使用钳制后的坐标评估子着色器。

### 矩阵有效性注释

代码中有一个重要的注释:

```cpp
// Strictly speaking, childMRec's total matrix is not valid. It is only valid inside the subset
// rectangle. However, we don't mark it as such because we want the "total matrix is valid"
// behavior in SkImageShader for filtering.
```

这说明:
- 从技术上讲,子矩阵仅在子集矩形内有效
- 但为了与 `SkImageShader` 的过滤行为兼容,故意不标记为无效
- 这是一个权衡设计,优先考虑图像过滤的正确性

### 序列化实现

**写入 (flatten)**:
```cpp
void flatten(SkWriteBuffer& buffer) const {
    buffer.writeFlattenable(fShader.get());  // 序列化子着色器
    buffer.writeRect(fSubset);                // 序列化矩形
}
```

**读取 (CreateProc)**:
```cpp
sk_sp<SkFlattenable> SkCoordClampShader::CreateProc(SkReadBuffer& buffer) {
    sk_sp<SkShader> shader(buffer.readShader());  // 反序列化子着色器
    SkRect subset = buffer.readRect();             // 反序列化矩形
    if (!buffer.validate(SkToBool(shader))) {      // 验证子着色器存在
        return nullptr;
    }
    return SkShaders::CoordClamp(std::move(shader), subset);
}
```

序列化格式简单明了,仅存储子着色器和限制矩形。

### 向后兼容性

```cpp
void SkRegisterCoordClampShaderFlattenable() {
    SK_REGISTER_FLATTENABLE(SkCoordClampShader);

    // Previous name
    SkFlattenable::Register("SkShader_CoordClamp", SkCoordClampShader::CreateProc);
}
```

注册了旧名称 `"SkShader_CoordClamp"`,确保旧版本 SKP 文件可以正确加载。

## 依赖关系

### 直接依赖

- **SkShaderBase**: 基类,提供着色器接口
- **SkShader**: 公共着色器接口
- **SkRect**: 矩形表示
- **SkRasterPipeline**: 光栅管线系统
- **SkRasterPipelineOp**: 管线操作定义 (`clamp_x_and_y`)
- **SkRasterPipelineContexts**: 管线上下文定义
- **SkArenaAlloc**: 竞技场分配器,用于高效内存分配
- **SkFlattenable**: 序列化框架

### 被依赖关系

作为工具类着色器,可能被以下场景使用:
- **图像裁剪**: 与 `SkImageShader` 配合限制采样区域
- **纹理映射**: 防止纹理坐标溢出
- **九宫格绘制**: 限制每个九宫格区域的坐标
- **特效组合**: 作为复杂着色器链的一部分

### 典型使用模式

```cpp
// 限制图像着色器采样到特定子区域
auto imageShader = SkImageShader::Make(...);
auto clampedShader = SkShaders::CoordClamp(imageShader, SkRect::MakeXYWH(10, 10, 100, 100));
paint.setShader(clampedShader);
```

## 设计模式与设计决策

### 装饰器模式

`SkCoordClampShader` 是装饰器模式的标准实现:
- **包装对象**: 持有子着色器的引用
- **透明转发**: 除坐标修改外,其他功能转发给子着色器
- **功能增强**: 在管线中插入钳制操作,不改变子着色器本身

### 不可变对象设计

着色器一旦创建就不可修改:
- `fShader` 和 `fSubset` 都是 `const` (通过构造初始化列表)
- 没有提供修改方法
- 线程安全,可以在多个上下文中共享

### 失败快速原则 (Fail-Fast)

工厂函数在参数无效时立即返回 `nullptr`:
```cpp
if (!shader) return nullptr;           // 立即检查子着色器
if (!subset.isSorted()) return nullptr; // 立即检查矩形有效性
```

这避免了创建无效对象,使错误更容易追踪。

### 懒惰评估与管线架构

坐标钳制不是在创建时执行,而是在管线构建时:
- 着色器创建仅存储参数
- 实际的钳制操作在 `appendStages()` 中添加到管线
- 允许管线优化器分析和优化整个管线

### 精确语义与兼容性权衡

关于矩阵有效性的设计决策体现了实用主义:
- 理论上应该标记矩阵仅在子集内有效
- 实际上为了与 `SkImageShader` 的过滤兼容而妥协
- 优先保证实际使用场景的正确性

## 性能考量

### 管线操作开销

`clamp_x_and_y` 是一个轻量级操作:
- 对每个像素执行 4 次 min/max 比较
- 现代 CPU 可以高效执行 (可能向量化)
- 开销相对于整体着色计算通常可以忽略

### 内存分配

使用 `SkArenaAlloc` 分配钳制上下文:
- 竞技场分配器提供快速批量分配
- 避免单独的堆分配开销
- 管线完成后统一释放

### 缓存友好性

上下文结构体紧凑 (4 个 float):
- 容易适应 CPU 缓存行
- 在管线执行期间保持热缓存
- 最小化内存访问延迟

### 优化机会

可能的优化方向:
1. **常量折叠**: 如果子集覆盖整个坐标空间,可以完全消除钳制
2. **边界检测**: 在某些情况下可以预先判断坐标是否需要钳制
3. **SIMD 加速**: 硬件支持向量化的 min/max 操作

### 与子着色器的协同

配合 `SkImageShader` 使用时:
- 钳制后的坐标保证在有效范围内
- 可能允许子着色器跳过边界检查
- 对于纹理采样,可能启用更快的采样路径

## 相关文件

### 核心依赖
- `src/shaders/SkShaderBase.h` - 着色器基类定义
- `src/shaders/SkShaderBase.cpp` - 着色器基类实现
- `include/core/SkShader.h` - 公共着色器接口
- `include/effects/SkShaders.h` - 着色器工厂函数声明

### 渲染管线
- `src/core/SkRasterPipeline.h` - 光栅管线核心
- `src/core/SkRasterPipelineOpList.h` - 管线操作列表
- `src/core/SkRasterPipelineOpContexts.h` - 管线上下文定义
- `src/base/SkArenaAlloc.h` - 竞技场分配器

### 几何与序列化
- `include/core/SkRect.h` - 矩形定义
- `src/core/SkReadBuffer.h` - 反序列化工具
- `src/core/SkWriteBuffer.h` - 序列化工具
- `include/core/SkFlattenable.h` - 可序列化对象基类

### 相关着色器
- `src/shaders/SkImageShader.h` - 图像着色器 (主要配合对象)
- `src/shaders/SkLocalMatrixShader.h` - 本地矩阵着色器 (类似装饰器)
- `src/shaders/SkTransformShader.h` - 变换着色器 (坐标操作相关)

### 工具与私有 API
- `src/core/SkEffectPriv.h` - 效果私有工具
- `include/private/base/SkTo.h` - 类型转换工具 (`SkToBool`)
