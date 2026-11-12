# -*- coding: utf-8 -*-
"""
透明小说阅读器 —— 背景可完全透明的桌面小说阅读工具
功能：导入 TXT 小说、自动分章、章节目录、背景透明（0-100%）、鼠标穿透、自动滚动、进度记忆
依赖：PyQt5
运行：python main.py
"""

import os
import sys
import re
import json
import hashlib
import ctypes
import faulthandler
from ctypes import wintypes

from PyQt5.QtCore import (Qt, QPoint, QRect, QTimer, QSize, QAbstractNativeEventFilter,
                          QEvent, pyqtSignal)
from PyQt5.QtGui import (QColor, QFont, QPainter, QPainterPath, QPen, QPixmap, QIcon,
                         QTextCursor, QTextBlockFormat, QFontMetrics, QKeySequence,
                         QFontMetricsF)
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTextBrowser, QSlider, QCheckBox, QComboBox,
                             QFontComboBox, QLineEdit, QListWidget, QListWidgetItem,
                             QFileDialog, QSizeGrip, QColorDialog, QGraphicsDropShadowEffect,
                             QStackedWidget, QMenu, QAction, QSystemTrayIcon, QShortcut,
                             QScrollBar, QMessageBox, QGraphicsOpacityEffect,
                             QScrollArea, QFrame)
from PyQt5.QtCore import QPropertyAnimation

APP_NAME = "透明小说阅读器"
DATA_DIR = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "TransparentNovelReader")
SETTINGS_PATH = os.path.join(DATA_DIR, "settings.json")
PROGRESS_PATH = os.path.join(DATA_DIR, "progress.json")
LIBRARY_PATH = os.path.join(DATA_DIR, "library.json")
CRASH_PATH = os.path.join(DATA_DIR, "crash.log")


def _setup_crash_log():
    """崩溃时把调用栈写进 crash.log，方便定位闪退原因"""
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        f = open(CRASH_PATH, "a", encoding="utf-8", buffering=1)
        f.write("\n===== 启动 %s =====\n" % __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        faulthandler.enable(file=f)
    except Exception:
        pass

DEFAULT_SETTINGS = {
    "bg_alpha": 0,              # 背景不透明度 0-100，0 = 完全透明（只显示文字）
    "font_family": "微软雅黑",
    "font_size": 20,
    "line_height": 1.8,
    "text_color": "#EAEAF0",
    "indent": True,             # 段首缩进两字
    "shadow": True,             # 文字阴影（提升在浅色桌面上的可读性）
    "always_on_top": True,
    "click_through": False,
    "ui_visible": True,
    "margin": 28,               # 正文左右留白
    "autoscroll_speed": 2,
    "window": [0, 0, 560, 800],
    "last_book": "",            # 上次读的书，下次启动自动接着打开
    "auto_hide_ui": True,       # 鼠标移开自动隐藏上下工具栏（默认开）
}

TEXT_COLORS = [
    ("#EAEAF0", "浅白"),
    ("#FFFFFF", "纯白"),
    ("#FFD9A0", "米黄"),
    ("#BFE5B0", "浅绿"),
    ("#F7C7D0", "浅粉"),
    ("#9FD8E8", "浅蓝"),
    ("#202020", "墨黑"),
]

QSS = """
QWidget { color: #D9D9DF; font-family: "微软雅黑"; }
QPushButton {
    background: rgba(255,255,255,0.075); border: none; border-radius: 7px;
    color: #DCDCE2; padding: 6px 12px; font-size: 12px;
}
QPushButton:hover { background: rgba(255,255,255,0.16); }
QPushButton:pressed { background: rgba(255,255,255,0.26); }
QPushButton:checked { background: rgba(96,160,255,0.42); color: #FFFFFF; }
QPushButton:disabled { color: rgba(255,255,255,0.25); }
QLineEdit, QComboBox, QFontComboBox {
    background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.10);
    border-radius: 6px; padding: 5px 8px; color: #E4E4EA; font-size: 12px;
}
QLineEdit:focus, QComboBox:focus { border: 1px solid rgba(96,160,255,0.65); }
QComboBox QAbstractItemView {
    background: #22222A; border: 1px solid rgba(255,255,255,0.14);
    selection-background-color: rgba(96,160,255,0.40); color: #E4E4EA; outline: none;
}
QListWidget {
    background: transparent; border: none; outline: none; color: #C9C9D2; font-size: 12px;
}
QListWidget::item { padding: 6px 8px; border-radius: 5px; }
QListWidget::item:selected { background: rgba(96,160,255,0.35); color: #FFFFFF; }
QListWidget::item:hover { background: rgba(255,255,255,0.09); }
QCheckBox { color: #C9C9D2; font-size: 12px; spacing: 6px; }
QCheckBox::indicator { width: 14px; height: 14px; border-radius: 4px;
    background: rgba(255,255,255,0.10); border: 1px solid rgba(255,255,255,0.18); }
QCheckBox::indicator:checked { background: rgba(96,160,255,0.85); border: 1px solid rgba(96,160,255,0.95); }
QSlider::groove:horizontal { height: 4px; background: rgba(255,255,255,0.16); border-radius: 2px; }
QSlider::handle:horizontal { width: 12px; height: 12px; margin: -5px 0; border-radius: 6px;
    background: #E8E8F0; }
QSlider::handle:horizontal:hover { background: #FFFFFF; }
QSlider::sub-page:horizontal { background: rgba(96,160,255,0.70); border-radius: 2px; }
QScrollBar:vertical { background: transparent; width: 8px; margin: 0; }
QScrollBar::handle:vertical { background: rgba(255,255,255,0.22); border-radius: 4px; min-height: 26px; }
QScrollBar::handle:vertical:hover { background: rgba(255,255,255,0.38); }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QMenu { background: #22222A; border: 1px solid rgba(255,255,255,0.14); color: #E4E4EA; padding: 4px; }
QMenu::item { padding: 6px 18px; border-radius: 5px; }
QMenu::item:selected { background: rgba(96,160,255,0.40); }
"""


# ----------------------------------------------------------------------------- 工具函数
def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(default, dict):
            merged = dict(default)
            merged.update(data if isinstance(data, dict) else {})
            return merged
        return data
    except Exception:
        return default


def save_json(path, data):
    try:
        ensure_data_dir()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def decode_text_file(path):
    """自动识别编码（UTF-8 / GBK / GB18030 / BIG5 / UTF-16），返回 (文本, 编码名)"""
    with open(path, "rb") as f:
        data = f.read()
    if not data:
        return "", "empty"

    candidates = []
    if data[:2] in (b"\xff\xfe", b"\xfe\xff"):
        candidates.append(("utf-16", "utf-16"))
    candidates += [("utf-8-sig", "utf-8"), ("utf-8", "utf-8"),
                   ("gb18030", "gb18030"), ("big5", "big5")]

    head = data[:8000]

    def quality(txt):
        score = 0
        for ch in txt:
            o = ord(ch)
            if "\u4e00" <= ch <= "\u9fff":
                score += 3
            elif ch in "，。、；：？！“”‘’《》（）—…·":
                score += 2
            elif 32 <= o < 127:
                score += 1
            elif ch in "\r\n\t":
                score += 1
            elif o < 32 or 0xE000 <= o <= 0xF8FF or 0xFFF0 <= o <= 0xFFFF:
                score -= 15
        return score

    best, best_score, best_enc = None, -10 ** 9, "utf-8"
    for codec, name in candidates:
        try:
            txt = head.decode(codec)
        except (UnicodeDecodeError, LookupError):
            continue
        q = quality(txt)
        if q > best_score:
            best, best_score, best_enc = codec, q, name

    codec = best or "utf-8"
    try:
        text = data.decode(codec, errors="replace")
    except LookupError:
        text = data.decode("utf-8", errors="replace")
    text = text.replace("\r\n", "\n").replace("\r", "\n").lstrip("\ufeff")
    return text, best_enc


def normalize_text(text):
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip("\n")


# 分章规则
PATTERNS = [
    re.compile(r"^\s{0,4}第\s*[0-9０-９零〇一二三四五六七八九十百千万两]{1,12}\s*[章节回卷部篇话折幕集][\s、\.。:：·\-—]*(.{0,28})$"),
    re.compile(r"^\s{0,4}([Cc]hapter|[Cc]HAPTER)\s*[0-9IVXLCivxlc]{1,8}[\s\.、:：\-—]*(.{0,28})$"),
    re.compile(r"^\s{0,4}(序章|序言|序|楔子|引子|序幕|前言|后记|尾声|终章|结局|大结局|番外篇?|附录|内容简介|作者的话)[\s\-—·:：\.]{0,4}(.{0,20})$"),
    re.compile(r"^\s{0,4}[0-9]{1,3}[\.、．]\s*(\S.{0,26})$"),
]


def is_heading(line):
    s = line.strip()
    if not s or len(s) > 36:
        return False
    for pat in PATTERNS:
        if pat.match(s):
            return True
    return False


class Book:
    """一本小说的数据结构：全文、章节切分"""

    def __init__(self, title, text, path=""):
        self.title = title
        self.path = path
        self.text = normalize_text(text)
        self.chapters = []          # [{"title": str, "start": int, "end": int}]  (字符偏移)
        self.build_chapters()

    @property
    def key(self):
        raw = (self.path or self.title).lower()
        try:
            raw += str(os.path.getsize(self.path))
        except Exception:
            raw += str(len(self.text))
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    def build_chapters(self, chunk_size=2200):
        text = self.text
        self.chapters = []
        if not text:
            return

        lines = text.split("\n")
        offsets = []
        pos = 0
        for ln in lines:
            offsets.append(pos)
            pos += len(ln) + 1

        heads = [i for i, ln in enumerate(lines) if is_heading(ln)]

        if heads:
            # 首个章节前的内容作为「前言/开头」
            if heads[0] > 0:
                pre = "\n".join(lines[:heads[0]]).strip()
                if pre:
                    self.chapters.append({"title": "开始", "start": 0, "end": offsets[heads[0]]})
            for n, hi in enumerate(heads):
                start = offsets[hi]
                end = offsets[heads[n + 1]] if n + 1 < len(heads) else len(text)
                title = lines[hi].strip()[:40]
                self.chapters.append({"title": title, "start": start, "end": end})
        else:
            # 没有识别到章节：按字数自动切分，避免一整本一屏读完
            total = len(text)
            if total <= chunk_size:
                self.chapters.append({"title": "全文", "start": 0, "end": total})
            else:
                n = 0
                p = 0
                while p < total:
                    n += 1
                    end = min(total, p + chunk_size)
                    # 尽量在换行处断开
                    cut = text.rfind("\n", p + 200, end)
                    if cut > p:
                        end = cut + 1
                    self.chapters.append({"title": "第 %d 段" % n, "start": p, "end": end})
                    p = end

    def chapter_text(self, idx):
        if 0 <= idx < len(self.chapters):
            c = self.chapters[idx]
            body = self.text[c["start"]:c["end"]]
            # 去掉首行章节标题，避免正文里重复出现
            first_nl = body.find("\n")
            if 0 < first_nl < 50 and is_heading(body[:first_nl]):
                body = body[first_nl + 1:]
            return body.strip("\n")
        return ""


class Bar(QWidget):
    """工具栏：半透明深色底片，保证在任何桌面背景上都能看清按钮"""

    def __init__(self, parent=None, alpha=140):
        super().__init__(parent)
        self.alpha = alpha

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(16, 16, 20, self.alpha))
        p.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 9, 9)


# ----------------------------------------------------------------------------- 面板基类
class Panel(QWidget):
    """带圆角半透明底的浮层面板"""

    def __init__(self, parent=None, bg=(26, 26, 32, 242), radius=12):
        super().__init__(parent)
        self._bg = QColor(*bg)
        self._radius = radius

    def set_bg(self, color):
        self._bg = QColor(color)
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(self._bg)
        p.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), self._radius, self._radius)


def slider_row(label, minv, maxv, value, fmt, on_change, suffix=""):
    row = QWidget()
    lay = QHBoxLayout(row)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(8)

    lb = QLabel(label)
    lb.setFixedWidth(52)
    lb.setStyleSheet("color:#9AA0AC;font-size:12px;")

    sl = QSlider(Qt.Horizontal)
    sl.setRange(minv, maxv)
    sl.setValue(value)
    sl.setFixedHeight(18)

    val = QLabel(fmt(value))
    val.setFixedWidth(44)
    val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    val.setStyleSheet("color:#8FA8C8;font-size:12px;")

    def _changed(v):
        val.setText(fmt(v))
        on_change(v)

    sl.valueChanged.connect(_changed)
    lay.addWidget(lb)
    lay.addWidget(sl, 1)
    lay.addWidget(val)
    return row, sl


# ----------------------------------------------------------------------------- 全局热键
class HotkeyFilter(QAbstractNativeEventFilter):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def nativeEventFilter(self, eventType, message):
        try:
            if eventType in (b"windows_generic_MSG", b"windows_dispatcher_MSG"):
                msg = wintypes.MSG.from_address(int(message))
                if msg.message == 0x0312:  # WM_HOTKEY
                    self.callback(int(msg.wParam))
        except Exception:
            pass
        return False, 0


# ----------------------------------------------------------------------------- 主窗口
class ReaderWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.settings = load_json(SETTINGS_PATH, DEFAULT_SETTINGS)
        self.progress = load_json(PROGRESS_PATH, {})
        self.library = load_json(LIBRARY_PATH, [])

        self.book = None
        self.idx = 0
        self.autoscroll_on = False
        self._drag_pos = None
        self._resize_edge = None
        self._hover_bar = False

        self.setWindowTitle(APP_NAME)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMouseTracking(True)
        self.setAcceptDrops(True)
        self.setStyleSheet(QSS)
        self.setMinimumSize(150, 60)      # 真正的最小尺寸在 _update_min_size 里按字号算

        self._build_ui()
        self._setup_shortcuts()
        QApplication.instance().installEventFilter(self)
        self._restore_geometry()
        self._apply_settings_all()
        self._init_tray()
        self._register_hotkey()
        self._start_keep_on_top()

        # 无书时显示欢迎页
        self._show_welcome()

    # ---------------- UI 构建
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(0)

        # 顶部工具条
        self.topbar = Bar(self, 178)
        self.topbar.setFixedHeight(38)
        top = QHBoxLayout(self.topbar)
        top.setContentsMargins(4, 0, 4, 0)
        top.setSpacing(6)

        self.title_label = QLabel("未打开书籍")
        self.title_label.setStyleSheet("color:#AEB6C4;font-size:12px;")
        self.title_label.setMinimumWidth(80)

        def tbtn(text, tip, slot, width=None, checkable=False):
            b = QPushButton(text)
            b.setToolTip(tip)
            b.setCheckable(checkable)
            b.setCursor(Qt.PointingHandCursor)
            if width:
                b.setFixedWidth(width)
            b.clicked.connect(slot)
            return b

        self.btn_open = tbtn("导入", "导入 txt 小说文件 (Ctrl+O)", self.import_files, 56)
        self.btn_toc = tbtn("目录", "章节列表与书架 (F3)", self.toggle_toc, 56)
        self.btn_set = tbtn("设置", "字体、透明度和阅读选项 (F4)", self.toggle_settings, 56)
        self.btn_through = tbtn("穿透", "鼠标穿透，可点到底下的窗口（热键恢复）", self.toggle_click_through, 56, True)
        self.btn_top = tbtn("置顶", "窗口始终在最前面", self.toggle_on_top, 56, True)
        self.btn_min = tbtn("－", "最小化", self.showMinimized, 34)
        self.btn_close = tbtn("✕", "退出阅读器", self.close, 34)

        top.addWidget(self.title_label, 1)
        for b in (self.btn_open, self.btn_toc, self.btn_set, self.btn_through,
                  self.btn_top, self.btn_min, self.btn_close):
            top.addWidget(b)

        # 正文
        self.view = QTextBrowser()
        self.view.setOpenExternalLinks(False)
        self.view.setFrameShape(QTextBrowser.NoFrame)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.view.setStyleSheet("QTextBrowser{background:transparent;border:none;}"
                                "QTextBrowser{selection-background-color:rgba(96,160,255,0.45);}")
        self.view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self._view_menu)
        self.view.verticalScrollBar().valueChanged.connect(self._on_scroll)

        self.drop_hint = QLabel("把 .txt 小说拖进来，或点击「导入」", self.view)
        self.drop_hint.setAlignment(Qt.AlignCenter)
        self.drop_hint.setStyleSheet("color:rgba(140,150,165,0.75);font-size:14px;")
        self.drop_hint.hide()

        # 底部工具条
        self.bottombar = Bar(self, 165)
        self.bottombar.setFixedHeight(40)
        bot = QHBoxLayout(self.bottombar)
        bot.setContentsMargins(4, 2, 4, 2)
        bot.setSpacing(6)

        self.btn_prev = tbtn("‹ 上一章", "上一章 (PageUp/Alt+←)", self.prev_chapter, 78)
        self.btn_next = tbtn("下一章 ›", "下一章 (PageDown/Alt+→)", self.next_chapter, 78)
        self.btn_auto = tbtn("自动滚", "自动滚动阅读（空格开关）", self.toggle_autoscroll, 66, True)

        self.chapter_slider = QSlider(Qt.Horizontal)
        self.chapter_slider.setRange(0, 0)
        self.chapter_slider.setFixedHeight(18)
        self.chapter_slider.sliderReleased.connect(self._slider_jump)
        self.chapter_slider.valueChanged.connect(self._slider_label)

        self.pos_label = QLabel("0 / 0")
        self.pos_label.setStyleSheet("color:#8E96A4;font-size:12px;")
        self.pos_label.setFixedWidth(70)
        self.pos_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        bot.addWidget(self.btn_prev)
        bot.addWidget(self.btn_next)
        bot.addWidget(self.btn_auto)
        bot.addWidget(self.chapter_slider, 1)
        bot.addWidget(self.pos_label)

        # 上下工具栏各自套一个固定高度的容器：自动隐藏时只把里面的栏藏起来，
        # 容器还占着原来的位置，所以正文字数、阅读位置都不会跳
        self.top_box = QWidget(self)
        tl0 = QVBoxLayout(self.top_box)
        tl0.setContentsMargins(0, 0, 0, 0)
        tl0.setSpacing(0)
        tl0.addWidget(self.topbar)
        self.top_box.setFixedHeight(38)
        self.bot_box = QWidget(self)
        bl0 = QVBoxLayout(self.bot_box)
        bl0.setContentsMargins(0, 0, 0, 0)
        bl0.setSpacing(0)
        bl0.addWidget(self.bottombar)
        self.bot_box.setFixedHeight(40)

        root.addWidget(self.top_box)
        root.addWidget(self.view, 1)
        root.addWidget(self.bot_box)

        # 自动隐藏工具栏用的透明度效果（只建一次，反复建删 QGraphicsEffect 会崩）
        self._setup_auto_hide()

        # 右下角缩放柄
        self.grip = QSizeGrip(self)
        self.grip.setFixedSize(16, 16)
        self.grip.setStyleSheet("background:transparent;")

        # 目录 / 书架面板
        self.toc_panel = Panel(self)
        self.toc_panel.setMinimumWidth(130)
        tl = QVBoxLayout(self.toc_panel)
        tl.setContentsMargins(12, 12, 12, 12)
        tl.setSpacing(8)

        toc_head = QHBoxLayout()
        self.btn_tab_chapters = QPushButton("章节")
        self.btn_tab_chapters.setCheckable(True)
        self.btn_tab_chapters.setChecked(True)
        self.btn_tab_books = QPushButton("书架")
        self.btn_tab_books.setCheckable(True)
        for b in (self.btn_tab_chapters, self.btn_tab_books):
            b.setCursor(Qt.PointingHandCursor)
            toc_head.addWidget(b)
        self.btn_tab_chapters.clicked.connect(lambda: self._switch_tab(0))
        self.btn_tab_books.clicked.connect(lambda: self._switch_tab(1))
        close_toc = QPushButton("✕")
        close_toc.setFixedWidth(30)
        close_toc.setCursor(Qt.PointingHandCursor)
        close_toc.clicked.connect(self.toggle_toc)
        toc_head.addWidget(close_toc)
        tl.addLayout(toc_head)

        self.toc_stack = QStackedWidget()

        # 章节页
        page1 = QWidget()
        p1 = QVBoxLayout(page1)
        p1.setContentsMargins(0, 0, 0, 0)
        p1.setSpacing(6)
        self.toc_search = QLineEdit()
        self.toc_search.setPlaceholderText("搜索章节名或章节序号…")
        self.toc_search.textChanged.connect(self._filter_chapters)
        self.toc_list = QListWidget()
        self.toc_list.itemClicked.connect(self._toc_clicked)
        p1.addWidget(self.toc_search)
        p1.addWidget(self.toc_list, 1)

        # 书架页
        page2 = QWidget()
        p2 = QVBoxLayout(page2)
        p2.setContentsMargins(0, 0, 0, 0)
        p2.setSpacing(6)
        self.book_list = QListWidget()
        self.book_list.itemClicked.connect(self._book_clicked)
        self.book_empty = QLabel("还没有导入过小说\n点上方「导入」添加 .txt 文件")
        self.book_empty.setAlignment(Qt.AlignCenter)
        self.book_empty.setStyleSheet("color:rgba(150,158,172,0.7);font-size:12px;")
        p2.addWidget(self.book_list, 1)
        p2.addWidget(self.book_empty)

        self.toc_stack.addWidget(page1)
        self.toc_stack.addWidget(page2)
        tl.addWidget(self.toc_stack, 1)

        # 设置面板
        self.set_panel = Panel(self)
        self.set_panel.setMinimumWidth(130)
        # 设置内容放进滚动区：窗口缩到很小时面板也塞得下，滚一滚就能改任何一项，
        # 不再靠「把窗口撑大」这种强扭的做法
        self.set_content = QWidget()
        self.set_content.setStyleSheet("background:transparent;")
        outer = QVBoxLayout(self.set_panel)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self.set_scroll = QScrollArea(self.set_panel)
        self.set_scroll.setWidgetResizable(True)
        self.set_scroll.setFrameShape(QFrame.NoFrame)
        self.set_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.set_scroll.setStyleSheet(
            "QScrollArea{background:transparent;border:none;}"
            "QScrollArea > QWidget > QWidget{background:transparent;}")
        self.set_scroll.setWidget(self.set_content)
        outer.addWidget(self.set_scroll)
        sl = QVBoxLayout(self.set_content)
        sl.setContentsMargins(14, 12, 14, 12)
        sl.setSpacing(9)

        sh = QHBoxLayout()
        t = QLabel("阅读设置")
        t.setStyleSheet("color:#E6E6EC;font-size:13px;font-weight:600;")
        sh.addWidget(t, 1)
        close_set = QPushButton("✕")
        close_set.setFixedWidth(30)
        close_set.setCursor(Qt.PointingHandCursor)
        close_set.clicked.connect(self.toggle_settings)
        sh.addWidget(close_set)
        sl.addLayout(sh)

        # 背景不透明度
        self.row_bgalpha, self.sl_bgalpha = slider_row(
            "背景", 0, 100, self.settings["bg_alpha"], lambda v: "%d%%" % v,
            self._on_bg_alpha)
        sl.addWidget(self.row_bgalpha)

        # 字号
        self.row_size, self.sl_size = slider_row(
            "字号", 12, 48, self.settings["font_size"], lambda v: "%d px" % v,
            self._on_font_size)
        sl.addWidget(self.row_size)

        # 行距
        self.row_lh, self.sl_lh = slider_row(
            "行距", 100, 300, int(self.settings["line_height"] * 100),
            lambda v: "%.1f" % (v / 100.0), self._on_line_height)
        sl.addWidget(self.row_lh)

        # 留白
        self.row_margin, self.sl_margin = slider_row(
            "留白", 0, 120, self.settings["margin"], lambda v: "%d px" % v,
            self._on_margin)
        sl.addWidget(self.row_margin)

        # 字体
        frow = QHBoxLayout()
        frow.setSpacing(8)
        fl = QLabel("字体")
        fl.setFixedWidth(52)
        fl.setStyleSheet("color:#9AA0AC;font-size:12px;")
        self.font_box = QFontComboBox()
        self.font_box.setFontFilters(QFontComboBox.ScalableFonts)
        self.font_box.setCurrentFont(QFont(self.settings["font_family"]))
        self.font_box.currentFontChanged.connect(self._on_font_family)
        frow.addWidget(fl)
        frow.addWidget(self.font_box, 1)
        sl.addLayout(frow)

        # 字色
        crow = QHBoxLayout()
        crow.setSpacing(6)
        cl = QLabel("字色")
        cl.setFixedWidth(52)
        cl.setStyleSheet("color:#9AA0AC;font-size:12px;")
        crow.addWidget(cl)
        self.color_btns = []
        for color, name in TEXT_COLORS:
            b = QPushButton()
            b.setFixedSize(20, 20)
            b.setToolTip(name)
            b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet("QPushButton{background:%s;border-radius:10px;border:1px solid rgba(255,255,255,0.25);}"
                            "QPushButton:hover{border:1px solid rgba(255,255,255,0.85);}" % color)
            b.clicked.connect(lambda _=False, c=color: self._set_text_color(c))
            self.color_btns.append((b, color))
            crow.addWidget(b)
        more = QPushButton("自定义")
        more.setFixedWidth(56)
        more.setCursor(Qt.PointingHandCursor)
        more.clicked.connect(self._pick_color)
        crow.addWidget(more, 1)
        sl.addLayout(crow)

        # 一键预设
        prow = QHBoxLayout()
        prow.setSpacing(6)
        pl = QLabel("预设")
        pl.setFixedWidth(52)
        pl.setStyleSheet("color:#9AA0AC;font-size:12px;")
        prow.addWidget(pl)
        for text, tip, slot in (("纯文字", "背景完全透明，只有文字", self._preset_plain),
                                ("易读", "很淡的暗底，文字更清楚", self._preset_readable),
                                ("深色字", "换成黑字，适合浅色页面", self._preset_dark)):
            b = QPushButton(text)
            b.setToolTip(tip)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(slot)
            prow.addWidget(b, 1)
        sl.addLayout(prow)

        # 选项
        self.cb_indent = QCheckBox("段首缩进两字")
        self.cb_indent.toggled.connect(self._on_indent)
        self.cb_shadow = QCheckBox("文字阴影（浅色背景下更清晰）")
        self.cb_shadow.toggled.connect(self._on_shadow)
        self.cb_ui = QCheckBox("隐藏上下工具栏（只留正文）")
        self.cb_ui.setToolTip("快捷键 Alt+H 随时切换；隐藏后鼠标移到窗口最顶部会浮出一排小按钮，"
                              "鼠标移开自动消失，不影响阅读")
        self.cb_ui.toggled.connect(self._on_ui_switch)
        self.cb_auto = QCheckBox("鼠标移开自动隐藏工具栏（移回就显示）")
        self.cb_auto.setToolTip("勾选后：鼠标离开窗口，上下工具栏淡出消失；鼠标移回窗口，工具栏淡入出现。"
                                "正文位置不会因为工具栏显隐而跳动")
        self.cb_auto.toggled.connect(self._on_auto_hide_switch)
        sl.addWidget(self.cb_indent)
        sl.addWidget(self.cb_shadow)
        sl.addWidget(self.cb_ui)
        sl.addWidget(self.cb_auto)

        # 自动滚动速度
        self.row_speed, self.sl_speed = slider_row(
            "滚动", 1, 12, self.settings["autoscroll_speed"], lambda v: "%d" % v,
            self._on_speed)
        sl.addWidget(self.row_speed)

        hint = QLabel("提示：背景 0% 时窗口完全透明，建议同时开启「穿透」，"
                      "之后用全局热键恢复（默认 Ctrl+Alt+T，若被其他软件占用会自动换键，"
                      "具体组合见「穿透」按钮的悬停提示），实在不行点托盘图标右键也能恢复。")
        hint.setWordWrap(True)
        hint.setStyleSheet("color:rgba(150,158,172,0.72);font-size:11px;")
        sl.addWidget(hint)
        sl.addStretch(1)

        # 隐藏 UI 的迷你条（沉浸模式）
        self.mini = QWidget(self)
        self.mini.setStyleSheet("QWidget{background:rgba(24,24,30,0.88);border-radius:9px;}")
        ml = QHBoxLayout(self.mini)
        ml.setContentsMargins(4, 2, 4, 2)
        ml.setSpacing(2)
        for text, slot in (("≡", self.toggle_toc), ("Aa", self.toggle_settings),
                           ("－", self.showMinimized), ("✕", self.close)):
            b = QPushButton(text)
            b.setFixedSize(30, 26)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(slot)
            ml.addWidget(b)
        self.mini.hide()

        self.toc_panel.hide()
        self.set_panel.hide()

    # ---------------- 托盘
    def _init_tray(self):
        pm = QPixmap(64, 64)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QColor(70, 140, 240))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(4, 4, 56, 56, 14, 14)
        p.setPen(QPen(QColor(255, 255, 255)))
        f = QFont("微软雅黑", 26)
        p.setFont(f)
        p.drawText(pm.rect(), Qt.AlignCenter, "阅")
        p.end()

        self.tray = QSystemTrayIcon(QIcon(pm), self)
        self.tray.setToolTip(APP_NAME)
        menu = QMenu()
        act_show = QAction("显示窗口", self)
        act_show.triggered.connect(self._show_front)
        act_open = QAction("导入小说", self)
        act_open.triggered.connect(self.import_files)
        self.act_through = QAction("鼠标穿透", self, checkable=True)
        self.act_through.triggered.connect(self.toggle_click_through)
        act_quit = QAction("退出", self)
        act_quit.triggered.connect(lambda: (self._save_all(), QApplication.quit()))
        menu.addAction(act_show)
        menu.addAction(act_open)
        menu.addAction(self.act_through)
        menu.addSeparator()
        menu.addAction(act_quit)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(lambda r: self._show_front() if r == QSystemTrayIcon.Trigger else None)
        self.tray.show()

    def _show_front(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    # ---------------- 全局热键（退出穿透；被占用时自动换下一个组合）
    HOTKEY_CANDIDATES = [
        ("Ctrl+Alt+T", 0x0001 | 0x0002, ord("T")),
        ("Ctrl+Alt+R", 0x0001 | 0x0002, ord("R")),
        ("Ctrl+Alt+U", 0x0001 | 0x0002, ord("U")),
        ("Ctrl+Alt+J", 0x0001 | 0x0002, ord("J")),
        ("Ctrl+Shift+T", 0x0002 | 0x0004, ord("T")),
        ("Ctrl+Alt+9", 0x0001 | 0x0002, 0x39),
    ]

    def _register_hotkey(self):
        self.hotkey_id = 0xB001
        self.hotkey_label = None
        self._hotkey_filter = HotkeyFilter(self._on_hotkey)
        QApplication.instance().installNativeEventFilter(self._hotkey_filter)
        QTimer.singleShot(300, self._do_register_hotkey)

    def _do_register_hotkey(self):
        try:
            user32 = ctypes.windll.user32
            hwnd = int(self.winId())
            user32.UnregisterHotKey(hwnd, self.hotkey_id)
            self.hotkey_label = None
            for label, mods, vk in self.HOTKEY_CANDIDATES:
                if user32.RegisterHotKey(hwnd, self.hotkey_id, mods, vk):
                    self.hotkey_label = label
                    break
        except Exception:
            self.hotkey_label = None
        if not hasattr(self, "btn_through"):
            return
        if self.hotkey_label:
            self.btn_through.setToolTip("鼠标穿透，可点到底下的窗口（%s 恢复）" % self.hotkey_label)
        else:
            self.btn_through.setToolTip("鼠标穿透（全局热键都被占用，可从托盘菜单恢复）")

    def _on_hotkey(self, hid):
        if hid == 0xB001:
            self.toggle_click_through()
            if not self.settings["click_through"]:
                self._show_front()

    # ---------------- 透明度 / 绘制
    def paintEvent(self, e):
        alpha = int(self.settings["bg_alpha"] * 2.55)
        if alpha <= 0:
            # 关键：不能一点都不画。分层窗口里 alpha=0 的像素会让鼠标消息穿透到
            # 下层窗口（滚轮/点击都会落到浏览器或桌面上）。画一层 alpha=1 的底色
            # （1/255，肉眼看不出来）就能让窗口重新接住鼠标。
            alpha = 1
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        # 先把整块表面清成全透明：Source 模式是直接替换像素，而不是半透明叠加。
        # 不清的话，工具栏淡出后那一片会留下上一帧的“残影”。
        p.setCompositionMode(QPainter.CompositionMode_Source)
        p.fillRect(self.rect(), Qt.transparent)
        p.setCompositionMode(QPainter.CompositionMode_SourceOver)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(18, 18, 22, alpha))
        p.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 12, 12)

    # ---------------- 设置应用
    def _apply_text_style(self):
        """正文的字体与颜色（切书、切章后都要重新应用，避免被临时样式覆盖）"""
        self.view.setFont(self.font)
        self.view.setStyleSheet(
            "QTextBrowser{background:transparent;border:none;color:%s;}"
            "QTextBrowser{selection-background-color:rgba(96,160,255,0.45);}"
            % self.settings["text_color"])

    def _apply_settings_all(self):
        s = self.settings
        self.font = QFont(s["font_family"], 12)
        self.font.setPixelSize(int(s["font_size"]))
        self._apply_text_style()
        self.view.setViewportMargins(int(s["margin"]), 12, int(s["margin"]), 12)

        self._apply_shadow()

        # 注意：这里不动窗口 flags（重建窗口句柄会让穿透状态和全局热键失效），
        # 只同步按钮的勾选状态
        self._update_min_size()
        self._update_compact()
        self.btn_top.setChecked(bool(s["always_on_top"]))
        self.btn_through.setChecked(bool(s["click_through"]))
        if hasattr(self, "act_through"):
            self.act_through.setChecked(bool(s["click_through"]))

        self.cb_indent.blockSignals(True)
        self.cb_indent.setChecked(bool(s["indent"]))
        self.cb_indent.blockSignals(False)
        self.cb_shadow.blockSignals(True)
        self.cb_shadow.setChecked(bool(s["shadow"]))
        self.cb_shadow.blockSignals(False)

        self.cb_ui.blockSignals(True)
        self.cb_ui.setChecked(not bool(s["ui_visible"]))
        self.cb_ui.blockSignals(False)

        self.cb_auto.blockSignals(True)
        self.cb_auto.setChecked(bool(s["auto_hide_ui"]))
        self.cb_auto.blockSignals(False)
        self._auto_timer.start()          # 常驻计时（迷你条显隐也用它）

        for b, c in self.color_btns:
            if c.lower() == s["text_color"].lower():
                b.setStyleSheet("QPushButton{background:%s;border-radius:10px;"
                                "border:2px solid rgba(120,180,255,0.95);}" % c)
            else:
                b.setStyleSheet("QPushButton{background:%s;border-radius:10px;"
                                "border:1px solid rgba(255,255,255,0.25);}"
                                "QPushButton:hover{border:1px solid rgba(255,255,255,0.85);}" % c)

        self._set_ui_visible(bool(s["ui_visible"]))
        self.view.viewport().update()

    def _apply_text_format(self):
        """给正文应用行距、段首缩进、颜色"""
        s = self.settings
        doc = self.view.document()
        cur = QTextCursor(doc)
        cur.select(QTextCursor.Document)
        bf = QTextBlockFormat()
        bf.setLineHeight(int(s["line_height"] * 100), QTextBlockFormat.ProportionalHeight)
        if s["indent"]:
            fm = QFontMetrics(self.font)
            bf.setTextIndent(fm.horizontalAdvance("　　"))
        else:
            bf.setTextIndent(0)
        cur.mergeBlockFormat(bf)

    # ---------------- 设置项回调
    def _on_bg_alpha(self, v):
        self.settings["bg_alpha"] = int(v)
        self.update()
        if v == 0 and not self.settings["click_through"]:
            pass

    def _on_font_size(self, v):
        self.settings["font_size"] = int(v)
        self.font.setPixelSize(int(v))
        self.view.setFont(self.font)
        self._apply_text_format()

    def _on_line_height(self, v):
        self.settings["line_height"] = v / 100.0
        self._apply_text_format()

    def _on_margin(self, v):
        self.settings["margin"] = int(v)
        self.view.setViewportMargins(int(v), 12, int(v), 12)

    def _on_font_family(self, f):
        self.settings["font_family"] = f.family()
        self.font = QFont(f.family(), 12)
        self.font.setPixelSize(int(self.settings["font_size"]))
        self.view.setFont(self.font)
        self._apply_text_format()

    def _on_indent(self, on):
        self.settings["indent"] = bool(on)
        self._apply_text_format()

    def _on_shadow(self, on):
        self.settings["shadow"] = bool(on)
        self._apply_shadow()

    def _apply_shadow(self):
        """文字描边：贴着字形勾一圈与字色相反的边，
        浅色字配黑影、深色字配白边，这样白色网页和深色壁纸上都看得清。
        注意：效果对象只创建一次，之后只改属性/开关，
        反复 setGraphicsEffect 会让 Qt 反复删除旧对象，极易重复释放崩溃。"""
        if not hasattr(self, "_shadow_eff"):
            self._shadow_eff = QGraphicsDropShadowEffect()
            self._shadow_eff.setBlurRadius(3)
            self._shadow_eff.setOffset(0, 0)
            self.view.setGraphicsEffect(self._shadow_eff)
        if self.settings["shadow"]:
            c = QColor(self.settings["text_color"])
            lum = 0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue()
            outline = QColor(0, 0, 0, 250) if lum > 128 else QColor(255, 255, 255, 250)
            self._shadow_eff.setColor(outline)
            self._shadow_eff.setEnabled(True)
        else:
            self._shadow_eff.setEnabled(False)

    def _on_speed(self, v):
        self.settings["autoscroll_speed"] = int(v)

    def _set_text_color(self, color):
        self.settings["text_color"] = color
        self._apply_settings_all()

    def _pick_color(self):
        c = QColorDialog.getColor(QColor(self.settings["text_color"]), self, "选择文字颜色")
        if c.isValid():
            self._set_text_color(c.name())

    # 一键预设
    def _preset_plain(self):
        self.sl_bgalpha.setValue(0)
        self.settings["indent"] = True
        self._set_text_color("#EAEAF0")

    def _preset_readable(self):
        self.sl_bgalpha.setValue(16)
        self.settings["indent"] = True
        self._set_text_color("#EAEAF0")

    def _preset_dark(self):
        self.sl_bgalpha.setValue(0)
        self.settings["indent"] = True
        self._set_text_color("#202020")

    # ---------------- 面板显隐
    def _switch_tab(self, i):
        self.toc_stack.setCurrentIndex(i)
        self.btn_tab_chapters.setChecked(i == 0)
        self.btn_tab_books.setChecked(i == 1)
        if i == 1:
            self._refresh_books()

    def toggle_toc(self):
        if self.toc_panel.isVisible():
            self.toc_panel.hide()
        else:
            self.set_panel.hide()
            self._refresh_chapters()
            self.toc_panel.show()
            self.toc_panel.raise_()
            self._layout_panels()
            if getattr(self, "_compact", False):
                self.mini.hide()        # 小窗里面板几乎铺满，别让迷你条压住面板标题

    def toggle_settings(self):
        if self.set_panel.isVisible():
            self.set_panel.hide()
        else:
            self.toc_panel.hide()
            self.set_panel.show()
            self.set_panel.raise_()
            self._layout_panels()
            if getattr(self, "_compact", False):
                self.mini.hide()

    def _layout_panels(self):
        if not hasattr(self, "toc_panel"):
            return
        pad = 8
        pw = max(130, min(300, self.width() - pad * 2))
        sw = max(130, min(320, self.width() - pad * 2))
        ph = max(60, self.height() - pad * 2)
        self.toc_panel.setGeometry(self.width() - pw - pad, pad, pw, ph)
        self.set_panel.setGeometry(self.width() - sw - pad, pad, sw, ph)

    # ---------------- 窗口拖动 / 缩放
    def _edge_at(self, pos):
        m = 8                       # 抓取带宽一点，小窗口也好按到
        r = self.rect()
        left = pos.x() <= m
        right = pos.x() >= r.width() - m
        top = pos.y() <= m
        bottom = pos.y() >= r.height() - m
        if top and left:
            return "tl"
        if top and right:
            return "tr"
        if bottom and left:
            return "bl"
        if bottom and right:
            return "br"
        if left:
            return "l"
        if right:
            return "r"
        if top:
            return "t"
        if bottom:
            return "b"
        return None

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            edge = self._edge_at(e.pos())
            if edge:
                self._resize_edge = edge
                self._resize_origin = e.globalPos()
                self._resize_rect = self.geometry()
                e.accept()
                return
            self._drag_pos = e.globalPos() - self.frameGeometry().topLeft()
        super().mousePressEvent(e)

    def _apply_resize(self, gp):
        d = gp - self._resize_origin
        g = QRect(self._resize_rect)
        if "l" in self._resize_edge:
            g.setLeft(min(g.left() + d.x(), g.right() - self.minimumWidth()))
        if "r" in self._resize_edge:
            g.setRight(max(g.right() + d.x(), g.left() + self.minimumWidth()))
        if "t" in self._resize_edge:
            g.setTop(min(g.top() + d.y(), g.bottom() - self.minimumHeight()))
        if "b" in self._resize_edge:
            g.setBottom(max(g.bottom() + d.y(), g.top() + self.minimumHeight()))
        self.setGeometry(g)
        self._layout_panels()

    def mouseMoveEvent(self, e):
        if self._resize_edge:
            self._apply_resize(e.globalPos())
            return
        if self._drag_pos is not None and (e.buttons() & Qt.LeftButton):
            self.move(e.globalPos() - self._drag_pos)
            return
        edge = self._edge_at(e.pos())
        cursors = {"l": Qt.SizeHorCursor, "r": Qt.SizeHorCursor, "t": Qt.SizeVerCursor,
                   "b": Qt.SizeVerCursor, "tl": Qt.SizeFDiagCursor, "br": Qt.SizeFDiagCursor,
                   "tr": Qt.SizeBDiagCursor, "bl": Qt.SizeBDiagCursor}
        self.setCursor(cursors.get(edge, Qt.ArrowCursor))
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        self._drag_pos = None
        self._resize_edge = None
        self.setCursor(Qt.ArrowCursor)
        self._save_window_geometry()
        super().mouseReleaseEvent(e)

    def resizeEvent(self, e):
        if hasattr(self, "toc_panel"):
            self._layout_panels()
            self.mini.move((self.width() - self.mini.sizeHint().width()) // 2, 6)
            self.grip.move(self.width() - 26, self.height() - 26)
            if hasattr(self, "drop_hint"):
                self.drop_hint.setGeometry(0, 0, self.width(), self.height())
        super().resizeEvent(e)
        self._update_compact()

    # ---------------- 最小尺寸 / 矮窗模式
    def _update_min_size(self):
        """最小窗口 = 只放得下一行字（随字号、行距变化）"""
        fm = QFontMetricsF(self.font)
        self._line_h = max(12.0, fm.lineSpacing() * float(self.settings["line_height"]))
        pad = 10 + 10 + 12 + 12                     # 窗口内边距 + 正文上下留白
        h = int(pad + self._line_h + 8)
        self.setMinimumSize(150, max(56, h))

    def _update_compact(self):
        """窗口太矮时把上下工具栏整个让出来，否则两条栏光占位就吃掉正文"""
        if not hasattr(self, "top_box"):
            return
        line = getattr(self, "_line_h", 36.0)
        need = 38 + 40 + 20 + 24 + int(line * 2)    # 两条栏 + 内边距 + 两行字
        compact = self.height() < need
        if compact == getattr(self, "_compact", None):
            return
        self._compact = compact
        bars_on = (not compact) and bool(self.settings.get("ui_visible"))
        self.top_box.setVisible(bars_on)
        self.bot_box.setVisible(bars_on)
        if bars_on and hasattr(self, "mini") and self.mini.isVisible():
            self.mini.hide()         # 工具栏回来了就把迷你条撤掉

    # ---------------- 迷你条自动显隐 + 全窗滚轮
    def eventFilter(self, obj, ev):
        et = ev.type()
        cursors = {"l": Qt.SizeHorCursor, "r": Qt.SizeHorCursor, "t": Qt.SizeVerCursor,
                   "b": Qt.SizeVerCursor, "tl": Qt.SizeFDiagCursor, "br": Qt.SizeFDiagCursor,
                   "tr": Qt.SizeBDiagCursor, "bl": Qt.SizeBDiagCursor}
        # 贴边拖动缩放：正文/滚动条盖住了窗口边缘，子控件会先吃掉鼠标事件，
        # 所以在应用级过滤器里补一遍——小窗口只剩几条缝隙时也能拖大小
        if et in (QEvent.MouseButtonPress, QEvent.MouseMove, QEvent.MouseButtonRelease) \
                and isinstance(obj, QWidget) and obj is not self and self.isAncestorOf(obj):
            if et == QEvent.MouseButtonPress and ev.button() == Qt.LeftButton:
                gp = QCursorPos()
                edge = self._edge_at(self.mapFromGlobal(gp))
                if edge:
                    self._resize_edge = edge
                    self._resize_origin = gp
                    self._resize_rect = self.geometry()
                    return True
            elif et == QEvent.MouseMove:
                if self._resize_edge and (ev.buttons() & Qt.LeftButton):
                    self._apply_resize(ev.globalPos())
                    return True
                if not self._resize_edge:
                    edge = self._edge_at(self.mapFromGlobal(QCursorPos()))
                    shape = cursors.get(edge, Qt.IBeamCursor if obj is self.view else Qt.ArrowCursor)
                    if obj.cursor().shape() != shape:
                        obj.setCursor(shape)
            elif et == QEvent.MouseButtonRelease and self._resize_edge:
                self._resize_edge = None
                self.setCursor(Qt.ArrowCursor)
                self._save_window_geometry()
                return True
        if et == QEvent.MouseMove and (not self.settings["ui_visible"]
                                       or getattr(self, "_compact", False)):
            local = self.mapFromGlobal(QCursorPos())
            panels_open = self.toc_panel.isVisible() or self.set_panel.isVisible()
            if self.rect().contains(local) and not panels_open:
                if local.y() < 28 and not self.mini.isVisible():
                    self.mini.adjustSize()
                    self.mini.move((self.width() - self.mini.width()) // 2, 6)
                    self.mini.show()
                    self.mini.raise_()
                elif local.y() > 70 and self.mini.isVisible():
                    self.mini.hide()
        elif et == QEvent.Wheel:
            # 滚轮全部由自己接管：不管鼠标停在正文、工具栏还是空白处都能滚，
            # 不依赖 QTextBrowser 自己的滚轮实现（它在无边框透明窗口里会失灵）。
            w = obj if isinstance(obj, QWidget) else None
            if w is not None and (w is self or self.isAncestorOf(w)):
                # 面板可见且光标在面板里：滚轮一律用来滚面板（面板小到只剩几十像素时
                # 靠它才能翻到下面的选项），滑块用拖动或左右键调
                gp = ev.globalPos()
                ppos = self.mapFromGlobal(gp)
                delta = ev.angleDelta().y()
                if delta and self.set_panel.isVisible() \
                        and self.set_panel.geometry().contains(ppos):
                    sb2 = self.set_scroll.verticalScrollBar()
                    sb2.setValue(sb2.value() - self._wheel_px(delta, sb2))
                    return True
                if delta and self.toc_panel.isVisible() \
                        and self.toc_panel.geometry().contains(ppos):
                    lst = self.toc_list if self.toc_stack.currentIndex() == 0 else self.book_list
                    sbs = lst.verticalScrollBar()
                    sbs.setValue(sbs.value() - self._wheel_px(delta, sbs))
                    return True
                if isinstance(w, (QSlider, QListWidget, QComboBox, QScrollBar)):
                    return False                      # 这些控件自己要用滚轮
                ang = ev.angleDelta().y()
                if ang:
                    self._wheel_scroll(ang)
                else:
                    self._wheel_scroll(ev.pixelDelta().y(), pixel_units=True)
                return True
        return super().eventFilter(obj, ev)

    def _wheel_px(self, delta, sb):
        """把滚轮增量换成要滚动多少像素：一格 = 120；精调滚轮只给 1~30 的小步长时，
        按 1/4 格算，避免 int() 取整后变成 0（面板就一动不动）"""
        notch = delta / 120.0
        if abs(notch) < 0.25:
            notch = 0.25 if delta > 0 else -0.25
        base = max(30, sb.singleStep() * 3)
        return int(notch * base)

    def _wheel_scroll(self, delta, pixel_units=False):
        '''delta>0 向上滚，delta<0 向下滚；pixel_units=True 时 delta 已经是像素'''
        sb = self.view.verticalScrollBar()
        line = max(1, self.view.fontMetrics().lineSpacing())
        if pixel_units:
            step = max(1, abs(int(delta)))
        else:
            step = max(1, int(abs(delta) / 120.0 * line * 2.2))
        if delta < 0:
            if sb.value() >= sb.maximum() and self.book and \
                    self.idx < len(self.book.chapters) - 1:
                self._load_chapter(self.idx + 1)      # 到底了，滚轮继续往下就翻下一章
            elif sb.value() < sb.maximum():
                sb.setValue(min(sb.maximum(), sb.value() + step))
        elif delta > 0:
            if sb.value() <= sb.minimum() and self.book and self.idx > 0:
                self._load_chapter(self.idx - 1)
                QTimer.singleShot(60, lambda: sb.setValue(sb.maximum()))
            elif sb.value() > sb.minimum():
                sb.setValue(max(sb.minimum(), sb.value() - step))

    # ---------------- 保持置顶
    def _start_keep_on_top(self):
        """Tool 窗口容易被别的置顶窗口（比如浏览器/微信）压到底下，
        定期把最顶层重新顶一下，否则鼠标滚轮和点击都会落到别的窗口上"""
        if not self.settings.get("always_on_top"):
            return
        self._top_timer = QTimer(self)
        self._top_timer.timeout.connect(self._keep_on_top)
        self._top_timer.start(3000)

    def _keep_on_top(self):
        if not self.settings.get("always_on_top"):
            return
        try:
            u = ctypes.windll.user32
            HWND_TOPMOST = -1
            SWP_NOSIZE, SWP_NOMOVE, SWP_NOACTIVATE = 0x1, 0x2, 0x10
            u.SetWindowPos(int(self.winId()), HWND_TOPMOST, 0, 0, 0, 0,
                           SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE)
        except Exception:
            pass

    # ---------------- 导入 / 打开
    def import_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "导入小说", "", "文本文件 (*.txt *.md *.text);;所有文件 (*.*)")
        if not files:
            return
        self.load_files(files)

    def load_files(self, files):
        if not files:
            return
        # 统一成绝对路径，保证记忆的位置和书架条目长期有效
        files = [os.path.abspath(os.path.expanduser(f)) for f in files]
        # 多文件：按文件名顺序合并成一本，每个文件作为一段整体
        if len(files) == 1:
            path = files[0]
            text, enc = decode_text_file(path)
            if not text.strip():
                QMessageBox.warning(self, "读取失败", "这个文件里没有可读的文本内容。")
                return
            title = os.path.splitext(os.path.basename(path))[0]
            self.book = Book(title, self._merge_note(text, path, enc), path)
        else:
            parts = []
            for p in sorted(files, key=lambda s: os.path.basename(s)):
                t, _ = decode_text_file(p)
                parts.append("%s\n\n%s" % (os.path.splitext(os.path.basename(p))[0], t))
            title = os.path.basename(os.path.dirname(files[0])) or "合集"
            self.book = Book(title, "\n\n".join(parts), files[0])

        self._register_library()
        self.settings["last_book"] = self.book.path or ""
        self._save_settings()
        self.idx = 0
        prog = self.progress.get(self.book.key)
        if prog:
            self.idx = min(int(prog.get("chapter", 0)), len(self.book.chapters) - 1)
        self._load_chapter(self.idx, restore_scroll=prog.get("scroll") if prog else None)
        self.drop_hint.hide()
        self._refresh_books()
        self.view.setFocus()

    @staticmethod
    def _merge_note(text, path, enc):
        return text

    def reopen_last(self):
        """启动时自动接着上次：同一本书、同一章、同一滚动位置"""
        if self.book:
            return False
        path = (self.settings.get("last_book") or "").strip()
        if not path:
            return False
        if not os.path.exists(path):
            self.title_label.setText("上次的书找不到了：%s" % os.path.basename(path))
            return False
        try:
            self.load_files([path])
            return True
        except Exception:
            return False

    def _register_library(self):
        if not self.book:
            return
        entry = {"title": self.book.title, "path": self.book.path,
                 "chapters": len(self.book.chapters)}
        self.library = [b for b in self.library if b.get("path") != entry["path"] and
                        b.get("title") != entry["title"]]
        self.library.insert(0, entry)
        self.library = self.library[:30]
        save_json(LIBRARY_PATH, self.library)

    def _refresh_books(self):
        self.book_list.clear()
        if not self.library:
            self.book_empty.show()
            self.book_list.hide()
            return
        self.book_empty.hide()
        self.book_list.show()
        for b in self.library:
            item = QListWidgetItem("%s    {%d 章}" % (b.get("title", "?"), int(b.get("chapters", 0))))
            item.setData(Qt.UserRole, b)
            item.setToolTip(b.get("path", ""))
            self.book_list.addItem(item)

    def _book_clicked(self, item):
        b = item.data(Qt.UserRole)
        path = b.get("path")
        if path and os.path.exists(path):
            self.load_files([path])
        else:
            QMessageBox.information(self, "文件不存在", "找不到原文件，可能已被移动或删除：\n%s" % path)

    # ---------------- 章节加载
    def _load_chapter(self, idx, restore_scroll=None):
        if not self.book or not self.book.chapters:
            return
        idx = max(0, min(idx, len(self.book.chapters) - 1))
        self.idx = idx
        text = self.book.chapter_text(idx)
        self._apply_text_style()
        self.view.setPlainText(text)
        self._apply_text_format()
        self.view.verticalScrollBar().blockSignals(True)
        if restore_scroll:
            QTimer.singleShot(60, lambda v=int(restore_scroll): self._restore_scroll(v))
        else:
            self.view.verticalScrollBar().setValue(0)
        self.view.verticalScrollBar().blockSignals(False)

        title = self.book.chapters[idx]["title"]
        self.title_label.setText("%s · %s" % (self.book.title, title))
        self.title_label.setToolTip(title)
        self.pos_label.setText("%d / %d" % (idx + 1, len(self.book.chapters)))

        self.chapter_slider.blockSignals(True)
        self.chapter_slider.setRange(0, len(self.book.chapters) - 1)
        self.chapter_slider.setValue(idx)
        self.chapter_slider.blockSignals(False)

        self.btn_prev.setEnabled(idx > 0)
        self.btn_next.setEnabled(idx < len(self.book.chapters) - 1)
        if self.toc_list.count():
            self.toc_list.setCurrentRow(idx)
            self.toc_list.scrollToItem(self.toc_list.item(idx))
        self._save_progress()

    def _restore_scroll(self, value):
        sb = self.view.verticalScrollBar()
        sb.setValue(min(value, sb.maximum()))

    def _on_scroll(self, v):
        if not hasattr(self, "_save_timer"):
            self._save_timer = QTimer(self)
            self._save_timer.setSingleShot(True)
            self._save_timer.timeout.connect(self._save_progress)
        self._save_timer.start(1200)

    def _save_progress(self):
        if not self.book:
            return
        self.progress[self.book.key] = {
            "chapter": self.idx,
            "scroll": self.view.verticalScrollBar().value(),
            "title": self.book.title,
            "path": self.book.path,
        }
        keys = list(self.progress.keys())[-60:]
        self.progress = {k: self.progress[k] for k in keys}
        save_json(PROGRESS_PATH, self.progress)

    # ---------------- 章节切换
    def prev_chapter(self):
        if self.book and self.idx > 0:
            self._load_chapter(self.idx - 1)

    def next_chapter(self):
        if self.book and self.idx < len(self.book.chapters) - 1:
            self._load_chapter(self.idx + 1)

    def _slider_jump(self):
        if self.book:
            self._load_chapter(self.chapter_slider.value())

    def _slider_label(self, v):
        if self.book:
            self.pos_label.setText("%d / %d" % (v + 1, len(self.book.chapters)))

    def _refresh_chapters(self):
        self.toc_list.clear()
        if not self.book:
            self.toc_list.addItem(QListWidgetItem("（还没有打开书）"))
            return
        for i, c in enumerate(self.book.chapters):
            item = QListWidgetItem("%4d. %s" % (i + 1, c["title"]))
            item.setData(Qt.UserRole, i)
            self.toc_list.addItem(item)
        self.toc_list.setCurrentRow(self.idx)
        self._refresh_books()

    def _filter_chapters(self, kw):
        kw = kw.strip()
        for i in range(self.toc_list.count()):
            item = self.toc_list.item(i)
            idx = item.data(Qt.UserRole)
            txt = item.text()
            if not kw or kw in txt or (kw.isdigit() and idx is not None and
                                       str(idx + 1).startswith(kw)):
                item.setHidden(False)
            else:
                item.setHidden(True)

    def _toc_clicked(self, item):
        if item is None:
            return
        idx = item.data(Qt.UserRole)
        if idx is not None:
            self._load_chapter(int(idx))

    # ---------------- 自动滚动
    def toggle_autoscroll(self):
        self.autoscroll_on = not self.autoscroll_on
        self.btn_auto.setChecked(self.autoscroll_on)
        if self.autoscroll_on:
            if not hasattr(self, "scroll_timer"):
                self.scroll_timer = QTimer(self)
                self.scroll_timer.timeout.connect(self._auto_scroll_tick)
            self.scroll_timer.start(40)
        else:
            if hasattr(self, "scroll_timer"):
                self.scroll_timer.stop()

    def _auto_scroll_tick(self):
        sb = self.view.verticalScrollBar()
        if sb.value() >= sb.maximum() - 1:
            if self.book and self.idx < len(self.book.chapters) - 1:
                self._load_chapter(self.idx + 1)
                self.view.verticalScrollBar().setValue(0)
            else:
                self.toggle_autoscroll()
            return
        sb.setValue(sb.value() + int(self.settings["autoscroll_speed"]))

    # ---------------- 穿透 / 置顶
    def toggle_click_through(self, checked=None):
        if checked is None:
            checked = not self.settings["click_through"]
        self.settings["click_through"] = bool(checked)
        self.btn_through.setChecked(bool(checked))
        if hasattr(self, "act_through"):
            self.act_through.setChecked(bool(checked))
        self._apply_click_through(bool(checked))
        self._save_settings()

    def _apply_click_through(self, on):
        try:
            user32 = ctypes.windll.user32
            hwnd = int(self.winId())
            GWL_EXSTYLE = -20
            WS_EX_TRANSPARENT = 0x00000020
            WS_EX_LAYERED = 0x00080000
            style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            if on:
                style |= (WS_EX_LAYERED | WS_EX_TRANSPARENT)
            else:
                style &= ~WS_EX_TRANSPARENT
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
            # 让新样式立刻生效（不移动、不改尺寸、不改层级）
            SWP_NOSIZE, SWP_NOMOVE, SWP_NOZORDER, SWP_FRAMECHANGED = 0x1, 0x2, 0x4, 0x20
            user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0,
                                SWP_NOSIZE | SWP_NOMOVE | SWP_NOZORDER | SWP_FRAMECHANGED)
        except Exception:
            pass

    def toggle_on_top(self, checked=None):
        if checked is None:
            checked = not self.settings["always_on_top"]
        self.settings["always_on_top"] = bool(checked)
        self.btn_top.setChecked(bool(checked))
        flags = self.windowFlags()
        if checked:
            flags |= Qt.WindowStaysOnTopHint
        else:
            flags &= ~Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.show()
        # flags 变化会重建窗口句柄：穿透样式与全局热键都要重新挂上
        self._apply_click_through(bool(self.settings["click_through"]))
        QTimer.singleShot(120, self._do_register_hotkey)
        if checked:
            self._start_keep_on_top()
        elif hasattr(self, "_top_timer"):
            self._top_timer.stop()
        self._save_settings()

    # ---------------- 鼠标移开自动隐藏工具栏
    def _setup_auto_hide(self):
        self._bar_eff_top = QGraphicsOpacityEffect(self.topbar)
        self._bar_eff_bot = QGraphicsOpacityEffect(self.bottombar)
        self._bar_eff_top.setOpacity(1.0)
        self._bar_eff_bot.setOpacity(1.0)
        self.topbar.setGraphicsEffect(self._bar_eff_top)
        self.bottombar.setGraphicsEffect(self._bar_eff_bot)
        self._bar_anim_top = QPropertyAnimation(self._bar_eff_top, b"opacity", self)
        self._bar_anim_bot = QPropertyAnimation(self._bar_eff_bot, b"opacity", self)
        self._bar_anim_top.finished.connect(
            lambda: self._fade_done(self.topbar, self._bar_eff_top))
        self._bar_anim_bot.finished.connect(
            lambda: self._fade_done(self.bottombar, self._bar_eff_bot))
        self._bars_hidden = False
        self._outside_ticks = 0
        self._auto_timer = QTimer(self)
        self._auto_timer.setInterval(250)
        self._auto_timer.timeout.connect(self._auto_hide_tick)
        self._auto_timer.start()      # 常驻计时：小窗迷你条、自动隐藏都靠它

    def _fade_done(self, wid, eff):
        """淡到全透明后把控件真正藏起来（只留透明像素会残影，必须 hide）"""
        if eff.opacity() <= 0.01:
            wid.hide()
            self.repaint()            # 整窗重绘一次，避免分层窗口在工具栏区域留下残影

    def _bars_soft(self, visible, animate=True):
        """淡入淡出工具栏；容器占位不变，所以正文不重排、阅读位置不跳"""
        if not hasattr(self, "_bar_eff_top"):
            return
        self._bars_hidden = not visible
        pairs = ((self._bar_eff_top, self._bar_anim_top, self.topbar),
                 (self._bar_eff_bot, self._bar_anim_bot, self.bottombar))
        for eff, anim, wid in pairs:
            anim.stop()
            target = 1.0 if visible else 0.0
            if not wid.isVisible():
                wid.show()
            wid.setAttribute(Qt.WA_TransparentForMouseEvents, not visible)
            if animate:
                anim.setDuration(160)
                anim.setStartValue(eff.opacity())
                anim.setEndValue(target)
                anim.start()
            else:
                eff.setOpacity(target)
                if not visible:
                    wid.hide()

    def _auto_hide_tick(self, pos=None):
        gp = QCursorPos() if pos is None else pos
        local = self.mapFromGlobal(gp)
        inside = self.rect().contains(local)
        # 矮窗（紧凑）模式：两条工具栏已整个让位，改用浮出的迷你条（≡ Aa － ✕）
        if getattr(self, "_compact", False):
            panels_open = (hasattr(self, "toc_panel") and
                           (self.toc_panel.isVisible() or self.set_panel.isVisible()))
            if inside and local.y() < 30 and not panels_open:
                if not self.mini.isVisible():
                    self.mini.adjustSize()      # 按内容撑开，免得按钮文字被压扁
                    self.mini.move((self.width() - self.mini.width()) // 2, 6)
                    self.mini.show()
                    self.mini.raise_()
            elif (not inside or local.y() > self.height() - 30 or panels_open) \
                    and self.mini.isVisible():
                self.mini.hide()
        if not self.settings.get("auto_hide_ui"):
            return
        if not self.settings.get("ui_visible"):        # 沉浸模式本来就没工具栏
            return
        if getattr(self, "_compact", False):           # 紧凑模式工具栏不参与布局
            return
        if self.settings.get("click_through"):
            return
        if self._drag_pos is not None or self._resize_edge:
            return
        panels_open = (hasattr(self, "toc_panel") and
                       (self.toc_panel.isVisible() or self.set_panel.isVisible()))
        if panels_open:
            self._outside_ticks = 0
            if self._bars_hidden:
                self._bars_soft(True)
            return
        if not self.isVisible() or self.isMinimized():
            return
        if inside:
            self._outside_ticks = 0
            if self._bars_hidden:
                self._bars_soft(True)
        else:
            self._outside_ticks += 1
            if self._outside_ticks >= 3 and not self._bars_hidden:
                self._bars_soft(False)

    def _on_auto_hide_switch(self, on):
        self.settings["auto_hide_ui"] = bool(on)
        if not on:
            self._bars_soft(True, animate=False)
        self._save_settings()

    def enterEvent(self, e):
        if self.settings.get("auto_hide_ui") and getattr(self, "_bars_hidden", False):
            self._outside_ticks = 0
            self._bars_soft(True)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._outside_ticks = 0
        super().leaveEvent(e)

    # ---------------- 沉浸模式（隐藏上下工具栏）
    def _on_ui_switch(self, hidden):
        self._set_ui_visible(not hidden, save=True)
        if hidden:
            self.mini.show()
            self.mini.raise_()

    def _set_ui_visible(self, on, save=False):
        self.settings["ui_visible"] = bool(on)
        bars_on = bool(on) and not getattr(self, "_compact", False)
        self.top_box.setVisible(bars_on)
        self.bot_box.setVisible(bars_on)
        if on:
            self.topbar.show()
            self.bottombar.show()
            self._bars_soft(True, animate=False)      # 从沉浸模式回来时恢复不透明度
        if hasattr(self, "cb_ui"):
            self.cb_ui.blockSignals(True)
            self.cb_ui.setChecked(not bool(on))
            self.cb_ui.blockSignals(False)
        if on:
            self.mini.hide()
        if save:
            self._save_settings()

    def toggle_ui(self):
        self._set_ui_visible(not self.settings["ui_visible"], save=True)
        if not self.settings["ui_visible"]:
            self.mini.show()
            self.mini.raise_()

    # ---------------- 右键菜单
    def _view_menu(self, pos):
        menu = QMenu(self)
        a1 = menu.addAction("上一章")
        a2 = menu.addAction("下一章")
        menu.addSeparator()
        a3 = menu.addAction("目录")
        a4 = menu.addAction("设置")
        a5 = menu.addAction("自动滚动")
        a5.setCheckable(True)
        a5.setChecked(self.autoscroll_on)
        menu.addSeparator()
        a6 = menu.addAction("隐藏工具栏")
        a6b = menu.addAction("鼠标移开自动隐藏工具栏")
        a6b.setCheckable(True)
        a6b.setChecked(bool(self.settings.get("auto_hide_ui")))
        a7 = menu.addAction("导入其他小说")
        menu.addSeparator()
        a8 = menu.addAction("退出")
        act = menu.exec_(self.view.mapToGlobal(pos))
        if act == a1:
            self.prev_chapter()
        elif act == a2:
            self.next_chapter()
        elif act == a3:
            self.toggle_toc()
        elif act == a4:
            self.toggle_settings()
        elif act == a5:
            self.toggle_autoscroll()
        elif act == a6:
            self.toggle_ui()
        elif act == a6b:
            on = not bool(self.settings.get("auto_hide_ui"))
            self.cb_auto.blockSignals(True)
            self.cb_auto.setChecked(on)
            self.cb_auto.blockSignals(False)
            self._on_auto_hide_switch(on)
        elif act == a7:
            self.import_files()
        elif act == a8:
            self.close()

    # ---------------- 拖拽导入
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            for u in e.mimeData().urls():
                if u.toLocalFile().lower().endswith((".txt", ".md", ".text")):
                    e.acceptProposedAction()
                    return
        e.ignore()

    def dropEvent(self, e):
        files = [u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()]
        files = [f for f in files if f.lower().endswith((".txt", ".md", ".text"))]
        if files:
            self.load_files(files)

    # ---------------- 键盘快捷键
    # Alt+H / F3 / F4 / Ctrl+O / 章节翻页 / 穿透 用 QShortcut，焦点在正文里也能响应；
    # 空格和 Esc 留在 keyPressEvent，避免抢掉搜索框里的空格输入。
    def _setup_shortcuts(self):
        for seq, slot in (
            ("Alt+H", self.toggle_ui),
            ("F3", self.toggle_toc),
            ("F4", self.toggle_settings),
            ("Ctrl+O", self.import_files),
            ("Alt+Left", self.prev_chapter),
            ("Alt+Right", self.next_chapter),
            ("Alt+T", self.toggle_click_through),
        ):
            sc = QShortcut(QKeySequence(seq), self)
            sc.setContext(Qt.WindowShortcut)
            sc.activated.connect(slot)

    def keyPressEvent(self, e):
        key = e.key()
        mod = e.modifiers()
        if key == Qt.Key_Space and not mod:
            self.toggle_autoscroll()
            return
        if key == Qt.Key_Escape:
            if self.settings["click_through"]:
                self.toggle_click_through(False)
            else:
                self.toc_panel.hide()
                self.set_panel.hide()
            return
        super().keyPressEvent(e)

    # ---------------- 欢迎页
    def _show_welcome(self):
        self.view.setPlainText(
            "\n\n\n\n透明小说阅读器\n\n"
            "· 点顶部「导入」或按 Ctrl+O 选择 .txt 小说，也可以直接把文件拖进窗口\n"
            "· 导入一次就够了：下次打开会自动接着上次那本书、上次看到的章节和位置\n"
            "· 打开后在「目录」里切换章节，进度会自动记住；换书请在「目录」→「书架」里点\n"
            "· 在「设置」里把背景拖到 0% 就只剩文字浮在桌面上，字号、字体、行距、颜色都能调\n"
            "· 需要一边看小说一边操作其他软件时，开「穿透」（或按热键），再按一次即可恢复\n"
            "· 按 Alt+H 隐藏工具栏，只留正文；勾选「鼠标移开自动隐藏工具栏」后，鼠标离开窗口工具栏就消失，移回来又出现\n"
            "· 在白色页面上看不清？按 F4 打开设置，点预设「深色字」；深色壁纸上就用默认的浅色字\n"
        )
        self._apply_text_format()
        welcome_font = QFont(self.font)          # 复制一份，别把正文用的字体对象改小
        welcome_font.setPixelSize(14)
        self.view.setFont(welcome_font)
        self.view.setStyleSheet("QTextBrowser{background:transparent;border:none;color:#8E96A4;}")
        self.drop_hint.show()
        self.drop_hint.raise_()

    # ---------------- 状态保存
    def _save_window_geometry(self):
        g = self.geometry()
        self.settings["window"] = [g.x(), g.y(), g.width(), g.height()]

    def _save_settings(self):
        self._save_window_geometry()
        save_json(SETTINGS_PATH, self.settings)

    def _restore_geometry(self):
        g = self.settings.get("window") or DEFAULT_SETTINGS["window"]
        try:
            x, y, w, h = [int(v) for v in g]
        except Exception:
            x, y, w, h = 0, 0, 560, 800
        screen = QApplication.primaryScreen().availableGeometry()
        w = max(self.minimumWidth(), min(w, screen.width()))
        h = max(self.minimumHeight(), min(h, screen.height()))
        if x == 0 and y == 0:
            x = screen.right() - w - 60
            y = screen.top() + 80
        x = max(screen.left(), min(x, screen.right() - w))
        y = max(screen.top(), min(y, screen.bottom() - h))
        self.setGeometry(x, y, w, h)

    def _save_all(self):
        self._save_progress()
        self._save_settings()

    def closeEvent(self, e):
        self._save_all()
        try:
            ctypes.windll.user32.UnregisterHotKey(int(self.winId()), self.hotkey_id)
        except Exception:
            pass
        try:
            self.tray.hide()
        except Exception:
            pass
        e.accept()
        QApplication.quit()


def QCursorPos():
    from PyQt5.QtGui import QCursor
    return QCursor.pos()


def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    QApplication.setStyle("Fusion")
    _setup_crash_log()

    def _hook(etype, value, tb):
        import traceback
        try:
            with open(CRASH_PATH, "a", encoding="utf-8") as f:
                f.write("\n===== 未捕获异常 =====\n")
                traceback.print_exception(etype, value, tb, file=f)
        except Exception:
            pass

    sys.excepthook = _hook

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setQuitOnLastWindowClosed(True)
    ensure_data_dir()

    w = ReaderWindow()
    w.show()

    # 命令行传参：可直接拖到 exe 图标上打开
    args = [a for a in sys.argv[1:] if os.path.exists(a)]
    if args:
        QTimer.singleShot(100, lambda: w.load_files(args))
    else:
        # 没带文件就自动接着上次读的那本，回到上次的章节和位置
        QTimer.singleShot(260, w.reopen_last)

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
