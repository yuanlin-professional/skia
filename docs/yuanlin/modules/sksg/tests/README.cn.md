# sksg/tests - 单元测试

## 概述

`tests/` 目录包含 SkSG 模块的单元测试。当前仅有一个测试文件 `SGTest.cpp`,覆盖了场景图的核心机制:节点创建、DAG 构建、失效传播、重验证和渲染。

## 目录结构

```
tests/
├── BUILD.bazel          # Bazel 构建配置
└── SGTest.cpp           # 场景图单元测试
```

## 关键测试

### SGTest.cpp

测试场景图核心功能:

1. **节点创建和属性**: 验证各种节点类型的工厂方法和属性 getter/setter
2. **DAG 构建**: 测试 Group 添加/移除子节点,EffectNode 包装
3. **失效传播**: 验证属性变更后失效标志正确向上传播
4. **重验证**: 测试 `revalidate()` 正确重新计算边界
5. **InvalidationController**: 验证脏区域追踪
6. **渲染顺序**: 确认 Group 子节点的渲染顺序
7. **可见性**: 测试 `setVisible(false)` 跳过渲染
8. **命中测试**: 测试 `nodeAt()` 返回正确的叶子节点

## 依赖关系

```
tests/
  ├── sksg/include (完整公开 API)
  ├── Skia 测试框架 (DEF_TEST, REPORTER_ASSERT)
  └── include/core (SkCanvas, SkSurface)
```

## 相关文档与参考

- **sksg 主文档**: `docs/yuanlin/modules/sksg/README.md`
- **sksg 实现**: `docs/yuanlin/modules/sksg/src/README.md`
