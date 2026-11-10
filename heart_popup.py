# -*- coding: utf-8 -*-
"""
Python 爱心弹窗 · 心之所向 爱之所往
=====================================================
零依赖，只用 Python 标准库（tkinter + wave + winsound + ctypes 调用系统 MCI）。

运行：
    python heart_popup.py
或双击同目录下的 run_heart.bat

演出流程（不会自动结束，直到你手动退出）：
    1. 爱心绽放  110 张小卡片沿心形参数方程依次弹出，拼成一颗完整的心
    2. 定格告白  屏幕中央出现一颗会一直跳动的大爱心
    3. 持续告白  小卡片不断冒出来、不会自动关闭，铺满屏幕后一直保持

随时退出：Esc / 空格 / 单击任意卡片 / 控制台 Ctrl+C（退出时音乐也会停）

BGM：
    只播放同目录的 bgm.mp3，循环播放，没有其它备选或兜底音乐。
    文件不存在时静音运行（弹窗照常显示）。
    查看当前会播哪首：python heart_popup.py --which-bgm
    不想放音乐：把下面 CONFIG 里的 ENABLE_BGM 改成 False。

想改内容：编辑 CONFIG 区的 TIPS、COLORS、弹窗速度等参数。
自检模式：python heart_popup.py --test   （只计算坐标，不弹窗口、不放音乐）
"""

import math
import os
import random
import sys
import wave
from array import array

try:
    import tkinter as tk
except ImportError:
    tk = None  # 精简版 Python 没带 tkinter 时，自动降级打开网页版

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ============================================================
# CONFIG —— 想改成自己的版本，改这里就够了
# ============================================================
TITLE = "心之所向"
TITLE_2 = "爱之所往"
SIGNATURE = "—— 写给你 ——"
HEADER = "♥  For You  ♥"

# 弹窗里随机出现的一句话（建议 4~8 个字，太长会挤出卡片）
TIPS = [
    "多喝热水", "好好吃饭", "别熬夜啦", "天冷加衣",
    "保持好心情", "我想你了", "顺顺利利", "今天也要开心",
    "遇见你真好", "余生请多指教", "愿你被温柔以待", "慢慢来我等你",
    "想和你碎碎念", "一起看日落吧", "你是我的偏爱", "万事胜意",
    "平安喜乐", "早点睡", "记得想我", "抱一下",
    "喜欢你不止今天", "岁岁年年", "你笑起来真好看", "别怕我在",
    "把温柔都给你", "余光是你", "心之所向", "爱之所往",
    "有你在真好", "要一直开心", "想见你一面", "喜欢就留下来",
]

# 卡片配色：(背景, 文字)，粉色系多写几次 = 出现概率更高
COLORS = [
    ("#FFE1EA", "#C2185B"),
    ("#FFF0F5", "#AD1457"),
    ("#FCE4EC", "#880E4F"),
    ("#FFD9E4", "#B71C5C"),
    ("#F8E8FF", "#7B1FA2"),
    ("#FFF4E0", "#BF360C"),
    ("#E6F4FF", "#1565C0"),
    ("#FFE9F0", "#AD1457"),
    ("#FCE4EC", "#880E4F"),
]

WIN_W, WIN_H = 172, 64          # 小卡片尺寸
FONT_FAMILY = "Microsoft YaHei"  # 中文字体，其他系统可改 "PingFang SC" 等

HEART_COUNT = 110               # 拼成爱心的小卡片数量
HEART_WIDTH_RATIO = 0.60        # 爱心宽度占屏幕宽度的比例
HEART_HEIGHT_RATIO = 0.70       # 爱心高度占屏幕高度的比例
HEART_INTERVAL_MS = 28          # 每张卡片出现间隔（毫秒）
HEART_HOLD_MS = 1600            # 爱心拼好后停留时间

TITLE_DELAY_MS = 700            # 心形拼好后，隔多久出现中央大爱心
SPAWN_INTERVAL_MS = 240         # 之后每隔多久冒出一张新卡片
MAX_WINDOWS = 200               # 窗口总数上限（防止无限开窗口拖慢系统）
GRID_GAP_X, GRID_GAP_Y = 28, 26  # 弹窗位置网格间隙
GRID_LIMIT = 150                # 位置池上限

FINALE_W, FINALE_H = 560, 380   # 中央大爱心卡片尺寸
TRANSPARENT_BG = "#010203"      # 用于抠出圆角的透明色（Windows 支持）

ENABLE_BGM = True               # 关掉音乐改成 False
BGM_FILE = "bgm.mp3"            # 唯一使用的音频文件；不存在则静音
# ============================================================


# ============================================================
# BGM：用标准库合成一段原创八音盒循环（约 23 秒）
# ============================================================
# 每个小节：(分解和弦的三个音, 主旋律 [(MIDI音高, 占几拍), ...])
BGM_BARS = [
    ([48, 52, 55], [(76, 1), (74, 1), (72, 1), (74, 1)]),   # C
    ([45, 48, 52], [(72, 1), (69, 1), (67, 1), (69, 1)]),   # Am
    ([41, 45, 48], [(69, 1), (72, 1), (74, 1), (72, 1)]),   # F
    ([43, 47, 50], [(71, 1), (74, 1), (72, 2)]),            # G
    ([48, 52, 55], [(76, 1), (79, 1), (76, 1), (74, 1)]),   # C
    ([45, 48, 52], [(72, 1), (76, 1), (72, 1), (69, 1)]),   # Am
    ([41, 45, 48], [(74, 1), (77, 1), (76, 1), (74, 1)]),   # F
    ([43, 47, 50], [(72, 2), (67, 2)]),                     # G
]
ARPEGGIO_ORDER = [0, 1, 2, 1, 0, 2, 1, 2]


def bgm_path():
    return os.path.join(BASE_DIR, BGM_FILE)


def find_bgm():
    """只用这一个音频文件；找不到返回 None（静音运行）"""
    path = bgm_path()
    return path if os.path.exists(path) else None


def make_bgm(path=None):
    """合成八音盒 WAV：正弦波 + 泛音 + 指数衰减包络 + 轻混响，首尾淡入淡出便于循环"""
    path = path or bgm_path()
    sr = 22050
    beat = 60.0 / BGM_BPM
    total_beats = len(BGM_BARS) * 4
    total_samples = int(sr * beat * total_beats)
    buf = array("f", [0.0]) * total_samples
    two_pi = 2 * math.pi

    def add_note(midi, start_beat, dur_beats, amp):
        freq = 440.0 * 2 ** ((midi - 69) / 12.0)
        i0 = int(start_beat * beat * sr)
        length = int(dur_beats * beat * sr)
        if i0 >= total_samples:
            return
        length = min(length, total_samples - i0)
        decay = 3.0 / (dur_beats * beat)
        f1, f2, f3 = freq * two_pi, 2 * freq * two_pi, 3 * freq * two_pi
        for i in range(length):
            t = i / sr
            env = (1.0 - math.exp(-t * 90.0)) * math.exp(-decay * t)
            s = (math.sin(f1 * t)
                 + 0.32 * math.sin(f2 * t)
                 + 0.12 * math.sin(f3 * t))
            buf[i0 + i] += s * env * amp

    for bar_idx, (chord, melody) in enumerate(BGM_BARS):
        base = bar_idx * 4
        for k, ci in enumerate(ARPEGGIO_ORDER):
            add_note(chord[ci], base + k * 0.5, 0.9, 0.085)
        add_note(chord[0] - 12, base, 1.9, 0.14)
        pos = 0.0
        for midi, dur in melody:
            add_note(midi, base + pos, dur * 0.95, 0.28)
            pos += dur

    # 两点延迟制造一点空间感
    dry = array("f", buf)
    d1, d2 = int(0.19 * sr), int(0.37 * sr)
    for i in range(total_samples):
        v = dry[i]
        if i >= d1:
            v += 0.18 * dry[i - d1]
        if i >= d2:
            v += 0.10 * dry[i - d2]
        buf[i] = v

    # 首尾淡入淡出，循环时不会爆音
    fade = int(0.08 * sr)
    for i in range(fade):
        f = i / fade
        buf[i] *= f
        buf[total_samples - 1 - i] *= f

    peak = max(abs(v) for v in buf) or 1.0
    gain = 0.72 / peak
    pcm = array("h", (int(max(-1.0, min(1.0, v * gain)) * 32767) for v in buf))
    with wave.open(path, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sr)
        f.writeframes(pcm.tobytes())
    return path


class BgmPlayer:
    """后台选曲 + 循环播放；支持常见音频格式，退出时保证停掉"""

    MCI_ALIAS = "heartpopupbgm"

    def __init__(self):
        self.mode = None
        self.proc = None
        self.pygame = None
        self.stopped = False
        self.track = None

    def start(self):
        """选曲并循环播放；音频命令都在主线程，避免跨线程访问 MCI 设备出错"""
        if not ENABLE_BGM:
            return
        try:
            path = find_bgm()
        except Exception as exc:
            print("BGM 准备失败（不影响弹窗）：", exc)
            return
        if not path:
            print("未找到 %s，本次静音运行（弹窗照常显示）。" % BGM_FILE)
            return
        self.track = os.path.basename(path)
        print("BGM：%s（唯一音源）" % self.track)

        ext = os.path.splitext(path)[1].lower()

        # WAV 走 winsound：最稳、零依赖
        if ext == ".wav":
            try:
                import winsound
                winsound.PlaySound(
                    path,
                    winsound.SND_FILENAME | winsound.SND_ASYNC
                    | winsound.SND_LOOP | winsound.SND_NODEFAULT,
                )
                self.mode = "winsound"
                if self.stopped:
                    self._stop_winsound()
                return
            except Exception:
                pass

        # MP3 / M4A / FLAC 等：调用 Windows 系统 MCI 解码，依然是零第三方依赖
        if sys.platform == "win32" and self._play_mci(path):
            if self.stopped:
                self._stop_mci()
            return

        # 装了 pygame 的话用它（跨平台、格式支持最全）
        try:
            import pygame
            pygame.mixer.init()
            pygame.mixer.music.load(path)
            pygame.mixer.music.play(-1)
            self.pygame = pygame
            self.mode = "pygame"
            if self.stopped:
                pygame.mixer.music.stop()
            return
        except Exception:
            pass

        # Linux 兜底（aplay 不循环，放一遍即可）
        try:
            import subprocess
            self.proc = subprocess.Popen(
                ["aplay", "-q", path],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            self.mode = "aplay"
            if self.stopped and self.proc:
                self.proc.terminate()
            return
        except Exception:
            pass

        print("这个音频没能播放：", self.track)
        print("建议转成 .wav 或 .mp3 再放入文件夹，或安装 pygame：pip install pygame")

    # ---------- Windows MCI（支持 mp3 等压缩格式） ----------
    @staticmethod
    def _mci(command):
        try:
            import ctypes
            winmm = ctypes.WinDLL("winmm")
            buf = ctypes.create_unicode_buffer(256)
            rc = winmm.mciSendStringW(command, buf, 256, 0)
            return rc, buf.value.strip()
        except Exception as exc:
            return -1, str(exc)

    def _play_mci(self, path):
        alias = self.MCI_ALIAS
        ext = os.path.splitext(path)[1].lower()
        type_hint = " type mpegvideo" if ext in (".mp3", ".wma", ".aac") else ""
        rc, _ = self._mci('open "%s"%s alias %s' % (path, type_hint, alias))
        if rc != 0:
            return False
        rc, _ = self._mci("play %s repeat" % alias)
        if rc != 0:
            self._mci("close %s" % alias)
            return False
        self.mode = "mci"
        # play ... repeat 在 Windows 上实测会自动循环。这里不再后台轮询状态，
        # 避免并发查询同一 MCI 设备导致「设备忙」；个别格式不循环时转成 wav 即可。
        return True

    def _stop_mci(self):
        self._mci("stop %s" % self.MCI_ALIAS)
        self._mci("close %s" % self.MCI_ALIAS)

    @staticmethod
    def _stop_winsound():
        try:
            import winsound
            winsound.PlaySound(None, winsound.SND_PURGE)
        except Exception:
            pass

    def stop(self):
        self.stopped = True
        if self.mode == "winsound":
            self._stop_winsound()
        elif self.mode == "mci":
            self._stop_mci()
        elif self.mode == "pygame" and self.pygame:
            try:
                self.pygame.mixer.music.stop()
            except Exception:
                pass
        elif self.mode == "aplay" and self.proc:
            try:
                self.proc.terminate()
            except Exception:
                pass
        # 即使后台线程还没走到播放那一步，也先清一次，避免退出后突然出声
        if sys.platform == "win32":
            self._stop_winsound()


# ============================================================
# 心形几何
# ============================================================
def heart_curve(n):
    """经典心形参数方程：x=16sin³t, y=13cost-5cos2t-2cos3t-cos4t"""
    points = []
    for i in range(n):
        t = i / n * 2 * math.pi
        x = 16 * math.sin(t) ** 3
        y = (13 * math.cos(t) - 5 * math.cos(2 * t)
             - 2 * math.cos(3 * t) - math.cos(4 * t))
        points.append((x, y))
    return points


def _normalize(raw, width, height, cx, cy):
    """把心形曲线等比缩放并平移到以 (cx, cy) 为中心的区域"""
    xs = [p[0] for p in raw]
    ys = [p[1] for p in raw]
    xmin, xmax, ymin, ymax = min(xs), max(xs), min(ys), max(ys)
    xmid, ymid = (xmin + xmax) / 2, (ymin + ymax) / 2
    return [(
        cx + (x - xmid) / (xmax - xmin) * width,
        cy - (y - ymid) / (ymax - ymin) * height,
    ) for x, y in raw]


def heart_points(n, sw, sh):
    """心形曲线上 n 个弹窗左上角坐标，等比缩放、自动适配屏幕并限制在屏幕内"""
    raw = heart_curve(n)
    xs = [p[0] for p in raw]
    ys = [p[1] for p in raw]
    span_x, span_y = max(xs) - min(xs), max(ys) - min(ys)
    unit = min(sw * HEART_WIDTH_RATIO / span_x,
               sh * HEART_HEIGHT_RATIO / span_y)
    pts = _normalize(raw, span_x * unit, span_y * unit, sw / 2, sh / 2)
    result = []
    for x, y in pts:
        sx = int(x - WIN_W / 2)
        sy = int(y - WIN_H / 2)
        result.append((max(0, min(sx, sw - WIN_W)),
                       max(0, min(sy, sh - WIN_H))))
    return result


def grid_points(sw, sh):
    """均匀的位置池：铺满屏幕的网格点，加随机抖动后打乱"""
    cols = max(3, sw // (WIN_W + GRID_GAP_X))
    rows = max(3, sh // (WIN_H + GRID_GAP_Y))
    cell_w, cell_h = sw / cols, sh / rows
    pts = []
    for r in range(rows):
        for c in range(cols):
            x = int(c * cell_w + (cell_w - WIN_W) / 2 + random.randint(-14, 14))
            y = int(r * cell_h + (cell_h - WIN_H) / 2 + random.randint(-10, 10))
            pts.append((max(0, min(x, sw - WIN_W)),
                        max(0, min(y, sh - WIN_H))))
    random.shuffle(pts)
    return pts[:GRID_LIMIT]


def rounded_rect(canvas, x1, y1, x2, y2, radius, **kwargs):
    """用平滑多边形画圆角矩形"""
    r = radius
    pts = [
        x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
        x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
        x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
    ]
    return canvas.create_polygon(pts, smooth=True, **kwargs)


# ============================================================
# 演出
# ============================================================
class HeartShow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()                     # 隐藏主窗口，只显示弹窗
        self.sw = self.root.winfo_screenwidth()
        self.sh = self.root.winfo_screenheight()
        self.windows = []
        self.alive = True
        self.title_win = None
        self.bgm = BgmPlayer()
        # bind_all 让所有弹窗都能收到按键
        self.root.bind_all("<Escape>", self.finish)
        self.root.bind_all("<space>", self.finish)

    # ---------- 基础工具 ----------
    @staticmethod
    def _destroy(win):
        try:
            if win.winfo_exists():
                win.destroy()
        except (tk.TclError, AttributeError):
            pass

    def _make_toplevel(self, w, h, x, y):
        win = tk.Toplevel(self.root)
        win.overrideredirect(True)               # 无边框卡片
        try:
            win.attributes("-topmost", True)     # 始终置顶
        except tk.TclError:
            pass
        win.geometry("%dx%d+%d+%d" % (w, h, x, y))
        win.bind("<Button-1>", self.finish)      # 点任意卡片也能退出
        return win

    def _canvas(self, win, w, h, fallback_bg):
        """优先用透明色实现圆角；不支持的系统回退成普通矩形卡片"""
        try:
            win.attributes("-transparentcolor", TRANSPARENT_BG)
            bg = TRANSPARENT_BG
        except tk.TclError:
            bg = fallback_bg
        canvas = tk.Canvas(win, width=w, height=h, bg=bg,
                           highlightthickness=0, bd=0)
        canvas.pack()
        return canvas, bg

    def _fade_in(self, win, alpha=0.0):
        if not self.alive:
            return
        try:
            if not win.winfo_exists():
                return
        except tk.TclError:
            return
        alpha = min(1.0, alpha + 0.25)
        try:
            win.attributes("-alpha", alpha)
        except tk.TclError:
            # 该系统不支持窗口透明度时，立刻恢复不透明，避免窗口隐形
            try:
                win.attributes("-alpha", 1.0)
            except tk.TclError:
                pass
            return
        if alpha < 1.0:
            self.root.after(35, lambda: self._fade_in(win, alpha))

    def popup(self, x, y, text=None, fade=False):
        if not self.alive:
            return None
        bg, fg = random.choice(COLORS)
        text = text if text else random.choice(TIPS)
        win = self._make_toplevel(WIN_W, WIN_H, x, y)
        canvas, _ = self._canvas(win, WIN_W, WIN_H, bg)

        rounded_rect(canvas, 5, 6, WIN_W - 3, WIN_H - 2, 16,
                     fill="#E8C9D2", outline="")
        rounded_rect(canvas, 4, 4, WIN_W - 4, WIN_H - 4, 16,
                     fill=bg, outline="#FFFFFF", width=2)
        canvas.create_text(WIN_W / 2, WIN_H / 2, text=text,
                           font=(FONT_FAMILY, 14, "bold"), fill=fg)
        canvas.create_text(WIN_W - 18, WIN_H / 2, text="♥",
                           font=(FONT_FAMILY, 11), fill="#F48FB1")

        self.windows.append(win)
        if fade:
            try:
                win.attributes("-alpha", 0.0)
                self._fade_in(win)
            except tk.TclError:
                try:
                    win.attributes("-alpha", 1.0)
                except tk.TclError:
                    pass
        return win

    def finish(self, event=None):
        """手动退出：停音乐、关掉所有窗口、结束主循环"""
        if not self.alive:
            return
        self.alive = False
        self.bgm.stop()
        for win in list(self.windows):
            self._destroy(win)
        self.windows.clear()
        try:
            self.root.quit()
        except tk.TclError:
            pass
        try:
            self.root.destroy()
        except tk.TclError:
            pass

    # ---------- 阶段一：爱心绽放 ----------
    def start(self):
        self.heart = heart_points(HEART_COUNT, self.sw, self.sh)
        self.hi = 0
        self._heart_step()

    def _heart_step(self):
        if not self.alive:
            return
        if self.hi < len(self.heart):
            x, y = self.heart[self.hi]
            self.popup(x, y, fade=True)
            self.hi += 1
            self.root.after(HEART_INTERVAL_MS, self._heart_step)
        else:
            self.root.after(HEART_HOLD_MS, self._show_title)

    # ---------- 阶段二：中央大爱心（常驻，不会自动消失） ----------
    def _show_title(self):
        if not self.alive:
            return
        w, h = FINALE_W, FINALE_H
        x, y = (self.sw - w) // 2, (self.sh - h) // 2
        win = self._make_toplevel(w, h, x, y)
        self.title_win = win
        self.windows.append(win)
        canvas, _ = self._canvas(win, w, h, "#FFF0F5")

        rounded_rect(canvas, 6, 8, w - 4, h - 4, 28, fill="#F6D5DE", outline="")
        rounded_rect(canvas, 4, 4, w - 6, h - 6, 28,
                     fill="#FFF5F8", outline="#FFC1D3", width=2)
        canvas.create_text(w / 2, 36, text=HEADER,
                           font=(FONT_FAMILY, 13), fill="#D81B60")

        self._finale_raw = heart_curve(120)
        pts = _normalize(self._finale_raw, 260, 240, w / 2, h / 2 - 6)
        flat = [v for p in pts for v in p]
        self._finale_canvas = canvas
        self._finale_heart = canvas.create_polygon(
            flat, smooth=True, fill="#FF6E9C", outline="#FFB3C9", width=3)

        canvas.create_text(w / 2, h / 2 - 30, text=TITLE,
                           font=(FONT_FAMILY, 26, "bold"), fill="#FFFFFF")
        canvas.create_text(w / 2, h / 2 + 12, text=TITLE_2,
                           font=(FONT_FAMILY, 26, "bold"), fill="#FFFFFF")
        canvas.create_text(w / 2, h - 40, text=SIGNATURE,
                           font=(FONT_FAMILY, 12), fill="#C2185B")

        self._beat(0)
        self.pool = grid_points(self.sw, self.sh)
        self.pool_idx = 0
        self.root.after(TITLE_DELAY_MS, self._spawn_step)

    def _beat(self, tick):
        """大爱心一直轻轻跳动，直到手动退出"""
        if not self.alive:
            return
        try:
            if not self._finale_canvas.winfo_exists():
                return
        except (tk.TclError, AttributeError):
            return
        scale = 1.0 + (0.035 if tick % 2 == 0 else -0.02)
        pts = _normalize(self._finale_raw, 260 * scale, 240 * scale,
                         FINALE_W / 2, FINALE_H / 2 - 6)
        try:
            self._finale_canvas.coords(self._finale_heart,
                                       *[v for p in pts for v in p])
        except tk.TclError:
            return
        self.root.after(520, lambda: self._beat(tick + 1))

    # ---------- 阶段三：一直弹，不自动关闭 ----------
    def _spawn_step(self):
        if not self.alive:
            return
        if len(self.windows) >= MAX_WINDOWS:
            # 到上限后不再新建，但一个都不关闭 —— 画面一直保持
            print("屏幕上已有 %d 张卡片，会一直保持，直到你手动退出。" % len(self.windows))
            return
        if self.pool_idx >= len(self.pool):
            random.shuffle(self.pool)
            self.pool_idx = 0
        x, y = self.pool[self.pool_idx]
        self.pool_idx += 1
        x = max(0, min(x + random.randint(-16, 16), self.sw - WIN_W))
        y = max(0, min(y + random.randint(-12, 12), self.sh - WIN_H))
        self.popup(x, y)
        # 让中央标题始终压在最上层，不被后来的小卡片盖住
        try:
            if self.title_win and self.title_win.winfo_exists():
                self.title_win.lift()
        except tk.TclError:
            pass
        self.root.after(SPAWN_INTERVAL_MS, self._spawn_step)

    def run(self):
        print("爱心弹窗已启动 —— 不会自动关闭")
        print("按 Esc / 空格 / 单击任意卡片 / Ctrl+C 才会退出（音乐会一起停）")
        self.bgm.start()
        self.root.after(120, self.start)
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.finish()
        print("已退出，愿你今天开心")


def selftest():
    """不开窗口、不放音乐，只验证坐标计算与 BGM 文件"""
    sw, sh = 1920, 1080
    pts = heart_points(HEART_COUNT, sw, sh)
    assert len(pts) == HEART_COUNT, "心形弹窗数量不对"
    assert all(0 <= x <= sw - WIN_W and 0 <= y <= sh - WIN_H for x, y in pts), \
        "心形弹窗坐标越界"
    grid = grid_points(sw, sh)
    assert 0 < len(grid) <= GRID_LIMIT, "位置池数量不对"
    assert all(0 <= x <= sw - WIN_W and 0 <= y <= sh - WIN_H for x, y in grid), \
        "位置池坐标越界"
    small = heart_points(HEART_COUNT, 800, 600)
    assert all(0 <= x <= 800 - WIN_W and 0 <= y <= 600 - WIN_H for x, y in small), \
        "小屏幕心形弹窗坐标越界"
    assert MAX_WINDOWS > HEART_COUNT, "窗口上限必须大于心形弹窗数"
    path = find_bgm()
    if path:
        assert os.path.isfile(path) and os.path.getsize(path) > 0, "BGM 文件无效"
        print("选曲：%s（%.1f MB）" % (os.path.basename(path),
                                     os.path.getsize(path) / 1024 / 1024))
    else:
        print("未找到 %s，将静音运行" % BGM_FILE)
    print("自检通过：心形 %d 个 / 位置池 %d 个 / 上限 %d 个窗口，坐标均未越界。"
          % (len(pts), len(grid), MAX_WINDOWS))


if __name__ == "__main__":
    if "--test" in sys.argv:
        selftest()
    elif "--which-bgm" in sys.argv:
        p = find_bgm()
        if p:
            print("当前 BGM（唯一）：", p)
        else:
            print("未找到 %s，会静音运行。把它放进同目录即可。" % BGM_FILE)
    elif tk is None:
        # 没装 tkinter 也能看到同款效果：直接用浏览器打开网页版
        import webbrowser
        print("当前 Python 未安装 tkinter，已为你打开网页版同款效果。")
        print("若想体验真正的桌面满屏弹窗，请安装官网 Python 3（勾选 tcl/tk）。")
        # index.html 是 GitHub Pages 入口；兼容旧的 heart_popup_preview.html 命名
        html = next((os.path.join(BASE_DIR, name)
                     for name in ("index.html", "heart_popup_preview.html")
                     if os.path.exists(os.path.join(BASE_DIR, name))), None)
        if html:
            webbrowser.open("file:///" + html.replace("\\", "/"))
        else:
            print("未找到网页版文件：index.html / heart_popup_preview.html")
    else:
        HeartShow().run()
