此资产包含为支持 EGL 和 GLES 的 x86_64 Chromebook 编译/链接 GPU 代码所需的头文件和库。

在任意 x86_64 Chromebook（例如 Pixelbook）上压缩 /usr/lib64 文件夹。将其解压到开发机器上的某个位置，并将该文件夹作为 create_and_upload 的输入：

    ./infra/bots/assets/chromebook_x86_64_gles/create_and_upload.py --lib_path [dir]

此脚本会安装以下 GL 软件包，然后将它们与解压的库打包在一起：

    libgles2-mesa-dev libegl1-mesa-dev

