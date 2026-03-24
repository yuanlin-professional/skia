# Ganesh Shader Assembly Branch Reference

## 1. 全局决策分支（影响整个shader结构）

| 条件 | true路径 | false路径 | 决策位置 |
|------|---------|----------|---------|
| pipeline.usesDstTexture() | 生成DstTexture采样代码+sampler | 无 | GrGLSLProgramBuilder.cpp:334 |
| pipeline.usesDstInputAttachment() | 生成input attachment加载代码 | 无 | GrGLSLProgramBuilder.cpp:381 |
| shaderCaps->fFBFetchSupport | FBFetch读取dst颜色 | 纹理/attachment读取 | GrGLSLFragmentShaderBuilder.cpp:25 |
| xp.hasSecondaryOutput() | 声明secondary output | 无 | GrGLSLProgramBuilder.cpp:415 |
| shaderCaps->mustEnableAdvBlendEqs() | 添加高级blend扩展+layout | 无 | GrGLSLFragmentShaderBuilder.cpp:47 |
| hasPointSize() | 添加sk_PointSize=1.0 | 无 | GrGLSLVertexGeoBuilder.cpp:37 |
| snapVerticesToPixelCenters() | floor+0.5对齐代码 | 直接转换 | GrGLSLVertexGeoBuilder.cpp:16 |
| colorXformHelper非空 | 生成色彩空间转换函数 | 无 | GrGLSLShaderBuilder.cpp:144 |
| FP使用sampleCoords | coords作为函数参数 | 无coords参数 | GrGLSLProgramBuilder.cpp:269 |
| FP坐标varying.type==float3 | 透视除法代码 | 直接使用float2 | GrGLSLProgramBuilder.cpp:290 |
| fp.isBlendFunction() | 添加_dst参数 | 无_dst参数 | GrGLSLProgramBuilder.cpp:260 |
| usePushConstants | push_constant layout | set/binding layout | GrVkUniformHandler.cpp:389 |

## 2. GeometryProcessor分支

### DefaultGeoProc (GrDefaultGeoProcFactory.cpp)
| 条件 | 影响 |
|------|------|
| hasVertexColor() | 顶点颜色varying vs uniform颜色 |
| tweakAlpha | coverage烘焙进alpha vs 独立coverage |
| hasExplicitLocalCoords() | 使用顶点属性 vs 矩阵变换 |
| coverage == 0xff | 无coverage代码 |
| 有vertex coverage attribute | pass-through coverage varying |

### QuadPerEdgeAAGP (QuadPerEdgeAA.cpp)
| 条件 | 影响 |
|------|------|
| CoverageMode::kWithPosition | 从位置属性提取coverage + 线性AA |
| 有纹理sampler | 纹理采样代码 |
| localCoords是float3 | 透视除法 |
| 有texture subset | 坐标钳制代码 |
| 有geometry subset | 几何子区域裁剪 |

### CircleGeometryProcessor (GrOvalOpFactory.cpp)
| 条件 | 影响 |
|------|------|
| fStroke | 内外边缘双alpha计算 vs 仅外边缘 |
| clip plane存在 | clip平面距离计算 |
| intersect plane存在 | 交集平面混合 |
| union plane存在 | 并集平面混合 |
| round cap centers存在 | 圆帽覆盖率计算 |

### EllipseGeometryProcessor (GrOvalOpFactory.cpp)
### DIEllipseGeometryProcessor (GrOvalOpFactory.cpp)
### ButtCapDashedCircleGP (GrOvalOpFactory.cpp)

### FillRRectOp::Processor (FillRRectOp.cpp)
| 条件 | 影响 |
|------|------|
| MSAA | 2x bloat multiplier |
| fakeNonAA | 无bloat |
| narrow rect | 窄矩形特殊几何 |
| linear coverage | 线性边缘coverage |
| arc coverage | 圆弧角coverage |
| 有local coords | 局部坐标varying |

### GrBitmapTextGeoProc (GrBitmapTextGeoProc.cpp)
| 条件 | 影响 |
|------|------|
| 有vertex color | pass-through vs uniform |
| mask format == ARGB | texture*color vs texture as coverage |
| color xform非空 | 色彩空间转换代码 |

### GrDistanceFieldA8TextGeoProc (GrDistanceFieldGeoProc.cpp)
| 条件 | 影响 |
|------|------|
| isUniformScale | 使用y-gradient |
| isSimilarity | 使用texture gradient length |
| general transform | 完整梯度计算 |
| gamma校正 | 额外gamma函数调用 |

### GrDistanceFieldLCDTextGeoProc (GrDistanceFieldGeoProc.cpp)
### GrDistanceFieldPathGeoProc (GrDistanceFieldGeoProc.cpp)
### GrConicEffect (GrBezierEffect.cpp)
### GrQuadEffect (GrBezierEffect.cpp)
### LatticeGP (LatticeOp.cpp)
### GrRRectShadowGeoProc (GrShadowGeoProc.cpp)
### MeshGP (DrawMeshOp.cpp) — 用户自定义VS/FS

## 3. FragmentProcessor分支

### GrTextureEffect (GrTextureEffect.cpp)
| ShaderMode | 生成的代码 |
|-----------|-----------|
| kNone | 无shader端wrap处理 |
| kClamp | clamp(coord, min, max) |
| kRepeat_Nearest_None | fract(coord*scale)*size |
| kRepeat_Linear_None | repeat+边界线性插值 |
| kRepeat_Linear_Mipmap | repeat+LOD选择+mip采样 |
| kRepeat_Nearest_Mipmap | repeat+LOD选择+最近邻 |
| kMirrorRepeat | mirror repeat公式 |
| kClampToBorder_Nearest | 边界硬过渡 |
| kClampToBorder_Filter | 边界渐变过渡 |

### GrBlendFragmentProcessor (GrBlendFragmentProcessor.cpp)
| 条件 | 影响 |
|------|------|
| fShareBlendLogic | GrGLSLBlend::BlendExpression(uniform mode) |
| !fShareBlendLogic | skgpu::BlendFuncName(mode)(src, dst) |
| 15+ SkBlendMode值 | 对应blend公式 |

### GrSkSLFP (GrSkSLFP.cpp) — 用户SkRuntimeEffect
| 条件 | 影响 |
|------|------|
| specialized uniform | 常量内联 vs 读uniform |
| 有child shader | invokeChild生成采样调用 |
| 有child colorFilter | invokeChild(inputColor) |
| 有child blender | invokeChild(src, dst) |
| toLinearSrgb调用 | 色彩空间转换代码 |
| fromLinearSrgb调用 | 逆色彩空间转换代码 |

### GrYUVtoRGBEffect (GrYUVtoRGBEffect.cpp)
| 条件 | 影响 |
|------|------|
| snap coords X/Y | 坐标对齐到texel中心 |
| 非identity色彩空间 | 色彩矩阵变换 |
| premul alpha | alpha预乘代码 |

### GrPerlinNoise2Effect (GrPerlinNoise2Effect.cpp)
| 条件 | 影响 |
|------|------|
| stitched | 有瓦片缝合逻辑 |
| 多octave | 循环累加 |

### CircularRRectEffect (GrRRectEffect.cpp)
| 条件 | 影响 |
|------|------|
| corner组合 | 不同距离计算公式 |
| inverse fill | 1-coverage |

### GrBicubicEffect (GrBicubicEffect.cpp)
| 条件 | 影响 |
|------|------|
| direction | XY/X-only/Y-only |
| clamp mode | unpremul/premul clamp |

### GrConvexPolyEffect (GrConvexPolyEffect.cpp)
| 条件 | 影响 |
|------|------|
| AA | saturate() |
| non-AA | step() |
| inverse | 反转 |
| edge count | 循环次数 |

### GrMatrixEffect (GrMatrixEffect.cpp)
### GrModulateAtlasCoverageEffect (GrModulateAtlasCoverageEffect.cpp)
### GrColorTableEffect (GrColorTableEffect.cpp)

## 4. XferProcessor分支

### PorterDuffXferProcessor (GrPorterDuffXferProcessor.cpp)
15种Porter-Duff公式各生成不同代码:
| Mode | 公式 |
|------|------|
| kClear | 0 |
| kSrc | S |
| kDst | D |
| kSrcOver | S + (1-Sa)*D |
| kDstOver | D + (1-Da)*S |
| kSrcIn | S*Da |
| kDstIn | D*Sa |
| kSrcOut | S*(1-Da) |
| kDstOut | D*(1-Sa) |
| kSrcATop | S*Da + D*(1-Sa) |
| kDstATop | D*Sa + S*(1-Da) |
| kXor | S*(1-Da) + D*(1-Sa) |
| kPlus | S+D |
| kModulate | S*D |
| kScreen | S+D-S*D |

### ShaderPDXferProcessor — shader端PD混合(需读dst)
### PDLCDXferProcessor — LCD子像素PD
### CoverageSetOpXP (GrCoverageSetOpXP.cpp)
| 条件 | 影响 |
|------|------|
| operation type | Replace/Intersect/Union/XOR/Diff/ReverseDiff |
| invert | coverage反转 |

### CustomXP (GrCustomXfermode.cpp)
### DisableColorXP (GrDisableColorXP.cpp)

## 5. 基础设施分支

### 色彩空间转换 (GrGLSLShaderBuilder.cpp:141-278)
| 条件 | 生成的函数 |
|------|-----------|
| applySrcTF() | src_tf(x) — 源transfer function |
| applyDstTF() | dst_tf(x) — 目标transfer function |
| applySrcOOTF() | src_ootf(color) — 源光学转换 |
| applyDstOOTF() | dst_ootf(color) — 目标光学转换 |
| applyGamutXform() | gamut_xform(color) — 色域矩阵 |
| applyUnpremul() | unpremul(color) |
| applyPremul() | color.rgb *= color.a |
| TF类型=sRGBish | sRGB公式 |
| TF类型=PQish | PQ公式 |
| TF类型=HLGish | HLG公式 |
| TF类型=HLGinvish | HLG逆公式 |

### Varying管理 (GrGLSLVarying.cpp)
| 条件 | 影响 |
|------|------|
| flat interpolation | varying声明加"flat"修饰 |
| noperspective | varying声明加"noperspective" |
| vertex→frag scope | 生成VS out + FS in |
| vertex→geo scope | 仅VS out |
| geo→frag scope | 仅FS in |

### 坐标变换 (GrGeometryProcessor.cpp:244+)
| 条件 | 影响 |
|------|------|
| varying type=float2 + nonsquare matrix support | float3x2(M)*coords |
| varying type=float2 + !nonsquare | (M*coords).xy |
| varying type=float3 | M*coords (保留w) |
| 有ancestor varying | 用ancestor结果作为输入 |
| isFragCoord() | 用设备坐标作为基础 |
