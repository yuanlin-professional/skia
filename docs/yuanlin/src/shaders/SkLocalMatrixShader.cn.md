# SkLocalMatrixShader

> 源文件
> - src/shaders/SkLocalMatrixShader.h
> - src/shaders/SkLocalMatrixShader.cpp

## 概述

`SkLocalMatrixShader` 是 Skia 中用于在子着色器上应用本地矩阵变换的装饰器着色器。它通过在子着色器的坐标系统中插入额外的矩阵变换,实现着色器的平移、旋转、缩放等操作,而无需修改子着色器本身。这种设计允许同一个着色器在不同位置和方向上被复用。

该文件还包含 `SkCTMShader`,它是一个特殊的着色器,用于替换当前变换矩阵(CTM)。这主要用于支持裁剪着色器,确保着色器使用裁剪定义时的CTM,而不是绘制时的CTM。

## 架构位置

`SkLocalMatrixShader` 位于 Skia 的着色器模块中:

- **模块路径**: `src/shaders/`
- **基类**: `SkShaderBase`
- **设计模式**: 装饰器模式
- **角色**: 变换装饰器,修改着色器坐标空间

## 主要类与结构体

### SkLocalMatrixShader

应用本地矩阵变换的装饰器着色器。

**核心成员**:
```cpp
SkMatrix fLocalMatrix;          // 本地变换矩阵
sk_sp<SkShader> fWrappedShader; // 被包装的子着色器
```

**主要方法**:
- `SkLocalMatrixShader(sk_sp<SkShader> wrapped, const SkMatrix& localMatrix)`: 构造函数
- `template<typename T, typename... Args> static sk_sp<SkShader> MakeWrapped(...)`: 模板工厂方法
- `bool appendStages()`: 将变换和子着色器添加到管线
- `sk_sp<SkShader> makeAsALocalMatrixShader()`: 解包本地矩阵着色器
- `bool isOpaque()`: 透明度查询(委托给子着色器)
- `GradientType asGradient()`: 渐变类型查询(合并矩阵)

### SkCTMShader

替换CTM的特殊着色器,用于裁剪着色器支持。

**核心成员**:
```cpp
sk_sp<SkShader> fProxyShader;  // 代理着色器
SkMatrix fCTM;                 // 要使用的CTM
```

**主要方法**:
- `SkCTMShader(sk_sp<SkShader> proxy, const SkMatrix& ctm)`: 构造函数
- `bool appendStages()`: 使用固定CTM添加阶段
- `const SkMatrix& ctm()`: 获取CTM
- `sk_sp<SkShader> proxyShader()`: 获取代理着色器

## 公共 API 函数

### SkLocalMatrixShader::MakeWrapped()

```cpp
template <typename T, typename... Args>
static std::enable_if_t<std::is_base_of_v<SkShader, T>, sk_sp<SkShader>>
MakeWrapped(const SkMatrix* localMatrix, Args&&... args)
```

模板工厂方法,用于创建带本地矩阵的着色器。

**参数**:
- `localMatrix`: 本地矩阵指针,如果为 `nullptr` 则不应用变换
- `args`: 转发给 `T` 构造函数的参数

**返回值**: 如果 `localMatrix` 非空,返回包装的着色器;否则直接返回 `T` 实例

**实现**:
```cpp
auto t = sk_make_sp<T>(std::forward<Args>(args)...);
if (localMatrix) {
    return t->makeWithLocalMatrix(*localMatrix);
}
return t;
```

**使用场景**: 条件性地应用本地矩阵,简化调用代码

### makeAsALocalMatrixShader()

```cpp
sk_sp<SkShader> makeAsALocalMatrixShader(SkMatrix* localMatrix) const override
```

解包本地矩阵着色器,返回被包装的着色器。

**参数**: `localMatrix` - 如果非空,输出本地矩阵

**返回值**: 被包装的子着色器

**用途**: 允许外部代码检测和处理本地矩阵着色器

### appendStages()

```cpp
bool appendStages(const SkStageRec& rec, const SkShaders::MatrixRec& mRec) const override
```

将本地矩阵和子着色器添加到管线。

**实现**:
```cpp
return as_SB(fWrappedShader)->appendStages(rec, mRec.concat(fLocalMatrix));
```

**关键**: 通过 `mRec.concat(fLocalMatrix)` 将本地矩阵链接到矩阵记录中,然后递归调用子着色器。

## 内部实现细节

### 矩阵连接

本地矩阵与现有变换矩阵的连接方式:

```cpp
// 在 appendStages 中
mRec.concat(fLocalMatrix)

// 在 asGradient 中
*localMatrix = ConcatLocalMatrices(fLocalMatrix, *localMatrix);

// 在 onIsAImage 中
*outMatrix = ConcatLocalMatrices(fLocalMatrix, imageMatrix);
```

使用 `ConcatLocalMatrices()` 工具函数确保正确的矩阵顺序和语义。

### 透明度和常量性委托

大多数查询方法直接委托给子着色器:

```cpp
bool isOpaque() const override {
    return as_SB(fWrappedShader)->isOpaque();
}

bool isConstant(SkColor4f* color) const {
    return as_SB(fWrappedShader)->isConstant(color);
}

bool onAsLuminanceColor(SkColor4f* color) const {
    return as_SB(fWrappedShader)->asLuminanceColor(color);
}
```

本地矩阵不影响这些属性,所以直接转发查询。

### 渐变类型处理

```cpp
GradientType asGradient(GradientInfo* info, SkMatrix* localMatrix) const
```

特殊处理:
1. 调用子着色器的 `asGradient()`
2. 如果是渐变,合并本地矩阵到输出矩阵中
3. 返回渐变类型

这允许渐变识别正确工作,同时保留变换信息。

### 图像检测

```cpp
SkImage* onIsAImage(SkMatrix* outMatrix, SkTileMode* mode) const
```

检测子着色器是否是图像着色器:
1. 调用子着色器的 `isAImage()`
2. 如果是图像,合并本地矩阵到图像矩阵中
3. 返回图像指针

### 序列化

**写入**:
```cpp
void flatten(SkWriteBuffer& buffer) const {
    buffer.writeMatrix(fLocalMatrix);
    buffer.writeFlattenable(fWrappedShader.get());
}
```

**读取**:
```cpp
sk_sp<SkFlattenable> CreateProc(SkReadBuffer& buffer) {
    SkMatrix lm;
    buffer.readMatrix(&lm);
    auto baseShader(buffer.readShader());
    if (!baseShader) {
        return nullptr;
    }
    return baseShader->makeWithLocalMatrix(lm);
}
```

使用 `makeWithLocalMatrix()` 确保通过标准路径创建。

### SkCTMShader 实现

`SkCTMShader` 的关键区别:

1. **固定CTM**:
   ```cpp
   bool appendStages(const SkStageRec& rec, const SkShaders::MatrixRec&) const {
       return as_SB(fProxyShader)->appendRootStages(rec, fCTM);
   }
   ```
   使用 `appendRootStages()` 并传入固定的 `fCTM`,忽略传入的矩阵记录。

2. **不可序列化**:
   ```cpp
   void flatten(SkWriteBuffer&) const override { SkASSERT(false); }
   sk_sp<SkFlattenable> CreateProc(SkReadBuffer&) { SkASSERT(false); return nullptr; }
   ```
   CTM着色器是临时的,不应该被序列化。

## 依赖关系

### 直接依赖

- **SkShaderBase**: 基类
- **SkMatrix**: 矩阵变换
- **SkShader**: 公共着色器接口
- **SkReadBuffer/SkWriteBuffer**: 序列化
- **SkArenaAlloc**: 内存分配(遗留上下文)

### 被依赖关系

- **SkShader::makeWithLocalMatrix()**: 公共API调用此实现
- **图像着色器**: 常用局部矩阵变换
- **渐变着色器**: 用于定位和缩放
- **裁剪着色器**: 使用 `SkCTMShader`

## 设计模式与设计决策

### 装饰器模式

经典的装饰器实现:
- 包装子着色器
- 添加行为(矩阵变换)
- 转发大部分调用

### 模板工厂方法

`MakeWrapped()` 使用 C++ 模板和完美转发:
- 类型安全
- 零开销抽象
- 简化条件性包装逻辑

### 查询方法的透明性

大多数查询方法透明转发:
- 本地矩阵不影响语义属性
- 仅在需要时修改矩阵相关结果
- 保持着色器身份的可检测性

### CTM 着色器的特殊性

`SkCTMShader` 的设计考虑:
- 不可序列化:它是临时的,仅在绘制期间存在
- 固定CTM:防止累积不希望的变换
- 专用于裁剪:解决特定的架构需求

## 性能考量

### 零拷贝转发

大多数操作直接转发给子着色器:
- 无额外开销
- 编译器可能内联调用
- 仅矩阵连接有小成本

### 矩阵连接优化

矩阵在管线构建时连接,而不是每像素:
- 单次矩阵乘法
- 结果在管线中重用
- 对渲染性能影响最小

### 条件性包装

`MakeWrapped()` 避免不必要的包装:
```cpp
if (localMatrix) {
    return t->makeWithLocalMatrix(*localMatrix);
}
return t;  // 直接返回,无包装开销
```

### 内联潜力

简单的委托方法(如 `isOpaque()`)易于内联:
- 编译器可能完全消除包装层
- 接近直接调用子着色器的性能

## 相关文件

### 核心依赖
- `src/shaders/SkShaderBase.h` - 着色器基类
- `include/core/SkShader.h` - 公共接口
- `include/core/SkMatrix.h` - 矩阵定义

### 序列化
- `src/core/SkReadBuffer.h` - 反序列化
- `src/core/SkWriteBuffer.h` - 序列化

### 相关着色器
- `src/shaders/SkImageShader.h` - 常与本地矩阵一起使用
- `src/shaders/gradients/SkGradientBaseShader.h` - 渐变着色器
- `src/shaders/SkPictureShader.h` - 图片着色器

### 矩阵工具
- `src/shaders/SkShaderBase.h` - `ConcatLocalMatrices()` 定义
- `src/shaders/SkShaderBase.cpp` - 矩阵连接实现

### 遗留支持
- `src/base/SkArenaAlloc.h` - 竞技场分配器
- 遗留上下文相关代码(ifdef SK_ENABLE_LEGACY_SHADERCONTEXT)
