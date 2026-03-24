# Skottie iOS 示例应用

## Metal

如何为 Metal 后端编译：

    cd $SKIA_ROOT_DIRECTORY

    mkdir -p out/ios_arm64_mtl
    cat > out/ios_arm64_mtl/args.gn <<EOM
    target_os="ios"
    target_cpu="arm64"
    skia_use_metal=true
    skia_use_expat=false
    skia_enable_pdf=false
    EOM

    tools/git-sync-deps
    bin/gn gen out/ios_arm64_mtl
    ninja -C out/ios_arm64_mtl skottie_example

然后安装 `out/ios_arm64_mtl/skottie_example.app` 应用包。

## CPU

如何为 CPU 后端编译：

    cd $SKIA_ROOT_DIRECTORY

    mkdir -p out/ios_arm64_cpu
    cat > out/ios_arm64_cpu/args.gn <<EOM
    target_cpu="arm64"
    target_os="ios"
    skia_enable_ganesh=false
    skia_enable_pdf=false
    skia_use_expat=false
    EOM

    tools/git-sync-deps
    bin/gn gen out/ios_arm64_cpu
    ninja -C out/ios_arm64_cpu skottie_example

然后安装 `out/ios_arm64_cpu/skottie_example.app` 应用包。

## OpenGL

如何为 OpenGL 后端编译：

    cd $SKIA_ROOT_DIRECTORY

    mkdir -p out/ios_arm64_gl
    cat > out/ios_arm64_gl/args.gn <<EOM
    target_cpu="arm64"
    target_os="ios"
    skia_enable_ganesh=true
    skia_use_metal=false
    skia_enable_pdf=false
    skia_use_expat=false
    EOM

    tools/git-sync-deps
    bin/gn gen out/ios_arm64_gl
    ninja -C out/ios_arm64_gl skottie_example

然后安装 `out/ios_arm64_gl/skottie_example.app` 应用包。
