"""
使用系统命令播放音频的模块，作为miniaudio的备选方案
"""
import os
import sys
import subprocess
import logging
import threading
import time
from PySide6.QtCore import QObject, Signal, Slot

class SystemAudioPlayer(QObject):
    """使用系统命令播放音频的类"""

    # 信号
    playback_started = Signal()
    playback_finished = Signal()
    playback_error = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._playback_thread = None
        self._stop_event = threading.Event()
        self._current_file_path = None
        self._process = None

    def is_available(self):
        """检查是否可用"""
        return True  # 系统命令总是可用的

    def supports_pause(self):
        return False

    @Slot(str)
    def play_file(self, file_path):
        """播放指定路径的音频文件"""
        if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
            logging.error(f"音频文件无效或为空: {file_path}")
            self.playback_error.emit(f"音频文件无效或为空: {file_path}")
            return

        try:
            self.stop()  # 先停止之前的播放
            self._current_file_path = file_path
            self._stop_event.clear()
            self._playback_thread = threading.Thread(target=self._play_in_thread, args=(file_path,))
            self._playback_thread.daemon = True  # 允许应用程序退出，即使线程仍在运行
            self._playback_thread.start()
        except Exception as e:
            logging.error(f"启动播放线程时出错: {e}", exc_info=True)
            self.playback_error.emit(f"启动播放时出错: {e}")

    def _play_in_thread(self, file_path):
        """在线程中处理播放"""
        try:
            logging.info(f"SystemAudioPlayer线程: 开始播放 {file_path}")
            self.playback_started.emit()

            # 尝试使用多种方法播放
            success = False

            # 1. 尝试使用ffplay (无窗口)
            if not success and not self._stop_event.is_set():
                success = self._play_with_ffplay(file_path)

            # 2. 尝试使用PowerShell的SoundPlayer (无窗口)
            if not success and not self._stop_event.is_set():
                success = self._play_with_powershell(file_path)

            # 3. Windows Media Player方法已禁用，因为它会显示窗口
            # if not success and not self._stop_event.is_set():
            #     success = self._play_with_windows_media(file_path)

            if not success:
                logging.error(f"所有播放方法都失败: {file_path}")
                self.playback_error.emit("所有播放方法都失败")
            else:
                logging.info(f"SystemAudioPlayer线程: 播放完成 {file_path}")
                self.playback_finished.emit()

        except Exception as e:
            logging.error(f"SystemAudioPlayer线程: 播放 {file_path} 时出错: {e}", exc_info=True)
            self.playback_error.emit(f"播放失败: {e}")

    def _play_with_ffplay(self, file_path):
        """使用ffplay播放音频文件"""
        try:
            # 尝试在当前目录和资源目录中查找ffplay.exe
            ffplay_paths = [
                "ffplay.exe",  # 当前目录
                os.path.join(os.path.dirname(sys.executable), "ffplay.exe"),  # 可执行文件目录
                os.path.join(getattr(sys, '_MEIPASS', os.path.abspath(".")), "ffplay.exe"),  # PyInstaller打包目录
            ]

            ffplay_exe = None
            for path in ffplay_paths:
                if os.path.exists(path):
                    ffplay_exe = path
                    logging.info(f"找到ffplay.exe: {path}")
                    break

            if not ffplay_exe:
                logging.error("找不到ffplay.exe")
                return False

            # 使用ffplay播放音频，添加更多参数确保无窗口
            cmd = [
                ffplay_exe,
                "-nodisp",      # 不显示视频
                "-autoexit",    # 播放完成后自动退出
                "-loglevel", "quiet",  # 不显示日志
                "-hide_banner", # 隐藏横幅
                file_path
            ]
            logging.info(f"执行命令: {cmd}")

            # 创建无窗口的进程
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE

            # 重定向标准输出和错误输出
            devnull = open(os.devnull, 'w')

            self._process = subprocess.Popen(
                cmd,
                startupinfo=startupinfo,
                stdout=devnull,
                stderr=devnull,
                stdin=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            # 等待进程完成或停止事件
            while self._process.poll() is None and not self._stop_event.is_set():
                time.sleep(0.1)

            # 如果进程仍在运行，终止它
            if self._process.poll() is None:
                self._process.terminate()
                self._process.wait(timeout=1)

            devnull.close()
            return True
        except Exception as e:
            logging.error(f"使用ffplay播放音频时出错: {e}")
            return False

    def _play_with_windows_media(self, file_path):
        """使用Windows Media Player播放音频文件"""
        try:
            # 使用Windows Media Player播放
            cmd = f'start wmplayer "{file_path}" /play /close'
            logging.info(f"执行命令: {cmd}")

            self._process = subprocess.Popen(cmd, shell=True)

            # 等待一段时间，让Windows Media Player启动
            time.sleep(2)

            # 等待停止事件
            while not self._stop_event.is_set():
                time.sleep(0.1)

            # 尝试终止进程
            try:
                self._process.terminate()
                self._process.wait(timeout=1)
            except:
                pass

            return True
        except Exception as e:
            logging.error(f"使用Windows Media Player播放音频时出错: {e}")
            return False

    def _play_with_powershell(self, file_path):
        """使用PowerShell的SoundPlayer播放音频文件"""
        try:
            # 使用PowerShell的SoundPlayer播放
            cmd = f'powershell -WindowStyle Hidden -c "(New-Object Media.SoundPlayer \'{file_path}\').PlaySync()"'
            logging.info(f"执行命令: {cmd}")

            # 创建无窗口的进程
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE

            # 重定向标准输出和错误输出
            devnull = open(os.devnull, 'w')

            self._process = subprocess.Popen(
                cmd,
                shell=True,
                startupinfo=startupinfo,
                stdout=devnull,
                stderr=devnull,
                stdin=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            # 等待进程完成或停止事件
            while self._process.poll() is None and not self._stop_event.is_set():
                time.sleep(0.1)

            # 如果进程仍在运行，终止它
            if self._process.poll() is None:
                self._process.terminate()
                self._process.wait(timeout=1)

            devnull.close()
            return True
        except Exception as e:
            logging.error(f"使用PowerShell播放音频时出错: {e}")
            return False

    @Slot()
    def stop(self):
        """停止当前播放的音频"""
        if self._playback_thread and self._playback_thread.is_alive():
            logging.info("SystemAudioPlayer: 请求停止播放...")
            self._stop_event.set()

            # 如果进程存在，尝试终止它
            if self._process and hasattr(self._process, 'poll') and self._process.poll() is None:
                try:
                    self._process.terminate()
                    self._process.wait(timeout=1)
                except:
                    pass

            # 等待线程结束
            self._playback_thread.join(timeout=0.5)
            if self._playback_thread.is_alive():
                logging.warning("SystemAudioPlayer: 播放线程未能优雅地停止。")
            self._playback_thread = None
        else:
            # 确保停止事件被设置，即使线程已经结束/未启动
            self._stop_event.set()

    def pause(self):
        """暂停播放（如果支持）"""
        logging.warning("SystemAudioPlayer: 暂停功能不支持")

    def resume(self):
        """恢复播放（如果支持）"""
        logging.warning("SystemAudioPlayer: 恢复功能不支持")
