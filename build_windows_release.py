import os
import sys
import shutil
import subprocess
import zipfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def build():
    root_dir = os.path.abspath(os.path.dirname(__file__))
    server_dir = os.path.join(root_dir, "ps5pack", "app", "server")
    output_dir = os.path.join(root_dir, "dist_windows")
    release_dir = os.path.join(output_dir, "ps5pack_windows_v1.2.6")
    
    print("==================================================")
    print("[*] 正在构建 PS5 AMPR LZ4 压缩工具 Windows 独立发行版...")
    print("==================================================")

    if os.path.exists(output_dir):
        shutil.rmtree(output_dir, ignore_errors=True)
    os.makedirs(release_dir, exist_ok=True)

    # 1. 准备 PyInstaller 打包参数
    main_py = os.path.join(server_dir, "main.py")
    static_src = os.path.join(server_dir, "static")
    engine_src = os.path.join(server_dir, "engine")
    version_src = os.path.join(server_dir, "version.txt")

    # 构建数据附加参数 (Windows 格式: src;dest)
    add_data = [
        f"--add-data={static_src};static",
        f"--add-data={engine_src};engine",
        f"--add-data={version_src};."
    ]

    pyinstaller_cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=ps5pack",
        "--onedir",
        "--noconfirm",
        "--clean",
        f"--paths={server_dir}",
        f"--paths={engine_src}",
        "--hidden-import=lz4",
        "--hidden-import=lz4.block",
        "--hidden-import=lz4.frame",
        "--hidden-import=tkinter",
        "--hidden-import=tkinter.filedialog",
        "--hidden-import=tomllib",
        "--hidden-import=build_ampr_index",
        "--hidden-import=ampr_pack",
        "--hidden-import=ampr_pack_format",
        f"--distpath={release_dir}",
        f"--workpath={os.path.join(output_dir, 'build')}",
        f"--specpath={output_dir}",
    ] + add_data + [main_py]

    print("\n[>] 正在调用 PyInstaller 编译独立可执行程序...")
    res = subprocess.run(pyinstaller_cmd, text=True)
    if res.returncode != 0:
        raise RuntimeError("PyInstaller 打包失败！")

    # 2. 优化便携包目录结构：将 dist/ps5pack/ 内容移动到顶层或创建快捷运行批处理
    ps5pack_dist = os.path.join(release_dir, "ps5pack")
    
    # 3. 创建一键启动批处理脚本
    bat_content = """@echo off
chcp 65001 >nul
cd /d "%~dp0"
title PS5 AMPR LZ4 游戏压缩工具 (Windows 便携版)

echo ================================================================
echo   PS5 AMPR LZ4 游戏压缩工具 - Windows 本地独立便携版
echo   版本: v1.2.6  ^|  专为 Windows 10/11 深度优化
echo ================================================================
echo.
echo [*] 正在启动后台压缩引擎...
echo [*] 本地服务监听端口: 8765
echo [*] 即将自动在您的默认浏览器中打开 Web 操作大屏...
echo.

ps5pack\\ps5pack.exe --port 8765 --open-browser

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [!] 程序异常退出，请检查上方日志。
    pause
)
"""
    with open(os.path.join(release_dir, "启动PS5压缩工具.bat"), "w", encoding="utf-8") as f:
        f.write(bat_content)

    # 4. 创建 Windows 使用说明
    readme_content = """================================================================
🎮 PS5 AMPR LZ4 游戏压缩工具 (Windows 便携独立版 v1.2.6)
================================================================

【特性简介】
1. 完全独立便携，开箱即用，无需在 Windows 上配置任何 Python 环境；
2. 双击【启动PS5压缩工具.bat】即可自动在默认浏览器中打开现代化操作大屏；
3. 支持点击“浏览”呼出 Windows 系统原生经典文件夹选择器；
4. 顶部支持一键直达所有 Windows 本地物理磁盘 (C盘、D盘、E盘、移动硬盘等)；
5. 内置索尼官方 AMPR LZ4-HC 高性能多分卷压缩算法、四级智能 Profile 匹配库以及
   Drakmor 官方最新 libSceAmpr.sprx 运行时解压驱动；
6. 支持 libSceAmpr.sprx 版本智能比对、缺失自动注入与低版本强制替换升级；
7. 实时吞吐监控、分块进度、哈希完整性校验全流程自动化。

【使用方法】
1. 双击运行目录下的【启动PS5压缩工具.bat】；
2. 浏览器将自动打开 http://127.0.0.1:8765；
3. 在【游戏源路径】中选择解包游戏根目录（包含 eboot.bin / sce_sys 的目录）；
4. 在【输出目录】中指定压缩产物存放路径；
5. 点击【⚡ 开始压缩与打包】即可在本地 CPU 满血加速压缩！
6. 打包完成后，产物可直接拷贝至破解 PS5 的 /app0 分区即拷即玩。

祝使用愉快！
"""
    with open(os.path.join(release_dir, "使用说明.txt"), "w", encoding="utf-8") as f:
        f.write(readme_content)

    # 5. 自动压缩为 ZIP 包
    zip_output = os.path.join(root_dir, "ps5pack_windows_v1.2.6.zip")
    print(f"\n[>] 正在生成最终发布压缩包: {zip_output} ...")
    if os.path.exists(zip_output):
        os.remove(zip_output)

    with zipfile.ZipFile(zip_output, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(release_dir):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, output_dir)
                zf.write(full_path, rel_path)

    zip_size = os.path.getsize(zip_output)
    print("==================================================")
    print(f"[+] Windows 独立版本构建圆满完成！")
    print(f"   发布目录: {release_dir}")
    print(f"   便携压缩包: {zip_output} ({round(zip_size / 1024 / 1024, 2)} MB)")
    print("==================================================")

if __name__ == "__main__":
    build()
