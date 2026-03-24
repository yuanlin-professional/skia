# FuzzPathMeasure

> 源文件: fuzz/FuzzPathMeasure.cpp

## 概述

FuzzPathMeasure 是一个用于模糊测试 `SkPathMeasure` 类的模块。该文件通过生成随机的"邪恶路径"(包含极端几何形状和参数的路径),并对其进行长度测量、位置获取、切线计算以及片段提取等操作,验证路径测量API在处理异常输入时的健壮性和稳定性。

## 架构位置

```
skia/
  ├── fuzz/                          # 模糊测试根目录
  │   ├── FuzzPathMeasure.cpp       # 本文件:路径测量测试
  │   ├── FuzzPath.cpp              # 路径反序列化测试
  │   ├── FuzzPathop.cpp            # 路径布尔运算测试
  │   └── FuzzCommon.h              # 通用辅助函数(FuzzEvilPath)
  ├── include/core/                  # 核心 API
  │   ├── SkPathMeasure.h           # 路径测量类声明
  │   ├── SkPathBuilder.h           # 路径构建器
  │   └── SkPath.h                  # 路径类
  └── src/core/                      # 核心实现
      └── SkPathMeasure.cpp         # 路径测量实现
```

`SkPathMeasure` 用于测量路径长度、获取路径上特定位置的坐标和切线,是动画和路径编辑的关键组件。

## 主要类与结构体

### 核心测试目标

**SkPathMeasure** (`include/core/SkPathMeasure.h`)
- **作用**: 提供路径测量和采样功能
- **关键方法**:
  - `getLength()`: 获取当前轮廓的长度
  - `getPosTan(SkScalar distance, SkPoint* pos, SkVector* tan)`: 获取指定距离处的位置和切线
  - `getSegment(SkScalar start, SkScalar stop, SkPathBuilder* dst, bool startWithMoveTo)`: 提取路径片段
  - `nextContour()`: 移动到下一个轮廓

### 辅助函数

**FuzzEvilPath** (`fuzz/FuzzCommon.h`)
- **作用**: 生成包含极端参数的"邪恶路径"
- **特点**: 包含 NaN、Inf、超大坐标、退化曲线等

**ignoreResult**
```cpp
void inline ignoreResult(bool)
```
- 显式忽略返回值,表明测试关注崩溃而非正确性

## 公共 API 函数

### DEF_FUZZ(PathMeasure, fuzz)

```cpp
DEF_FUZZ(PathMeasure, fuzz)
```

**功能**: 模糊测试路径测量API的健壮性

**实现流程**:

1. **生成随机参数**
   ```cpp
   uint8_t bits;                    // 控制标志位
   fuzz->next(&bits);
   SkScalar distance[6];            // 6 个随机距离值
   for (auto index = 0; index < 6; ++index) {
       fuzz->next(&distance[index]);
   }
   ```

2. **生成邪恶路径**
   ```cpp
   SkPath path = FuzzEvilPath(fuzz, SkPath::Verb::kDone_Verb);
   ```

3. **尺寸验证和缩放**
   ```cpp
   SkRect bounds = path.getBounds();
   SkScalar maxDim = std::max(bounds.width(), bounds.height());
   if (maxDim > 1000000) {
       return;  // 跳过过大的路径
   }
   SkScalar resScale = maxDim / 1000;  // 计算分辨率缩放
   ```

4. **创建测量对象**
   ```cpp
   SkPathMeasure measure(path, bits & 1, resScale);
   ```

5. **测试位置和切线**
   ```cpp
   SkPoint position;
   SkVector tangent;
   ignoreResult(measure.getPosTan(distance[0], &position, &tangent));
   ```

6. **测试片段提取**
   ```cpp
   SkPathBuilder dst;
   ignoreResult(measure.getSegment(distance[1], distance[2], &dst, (bits >> 1) & 1));
   ```

7. **测试多轮廓处理**
   ```cpp
   ignoreResult(measure.nextContour());
   ignoreResult(measure.getPosTan(distance[3], &position, &tangent));
   ignoreResult(measure.getSegment(distance[4], distance[5], &dst, (bits >> 2) & 1));
   ```

## 内部实现细节

### 尺寸限制机制

```cpp
if (maxDim > 1000000) {
    return;
}
```

**设计理由**:
- 防止极大路径导致计算超时
- 避免内存溢出
- 1000000 是经验值,平衡测试覆盖和性能

### 分辨率缩放

```cpp
SkScalar resScale = maxDim / 1000;
SkPathMeasure measure(path, bits & 1, resScale);
```

**作用**:
- 自适应调整曲线细分精度
- 大路径使用较粗的分辨率
- 避免过度细分导致性能问题

### 位标志解析

```cpp
bits & 1         // forceClosed: 是否强制闭合路径
(bits >> 1) & 1  // startWithMoveTo (第一次片段提取)
(bits >> 2) & 1  // startWithMoveTo (第二次片段提取)
```

**测试覆盖**:
- 闭合路径 vs 开放路径
- 片段是否以 moveTo 开始
- 不同标志组合

### 测试场景

1. **正常距离**: 0 到路径长度
2. **负距离**: 测试边界处理
3. **超长距离**: 超过路径长度的值
4. **NaN/Inf 距离**: 特殊浮点值
5. **片段提取**:
   - start < stop: 正向提取
   - start > stop: 反向提取(可能不支持)
   - start = stop: 零长度片段

## 依赖关系

### 直接依赖

- **SkPathMeasure** (`include/core/SkPathMeasure.h`)
  - 核心测试目标

- **FuzzEvilPath** (`fuzz/FuzzCommon.h`)
  - 生成测试路径

- **SkPathBuilder** (`include/core/SkPathBuilder.h`)
  - 接收提取的路径片段

### 间接依赖

- **SkPath** (`include/core/SkPath.h`)
  - 路径表示

- **SkContourMeasure** (内部)
  - `SkPathMeasure` 的实际实现类

## 设计模式与设计决策

### 设计模式

1. **边界测试模式**
   - 测试各种距离值(负、零、超长、特殊)
   - 覆盖边界条件

2. **状态转换测试**
   - 测试多轮廓路径的状态切换
   - 验证 `nextContour` 的正确性

### 设计决策

1. **尺寸限制**
   - 防止超时是测试的首要目标
   - 牺牲极端情况覆盖换取测试稳定性

2. **多次采样**
   - 使用 6 个独立的距离值
   - 增加触发边缘情况的概率

3. **返回值忽略**
   - 关注崩溃而非功能正确性
   - 简化测试逻辑

4. **分辨率自适应**
   - 根据路径大小调整精度
   - 避免一刀切的固定参数

## 性能考量

### 测试效率

1. **早期退出**
   - 跳过过大路径
   - 避免无意义的长时间计算

2. **分辨率控制**
   - 通过 `resScale` 限制曲线细分
   - 平衡精度和性能

3. **内存管理**
   - 使用栈分配的对象
   - `SkPathBuilder` 动态增长但有合理上限

### 算法复杂度

- **路径测量初始化**: O(n),其中 n 是路径复杂度
- **getPosTan**: O(log n)(二分查找轮廓 + 曲线求值)
- **getSegment**: O(m),其中 m 是片段复杂度
- **nextContour**: O(1)

## 相关文件

### 核心实现
- `include/core/SkPathMeasure.h` - 路径测量类声明
- `src/core/SkPathMeasure.cpp` - 实现
- `src/core/SkContourMeasure.h` - 轮廓测量(内部)

### 相关测试
- `fuzz/oss_fuzz/FuzzPathMeasure.cpp` - OSS-Fuzz 版本
- `tests/PathMeasureTest.cpp` - 单元测试
- `fuzz/FuzzPath.cpp` - 路径基础测试

### 使用场景
- `modules/skottie/src/SkottieMotionTile.cpp` - 动画路径跟随
- `src/effects/SkDashPathEffect.cpp` - 虚线路径效果
- `modules/svg/src/SkSVGPath.cpp` - SVG 路径处理

### 测试基础设施
- `fuzz/Fuzz.h` - 模糊测试工具类
- `fuzz/FuzzCommon.h` - 通用辅助函数(FuzzEvilPath)

### 文档
- `site/dev/testing/fuzz.md` - 模糊测试指南
- `docs/SkPathMeasure_Reference.md` - API 参考文档
