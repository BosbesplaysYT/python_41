# main.py
import sys, os, json, subprocess, tempfile, traceback, shutil
import markdown

from PyQt6.QtGui import QColor, QFont, QPalette, QTextCharFormat, QTextCursor, QTextDocument, QFileSystemModel, QAction, QIcon
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QSplitter, QTabWidget, QPlainTextEdit,
    QTreeView, QDockWidget, QLineEdit, QPushButton, QListWidget,
    QTextEdit, QLabel, QVBoxLayout, QHBoxLayout, QMessageBox,
    QFileDialog, QInputDialog, QMenu, QAbstractItemView, QStackedWidget
)
from PyQt6.QtCore import Qt, QTimer, QPoint


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

# ────── Code Editor with line numbers, bracket match & minimap stub ─────────
class CodeEditor(QPlainTextEdit):
    def __init__(self):
        super().__init__()
        self.setFont(QFont("Fira Code", 12))
        self.cursorPositionChanged.connect(self.match_brackets)
        # Simplified minimap placeholder: will just draw a grey bar
        self.minimap = QWidget(self)
        self.minimap.setFixedWidth(80)
        self.minimap.setStyleSheet("background-color: rgba(200,200,200,0.1);")
        self.update_viewport_margins()
    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        h = self.viewport().height()
        self.minimap.setGeometry(self.viewport().width()-80, 0, 80, h)
    def update_viewport_margins(self):
        self.setViewportMargins(0,0,80,0)
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
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.addWidget(self.tabs)
        lay = QVBoxLayout(self)
        lay.addWidget(self.splitter)

    def new_tab(self, path=None):
        ed = CodeEditor()
        ed.file_path = path
        # connect modification tracking
        ed.document().modificationChanged.connect(
            lambda modified, ed=ed: self._mark_unsaved(ed, modified)
        )

        if path:
            # your existing load logic (UTF-8 / fallback)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except UnicodeDecodeError:
                with open(path, 'r', encoding='latin-1', errors='replace') as f:
                    content = f.read()
            ed.setPlainText(content)
        idx = self.tabs.addTab(ed, os.path.basename(path) if path else "Untitled")
        self.tabs.setCurrentIndex(idx)

        # clear the “modified” flag after loading
        ed.document().setModified(False)
        return ed

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

    def close_tab(self, i):
        self.tabs.removeTab(i)

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
class FindReplaceDock(QDockWidget):
    def __init__(self, parent):
        super().__init__("Find / Replace", parent)
        w=QWidget(); lay=QVBoxLayout(w)
        self.find = QLineEdit(); self.find.setPlaceholderText("Find (regex)")
        self.rep  = QLineEdit(); self.rep.setPlaceholderText("Replace")
        b1=QPushButton("Find Next"); b2=QPushButton("Replace")
        b1.clicked.connect(self.find_next); b2.clicked.connect(self.replace_one)
        for x in (self.find, self.rep, b1, b2): lay.addWidget(x)
        self.setWidget(w)
    def find_next(self):
        ed = self.parent().editor_area.current_editor()
        flag = QTextDocument.FindFlag(0)
        ed.find(self.find.text(), flag)
    def replace_one(self):
        ed = self.parent().editor_area.current_editor()
        tc=ed.textCursor()
        if tc.hasSelection():
            tc.insertText(self.rep.text())

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

# ────── Markdown Preview Dock ───────────────────────────────────────────────
class MarkdownDock(QDockWidget):
    def __init__(self, parent):
        super().__init__("Markdown Preview", parent)
        self.viewer = QTextEdit()
        self.viewer.setReadOnly(True)
        self.setWidget(self.viewer)

    def set_editor(self, editor):
        # two-way scroll sync
        sb_ed = editor.verticalScrollBar()
        sb_md = self.viewer.verticalScrollBar()
        sb_ed.valueChanged.connect(sb_md.setValue)
        sb_md.valueChanged.connect(sb_ed.setValue)
        # update on text change
        editor.textChanged.connect(lambda: self.update(editor.toPlainText()))

    def update(self, source_md: str):
        html = markdown.markdown(source_md)
        self.viewer.setHtml(html)

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
        self.project_sidebar = ProjectSidebar(self.project_dir)
        proj_dock = QDockWidget("Project", self)
        proj_dock.setWidget(self.project_sidebar)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, proj_dock)
        self.find_dock = FindReplaceDock(self)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.find_dock)
        self.git_dock = GitDock(self, os.getcwd())
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.git_dock)
        self.md_dock = MarkdownDock(self)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.md_dock)
        self.term_dock = TerminalDock(self)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.term_dock)
        # autosave & recovery
        self.autosave_dir = os.path.join(tempfile.gettempdir(), "nexus_autosaves")
        os.makedirs(self.autosave_dir, exist_ok=True)
        QTimer(self).start(30000); self.findChild(QTimer).timeout.connect(self.autosave_all)
        # load plugins
        self.plugins = load_plugins(self)
        # new initial tab
        self.editor_area.new_tab()
        self.editor_area.tabs.currentChanged.connect(self.on_tab_changed)

        # ─── Add “Open Folder…” under File ───────────────────────────────────
        file_menu = self.menuBar().addMenu("&File")
        # Save action
        save_act = QAction("&Save", self)
        save_act.setShortcut("Ctrl+S")
        save_act.triggered.connect(self.save_file)
        file_menu.addAction(save_act)
        open_folder_act = QAction("Open &Folder...", self)
        open_folder_act.setShortcut("Ctrl+K")
        open_folder_act.triggered.connect(self.open_folder)
        file_menu.addAction(open_folder_act)
        # menu / toolbar omitted for brevity—just wire new_tab, open, save, theme switcher, etc.
        # LSP stub
        # self.lsp = SomeLSPClient(self.editor_area)

    # ─── Slot: Open a new project directory ────────────────────────────────
    def open_folder(self):
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
        ed = self.editor_area.current_editor()
        if ed is None:
            return

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

        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(ed.toPlainText())
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Could not save file:\n{e}")
            return

        # clear modified flag → removes the dot
        ed.document().setModified(False)

    def closeEvent(self, ev):
        # on close, prompt to recover if no real tabs open
        super().closeEvent(ev)

    def on_tab_changed(self, idx):
        ed = self.editor_area.current_editor()
        # we store the file path on the editor widget when opening:
        path = getattr(ed, "file_path", None)
        if path and path.lower().endswith(".md"):
            # load fresh text (in case external edits)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    txt = f.read()
            except:
                txt = ed.toPlainText()
            ed.blockSignals(True)
            ed.setPlainText(txt)
            ed.blockSignals(False)

            # update and sync
            self.md_dock.update(txt)
            self.md_dock.set_editor(ed)
        else:
            # clear preview & disconnect old signals
            self.md_dock.viewer.clear()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    w = MainWindow()
    w.resize(1200, 800)
    w.show()
    sys.exit(app.exec())
