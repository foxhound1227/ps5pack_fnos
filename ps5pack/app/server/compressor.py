#!/usr/bin/env python3
"""
PS5 Game AMPR LZ4 Compressor Core Engine
========================================
负责核心任务调度、ampr_pack 调用、实时进度解析、Loose 文件复制与完整性校验。
"""

import os
import sys
import json
import time
import shutil
import subprocess
import threading
import re
import hashlib
import fnmatch
from pathlib import Path
from typing import Dict, Any, List, Optional

DISK_IMAGE_EXTS = {".exfat", ".img", ".iso", ".bin", ".raw"}

# 全局安全防御排除清单（对齐 Nazky/Lazy_AMPR 与 PS5 引导兼容标准）
# 规则说明：由于 fnmatchcase 机制中 '**/xxx' 不匹配根目录文件，因此所有模式均同时声明 'xxx' 与 '**/xxx'
SAFETY_EXCLUSIONS = (
    # 1. 签名与可执行入口（PS5 OS 加载必需）
    "eboot.bin", "**/eboot.bin",
    "*.elf", "**/*.elf",
    "*.self", "**/*.self",
    "*.prx", "**/*.prx",
    "*.sprx", "**/*.sprx",
    "sce_module/**", "**/sce_module/**",
    "sce_sys/**", "**/sce_sys/**",
    "fakelib/**", "**/fakelib/**",
    "system/**", "**/system/**",
    "decrypted/**", "**/decrypted/**",
    "mods/**", "**/mods/**",
    "save/**", "**/save/**",
    "_DUPLEX_/**", "**/_DUPLEX_/**",
    "trophy2/**", "**/trophy2/**",
    "uds/**", "**/uds/**",

    # 2. 游戏代码运行时核心（Unity / Capcom RE Engine / 虚幻引擎 / 索尼第一方代码引导）
    "*.rds", "**/*.rds",
    "runtime_il2cppMasterPS5.rds", "**/runtime_il2cppMasterPS5.rds",
    "*.args", "**/*.args",
    "natives/**", "**/natives/**",
    "*.utoc", "**/*.utoc",
    "*.cache", "**/*.cache",
    "*.odx", "**/*.odx",
    "*.odxb", "**/*.odxb",

    # 3. 签名凭据、存档 Key 与内部索引
    "keystone", "**/keystone",
    "nptitle.dat", "**/nptitle.dat",
    "ampr_emu.index", "**/ampr_emu.index",
    "ampr_assets.index", "**/ampr_assets.index",
    "ampr_assets.index.crc", "**/ampr_assets.index.crc",
    "ampr_assets.index.runtime", "**/ampr_assets.index.runtime",
    "ampr_assets-*.pak", "**/ampr_assets-*.pak",

    # 4. 开机敏感视频与动画容器（底层通过 mmap 直读，必须 loose 否则开机启动图后死锁）
    "*.bk2", "**/*.bk2",
    "*.usm", "**/*.usm",
    "*.ivf", "**/*.ivf",
    "*.mp4", "**/*.mp4",
    "*.m4v", "**/*.m4v",
    "*.mkv", "**/*.mkv",
    "*.avi", "**/*.avi",
    "*.webm", "**/*.webm",
    "video/**", "**/video/**",
    "movie/**", "**/movie/**",
    "movies/**", "**/movies/**",
    "cutscene/**", "**/cutscene/**",
    "cutscenes/**", "**/cutscenes/**",
    "fmv/**", "**/fmv/**",
    "cinematic/**", "**/cinematic/**",
    "cinematics/**", "**/cinematics/**",

    # 5. 音频容器与 SoundBank（开机期直接读取）
    "*.bnk", "**/*.bnk",
    "*.wem", "**/*.wem",
    "*.at9", "**/*.at9",
    "*.sxd", "**/*.sxd",
    "*.ogg", "**/*.ogg",
    "*.opus", "**/*.opus",
    "*.flac", "**/*.flac",
    "*.mp3", "**/*.mp3",
    "*.aac", "**/*.aac",
    "*.m4a", "**/*.m4a",
    "soundbank/**", "**/soundbank/**",

    # 6. 配置文件、数据表与脚本（轻量级，明文直读）
    "*.ini", "**/*.ini",
    "*.cfg", "**/*.cfg",
    "*.json", "**/*.json",
    "*.xml", "**/*.xml",
    "*.txt", "**/*.txt",
    "*.dat", "**/*.dat",
    "*.bak", "**/*.bak",
    "*.pfs", "**/*.pfs",
    "*.url", "**/*.url",
    "*.sfx", "**/*.sfx",
    "param.sfx", "**/param.sfx",

    # 7. 贴图与已压缩格式（LZ4 零压缩收益）
    "*.png", "**/*.png",
    "*.jpg", "**/*.jpg",
    "*.jpeg", "**/*.jpeg",
    "*.webp", "**/*.webp",
    "*.dds", "**/*.dds",
    "*.ktx", "**/*.ktx",
    "*.ktx2", "**/*.ktx2",
    "*.otf", "**/*.otf",
    "*.ttf", "**/*.ttf",
)

class ImageMountContext:
    """Linux 虚拟磁盘镜像只读挂载上下文 (支持 .exfat, .img, .iso, .raw 等)"""
    def __init__(self, image_path: str, mount_base: str):
        self.image_path = os.path.abspath(image_path)
        self.mount_base = mount_base
        self.mount_point = ""
        self.is_mounted = False

    def __enter__(self) -> str:
        if not os.path.isfile(self.image_path):
            raise FileNotFoundError(f"镜像文件不存在: {self.image_path}")

        token = hashlib.md5(f"{self.image_path}_{time.time()}".encode()).hexdigest()[:8]
        self.mount_point = os.path.join(self.mount_base, f"mnt_{token}")
        os.makedirs(self.mount_point, exist_ok=True)

        if os.name != "nt":
            # 1. 优先尝试自动探测文件系统类型 (loop,ro)
            cmd = ["mount", "-o", "loop,ro", self.image_path, self.mount_point]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode != 0:
                # 2. 尝试显式指定 -t exfat 挂载
                cmd_exfat = ["mount", "-t", "exfat", "-o", "loop,ro", self.image_path, self.mount_point]
                res_exfat = subprocess.run(cmd_exfat, capture_output=True, text=True)
                if res_exfat.returncode != 0:
                    try:
                        os.rmdir(self.mount_point)
                    except Exception:
                        pass
                    err_msg = res.stderr.strip() or res_exfat.stderr.strip() or "mount 执行异常"
                    raise RuntimeError(f"挂载镜像文件失败 ({err_msg})，请确保具有系统权限及 exfat 支持")

            self.is_mounted = True
            return self.mount_point
        else:
            raise NotImplementedError("Windows 开发环境暂不支持直接 loop 挂载 Linux 镜像，请在飞牛 OS 下运行")

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.is_mounted and self.mount_point:
            if os.name != "nt":
                try:
                    res = subprocess.run(["umount", self.mount_point], capture_output=True, text=True)
                    if res.returncode != 0:
                        subprocess.run(["umount", "-l", self.mount_point], capture_output=True, text=True)
                except Exception:
                    pass
            try:
                if os.path.exists(self.mount_point):
                    os.rmdir(self.mount_point)
            except Exception:
                pass
            self.is_mounted = False

ENGINE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "engine")
DEFAULT_PROFILE_PATH = os.path.join(ENGINE_DIR, "generic_ps5.toml")
BUILD_INDEX_PY = os.path.join(ENGINE_DIR, "build_ampr_index.py")
AMPR_PACK_PY = os.path.join(ENGINE_DIR, "ampr_pack.py")

class CompressorManager:
    def __init__(self, data_dir: Optional[str] = None):
        if data_dir is None:
            data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        self.history_file = os.path.join(self.data_dir, "history.json")
        self.last_paths_file = os.path.join(self.data_dir, "last_paths.json")
        
        self.lock = threading.Lock()
        self.current_process: Optional[subprocess.Popen] = None
        self.worker_thread: Optional[threading.Thread] = None
        self.stop_requested = False
        
        # 活跃任务状态
        self.task_state: Dict[str, Any] = {
            "status": "idle",          # idle, scanning, indexing, packing, verifying, copying_loose, completed, failed, stopped
            "step": "",                # 步骤描述
            "progress": 0,             # 0 - 100
            "speed": "—",              # 例如 "145.2 MiB/s"
            "elapsed": 0,              # 已用秒数
            "eta": "—",                # 预估剩余时间
            "logical_bytes": 0,        # 原始解压大小
            "stored_bytes": 0,         # 压缩后大小
            "saved_bytes": 0,          # 节省字节
            "saving_pct": 0.0,         # 节省百分比
            "current_file": "—",       # 当前正在处理的文件
            "packed_files": 0,         # 已打包文件数
            "loose_files": 0,          # 散文件数
            "loose_copied": 0,         # 成功复制的散文件数
            "game_name": "",           # 游戏名称
            "src_path": "",            # 输入路径
            "out_path": "",            # 输出路径
            "start_time": 0,
            "end_time": 0,
            "error": "",
            "live_log": "",            # 单行实时刷新状态 (In-place live line)
            "logs": []                 # 永久历史日志 (重要阶段与里程碑)
        }
        self.load_history()

    def add_log(self, message: str):
        timestamp = time.strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        with self.lock:
            self.task_state["logs"].append(log_entry)
            if len(self.task_state["logs"]) > 500:
                self.task_state["logs"].pop(0)

    def load_history(self, limit: int = 5) -> List[Dict[str, Any]]:
        """读取历史记录，默认返回最近 5 条；limit=0 时返回全部"""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        if limit and limit > 0:
                            return data[:limit]
                        return data
                    return []
            except Exception:
                return []
        return []

    def save_history_entry(self, entry: Dict[str, Any]):
        history = self.load_history(limit=0)
        history.insert(0, entry)
        if len(history) > 50:
            history = history[:50]
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.add_log(f"保存历史记录失败: {e}")

    def load_last_paths(self) -> Dict[str, str]:
        """读取最近一次配置的游戏源目录和输出目录"""
        if os.path.exists(self.last_paths_file):
            try:
                with open(self.last_paths_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"src": "", "out": ""}

    def save_last_paths(self, src: str = "", out: str = ""):
        """持久化保存最近一次配置的游戏源目录和输出目录"""
        if not src and not out:
            return
        data = self.load_last_paths()
        if src:
            data["src"] = src
        if out:
            data["out"] = out
        try:
            with open(self.last_paths_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def inspect_leaf(self, path: str) -> Dict[str, Any]:
        """嗅探指定路径是否为 PS5 游戏根目录，支持多层嵌套自动发现"""
        if not path or not os.path.exists(path):
            return {"valid": False, "reason": "路径不存在", "leaf": path}

        # 如果传入的是磁盘镜像单文件 (.exfat, .img, .iso, .bin, .raw)
        if os.path.isfile(path):
            ext = os.path.splitext(path)[1].lower()
            if ext in DISK_IMAGE_EXTS:
                if os.name != "nt":
                    try:
                        with ImageMountContext(path, self.data_dir) as mnt:
                            sub_res = self.inspect_leaf(mnt)
                            sub_res["is_image"] = True
                            sub_res["leaf"] = path
                            sub_res["message"] = f"✓ 镜像探测成功: 内部包含 PS5 游戏特征，已准备好自动挂载流水线"
                            return sub_res
                    except Exception as e:
                        return {
                            "valid": True,
                            "is_leaf": True,
                            "is_image": True,
                            "leaf": path,
                            "message": f"已识别 {ext.upper()} 磁盘单文件镜像，将在后台自动安全挂载"
                        }
                else:
                    return {
                        "valid": True,
                        "is_leaf": True,
                        "is_image": True,
                        "leaf": path,
                        "message": f"已识别 {ext.upper()} 虚拟磁盘单文件镜像 (在飞牛 OS 下将自动只读挂载)"
                    }
            else:
                return {"valid": False, "reason": "不支持的文件类型", "leaf": path, "message": "所选文件非支持的磁盘镜像格式 (.exfat/.img/.iso/.bin)"}

        def check_dir(d: str) -> bool:
            has_eboot = os.path.isfile(os.path.join(d, "eboot.bin"))
            has_sce_sys = os.path.isdir(os.path.join(d, "sce_sys"))
            has_d = os.path.isdir(os.path.join(d, "d"))
            return has_eboot or has_sce_sys or has_d

        if check_dir(path):
            return {
                "valid": True,
                "is_leaf": True,
                "leaf": path,
                "has_eboot": os.path.isfile(os.path.join(path, "eboot.bin")),
                "has_sce_sys": os.path.isdir(os.path.join(path, "sce_sys")),
                "message": "当前路径为标准 PS5 游戏根目录"
            }
        
        # 深度探测 3 层子目录
        candidate_leaf = None
        for root, dirs, files in os.walk(path):
            depth = len(Path(root).relative_to(Path(path)).parts)
            if depth > 3:
                continue
            if check_dir(root):
                candidate_leaf = root
                break
        
        if candidate_leaf:
            return {
                "valid": True,
                "is_leaf": False,
                "leaf": candidate_leaf,
                "has_eboot": os.path.isfile(os.path.join(candidate_leaf, "eboot.bin")),
                "has_sce_sys": os.path.isdir(os.path.join(candidate_leaf, "sce_sys")),
                "message": f"检测到真实游戏根目录位于子目录: {candidate_leaf}"
            }
        
        return {
            "valid": False,
            "is_leaf": False,
            "leaf": path,
            "message": "未在当前目录或子目录中找到 eboot.bin 或 sce_sys/，可能非解包游戏根目录"
        }

    def start_task(self, options: Dict[str, Any]) -> Dict[str, Any]:
        with self.lock:
            if self.task_state["status"] not in ("idle", "completed", "failed", "stopped"):
                return {"success": False, "message": "已有任务正在运行中"}

            src = options.get("src", "").strip()
            out = options.get("out", "").strip()
            if not src or not os.path.exists(src):
                return {"success": False, "message": "游戏源目录不存在"}
            if not out:
                return {"success": False, "message": "输出目录不能为空"}

            # 参数提取与默认值
            workers = int(options.get("workers", 4))
            level = int(options.get("level", 9))
            max_pack_size = options.get("max_pack_size", "16GiB")
            pack_count = int(options.get("pack_count", 4))
            auto_loose_ratio = float(options.get("auto_loose_ratio", 0.05))
            copy_loose = bool(options.get("copy_loose", True))
            verify = bool(options.get("verify", True))
            leaf_check = bool(options.get("leaf_check", True))

            # 重置状态
            self.stop_requested = False
            self.task_state.update({
                "status": "scanning",
                "step": "准备中...",
                "progress": 0,
                "speed": "—",
                "elapsed": 0,
                "eta": "—",
                "logical_bytes": 0,
                "stored_bytes": 0,
                "saved_bytes": 0,
                "saving_pct": 0.0,
                "current_file": "—",
                "packed_files": 0,
                "loose_files": 0,
                "loose_copied": 0,
                "game_name": os.path.basename(src.rstrip("/\\")),
                "src_path": src,
                "out_path": out,
                "start_time": time.time(),
                "end_time": 0,
                "error": "",
                "live_log": "",
                "logs": []
            })
            self._last_pack_milestone = 0
            self.save_last_paths(src, out)

            # 启动工作线程
            self.worker_thread = threading.Thread(
                target=self._run_pipeline,
                args=(src, out, workers, level, max_pack_size, pack_count, auto_loose_ratio, copy_loose, verify, leaf_check),
                daemon=True
            )
            self.worker_thread.start()
            return {"success": True, "message": "任务已启动"}

    def stop_task(self) -> Dict[str, Any]:
        with self.lock:
            if self.task_state["status"] in ("idle", "completed", "failed", "stopped"):
                return {"success": False, "message": "当前没有正在执行的任务"}
            
            self.stop_requested = True
            self.add_log("⚠️ 收到用户终止指令，正在停止进程...")
            if self.current_process and self.current_process.poll() is None:
                try:
                    self.current_process.terminate()
                    time.sleep(1)
                    if self.current_process.poll() is None:
                        self.current_process.kill()
                except Exception as e:
                    self.add_log(f"终止进程发生异常: {e}")
            
            self.task_state["status"] = "stopped"
            self.task_state["step"] = "任务已被用户终止"
            return {"success": True, "message": "任务已终止"}

    def _run_pipeline(self, src: str, out: str, workers: int, level: int, max_pack_size: str,
                      pack_count: int, auto_loose_ratio: float, copy_loose: bool, verify: bool, leaf_check: bool):
        start_ts = time.time()
        self.add_log("=" * 50)
        self.add_log("🚀 PS5 AMPR LZ4 资产压缩流水线启动")
        self.add_log(f"   源目录:   {src}")
        self.add_log(f"   输出目录: {out}")
        self.add_log(f"   并发线程: {workers}")
        self.add_log(f"   压缩等级: {level}")
        self.add_log(f"   分卷上限: {max_pack_size} (Lanes: {pack_count})")
        self.add_log(f"   散文件复制: {'开启' if copy_loose else '关闭'}")
        self.add_log(f"   产物验证:   {'开启' if verify else '关闭'}")
        self.add_log("=" * 50)

        py_bin = sys.executable
        mounter: Optional[ImageMountContext] = None

        try:
            os.makedirs(out, exist_ok=True)
            
            # --- 步骤 0: 虚拟磁盘镜像单文件探测与只读挂载 ---
            real_src = src
            if os.path.isfile(src):
                ext = os.path.splitext(src)[1].lower()
                if ext in DISK_IMAGE_EXTS:
                    self.task_state["step"] = f"正在只读挂载 {ext.upper()} 单文件镜像..."
                    self.add_log(f"💿 识别到输入源为虚拟磁盘镜像: {os.path.basename(src)}")
                    self.add_log("▶ 正在通过系统 loop 机制进行只读挂载...")
                    mounter = ImageMountContext(src, self.data_dir)
                    real_src = mounter.__enter__()
                    self.add_log(f"✓ 磁盘镜像已成功只读挂载，虚拟路径: {real_src}")

            # --- 步骤 1: 智能探查与叶子目录确认 ---
            if leaf_check:
                self.task_state["step"] = "正在探查游戏根目录..."
                inspection = self.inspect_leaf(real_src)
                if inspection.get("valid"):
                    if not inspection.get("is_leaf"):
                        real_src = inspection.get("leaf")
                        self.add_log(f"💡 自动检测到嵌套游戏叶子目录，重定向源路径为: {real_src}")
                    else:
                        self.add_log("✓ 验证通过: 目录包含 PS5 游戏特征文件 (eboot.bin / sce_sys)")
                else:
                    self.add_log(f"⚠️ 警告: {inspection.get('message')}，仍将尝试继续处理")

            if self.stop_requested:
                return

            # --- 步骤 2: 构建 AMPR 索引 ---
            self.task_state["status"] = "indexing"
            self.task_state["step"] = "[1/4] 构建 AMPR 游戏资产索引..."
            self.task_state["progress"] = 5
            self.add_log("▶ [1/4] 检查并构建 AMPR 索引...")

            index_in_game = os.path.join(real_src, "ampr_emu.index")
            index_target = os.path.join(out, "ampr_emu.index")
            if os.path.isfile(index_in_game) and os.path.getsize(index_in_game) > 0:
                self.add_log(f"  复用源目录已有索引: {index_in_game}")
                shutil.copy2(index_in_game, index_target)
            else:
                self.add_log(f"  执行 build_ampr_index.py 生成索引...")
                cmd = [py_bin, BUILD_INDEX_PY, real_src, "-o", index_target]
                res = subprocess.run(cmd, capture_output=True, text=True)
                if res.returncode != 0:
                    raise RuntimeError(f"构建索引失败: {res.stderr or res.stdout}")
                self.add_log(f"  ✓ 索引构建成功: {os.path.getsize(index_target)} 字节")

            if self.stop_requested:
                return

            # --- 步骤 3: 动态生成定制 profile.toml ---
            profile_target = os.path.join(out, "pack_profile.toml")
            self._generate_profile(DEFAULT_PROFILE_PATH, profile_target, workers, level, max_pack_size, pack_count, auto_loose_ratio)
            self.add_log(f"✓ 已生成定制配置: {profile_target}")

            if self.stop_requested:
                return

            # --- 步骤 4: 执行 ampr_pack.py pack ---
            self.task_state["status"] = "packing"
            self.task_state["step"] = "[2/4] 执行 LZ4-HC 资产压缩与打包..."
            self.task_state["progress"] = 10
            self.add_log("▶ [2/4] 启动 ampr_pack.py pack 压缩引擎...")

            # 计算上级目录 (parent_dir) 用于存放打包调试日志 (pack.log)
            # 保持目标输出目录 (out) 纯净整洁，仅保留 PS5 必要产物与用户要求的 verify.log
            clean_out = os.path.abspath(out.rstrip("/\\"))
            parent_dir = os.path.dirname(clean_out)
            if not parent_dir or not os.path.exists(parent_dir):
                parent_dir = clean_out

            pack_tmp_json = os.path.join(parent_dir, ".pack_json")
            pack_log_file = os.path.join(parent_dir, "pack.log")
            self.add_log(f"  打包日志保存至上级目录: {pack_log_file}")

            # 清理目标目录下可能遗留的旧 pack.log
            old_pack_log = os.path.join(out, "pack.log")
            if os.path.isfile(old_pack_log):
                try:
                    os.remove(old_pack_log)
                except Exception:
                    pass
            
            cmd_pack = [
                py_bin, AMPR_PACK_PY, "pack",
                "--root", real_src,
                "--ampr-index", index_target,
                "--output", out,
                "--config", profile_target
            ]
            for pattern in SAFETY_EXCLUSIONS:
                cmd_pack.extend(["--exclude", pattern])

            with open(pack_log_file, "w", encoding="utf-8") as log_f, open(pack_tmp_json, "w", encoding="utf-8") as json_f:
                proc = subprocess.Popen(
                    cmd_pack,
                    stdout=json_f,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1
                )
                self.current_process = proc

                # 实时读取 stderr 日志并解析进度
                for line in proc.stderr:
                    log_f.write(line)
                    log_f.flush()
                    self._parse_pack_line(line)
                    if self.stop_requested:
                        proc.terminate()
                        break

                proc.wait()
                if proc.returncode != 0 and not self.stop_requested:
                    raise RuntimeError(f"ampr_pack 压缩异常退出 (退出码 {proc.returncode})，详见 {pack_log_file}")

            if self.stop_requested:
                return

            self.task_state["progress"] = 80
            self.task_state["live_log"] = ""
            self.add_log("✓ 资产压缩打包完成！")

            # 读取 .pack_json 统计信息
            pack_meta = {}
            if os.path.isfile(pack_tmp_json):
                try:
                    with open(pack_tmp_json, "r", encoding="utf-8") as f:
                        pack_meta = json.load(f)
                        self.task_state["logical_bytes"] = pack_meta.get("logical_bytes", 0)
                        self.task_state["stored_bytes"] = pack_meta.get("stored_bytes", 0)
                        self.task_state["packed_files"] = pack_meta.get("files_packed", 0)
                        self.task_state["loose_files"] = pack_meta.get("files_loose", 0)
                        if self.task_state["logical_bytes"] > 0:
                            saved = self.task_state["logical_bytes"] - self.task_state["stored_bytes"]
                            self.task_state["saved_bytes"] = saved
                            self.task_state["saving_pct"] = round((saved / self.task_state["logical_bytes"]) * 100, 1)
                except Exception as e:
                    self.add_log(f"解析 .pack_json 出现警告: {e}")
                finally:
                    try:
                        os.remove(pack_tmp_json)
                    except Exception:
                        pass

            # 清理目标目录下可能残留的旧 .pack_json
            old_json = os.path.join(out, ".pack_json")
            if os.path.isfile(old_json):
                try:
                    os.remove(old_json)
                except Exception:
                    pass

            # --- 步骤 5: 执行校验 ---
            if verify and not self.stop_requested:
                self.task_state["status"] = "verifying"
                self.task_state["step"] = "[3/4] 验证产物完整性与哈希一致性..."
                self.task_state["progress"] = 85
                self.add_log("▶ [3/4] 启动 ampr_pack.py verify 校验...")
                
                verify_index = os.path.join(out, "ampr_assets.index")
                verify_log_file = os.path.join(out, "verify.log")
                self.add_log(f"  校验日志保留于目标目录: {verify_log_file}")
                cmd_verify = [
                    py_bin, AMPR_PACK_PY, "verify",
                    "--index", verify_index,
                    "--root", real_src
                ]
                with open(verify_log_file, "w", encoding="utf-8") as vf:
                    v_proc = subprocess.Popen(
                        cmd_verify,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        bufsize=1
                    )
                    self.current_process = v_proc

                    last_v_milestone = 0

                    for line in v_proc.stderr:
                        vf.write(line)
                        vf.flush()

                        # 解析 [verify XX%] 或 [verify_crc XX%]
                        pct_m = re.search(r'\[verify\s+(\d+)%\]', line)
                        if pct_m:
                            v_pct = int(pct_m.group(1))
                            # 映射到 80% - 92%
                            self.task_state["progress"] = 80 + int(v_pct * 0.12)
                            self.task_state["step"] = f"[3/4] 验证产物完整性与哈希一致性 ({v_pct}%)"

                            cur_m = re.search(r'current=([^,\s]+)', line)
                            if cur_m:
                                self.task_state["current_file"] = os.path.basename(cur_m.group(1))

                            details_m = re.search(r'comparing:\s*(.+)', line)
                            details_str = details_m.group(1) if details_m else ""

                            # 略缩精简校验详情
                            compact_v = details_str
                            f_vm = re.search(r'files\s+([\d/]+)', details_str)
                            b_vm = re.search(r'([\d\.]+\s+[KMGT]?i?B\s*/\s*[\d\.]+\s+[KMGT]?i?B)', details_str)
                            if f_vm and b_vm:
                                compact_v = f"{b_vm.group(1)} ({f_vm.group(1)})"
                            elif f_vm:
                                compact_v = f"文件 {f_vm.group(1)}"

                            # 1. 实时单行原地刷新（结构化胶囊分割）
                            self.task_state["live_log"] = f"🔍 校验 {v_pct}% · 比对原盘哈希 · {compact_v}"

                            # 2. 里程碑打点：每 20% (20%, 40%, 60%, 80%) 记录一条永久历史日志
                            v_tier = (v_pct // 20) * 20
                            if v_tier > last_v_milestone and v_tier in (20, 40, 60, 80):
                                last_v_milestone = v_tier
                                self.add_log(f"🔍 [校验里程碑 {v_tier}%] 原盘哈希比对通过 ({compact_v})")

                    v_proc.wait()
                    self.task_state["live_log"] = ""
                    if v_proc.returncode == 0:
                        self.task_state["progress"] = 92
                        self.add_log("✓ 产物验证 100% 通过！所有 .pak 数据块哈希一致。")
                    else:
                        self.add_log(f"⚠️ 产物验证返回状态码 {v_proc.returncode}，详情请查看 verify.log")

            if self.stop_requested:
                return

            # --- 步骤 6: 复制 Loose 散文件 (PS5 部署必需) ---
            if copy_loose and not self.stop_requested:
                self.task_state["status"] = "copying_loose"
                self.task_state["step"] = "[4/4] 复制 Loose 启动散文件 (eboot / sce_sys / 媒体)..."
                self.task_state["progress"] = 92
                self.add_log("▶ [4/4] 复制 Loose 启动文件（确保 PS5 能够正常识别引导）...")
                
                copied_cnt, skipped_cnt = self._copy_loose_files(real_src, out, pack_meta)
                self.task_state["loose_copied"] = copied_cnt
                self.add_log(f"✓ 成功复制 {copied_cnt} 个 Loose 散文件 (跳过 {skipped_cnt} 个)")

            # --- 完成总结 ---
            end_ts = time.time()
            total_elapsed = int(end_ts - start_ts)
            self.task_state["status"] = "completed"
            self.task_state["step"] = "全部完成！产物已可直接部署至 PS5 /app0"
            self.task_state["progress"] = 100
            self.task_state["elapsed"] = total_elapsed
            self.task_state["end_time"] = end_ts
            
            log_mb = round(self.task_state["logical_bytes"] / 1024 / 1024 / 1024, 2)
            stored_mb = round(self.task_state["stored_bytes"] / 1024 / 1024 / 1024, 2)
            saved_mb = round(self.task_state["saved_bytes"] / 1024 / 1024 / 1024, 2)

            self.add_log("=" * 50)
            self.add_log(f"🎉 压缩打包圆满完成！总耗时: {total_elapsed} 秒")
            self.add_log(f"   原始体积: {log_mb} GiB")
            self.add_log(f"   压缩体积: {stored_mb} GiB")
            self.add_log(f"   节省空间: {saved_mb} GiB ({self.task_state['saving_pct']}%)")
            self.add_log(f"   打包分卷数: {self.task_state['packed_files']} 个文件打包入 .pak")
            self.add_log(f"   产物目录: {out}")
            self.add_log("=" * 50)

            # 保存至历史记录
            self.save_history_entry({
                "game_name": self.task_state["game_name"],
                "src": real_src,
                "out": out,
                "elapsed": total_elapsed,
                "logical_gb": log_mb,
                "stored_gb": stored_mb,
                "saved_gb": saved_mb,
                "saving_pct": self.task_state["saving_pct"],
                "date": time.strftime("%Y-%m-%d %H:%M:%S"),
                "status": "success"
            })

        except Exception as e:
            if not self.stop_requested:
                self.task_state["status"] = "failed"
                self.task_state["step"] = f"失败: {e}"
                self.task_state["error"] = str(e)
                self.add_log(f"❌ 任务发生错误终止: {e}")
                self.save_history_entry({
                    "game_name": self.task_state["game_name"],
                    "src": src,
                    "out": out,
                    "date": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "failed",
                    "error": str(e)
                })
        finally:
            if mounter:
                try:
                    mounter.__exit__(None, None, None)
                    self.add_log("✓ 虚拟磁盘镜像已安全卸载并释放资源")
                except Exception as e:
                    self.add_log(f"⚠️ 卸载虚拟镜像提示: {e}")
            self.task_state["live_log"] = ""
            self.current_process = None

    def _generate_profile(self, template_path: str, out_path: str, workers: int, level: int,
                          max_pack_size: str, pack_count: int, auto_loose_ratio: float):
        """根据用户自定义参数，渲染 profile.toml"""
        with open(template_path, "r", encoding="utf-8") as f:
            content = f.read()

        content = re.sub(r"^workers\s*=\s*\d+", f"workers = {workers}", content, flags=re.MULTILINE)
        content = re.sub(r"^compression_level\s*=\s*\d+", f"compression_level = {level}", content, flags=re.MULTILINE)
        content = re.sub(r'max_pack_size\s*=\s*"[^"]+"', f'max_pack_size = "{max_pack_size}"', content, flags=re.MULTILINE)
        content = re.sub(r"pack_count\s*=\s*\d+", f"pack_count = {pack_count}", content, flags=re.MULTILINE)
        content = re.sub(r"auto_loose_min_savings_ratio\s*=\s*[\d\.]+", f"auto_loose_min_savings_ratio = {auto_loose_ratio}", content, flags=re.MULTILINE)

        with open(out_path, "w", encoding="utf-8") as f:
            f.write(content)

    def _parse_pack_line(self, line: str):
        """解析 ampr_pack 进度行并平滑更新状态与日志打印"""
        if "[pack" not in line:
            return

        pct_match = re.search(r'\[pack\s+(\d+)%\]', line)
        if not pct_match:
            return

        pct = int(pct_match.group(1))
        # 映射到 10% - 80% 之间的总体进度
        mapped_progress = 10 + int(pct * 0.7)
        self.task_state["progress"] = mapped_progress

        speed_str = ""
        speed_match = re.search(r'([\d\.]+\s+[KMGT]?i?B/s)', line)
        if speed_match:
            speed_str = speed_match.group(1)
            self.task_state["speed"] = speed_str

        cur_file = ""
        cur_match = re.search(r'current=([^,\s]+)', line)
        if cur_match:
            cur_file = os.path.basename(cur_match.group(1))
            self.task_state["current_file"] = cur_file

        eta_str = ""
        eta_match = re.search(r'ETA\s+([\d:]+)', line)
        if eta_match:
            raw_eta = eta_match.group(1)
            parts = raw_eta.split(':')
            if len(parts) == 3 and parts[0] == '00':
                eta_str = f"剩余 {parts[1]}:{parts[2]}"
            elif len(parts) == 3:
                eta_str = f"剩余 {int(parts[0])}h{parts[1]}m"
            else:
                eta_str = f"剩余 {raw_eta}"
            self.task_state["eta"] = eta_str

        # 提取文件数或字节数进度详情 (例如: files 6/17060, 321.6 MiB/132.6 GiB)
        details_match = re.search(r'(?:packing|planning|finalizing):\s*([^,\n]+(?:,\s*[^,\n]+)?)', line)
        raw_details = details_match.group(1).strip() if details_match else ""

        # 略缩精简 details (例如将 "files 6/17060, 321.6 MiB/132.6 GiB" 略缩为 "321.6M/132.6G (6/17060)")
        compact_details = raw_details
        f_m = re.search(r'files\s+([\d/]+)', raw_details)
        b_m = re.search(r'([\d\.]+\s+[KMGT]?i?B\s*/\s*[\d\.]+\s+[KMGT]?i?B)', raw_details)
        if f_m and b_m:
            compact_details = f"{b_m.group(1)} ({f_m.group(1)})"
        elif f_m:
            compact_details = f"{f_m.group(1)} 件"

        # 更新大屏步骤描述
        self.task_state["step"] = f"[2/4] 打包压缩中 ({pct}%)" + (f" - {speed_str}" if speed_str else "")

        # 1. 实时单行刷新 (Live Log)：结构化略缩，杜绝冗长文本撑爆窗口（以 · 分隔）
        live_parts = [f"⚡ 压缩 {pct}%"]
        if speed_str:
            live_parts.append(speed_str)
        if compact_details:
            live_parts.append(compact_details)
        if eta_str:
            live_parts.append(eta_str)
        if cur_file:
            if len(cur_file) <= 20:
                live_parts.append(f"当前: {cur_file}")
            else:
                live_parts.append(f"当前: {cur_file[:8]}...{cur_file[-8:]}")
        self.task_state["live_log"] = " · ".join(live_parts)

        # 2. 里程碑打点 (Milestone Log)：每 10% 记录一条永久历史日志 (10%, 20%, 30%...90%)
        curr_tier = (pct // 10) * 10
        milestone = getattr(self, "_last_pack_milestone", 0)
        if curr_tier > milestone and curr_tier in (10, 20, 30, 40, 50, 60, 70, 80, 90):
            self._last_pack_milestone = curr_tier
            m_parts = [f"⚡ [压缩里程碑 {curr_tier}%]"]
            if compact_details:
                m_parts.append(compact_details)
            if speed_str:
                m_parts.append(speed_str)
            if eta_str:
                m_parts.append(eta_str)
            self.add_log(" · ".join(m_parts))

    def _copy_loose_files(self, src_root: str, out_root: str, pack_meta: Dict[str, Any]) -> tuple:
        """精准复制 loose 文件及 PS5 必要启动文件，带进度条与动态日志"""
        loose_paths = set(pack_meta.get("loose_paths", []))

        # 1. 扫描已知开机必需的重点目录，无论如何强制全量包含
        critical_dirs = ["sce_module", "fakelib", "sce_sys", "natives", "system", "video", "movie", "movies", "soundbank"]
        for special_dir in critical_dirs:
            spec_full = os.path.join(src_root, special_dir)
            if os.path.isdir(spec_full):
                for root, _, files in os.walk(spec_full):
                    for file in files:
                        rel = os.path.relpath(os.path.join(root, file), src_root).replace("\\", "/")
                        loose_paths.add(rel)

        # 2. 全盘遍历扫描：任何匹配 SAFETY_EXCLUSIONS 的散文件，确保 100% 复制到产物目录
        for dirpath, dirnames, filenames in os.walk(src_root):
            for fn in filenames:
                full_path = os.path.join(dirpath, fn)
                rel_path = os.path.relpath(full_path, src_root).replace("\\", "/")
                # 检查是否匹配 SAFETY_EXCLUSIONS 中的任何规则
                if any(fnmatch.fnmatchcase(rel_path, pat) for pat in SAFETY_EXCLUSIONS):
                    loose_paths.add(rel_path)

        all_to_copy = sorted(loose_paths)
        total_loose = len(all_to_copy) or 1
        copied = 0
        skipped = 0

        for idx, rel in enumerate(all_to_copy, 1):
            src_file = os.path.join(src_root, rel)
            out_file = os.path.join(out_root, rel)
            if not os.path.isfile(src_file):
                skipped += 1
                continue
            
            os.makedirs(os.path.dirname(out_file), exist_ok=True)
            if os.path.isfile(out_file) and os.path.getsize(out_file) == os.path.getsize(src_file):
                copied += 1
                continue

            shutil.copy2(src_file, out_file)
            copied += 1
            
            # 平滑推动 92% -> 98%
            mapped_p = 92 + int(idx / total_loose * 6)
            self.task_state["progress"] = min(98, mapped_p)
            self.task_state["step"] = f"[4/4] 复制 Loose 启动散文件 ({idx}/{total_loose})"
            self.task_state["current_file"] = os.path.basename(rel)

            if copied % 15 == 0 or idx == total_loose:
                self.add_log(f"  复制散文件进度: {idx}/{total_loose} ({mapped_p}%) - {os.path.basename(rel)}")

        return copied, skipped

    def browse_fs(self, target_dir: Optional[str] = None) -> Dict[str, Any]:
        """安全列出 NAS 目录用于文件选择器，彻底过滤 Linux 底层系统目录与授权杂项，只呈现 NAS 存储空间卷"""
        # 探测飞牛 NAS 存储空间卷 (/vol1 ~ /vol16)
        volumes = []
        if os.name != "nt":
            for v_idx in range(1, 17):
                v_path = f"/vol{v_idx}"
                if os.path.exists(v_path):
                    volumes.append(v_path)
        else:
            volumes = [os.path.abspath(os.sep)]

        # 如果未传入目标目录或为根目录或不存在，默认呈现“NAS 纯净根视图”
        is_root_view = False
        if not target_dir or target_dir in ("/", "\\") or not os.path.exists(target_dir):
            is_root_view = True
            target_dir = "/"
            if os.name == "nt":
                target_dir = os.path.abspath(os.sep)

        items = []

        if is_root_view and os.name != "nt":
            # 在 NAS 根视图下：只展示纯粹的 NAS 存储空间卷，彻底删除授权目录杂项
            for v_path in volumes:
                v_num = re.findall(r'\d+', v_path)
                display_name = f"存储空间 {v_num[0]} ({v_path})" if v_num else f"存储卷 ({v_path})"
                items.append({
                    "name": display_name,
                    "path": v_path,
                    "is_dir": True,
                    "is_volume": True,
                    "size": 0
                })
            
            return {
                "current": "/",
                "parent": "",
                "items": items,
                "volumes": volumes,
                "is_nas_root": True
            }

        # 针对具体目录的扫描：过滤底层系统黑名单与 @ 系统内部私有目录
        SYSTEM_BLACKLIST = {
            'bin', 'boot', 'dev', 'etc', 'home', 'lib', 'lib64', 'media', 'mnt', 
            'opt', 'proc', 'root', 'run', 'sbin', 'srv', 'sys', 'tmp', 'usr', 'var', 
            'lost+found', 'etc.defaults', 'aquota.group', 'aquota.user'
        }

        target_dir = os.path.abspath(target_dir)
        try:
            with os.scandir(target_dir) as it:
                for entry in it:
                    # 隐藏所有以 . 开头的隐藏目录/文件
                    if entry.name.startswith("."):
                        continue
                    # 隐藏系统内部 @ 开头的私有目录（如 @appcenter, @docker, @tmp, @eaDir 等）
                    if entry.name.startswith("@"):
                        continue
                    # 如果当前路径是系统根 /，严格拦截黑名单
                    if target_dir in ("/", "\\") and entry.name.lower() in SYSTEM_BLACKLIST:
                        continue
                    
                    try:
                        is_dir = entry.is_dir(follow_symlinks=True)
                        is_image = False
                        file_size = 0
                        if not is_dir:
                            name_lower = entry.name.lower()
                            if any(name_lower.endswith(ext) for ext in DISK_IMAGE_EXTS):
                                is_image = True
                                try:
                                    file_size = entry.stat().st_size
                                except Exception:
                                    pass
                            else:
                                continue

                        items.append({
                            "name": entry.name,
                            "path": entry.path.replace("\\", "/"),
                            "is_dir": is_dir,
                            "is_image": is_image,
                            "size": file_size
                        })
                    except (PermissionError, OSError):
                        continue
        except (PermissionError, OSError) as e:
            return {"current": target_dir, "parent": os.path.dirname(target_dir), "items": [], "error": str(e), "volumes": volumes}

        items.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
        parent_dir = os.path.dirname(target_dir) if target_dir != os.path.dirname(target_dir) else "/"
        if target_dir in volumes:
            parent_dir = "/"

        return {
            "current": target_dir.replace("\\", "/"),
            "parent": parent_dir.replace("\\", "/"),
            "items": items,
            "volumes": volumes
        }

    def list_output_files(self, out_dir: str) -> List[Dict[str, Any]]:
        """列出输出目录中的产物文件"""
        if not out_dir or not os.path.isdir(out_dir):
            return []
        res = []
        try:
            for root, _, files in os.walk(out_dir):
                for f in files:
                    full = os.path.join(root, f)
                    rel = os.path.relpath(full, out_dir).replace("\\", "/")
                    size = os.path.getsize(full)
                    res.append({
                        "name": rel,
                        "size": size,
                        "size_human": self._human_size(size),
                        "is_pak": rel.endswith(".pak"),
                        "is_index": rel.endswith(".index")
                    })
        except Exception:
            pass
        res.sort(key=lambda x: (not x["is_pak"], not x["is_index"], x["name"]))
        return res

    @staticmethod
    def _human_size(n_bytes: int) -> str:
        for unit in ['B', 'KiB', 'MiB', 'GiB', 'TiB']:
            if n_bytes < 1024.0:
                return f"{n_bytes:.1f} {unit}"
            n_bytes /= 1024.0
        return f"{n_bytes:.1f} PiB"

# 全局单例
compressor_manager = CompressorManager()
