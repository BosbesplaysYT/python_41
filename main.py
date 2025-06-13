# main.py
import sys, os, json, subprocess, re, traceback, shutil
import markdown
from PIL import Image
from PIL.ImageQt import ImageQt
from PyQt6.QtGui import QColor, QFont, QPalette, QTextCharFormat, QTextCursor, QTextDocument, QFileSystemModel, QAction, QIcon, QPainter, QPixmap, QShortcut, QKeySequence
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QSplitter, QTabWidget, QPlainTextEdit,
    QTreeView, QDockWidget, QLineEdit, QPushButton, QListWidget,
    QTextEdit, QLabel, QVBoxLayout, QHBoxLayout, QMessageBox,
    QFileDialog, QInputDialog, QMenu, QAbstractItemView, QStackedWidget,
    QCheckBox, QListWidgetItem, QHeaderView, QDialog
)
from PyQt6.QtCore import Qt, QTimer, QPoint, QSize, QRect, QThread, pyqtSignal, QStandardPaths, QUrl
from PyQt6.QtWebEngineWidgets import QWebEngineView
from your_splash_module import NexusSplash
from config import is_first_launch, mark_launched

# ────── Utility: Theme Manager ────────────────────────────────────────────────
def load_theme(path):
    """
    Load a JSON theme from `path`. If the file is missing or invalid,
    fall back to the default Fusion palette and no extra formats.
    """
    try:
        with open(path, 'r') as f:
            cfg = json.load(f)
        palette = QPalette()
        for role, col in cfg.get("palette", {}).items():
            # map JSON key to QPalette.ColorRole
            palette.setColor(
                getattr(QPalette.ColorRole, role),
                QColor(col)
            )
        formats = cfg.get("formats", {})
    except (FileNotFoundError, json.JSONDecodeError, AttributeError) as e:
        # fallback
        print(f"⚠️  Warning: could not load theme '{path}': {e}")
        palette = QApplication.instance().style().standardPalette()
        formats = {}
    return palette, formats

dark_stylesheet = """
/* GENERAL */
QWidget {
    background-color: #2d2d2d;
    color: #f0f0f0;
    font-size: 14px;
}

/* QPushButton */
QPushButton {
    background-color: #3a3a3a;
    color: #ffffff;
    border: 1px solid #5a5a5a;
    padding: 6px 12px;
    border-radius: 4px;
}
QPushButton:hover {
    background-color: #505050;
}
QPushButton:pressed {
    background-color: #606060;
}
QPushButton:disabled {
    background-color: #2d2d2d;
    color: #888888;
}

/* QLineEdit, QTextEdit */
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #1e1e1e;
    color: #f0f0f0;
    border: 1px solid #5a5a5a;
    border-radius: 3px;
    padding: 4px;
}
QLineEdit:disabled {
    color: #888888;
}

/* QLabel */
QLabel {
    color: #e0e0e0;
}

/* QCheckBox, QRadioButton */
QCheckBox, QRadioButton {
    color: #e0e0e0;
    spacing: 6px;
}
QCheckBox::indicator, QRadioButton::indicator {
    width: 16px;
    height: 16px;
}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {
    background-color: #5a5a5a;
    border: 1px solid #888888;
}

/* QComboBox */
QComboBox {
    background-color: #3a3a3a;
    color: #ffffff;
    border: 1px solid #5a5a5a;
    padding: 4px;
}
QComboBox QAbstractItemView {
    background-color: #2d2d2d;
    color: #f0f0f0;
    selection-background-color: #505050;
    border: 1px solid #5a5a5a;
}

/* QTabWidget */
QTabWidget::pane {
    border: 1px solid #444444;
}
QTabBar::tab {
    background-color: #3a3a3a;
    border: 1px solid #5a5a5a;
    padding: 6px;
}
QTabBar::tab:selected {
    background-color: #505050;
}

/* QScrollBar */
QScrollBar:vertical, QScrollBar:horizontal {
    background-color: #2d2d2d;
    border: none;
    width: 10px;
    height: 10px;
    margin: 0px;
}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
    background-color: #5a5a5a;
    min-height: 20px;
    min-width: 20px;
}
QScrollBar::add-line, QScrollBar::sub-line {
    background: none;
}
QScrollBar::add-page, QScrollBar::sub-page {
    background: none;
}

/* QProgressBar */
QProgressBar {
    border: 1px solid #5a5a5a;
    text-align: center;
    background-color: #1e1e1e;
    color: #ffffff;
}
QProgressBar::chunk {
    background-color: #5a5a5a;
}

/* QTableView, QListView, QTreeView */
QTableView, QListView, QTreeView {
    background-color: #1e1e1e;
    color: #f0f0f0;
    gridline-color: #444444;
    selection-background-color: #505050;
    selection-color: #ffffff;
}
QHeaderView::section {
    background-color: #3a3a3a;
    color: #f0f0f0;
    border: 1px solid #444444;
    padding: 4px;
}
"""

light_stylesheet = """
QWidget {
    background-color: #f2f2f2;
    color: #2d2d2d;
    font-size: 14px;
}

/* QPushButton */
QPushButton {
    background-color: #e0e0e0;
    color: #000000;
    border: 1px solid #a0a0a0;
    padding: 6px 12px;
    border-radius: 4px;
}
QPushButton:hover {
    background-color: #d0d0d0;
}
QPushButton:pressed {
    background-color: #c0c0c0;
}
QPushButton:disabled {
    background-color: #f2f2f2;
    color: #888888;
}

/* QLineEdit, QTextEdit */
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #ffffff;
    color: #2d2d2d;
    border: 1px solid #a0a0a0;
    border-radius: 3px;
    padding: 4px;
}

/* QLabel */
QLabel {
    color: #2d2d2d;
}

/* QCheckBox, QRadioButton */
QCheckBox, QRadioButton {
    color: #2d2d2d;
    spacing: 6px;
}
QCheckBox::indicator, QRadioButton::indicator {
    width: 16px;
    height: 16px;
}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {
    background-color: #a0a0a0;
    border: 1px solid #888888;
}

/* QComboBox */
QComboBox {
    background-color: #e0e0e0;
    color: #000000;
    border: 1px solid #a0a0a0;
    padding: 4px;
}
QComboBox QAbstractItemView {
    background-color: #f2f2f2;
    color: #2d2d2d;
    selection-background-color: #d0d0d0;
    border: 1px solid #a0a0a0;
}

/* QTabWidget */
QTabWidget::pane {
    border: 1px solid #cccccc;
}
QTabBar::tab {
    background-color: #e0e0e0;
    border: 1px solid #b0b0b0;
    padding: 6px;
}
QTabBar::tab:selected {
    background-color: #d0d0d0;
}

/* QScrollBar */
QScrollBar:vertical, QScrollBar:horizontal {
    background-color: #f2f2f2;
    border: none;
    width: 10px;
    height: 10px;
    margin: 0px;
}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
    background-color: #b0b0b0;
    min-height: 20px;
    min-width: 20px;
}

/* QProgressBar */
QProgressBar {
    border: 1px solid #a0a0a0;
    text-align: center;
    background-color: #ffffff;
    color: #000000;
}
QProgressBar::chunk {
    background-color: #a0a0a0;
}

/* QTableView, QListView, QTreeView */
QTableView, QListView, QTreeView {
    background-color: #ffffff;
    color: #2d2d2d;
    gridline-color: #cccccc;
    selection-background-color: #d0d0d0;
    selection-color: #000000;
}
QHeaderView::section {
    background-color: #e0e0e0;
    color: #2d2d2d;
    border: 1px solid #b0b0b0;
    padding: 4px;
}
"""

class QuickOpenDialog(QDialog):
    def __init__(self, open_callback, parent=None):
        super().__init__(parent, flags=Qt.WindowType.FramelessWindowHint)
        self.setModal(True)
        self.open_callback = open_callback

        # ── Build UI ────────────────────────────────────────────────────────
        lay = QVBoxLayout(self)
        lay.setContentsMargins(5, 5, 5, 5)

        self.input = QLineEdit(self)
        self.input.setPlaceholderText("Type to search files… (Esc to close)")
        lay.addWidget(self.input)

        self.list = QListWidget(self)
        lay.addWidget(self.list)

        # ── Signals ────────────────────────────────────────────────────────
        self.input.textChanged.connect(self.on_filter)
        self.list.itemActivated.connect(lambda item: self.open_and_close(item.text()))

        # placeholder; will be refreshed on show
        self.root = ""
        self.files = []

    def refresh_file_list(self):
        """Read current project_dir from parent and re-walk the tree."""
        parent = self.parent()
        if not parent or not hasattr(parent, "project_dir"):
            return

        self.root = parent.project_dir
        self.files = []
        for dirpath, _, filenames in os.walk(self.root):
            for fname in filenames:
                rel = os.path.relpath(os.path.join(dirpath, fname), self.root)
                self.files.append(rel)

    def showEvent(self, ev):
        """Before showing, update file list and reposition & resize."""
        parent = self.parent()
        if parent:
            # 1) refresh to new project_dir
            self.refresh_file_list()

            # 2) resize to 60% of parent width
            target_w = int(parent.width() * 0.6)
            self.setFixedWidth(target_w)

            # 3) center horizontally, 20px from top
            geo = parent.geometry()
            x = geo.x() + (geo.width() - self.width()) // 2
            y = geo.y() + 20
            self.move(x, y)

        super().showEvent(ev)
        self.input.clear()
        self.list.clear()
        self.input.setFocus()

    def on_filter(self, text: str):
        """Filter file list by substring, show up to 50 results."""
        self.list.clear()
        if not text:
            return
        lower = text.lower()
        count = 0
        for f in self.files:
            if lower in f.lower():
                self.list.addItem(QListWidgetItem(f))
                count += 1
                if count >= 50:
                    break
        if self.list.count():
            self.list.setCurrentRow(0)

    def open_and_close(self, relpath: str):
        """Open selected file and close dialog."""
        full = os.path.join(self.root, relpath)
        self.open_callback(full)
        self.close()

    def keyPressEvent(self, ev):
        # Esc to close, Down to go into list
        if ev.key() == Qt.Key.Key_Escape:
            self.close()
        elif ev.key() == Qt.Key.Key_Down:
            self.list.setFocus()
        else:
            super().keyPressEvent(ev)

class SearchWorker(QThread):
    # file path, line number, line text
    result_found = pyqtSignal(str, int, str)
    search_done  = pyqtSignal()

    def __init__(self, root, pattern, opts, parent=None):
        super().__init__(parent)
        self.root, self.pattern, self.opts = root, pattern, opts

    def run(self):
        # build regex
        pat = self.pattern
        flags = 0 if self.opts['case'] else re.IGNORECASE
        if not self.opts['regex']:
            pat = re.escape(pat)
        if self.opts['whole']:
            pat = r'\b' + pat + r'\b'
        regex = re.compile(pat, flags)

        include = self.opts['include']
        exclude = self.opts['exclude']

        for dirpath, _, files in os.walk(self.root):
            for fn in files:
                ext = os.path.splitext(fn)[1]
                # Check include patterns
                if include:
                    matched = False
                    for pat in include:
                        if pat.startswith('.') and ext == pat:
                            matched = True
                            break
                        if not pat.startswith('.') and fn == pat:
                            matched = True
                            break
                    if not matched:
                        continue
                # Check exclude patterns
                skip = False
                for pat in exclude:
                    if pat.startswith('.') and ext == pat:
                        skip = True
                        break
                    if not pat.startswith('.') and fn == pat:
                        skip = True
                        break
                if skip:
                    continue

                full = os.path.join(dirpath, fn)
                try:
                    with open(full, 'r', encoding='utf-8') as f:
                        for i, line in enumerate(f, start=1):
                            if regex.search(line):
                                self.result_found.emit(full, i, line.rstrip())
                except Exception:
                    continue
        self.search_done.emit()

# ────── Plugin API Stub ─────────────────────────────────────────────────────
class PluginInterface:
    def __init__(self, main_win): self.main = main_win
    def activate(self): pass
    def deactivate(self): pass

def load_plugins(main_win):
    plugins = []
    plug_dir = os.path.join(os.path.dirname(__file__), "plugins")
    if not os.path.isdir(plug_dir): return plugins
    sys.path.insert(0, plug_dir)
    for fn in os.listdir(plug_dir):
        if fn.endswith(".py"):
            name = fn[:-3]
            try:
                mod = __import__(name)
                if hasattr(mod, "Plugin"):
                    p = mod.Plugin(main_win)
                    p.activate()
                    plugins.append(p)
            except Exception:
                traceback.print_exc()
    return plugins

class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.code_editor = editor

    def sizeHint(self):
        return QSize(self.code_editor.lineNumberAreaWidth(), 0)

    def paintEvent(self, event):
        self.code_editor.lineNumberAreaPaintEvent(event)

# ────── Code Editor with line numbers, bracket match & minimap stub ─────────
class CodeEditor(QPlainTextEdit):
    def __init__(self):
        super().__init__()
        self.lineNumberArea = LineNumberArea(self)  # ✅ Moved this line to the top
        # after creating lineNumberArea:
        self.blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.updateRequest.connect(self.updateLineNumberArea)
        # ensure we have the right margin from the start:
        self.updateLineNumberAreaWidth(0)

        self.setFont(QFont("Fira Code", 12))
        self.cursorPositionChanged.connect(self.match_brackets)
        # Simplified minimap placeholder: will just draw a grey bar
        self.minimap = QWidget(self)
        self.minimap.setFixedWidth(80)
        self.minimap.setStyleSheet("background-color: rgba(200,200,200,0.1);")
        self.update_viewport_margins()

    def lineNumberAreaWidth(self):
        # enough space for the number of digits in the block count
        digits = len(str(max(1, self.blockCount())))
        # padding: 3px + digit_width*d + extra
        space = self.fontMetrics().horizontalAdvance("9") * digits + 12
        return space

    def updateLineNumberAreaWidth(self, _):
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)

    def updateLineNumberArea(self, rect, dy):
        if dy:
            self.lineNumberArea.scroll(0, dy)
        else:
            self.lineNumberArea.update(0, rect.y(), self.lineNumberArea.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.updateLineNumberAreaWidth(0)

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        cr = self.contentsRect()
        self.lineNumberArea.setGeometry(
            QRect(cr.left(), cr.top(), self.lineNumberAreaWidth(), cr.height())
        )

    def lineNumberAreaPaintEvent(self, event):
        painter = QPainter(self.lineNumberArea)
        painter.fillRect(event.rect(), QColor("#2e3440"))   # dark gutter
        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(QColor("#4c566a"))
                x = self.lineNumberArea.width() - self.fontMetrics().horizontalAdvance(number) - 6
                painter.drawText(x, top, self.fontMetrics().horizontalAdvance(number), self.fontMetrics().height(),
                                 Qt.AlignmentFlag.AlignRight, number)
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1
        painter.end()

    def update_viewport_margins(self):
        left = self.lineNumberAreaWidth()
        right = 80  # your minimap
        self.setViewportMargins(left, 0, right, 0)

    def match_brackets(self):
        tc = self.textCursor()
        pos = tc.position()
        text = self.toPlainText()
        pairs = {'(':')','[':']','{':'}'}
        # find on left
        left = text[pos-1] if pos-1 < len(text) and pos>0 else ''
        right = text[pos] if pos < len(text) else ''
        match_pos = None
        if left in pairs:
            # naive forward scan
            stack=1
            for i in range(pos, len(text)):
                if text[i]==left: stack+=1
                if text[i]==pairs[left]:
                    stack-=1
                    if stack==0: match_pos=i; break
        elif right in pairs.values():
            inv = {v:k for k,v in pairs.items()}
            stack=1
            for i in range(pos-2, -1, -1):
                if text[i]==right: stack+=1
                if text[i]==inv[right]:
                    stack-=1
                    if stack==0: match_pos=i; break
        # highlight both
        extra=[]
        fmt = QTextCharFormat()
        fmt.setBackground(QColor("#3b4252"))
        for p in (pos-1, match_pos or -1):
            if p and p>=0:
                sel = QTextEdit.ExtraSelection()
                tc2 = self.textCursor()
                tc2.setPosition(p)
                tc2.movePosition(QTextCursor.MoveOperation.NextCharacter, QTextCursor.MoveMode.KeepAnchor)
                sel.cursor=tc2; sel.format=fmt
                extra.append(sel)
        self.setExtraSelections(extra)

# ────── Editor Area with Tabs & Splits ────────────────────────────────────────
class EditorArea(QWidget):
    def __init__(self):
        super().__init__()
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_primary_tab)

        # secondary tabs for the split pane (created on first split)
        self.secondary_tabs = None
        
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.addWidget(self.tabs)
        lay = QVBoxLayout(self)
        lay.addWidget(self.splitter)

    def new_tab(self, path=None):
        if path:
            ext = os.path.splitext(path)[1].lower()
            
            # Handle images
            if ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico']:
                return self._open_image_tab(path)
                
            # Handle HTML
            elif ext in ['.html', '.htm']:
                return self._open_html_tab(path)
                
            # Handle Markdown
            elif ext == '.md':
                return self._open_markdown_tab(path)
        
        # Default to text editor
        return self._open_text_tab(path)

    def _open_text_tab(self, path):
        ed = CodeEditor()
        ed.file_path = path
        ed.document().modificationChanged.connect(
            lambda modified, ed=ed: self._mark_unsaved(ed, modified)
        )

        if path:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except UnicodeDecodeError:
                with open(path, 'r', encoding='latin-1', errors='replace') as f:
                    content = f.read()
            ed.setPlainText(content)
        
        idx = self.tabs.addTab(ed, os.path.basename(path) if path else "Untitled")
        self.tabs.setCurrentIndex(idx)
        ed.document().setModified(False)
        return ed

    def _open_image_tab(self, path):
        try:
            # Load image using PIL to handle all formats including .ico
            img = Image.open(path)
            qimg = ImageQt(img).copy()
            pixmap = QPixmap.fromImage(qimg)
            
            # Create display widget
            container = QWidget()
            layout = QVBoxLayout(container)
            label = QLabel()
            label.setPixmap(pixmap)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(label)

            container.file_path = path
            
            # Add to tab
            idx = self.tabs.addTab(container, os.path.basename(path))
            self.tabs.setCurrentIndex(idx)
            return container
        except Exception as e:
            QMessageBox.warning(self, "Image Error", f"Could not open image: {e}")
            return self._open_text_tab(path)

    def _open_html_tab(self, path):
        # Create splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: Code editor
        editor = CodeEditor()
        editor.file_path = path
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        editor.setPlainText(content)
        editor.document().setModified(False)

        # Right: Web view preview
        webview = QWebEngineView()
        # load with correct base URL so <img src="..."> works
        base = QUrl.fromLocalFile(path)
        webview.setHtml(content, base)

        # Connect editor to update preview live
        editor.textChanged.connect(
            lambda: webview.setHtml(editor.toPlainText(), base)
        )

        splitter.addWidget(editor)
        splitter.addWidget(webview)
        splitter.setSizes([300, 300])

        # attach attributes for state + reload-on-save
        splitter.file_path = path
        splitter.editor   = editor
        splitter.webview  = webview

        idx = self.tabs.addTab(splitter, os.path.basename(path))
        self.tabs.setCurrentIndex(idx)
        return splitter


    def _open_markdown_tab(self, path):
        splitter = QSplitter(Qt.Orientation.Horizontal)

        editor = CodeEditor()
        editor.file_path = path
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            md = f.read()
        editor.setPlainText(md)
        editor.document().setModified(False)

        preview = QTextEdit()
        preview.setReadOnly(True)
        preview.setHtml(markdown.markdown(md))

        editor.textChanged.connect(
            lambda: self.update_markdown_preview(editor, preview)
        )

        # sync scrolling
        sb_ed = editor.verticalScrollBar()
        sb_md = preview.verticalScrollBar()
        sb_ed.valueChanged.connect(sb_md.setValue)
        sb_md.valueChanged.connect(sb_ed.setValue)

        splitter.addWidget(editor)
        splitter.addWidget(preview)
        splitter.setSizes([300, 300])

        splitter.file_path = path
        splitter.editor   = editor
        splitter.preview  = preview

        idx = self.tabs.addTab(splitter, os.path.basename(path))
        self.tabs.setCurrentIndex(idx)
        return splitter


    def update_markdown_preview(self, editor, preview):
        source_md = editor.toPlainText()
        html = markdown.markdown(source_md)
        preview.setHtml(html)

    def _mark_unsaved(self, ed, modified):
        """Add or remove the white-dot indicator in the tab text."""
        idx = self.tabs.indexOf(ed)
        if idx < 0:
            return
        text = self.tabs.tabText(idx)
        dot = " ●"
        if modified:
            if not text.endswith(dot):
                self.tabs.setTabText(idx, text + dot)
        else:
            if text.endswith(dot):
                self.tabs.setTabText(idx, text[:-len(dot)])

    def close_primary_tab(self, index):
        self.tabs.removeTab(index)
        # if you want to automatically collapse the split when both are gone:
        if self.tabs.count() == 0 and self.secondary_tabs:
            self.splitter.widget(1).deleteLater()
            self.secondary_tabs = None

    def close_secondary_tab(self, index):
        if not self.secondary_tabs:
            return
        self.secondary_tabs.removeTab(index)
        if self.secondary_tabs.count() == 0:
            self.splitter.widget(1).deleteLater()
            self.secondary_tabs = None

    def split_current(self):
        ed = self.current_editor()
        if not ed:
            return
        # first-time: create the secondary QTabWidget
        if not self.secondary_tabs:
            self.secondary_tabs = QTabWidget()
            self.secondary_tabs.setTabsClosable(True)
            self.secondary_tabs.tabCloseRequested.connect(self.close_secondary_tab)
            self.splitter.addWidget(self.secondary_tabs)

        # clone the editor into the split pane
        ed2 = CodeEditor()
        ed2.file_path = ed.file_path
        ed2.setPlainText(ed.toPlainText())
        ed2.document().setModified(ed.document().isModified())
        # copy your signals if you need them (bracket‐match, etc.)
        idx = self.secondary_tabs.addTab(ed2, self.tabs.tabText(self.tabs.currentIndex()))
        self.secondary_tabs.setCurrentIndex(idx)

    def current_editor(self):
        return self.tabs.currentWidget()

class ProjectSidebar(QWidget):
    def __init__(self, root):
        super().__init__()
        self.root = root

        # ── Toolbar ─────────────────────────────────────────────────────────
        tb = QHBoxLayout()
        new_file_btn = QPushButton()
        new_file_btn.setIcon(QIcon("icons/icon-file.png"))
        new_file_btn.setToolTip("New File")
        new_file_btn.clicked.connect(lambda: self.create_item(self.root, is_folder=False))
        tb.addWidget(new_file_btn)

        new_folder_btn = QPushButton()
        new_folder_btn.setIcon(QIcon("icons/icon-folder.png"))
        new_folder_btn.setToolTip("New Folder")
        new_folder_btn.clicked.connect(lambda: self.create_item(self.root, is_folder=True))
        tb.addWidget(new_folder_btn)
        tb.addStretch()

        # ── File Tree ───────────────────────────────────────────────────────
        self.tree = QTreeView()
        self.model = QFileSystemModel()
        self.model.setReadOnly(False)
        self.model.setRootPath(self.root)
        self.tree.setModel(self.model)
        self.tree.hideColumn(1)
        self.tree.hideColumn(2)
        self.tree.hideColumn(3)

        # make the “Name” column take up all available space
        hdr = self.tree.header()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tree.setRootIndex(self.model.index(self.root))

        # enable drag & drop
        self.tree.setDragEnabled(True)
        self.tree.setAcceptDrops(True)
        self.tree.setDropIndicatorShown(True)
        self.tree.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.tree.setDefaultDropAction(Qt.DropAction.MoveAction)

        # disable built-in editing (we’ll handle inline creates only)
        self.tree.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        # signals
        self.tree.doubleClicked.connect(self.open_file)
        self.tree.customContextMenuRequested.connect(self.on_context_menu)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        # ── Layout ──────────────────────────────────────────────────────────
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0,0,0,0)
        lay.addLayout(tb)
        lay.addWidget(self.tree)

    def open_file(self, idx):
        path = self.model.filePath(idx)
        if os.path.isfile(path):
            main_win = self.window()
            main_win.editor_area.new_tab(path)

    def on_context_menu(self, point: QPoint):
        idx = self.tree.indexAt(point)
        if idx.isValid():
            path = self.model.filePath(idx)
            is_dir = self.model.isDir(idx)
        else:
            path = self.root
            is_dir = True

        menu = QMenu(self)
        menu.addAction("New File",   lambda: self.create_item(path, False))
        menu.addAction("New Folder", lambda: self.create_item(path, True))
        if idx.isValid():
            menu.addSeparator()
            menu.addAction("Rename", lambda: self.rename_item(idx))
            menu.addAction("Delete", lambda: self.delete_item(path, is_dir))
        menu.exec(self.tree.mapToGlobal(point))

    def create_item(self, base_path: str, is_folder: bool):
        # inline-create an untitled, then start rename
        name = "untitled_folder" if is_folder else "untitled"
        new_path = os.path.join(base_path, name)
        i = 1
        while os.path.exists(new_path):
            new_path = os.path.join(base_path, f"{name}_{i}")
            i += 1

        try:
            if is_folder:
                os.makedirs(new_path)
            else:
                with open(new_path, 'x', encoding='utf-8'):
                    pass
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not create item:\n{e}")
            return

        self.refresh()
        idx = self.model.index(new_path)
        if idx.isValid():
            self.tree.scrollTo(idx)
            self.tree.setCurrentIndex(idx)
            self.tree.edit(idx)  # inline rename

    def rename_item(self, idx):
        old_path = self.model.filePath(idx)
        old_name = os.path.basename(old_path)
        new_name, ok = QInputDialog.getText(self, "Rename", "New name:", text=old_name)
        if not ok or not new_name or new_name == old_name:
            return
        new_path = os.path.join(os.path.dirname(old_path), new_name)
        try:
            os.rename(old_path, new_path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not rename:\n{e}")
            return
        self.refresh()

    def delete_item(self, path: str, is_dir: bool):
        resp = QMessageBox.question(
            self, "Delete",
            f"Are you sure you want to delete:\n{path}?",
            QMessageBox.StandardButton.Yes, QMessageBox.StandardButton.No
        )
        if resp != QMessageBox.StandardButton.Yes:
            return
        try:
            if is_dir:
                shutil.rmtree(path)
            else:
                os.remove(path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not delete:\n{e}")
            return
        self.refresh()

    def refresh(self):
        # refresh entire tree
        self.model.setRootPath(self.root)
        self.tree.setRootIndex(self.model.index(self.root))

    def dragMoveEvent(self, event):
        event.accept()  # allow moving anywhere

    def dropEvent(self, event):
        # gather source paths
        urls = event.mimeData().urls()
        src_paths = [u.toLocalFile() for u in urls if u.isLocalFile()]
        if not src_paths:
            return

        # find drop target
        pos = event.position().toPoint()
        idx = self.tree.indexAt(pos)
        if idx.isValid() and self.model.isDir(idx):
            dest_dir = self.model.filePath(idx)
        elif idx.isValid() and not self.model.isDir(idx):
            # dropped onto a file: make a new folder alongside it
            target_file = self.model.filePath(idx)
            base = os.path.dirname(target_file)
            folder_name, ok = QInputDialog.getText(
                self, "New Folder", "Folder name for grouped files:"
            )
            if not ok or not folder_name:
                return
            dest_dir = os.path.join(base, folder_name)
            try:
                os.makedirs(dest_dir, exist_ok=False)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not create folder:\n{e}")
                return
            # move the target file in
            shutil.move(target_file, os.path.join(dest_dir, os.path.basename(target_file)))
        else:
            # dropped onto blank area → project root
            dest_dir = self.root

        # move all sources
        for src in src_paths:
            try:
                shutil.move(src, os.path.join(dest_dir, os.path.basename(src)))
            except Exception as e:
                QMessageBox.warning(self, "Warning", f"Could not move {src}:\n{e}")

        self.refresh()
        event.accept()

# ────── Find & Replace Dock ──────────────────────────────────────────────────
class SearchDock(QDockWidget):
    def __init__(self, parent):
        super().__init__("Search & Replace", parent)
        self.parent = parent

        # State for replace iteration
        self.matches = []           # list of (file, line, start, length)
        self.current_index = 0
        self.last_tab = None

        # — UI Setup —
        w = QWidget(); lay = QVBoxLayout(w)

        # 1) Replace-mode toggle (no separate Replace button)
        self.replace_mode = QPushButton("Replace Mode OFF", checkable=True)
        self.replace_mode.toggled.connect(self.on_toggle_replace)
        lay.addWidget(self.replace_mode)

        # 2) Search & Replace inputs
        self.find = QLineEdit(); self.find.setPlaceholderText("Search pattern")
        self.rep  = QLineEdit(); self.rep.setPlaceholderText("Replacement text")
        self.rep.setEnabled(False)
        # pressing Enter in rep field triggers one replace
        self.rep.returnPressed.connect(self.replace_next)
        lay.addWidget(self.find)
        lay.addWidget(self.rep)

        # 3) Options
        opts = QHBoxLayout()
        self.use_regex      = QCheckBox("Regex")
        self.case_sensitive = QCheckBox("Case-sensitive")
        self.whole_word     = QCheckBox("Whole word")
        opts.addWidget(self.use_regex)
        opts.addWidget(self.case_sensitive)
        opts.addWidget(self.whole_word)
        lay.addLayout(opts)

        # 4) File filters
        filt = QHBoxLayout()
        self.include_ext = QLineEdit(); self.include_ext.setPlaceholderText("Include: .py,utils.py")
        self.exclude_ext = QLineEdit(); self.exclude_ext.setPlaceholderText("Exclude: .min.js,README.md")
        filt.addWidget(self.include_ext)
        filt.addWidget(self.exclude_ext)
        lay.addLayout(filt)

        # 5) Search button
        btn = QPushButton("Search")
        btn.clicked.connect(self.start_search)
        lay.addWidget(btn)

        # 6) Results list
        self.results = QListWidget()
        self.results.itemActivated.connect(self.open_result)
        lay.addWidget(self.results)

        self.setWidget(w)

    def on_toggle_replace(self, on):
        # enable the rep input when in replace mode
        self.rep.setEnabled(on)
        self.replace_mode.setText("Replace Mode ON" if on else "Replace Mode OFF")
        # reset iteration state
        self.matches = []
        self.current_index = 0
        if on:
            # build a fresh list of matches from results
            self._build_match_list()

    def _build_match_list(self):
        """Turn each QListWidgetItem into a precise (file,line,start,len) tuple."""
        pat = self.find.text()
        flags = 0 if self.case_sensitive.isChecked() else re.IGNORECASE
        if not self.use_regex.isChecked():
            pat = re.escape(pat)
        if self.whole_word.isChecked():
            pat = r'\b' + pat + r'\b'
        regex = re.compile(pat, flags)

        self.matches = []
        for idx in range(self.results.count()):
            it = self.results.item(idx)
            file, line = it.data
            # get the exact text of that line
            with open(file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            text = lines[line-1]
            m = regex.search(text)
            if m:
                self.matches.append((file, line, m.start(), m.end() - m.start()))

    def start_search(self):
        self.results.clear()
        self.matches = []
        self.current_index = 0

        opts = {
            'regex':   self.use_regex.isChecked(),
            'case':    self.case_sensitive.isChecked(),
            'whole':   self.whole_word.isChecked(),
            'include': [e.strip() for e in self.include_ext.text().split(',') if e.strip()],
            'exclude': [e.strip() for e in self.exclude_ext.text().split(',') if e.strip()],
        }
        root = self.parent.project_dir
        pattern = self.find.text().strip()
        if not pattern:
            return

        self.worker = SearchWorker(root, pattern, opts)
        self.worker.result_found.connect(self.add_result)
        self.worker.start()

    def add_result(self, file, line, snippet):
        item = QListWidgetItem(f"{os.path.relpath(file)}:{line}: {snippet}")
        item.data = (file, line)
        self.results.addItem(item)

    def open_result(self, item):
        # behaves like a normal “click result” during search mode
        file, line = item.data
        ed = self.parent.editor_area.new_tab(file)
        tc = ed.textCursor()
        block = ed.document().findBlockByLineNumber(line-1)
        tc.setPosition(block.position())
        ed.setTextCursor(tc)

    def replace_next(self):
        if not self.replace_mode.isChecked() or self.current_index >= len(self.matches):
            return  # nothing to do

        file, line, start, length = self.matches[self.current_index]

        # 1) close previous tab
        if self.last_tab is not None:
            self.parent.editor_area.tabs.removeTab(self.last_tab)
            self.last_tab = None

        # 2) open this file
        ed = self.parent.editor_area.new_tab(file)
        self.last_tab = self.parent.editor_area.tabs.currentIndex()

        # 3) move cursor & select
        tc = ed.textCursor()
        block = ed.document().findBlockByLineNumber(line-1)
        tc.setPosition(block.position() + start)
        tc.movePosition(QTextCursor.MoveOperation.Right,
                        QTextCursor.MoveMode.KeepAnchor,
                        length)
        ed.setTextCursor(tc)

        # 4) perform replacement
        tc.insertText(self.rep.text())

        # 5) save file immediately
        mw = self.parent
        mw.editor_area.tabs.setCurrentIndex(self.last_tab)
        mw.save_file()

        self.current_index += 1

        # 6) if done, turn off replace mode
        if self.current_index >= len(self.matches):
            QMessageBox.information(self, "Done", "All replacements complete.")
            self.replace_mode.setChecked(False)

# ────── Git Status Dock ──────────────────────────────────────────────────────
class GitDock(QDockWidget):
    def __init__(self, parent, repo):
        super().__init__("Git Status", parent)
        self.repo = repo
        w = QWidget()
        lay = QVBoxLayout(w)

        self.lst = QListWidget()
        self.lst.itemDoubleClicked.connect(self.show_diff)
        lay.addWidget(self.lst)

        btn = QPushButton("Refresh")
        btn.clicked.connect(self.refresh)
        lay.addWidget(btn)

        self.setWidget(w)
        self.refresh()

    def refresh(self):
        self.lst.clear()
        try:
            out = subprocess.check_output(
                ["git", "-C", self.repo, "status", "--porcelain"],
                stderr=subprocess.STDOUT
            ).decode().splitlines()
            if not out:
                self.lst.addItem("(clean — no changes)")
            else:
                self.lst.addItems(out)
        except subprocess.CalledProcessError as e:
            # non-zero exit (e.g. not a git repo)
            self.lst.addItem(f"⚠️  Git error: {e.output.decode().strip() or e}")
        except FileNotFoundError:
            # git not installed
            self.lst.addItem("⚠️  `git` not found on PATH")

    def show_diff(self, item):
        text = item.text()
        if text.startswith("⚠️"):
            return  # no diff for errors
        fn = text[3:]
        try:
            diff = subprocess.check_output(
                ["git", "-C", self.repo, "diff", fn],
                stderr=subprocess.STDOUT
            ).decode()
        except subprocess.CalledProcessError as e:
            diff = f"Error running git diff: {e.output.decode().strip()}"
        dlg = QMessageBox(self)
        dlg.setWindowTitle("Git Diff")
        dlg.setText(diff or "(no diff)")
        dlg.exec()

# ────── Terminal Pane ───────────────────────────────────────────────────────
class TerminalDock(QDockWidget):
    def __init__(self, parent):
        super().__init__("Terminal", parent)
        w = QWidget()
        lay = QVBoxLayout(w)

        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.input = QLineEdit()
        self.input.setPlaceholderText("Enter command and press Enter")
        self.input.returnPressed.connect(self.run_command)

        lay.addWidget(self.output)
        lay.addWidget(self.input)
        self.setWidget(w)

    def run_command(self):
        cmd = self.input.text().strip()
        if not cmd:
            return
        # echo prompt
        self.output.appendPlainText(f"$ {cmd}")
        try:
            proc = subprocess.Popen(
                cmd, shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            out, _ = proc.communicate()
            self.output.appendPlainText(out)
        except Exception as e:
            self.output.appendPlainText(f"Error running command: {e}")
        self.input.clear()
        # scroll to bottom
        sb = self.output.verticalScrollBar()
        sb.setValue(sb.maximum())

# ────── Main Window ──────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Nexus Editor 2.0")
        # ─── keep track of the current project directory ───────────────────────
        self.project_dir = os.getcwd()

        self.dark_mode_enabled = True  # default to dark mode
        self.apply_theme()
        # load theme
        pal, fmts = load_theme("themes/dracula.json")
        QApplication.instance().setPalette(pal)
        # ─── welcome screen ────────────────────────────────────────────────
        welcome = QWidget()
        wl = QVBoxLayout(welcome)
        wl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title = QLabel("Welcome to Nexus Editor")
        subtitle = QLabel("Open a folder or create a new file to get started")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        subtitle.setStyleSheet("font-size: 14px; color: gray;")
        wl.addWidget(title)
        wl.addWidget(subtitle)
        # match background to app
        welcome.setAutoFillBackground(True)
        bg = self.palette().color(QPalette.ColorRole.Window)
        p = welcome.palette()
        p.setColor(welcome.backgroundRole(), bg)
        welcome.setPalette(p)
        # central editor area
        self.editor_area = EditorArea()
        # ─── central stack ──────────────────────────────────────────────────
        self.central_stack = QStackedWidget()
        self.central_stack.addWidget(welcome)          # index 0
        self.central_stack.addWidget(self.editor_area) # index 1
        self.setCentralWidget(self.central_stack)
        self.central_stack.setCurrentIndex(0)  # start on welcome
        # docks
        # ─── Project sidebar uses self.project_dir ────────────────────────────
        # ─── docks (project, find, git, term) ─────────────────────────
        self.project_sidebar = ProjectSidebar(self.project_dir)
        proj_dock = QDockWidget("Project", self)
        proj_dock.setWidget(self.project_sidebar)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, proj_dock)

        self.search_dock = SearchDock(self)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.search_dock)

        self.git_dock  = GitDock(self, self.project_dir)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.git_dock)

        self.term_dock = TerminalDock(self)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.term_dock)

        # ─── hook tab changes for welcome/editor switch ────────────────────
        tabs = self.editor_area.tabs
        tabs.currentChanged.connect(lambda i: self.central_stack.setCurrentIndex(1))
        tabs.tabCloseRequested.connect(lambda _: QTimer.singleShot(0, self._check_tabs))

        # ─── load plugins, but skip initial new_tab ────────────────────────
        self.plugins = load_plugins(self)
        # no self.editor_area.new_tab() here

        # ─── File menu: Save, Open Folder … ──────────────────────────────
        file_menu = self.menuBar().addMenu("&File")
        save_act = QAction("&Save", self)
        save_act.setShortcut("Ctrl+S")
        save_act.triggered.connect(self.save_file)
        file_menu.addAction(save_act)

        open_folder_act = QAction("Open &Folder...", self)
        open_folder_act.setShortcut("Ctrl+K")
        open_folder_act.triggered.connect(self.open_folder)
        file_menu.addAction(open_folder_act)

        # ─── View Menu: Split, Toggle Theme ─────────────────────────────
        view_menu = self.menuBar().addMenu("&View")

        split_act = QAction("Split &Editor", self)
        split_act.setShortcut("Ctrl+\\")
        split_act.triggered.connect(self.editor_area.split_current)
        view_menu.addAction(split_act)

        # 👇 Add theme toggle action here
        toggle_theme_act = QAction("Toggle &Theme", self)
        toggle_theme_act.setShortcut("Ctrl+T")
        toggle_theme_act.triggered.connect(self.toggle_theme)
        view_menu.addAction(toggle_theme_act)

        # … inside MainWindow.__init__(), after you set up project_dir …
        self.quick_open = QuickOpenDialog(
            open_callback=lambda path: self.editor_area.new_tab(path),
            parent=self
        )
        QShortcut(QKeySequence("Ctrl+P"), self).activated.connect(self.quick_open.show)


        # ─── Session state paths ──────────────────────────────────────────
        self.state_path = os.path.join(
            QStandardPaths.writableLocation(QStandardPaths.StandardLocation.ConfigLocation),
            "nexus_state.json"
        )
        os.makedirs(os.path.dirname(self.state_path), exist_ok=True)

        # ─── Now restore last session ────────────────────────────────────
        self.load_state()

    def apply_theme(self):
        if self.dark_mode_enabled:
            self.setStyleSheet(dark_stylesheet)
        else:
            self.setStyleSheet(light_stylesheet)

    def toggle_theme(self):
        self.dark_mode_enabled = not self.dark_mode_enabled
        self.apply_theme()

    def load_state(self):
        """Restore last project folder, open tabs, and window geometry."""
        try:
            with open(self.state_path, 'r', encoding='utf-8') as f:
                state = json.load(f)
        except Exception:
            return  # nothing to restore

        proj = state.get("project_dir")
        tabs = state.get("open_tabs", [])
        win_size = state.get("window_size")
        win_pos = state.get("window_pos")

        if proj and os.path.isdir(proj):
            # change directory & update UI
            os.chdir(proj)
            self.project_dir = proj
            self.setWindowTitle(f"Nexus Editor 2.0 — {os.path.basename(proj)}")
            model = self.project_sidebar.model
            model.setRootPath(proj)
            self.project_sidebar.tree.setRootIndex(model.index(proj))

        # open each file
        for path in tabs:
            # ignore if missing
            if os.path.isfile(path):
                self.editor_area.new_tab(path)

        # restore window size and position if available
        if win_size and isinstance(win_size, list) and len(win_size) == 2:
            self.resize(win_size[0], win_size[1])
        if win_pos and isinstance(win_pos, list) and len(win_pos) == 2:
            self.move(win_pos[0], win_pos[1])

    def save_state(self):
        """Save current project folder + list of open tabs + window size."""
        tabs = []
        # primary
        for i in range(self.editor_area.tabs.count()):
            ed = self.editor_area.tabs.widget(i)
            p = getattr(ed, "file_path", None)
            if p:
                tabs.append(p)
        # secondary (if split exists)
        st = self.editor_area.secondary_tabs
        if st:
            for i in range(st.count()):
                ed = st.widget(i)
                p = getattr(ed, "file_path", None)
                if p:
                    tabs.append(p)

        state = {
            "project_dir": self.project_dir,
            "open_tabs": tabs,
            "window_size": [self.size().width(), self.size().height()],
            "window_pos": [self.pos().x(), self.pos().y()]
        }
        try:
            with open(self.state_path, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"⚠️  Could not save state: {e}")


    # ────── helper to show welcome if no tabs ─────────────────────────────
    def _check_tabs(self):
        if self.editor_area.tabs.count() == 0:
            self.central_stack.setCurrentIndex(0)

    # ─── Slot: Open a new project directory ────────────────────────────────
    def open_folder(self):
        # ── Clear existing open tabs ─────────────────
        # primary tabs
        self.editor_area.tabs.clear()
        # secondary split (if exists)
        if self.editor_area.secondary_tabs:
            self.splitter.widget(1).deleteLater()
            self.editor_area.secondary_tabs = None
        # reset welcome screen if desired
        self._check_tabs()
        folder = QFileDialog.getExistingDirectory(
            self,
            "Open Project Folder",
            self.project_dir
        )
        if not folder:
            return

        # Change working directory and remember it
        os.chdir(folder)
        self.project_dir = folder
        self.setWindowTitle(f"Nexus Editor 2.0 — {os.path.basename(folder)}")

        # Update project tree
        model = self.project_sidebar.model            # ← no ()
        model.setRootPath(folder)
        self.project_sidebar.tree.setRootIndex(
            model.index(folder)
        )

        # Update Git dock and refresh
        self.git_dock.repo = folder
        self.git_dock.refresh()


    def autosave_all(self):
        for i in range(self.editor_area.tabs.count()):
            ed = self.editor_area.tabs.widget(i)
            fn = self.editor_area.tabs.tabText(i)
            # ensure .autosave extension
            autosave_fn = f"{fn}.autosave"
            path = os.path.join(self.autosave_dir, autosave_fn)
            try:
                # write in UTF-8 so you can encode any character
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(ed.toPlainText())
            except Exception as e:
                print(f"⚠️  Failed to autosave '{fn}': {e}")
    
    def save_file(self):
        # 1) Figure out which widget is active, and extract the CodeEditor if needed
        current = self.editor_area.current_editor()
        # if we’re in an HTML/MD split, pull out the inner editor
        if hasattr(current, "editor") and isinstance(current.editor, QPlainTextEdit):
            ed = current.editor
        else:
            ed = current  # normal CodeEditor

        path = getattr(ed, "file_path", None)
        if not path:
            path, _ = QFileDialog.getSaveFileName(
                self, "Save File As", self.project_dir, "All Files (*)"
            )
            if not path:
                return
            ed.file_path = path
            idx = self.editor_area.tabs.currentIndex()
            self.editor_area.tabs.setTabText(idx, os.path.basename(path))

        # 2) Now safe to open/write
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(ed.toPlainText())
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Could not save file:\n{e}")
            return

        # 3) Clear modified flag on this editor
        ed.document().setModified(False)

        # 4) Reload any other open tabs on the same path
        def reload_ed(other):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except:
                return
            tc = other.textCursor()
            pos = tc.position()
            other.blockSignals(True)
            other.setPlainText(content)
            other.blockSignals(False)
            other.document().setModified(False)
            tc.setPosition(min(pos, len(content)))
            other.setTextCursor(tc)

        # primary tabs
        for i in range(self.editor_area.tabs.count()):
            w = self.editor_area.tabs.widget(i)
            # get its editor if it’s a splitter, else w itself
            target = w.editor if hasattr(w, "editor") else w
            if getattr(target, "file_path", None) == path and target is not ed:
                reload_ed(target)

        # secondary (split) tabs
        st = self.editor_area.secondary_tabs
        if st:
            for i in range(st.count()):
                w = st.widget(i)
                target = w.editor if hasattr(w, "editor") else w
                if getattr(target, "file_path", None) == path and target is not ed:
                    reload_ed(target)

        # 5) Update any live-preview panes
        from PyQt6.QtCore import QUrl
        import markdown
        def refresh_container(w):
            if getattr(w, "file_path", None) != path:
                return
            # HTML
            if hasattr(w, "webview") and hasattr(w, "editor"):
                base = QUrl.fromLocalFile(path)
                w.webview.setHtml(w.editor.toPlainText(), base)
            # Markdown
            elif hasattr(w, "preview") and hasattr(w, "editor"):
                w.preview.setHtml(markdown.markdown(w.editor.toPlainText()))

        for i in range(self.editor_area.tabs.count()):
            refresh_container(self.editor_area.tabs.widget(i))
        if st:
            for i in range(st.count()):
                refresh_container(st.widget(i))



    def closeEvent(self, ev):
        # Save state before closing
        self.save_state()
        super().closeEvent(ev)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(dark_stylesheet)
    app.setWindowIcon(QIcon(":/nexus_icon.ico"))

    def launch_main_window():
        w = MainWindow()
        w.showMaximized()
        w.show()

    if is_first_launch():
        # Show splash on first launch, then go straight to the main window
        splash = NexusSplash(next_step_callback=launch_main_window)
        splash.show()
        mark_launched()
    else:
        # On subsequent launches, skip the splash/onboarding entirely
        launch_main_window()

    sys.exit(app.exec())

if __name__ == '__main__':
    main()