# 三次方程求根模糊测试

> 源文件: `fuzz/FuzzCubicRoots.cpp`

## 概述

此文件对 Skia 的三次方程和二次方程求根算法进行模糊测试，包括 `SkCubics::RootsReal`、`SkCubics::RootsValidT` 和 `SkCubics::BinarySearchRootsValidT` 三种求解方法。验证所有输出根的有限性、唯一性和正确性。

## 架构位置

位于模糊测试框架 (`fuzz/`) 中，针对 `src/base/SkCubics.h` 中的数学工具。

## 公共 API 函数

- `DEF_FUZZ(CubicRoots, fuzz)` - 用随机系数 A,B,C,D 测试三种求根方法

## 内部实现细节

- `fuzz_cubic_real_roots` - 验证 RootsReal 返回 0-3 个有限的不重复根
- `fuzz_cubic_roots_valid_t` - 验证 RootsValidT 返回的根在 [0,1] 范围内
- `fuzz_cubic_roots_binary_search` - 验证二分搜索根在 [0,1] 范围内且回代误差 < 0.001
- 使用 `sk_doubles_nearly_equal_ulps` 检测重复根

## 依赖关系

- `src/base/SkCubics.h`, `src/base/SkQuads.h`

## 设计模式与设计决策

**属性验证**：不检查具体根值，而是验证根的数学性质（有限性、范围、唯一性、精度）。

## 性能考量

纯数学运算，执行速度极快。

## 相关文件

- `src/base/SkCubics.h` - 被测代码
