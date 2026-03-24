# SkMatrixInvert

> 源文件: src/core/SkMatrixInvert.h, src/core/SkMatrixInvert.cpp

## 概述

`SkMatrixInvert` 提供了矩阵求逆的核心功能,支持 2x2、3x3 和 4x4 矩阵的求逆运算。该模块使用列主序(column-major order)存储矩阵,并通过高精度浮点运算确保数值稳定性。求逆算法基于行列式展开和代数余子式方法,在检测到非可逆矩阵时会返回零行列式值。

该模块是 Skia 图形库中矩阵变换系统的基础组件,为 2D 和 3D 变换的逆运算提供底层支持。所有函数都支持原地求逆(in-place inversion),即输入和输出矩阵可以指向同一内存地址。

## 架构位置

`SkMatrixInvert` 位于 Skia 核心层(`src/core`)中,是矩阵运算子系统的一部分:

```
src/core/
├── SkMatrix.h/cpp          # 3x3 矩阵类,调用 SkInvert3x3Matrix
├── SkM44.h/cpp             # 4x4 矩阵类,调用 SkInvert4x4Matrix
├── SkMatrixInvert.h/cpp    # 矩阵求逆核心算法(本模块)
└── SkMatrixPriv.h          # 矩阵内部辅助功能
```

该模块被 `SkMatrix`、`SkM44` 等更高层的矩阵类使用,是变换管线中的关键计算单元。

## 主要函数

| 函数名 | 功能描述 |
|--------|---------|
| `SkInvert2x2Matrix` | 求 2x2 矩阵的逆,返回行列式值 |
| `SkInvert3x3Matrix` | 求 3x3 矩阵的逆,返回行列式值 |
| `SkInvert4x4Matrix` | 求 4x4 矩阵的逆,返回行列式值 |

## 公共 API 函数

### SkInvert2x2Matrix

```cpp
SkScalar SkInvert2x2Matrix(const SkScalar inMatrix[4], SkScalar outMatrix[4])
```

**功能**: 计算 2x2 矩阵的逆矩阵。

**参数**:
- `inMatrix`: 输入矩阵,以列主序存储的 4 个标量值
- `outMatrix`: 输出矩阵,可以与 `inMatrix` 指向同一地址,也可以为 `nullptr`

**返回值**: 输入矩阵的行列式。若为零,表示矩阵不可逆,`outMatrix` 处于不确定状态。

**算法**: 使用解析公式 `det = a00*a11 - a01*a10`,逆矩阵元素为伴随矩阵除以行列式。

**数值稳定性处理**: 使用 `sk_ieee_double_divide` 进行除法,检测溢出和非有限值。

### SkInvert3x3Matrix

```cpp
SkScalar SkInvert3x3Matrix(const SkScalar inMatrix[9], SkScalar outMatrix[9])
```

**功能**: 计算 3x3 矩阵的逆矩阵,用于 2D 透视变换。

**参数**:
- `inMatrix`: 输入矩阵,以列主序存储的 9 个标量值
- `outMatrix`: 输出矩阵,可原地求逆或为 `nullptr`

**返回值**: 行列式值,零表示矩阵不可逆。

**算法**: 通过代数余子式计算伴随矩阵,行列式通过第一行展开计算。

### SkInvert4x4Matrix

```cpp
SkScalar SkInvert4x4Matrix(const SkScalar inMatrix[16], SkScalar outMatrix[16])
```

**功能**: 计算 4x4 矩阵的逆矩阵,用于 3D 变换。

**参数**:
- `inMatrix`: 输入矩阵,以列主序存储的 16 个标量值
- `outMatrix`: 输出矩阵,可原地求逆或为 `nullptr`

**返回值**: 行列式值,零表示矩阵不可逆。

**算法**: 使用分块矩阵方法计算 11 个中间值 `b00` 至 `b11`,通过组合这些值得到逆矩阵元素。

## 内部实现细节

### 数值精度策略

1. **双精度中间计算**: 所有中间步骤使用 `double` 类型,即使输入/输出是 `SkScalar`(通常为 `float`)
2. **IEEE 除法**: 使用 `sk_ieee_double_divide(1.0, determinant)` 确保正确处理特殊值
3. **有限性检查**: 通过 `SkIsFinite` 检测所有输出值,任何 `NaN` 或 `Inf` 都会导致返回零行列式

### 行列式计算

- **2x2**: `det = a00*a11 - a01*a10`
- **3x3**: 通过第一行展开 `det = a00*b01 + a01*b11 + a02*b21`
- **4x4**: 分块计算 `det = b00*b11 - b01*b10 + b02*b09 + b03*b08 - b04*b07 + b05*b06`

### 内存布局

矩阵按列主序存储:
```
2x2: [a00, a10, a01, a11]
3x3: [a00, a10, a20, a01, a11, a21, a02, a12, a22]
4x4: [a00, a10, a20, a30, a01, ..., a33] (16个元素)
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `include/core/SkScalar.h` | 标量类型定义 |
| `include/private/base/SkFloatingPoint.h` | IEEE 浮点运算辅助函数(`sk_ieee_double_divide`, `SkIsFinite`) |

### 被依赖的模块

| 模块 | 使用方式 |
|------|----------|
| `SkMatrix` | 调用 `SkInvert3x3Matrix` 实现 `invert()` 方法 |
| `SkM44` | 调用 `SkInvert4x4Matrix` 实现 4x4 矩阵求逆 |
| Canvas 变换系统 | 通过矩阵类间接使用 |

## 设计模式与设计决策

### 函数式设计

采用纯函数设计,无全局状态,仅通过参数传递数据:
- 输入矩阵为 `const`,保证不被修改
- 支持 `outMatrix` 为 `nullptr`,仅计算行列式
- 支持原地求逆,提高内存效率

### 可选输出

允许 `outMatrix` 为 `nullptr` 的设计使得调用者可以:
1. 仅检查矩阵是否可逆(检查返回值是否为零)
2. 减少不必要的逆矩阵计算

### 错误处理策略

通过返回值传递错误状态:
- 返回行列式值本身,零值自然表示不可逆
- 溢出或非有限值时强制返回零,保证鲁棒性
- 不使用异常,符合 Skia 的性能优先原则

## 性能考量

### 计算复杂度

- **2x2**: 6 次乘法 + 8 次加减法,O(1) 常数时间
- **3x3**: 约 30 次乘法,O(1) 常数时间
- **4x4**: 约 80 次乘法,O(1) 常数时间

相比通用高斯消元法,该实现利用固定矩阵大小进行了充分优化。

### 内存访问优化

1. **顺序访问**: 列主序存储与 GPU 着色器兼容
2. **原地求逆支持**: 避免额外内存分配
3. **寄存器优化**: 中间变量(如 `b00-b11`)可被编译器分配到寄存器

### 双精度权衡

使用 `double` 中间计算带来额外成本,但换来:
- 避免累积误差导致的渲染瑕疵
- 减少边界情况下的数值不稳定性
- 现代处理器上双精度性能接近单精度

## 使用示例

### 检查矩阵可逆性

```cpp
SkScalar mat[9] = {...};
if (SkInvert3x3Matrix(mat, nullptr) != 0.0f) {
    // 矩阵可逆
}
```

### 原地求逆

```cpp
SkScalar mat[4] = {2, 0, 0, 2};
SkScalar det = SkInvert2x2Matrix(mat, mat);  // mat 现在包含逆矩阵
```

### 分离输入输出

```cpp
const SkScalar input[16] = {...};
SkScalar output[16];
if (SkInvert4x4Matrix(input, output) != 0.0f) {
    // output 包含有效的逆矩阵
}
```

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/core/SkMatrix.h` | 使用者 | 3x3 变换矩阵类 |
| `include/core/SkM44.h` | 使用者 | 4x4 变换矩阵类 |
| `include/private/base/SkFloatingPoint.h` | 依赖 | 浮点运算辅助函数 |
| `src/core/SkMatrixPriv.h` | 同级 | 矩阵私有辅助功能 |
| `src/core/SkMatrixUtils.h` | 同级 | 矩阵工具函数 |

## 注意事项

1. **列主序约定**: 与 OpenGL/Vulkan 一致,但与数学教科书的行主序不同
2. **行列式阈值**: 接近零但非零的行列式可能导致数值不稳定的逆矩阵
3. **非有限值检测**: 任何中间结果溢出都会导致失败,这在极端变换下可能发生
4. **精度损失**: 单精度输入的双精度计算结果转回单精度时会截断

该模块是 Skia 变换系统的数值计算核心,其鲁棒性和性能直接影响整个图形渲染管线。
