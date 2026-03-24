# FuzzRegionSetPath (OSS-Fuzz)

> 源文件: fuzz/oss_fuzz/FuzzRegionSetPath.cpp

## 概述

测试 `SkRegion::setPath()` 方法,该方法将任意路径转换为区域表示。这是路径到矩形集合的转换,用于高效的区域操作和裁剪。

## 架构位置

测试 `include/core/SkRegion.h` 的路径转换功能。

## 主要类与结构体

### FuzzRegionSetPath 函数

```cpp
void FuzzRegionSetPath(Fuzz* fuzz)
```

执行步骤:
1. 生成随机路径: `FuzzNicePath(fuzz, 1000)`
2. 可选初始化区域 r1
3. 生成随机区域 r2 作为裁剪
4. 执行路径转换: `r1.setPath(p, r2)`
5. 验证结果区域的有效性

### LLVMFuzzerTestOneInput

最大输入 512 字节,平衡复杂度和性能。

## 内部实现细节

### setPath 算法

将路径光栅化为区域:
1. 扫描线算法遍历路径
2. 计算与区域 r2 的交集
3. 生成矩形集合表示

### 验证操作

```cpp
r1.computeRegionComplexity();
r1.isComplex();
r1.contains(0,0) or r1.contains(1,1);
```

确保区域结构正确,触发内部一致性检查。

### 边界情况

- 空路径
- 自相交路径
- 非常复杂的路径(1000个操作)
- 退化矩形

## 依赖关系

- `fuzz/FuzzCommon.h`: `FuzzNicePath` 函数
- `include/core/SkPath.h`: 路径定义
- `src/core/SkRegion.cpp`: 区域实现

## 设计模式与设计决策

### 路径光栅化

setPath 是路径到区域的桥梁:
- 路径: 连续几何
- 区域: 离散矩形集

### 参数化测试

通过 `initR1` 标志测试两种场景:
- 未初始化区域
- 预初始化区域

## 性能考量

- **路径复杂度**: 限制为 1000 个操作
- **光栅化成本**: O(n) 扫描线算法
- **内存**: 复杂路径生成大量矩形

## 相关文件

- `src/core/SkScan.cpp`: 扫描线光栅化
- `tests/RegionTest.cpp`: 区域单元测试

该 fuzzer 发现了多个 setPath 实现中的边界情况错误,提高了区域操作的可靠性。
