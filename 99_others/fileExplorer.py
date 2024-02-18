import os
import sys
from datetime import datetime
import subprocess
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMainWindow, QTreeWidget, QTreeWidgetItem, QFileDialog, QPushButton, QVBoxLayout,QHBoxLayout, QWidget, QMenu, QComboBox, QLineEdit, QTreeWidgetItemIterator
import dict_map

class rightClickMenu(QTreeWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

    def contextMenuEvent(self, event):
        print("contextMenuEvent")
        contextMenu = QMenu(self)

        openLocationAction = contextMenu.addAction("打开文件位置")
        previewFileAction = contextMenu.addAction("预览文件")

        action = contextMenu.exec(self.viewport().mapToGlobal(event.pos()))

        if action == openLocationAction:
            self.openFileLocation()
        elif action == previewFileAction:
            self.previewFile()

    def openFileLocation(self):
        selected_item = self.currentItem()
        if selected_item:
            file_path = selected_item.text(0)
            if sys.platform == 'win32':
                os.startfile(os.path.dirname(file_path))
            elif sys.platform == 'darwin':  # macOS
                subprocess.Popen(['open', '--', os.path.dirname(file_path)])
            # Linux 或其他平台的逻辑可以在这里添加

    def previewFile(self):
        selected_item = self.currentItem()
        if selected_item:
            file_path = selected_item.text(0)
            if sys.platform == 'win32':
                os.startfile(file_path)
            elif sys.platform == 'darwin':  # macOS
                subprocess.Popen(['open', file_path])
            # Linux 或其他平台的逻辑可以在这里添加

class FileExplorer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.isTreeExpanded = False  # 用于跟踪树状视图的当前状态
        self.treeWidget = rightClickMenu()
        self.initUI()

    def initUI(self):
        # 创建中心部件和布局
        centralWidget = QWidget(self)
        mainLayout = QVBoxLayout(centralWidget)  # 主垂直布局

        # 创建树状视图
        self.treeWidget = QTreeWidget()
        self.treeWidget.setHeaderLabels(["文件名", "在动画中", "类型", "修改日期", "创建日期"])
        mainLayout.addWidget(self.treeWidget)

        # 创建水平布局来放置按钮
        buttonLayout = QHBoxLayout()

        # 创建打开文件夹的按钮并添加到水平布局
        self.openFolderBtn = QPushButton("打开文件夹")
        self.openFolderBtn.clicked.connect(self.openFolderDialog)
        buttonLayout.addWidget(self.openFolderBtn)

        # 创建切换树状视图展开/折叠的按钮并添加到水平布局
        self.toggleTreeViewBtn = QPushButton("展开/折叠")
        self.toggleTreeViewBtn.clicked.connect(self.toggleTreeView)
        buttonLayout.addWidget(self.toggleTreeViewBtn)

        # 创建“打开文件位置”的按钮并添加到水平布局
        self.openLocationBtn = QPushButton("打开文件位置")
        self.openLocationBtn.clicked.connect(self.openSelectedFileLocation)
        buttonLayout.addWidget(self.openLocationBtn)

        # 将按钮的水平布局添加到主垂直布局
        mainLayout.addLayout(buttonLayout)

        # 创建搜索栏
        self.searchBar = QLineEdit(self)
        self.searchBar.setPlaceholderText("搜索...")
        self.searchBar.textChanged.connect(self.onSearchTextChanged)

        # 创建下拉菜单用于选择搜索类型
        self.searchTypeComboBox = QComboBox(self)
        self.searchTypeComboBox.addItems(["按名称", "按类型", "按动画工程"])

        self.matchTypeComboBox = QComboBox(self)
        self.matchTypeComboBox.addItems(["全部匹配", "部分匹配"])
        self.matchTypeComboBox.currentIndexChanged.connect(self.onSearchTextChanged)  # 当选择改变时更新搜索

        # 将搜索栏和下拉菜单添加到布局中
        searchLayout = QHBoxLayout()
        searchLayout.addWidget(self.searchBar)
        searchLayout.addWidget(self.searchTypeComboBox)
        searchLayout.addWidget(self.matchTypeComboBox)
        mainLayout.insertLayout(0, searchLayout)  # 在布局的顶部添加

        # 设置中心部件和窗口属性
        self.setCentralWidget(centralWidget)
        self.setGeometry(300, 300, 600, 400)
        self.setWindowTitle('文件浏览器')
        self.show()

    def openFolderDialog(self):
        folderPath = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if folderPath:
            self.populateTree(folderPath)

    def populateTree(self, folderPath):
        self.treeWidget.clear()
        root = QTreeWidgetItem(self.treeWidget, [os.path.basename(folderPath)])
        root.setData(0, Qt.UserRole, folderPath)  # 存储根文件夹的路径
        self.addTreeItems(root, folderPath)

    def addTreeItems(self, parentItem, path):
        for name in os.listdir(path):
            if name == 'Thumbs.db' or name == '.DS_Store':
                continue  # 跳过这些文件

            filePath = os.path.join(path, name)  # 先定义filePath

            if os.path.islink(filePath) or filePath.endswith('.fcpbundle'):
                # 处理符号链接或特定文件，例如添加到树视图但不递归
                fileItem = QTreeWidgetItem(parentItem, [name, "", "FCPX工程", "", ""])
                continue  # 跳过后续的递归处理

            if os.path.isdir(filePath):
                dirItem = QTreeWidgetItem(parentItem, [name])
                dirItem.setData(0, Qt.UserRole, filePath)  # 存储完整路径
                self.addTreeItems(dirItem, filePath)
            else:
                fileType = self.getFileTags(name)
                inAnimation = self.getInAnimationTags(name)
                modified = datetime.fromtimestamp(os.path.getmtime(filePath)).strftime('%Y-%m-%d %H:%M:%S')
                created = datetime.fromtimestamp(os.path.getctime(filePath)).strftime('%Y-%m-%d %H:%M:%S')
                fileItem = QTreeWidgetItem(parentItem, [name, inAnimation, fileType, modified, created])
                fileItem.setData(0, Qt.UserRole, filePath)  # 同样存储文件的完整路径

    def onSearchTextChanged(self, _):
        text = self.searchBar.text()
        search_type = self.searchTypeComboBox.currentText()
        match_type = self.matchTypeComboBox.currentText()
        self.filterTreeItems(text, search_type, match_type)

    def filterTreeItems(self, text, search_type, match_type):
        iterator = QTreeWidgetItemIterator(self.treeWidget)
        while iterator.value():
            item = iterator.value()
            item_full_text = item.text(0)  # 获取完整的文件名
            _, item_extension = os.path.splitext(item_full_text)  # 分离扩展名

            if search_type == "按名称":
                item_text = item_full_text.rsplit('.', 1)[0]  # 移除扩展名
            elif search_type == "按类型":  # "按类型"
                item_text = item_extension
            elif search_type == "按动画工程":
                item_text = item.text(1)

            match = self.isMatch(item_text, text, match_type)

            if match:
                self.makeParentsVisible(item)
            else:
                item.setHidden(True)

            iterator += 1

    def isMatch(self, item_text, search_text, match_type):
        if match_type == "全部匹配":
            return item_text.lower() == search_text.lower()
        elif match_type == "部分匹配":
            return search_text.lower() in item_text.lower()
        return False

    def makeParentsVisible(self, item):
        while item:
            item.setHidden(False)
            item = item.parent()

    def openSelectedFileLocation(self):
        selected_item = self.treeWidget.currentItem()
        if selected_item:
            file_path = selected_item.data(0, Qt.UserRole)
            if file_path:  # 检查 file_path 是否为 None
                if sys.platform == 'win32':
                    os.startfile(os.path.dirname(file_path))  # 在 Windows 上打开文件夹
                elif sys.platform == 'darwin':  # macOS
                    self.open_and_select_file_mac(file_path)  # 在 macOS 上打开并选中文件

    def open_and_select_file_mac(self, file_path):
        script = f'''
        tell application "Finder"
            reveal POSIX file "{file_path}"
            activate
        end tell
        '''
        subprocess.run(["osascript", "-e", script])

    def toggleTreeView(self):
        # 切换树状视图的展开和折叠状态
        if self.isTreeExpanded:
            self.treeWidget.collapseAll()
        else:
            self.treeWidget.expandAll()
        self.isTreeExpanded = not self.isTreeExpanded

    def getInAnimationTags(self, filename):
        # 定义关键词到标签的映射
        keyword_map = dict_map.keyword_map
        # 将文件名转换为小写以进行不区分大小写的比较
        filename_lower = filename.lower()

        # 检查每个关键词是否出现在文件名中
        for keyword, tag in keyword_map.items():
            if keyword in filename_lower:
                return tag

        # 如果没有找到匹配的关键词，返回空字符串
        return ""

    def getFileTags(self, filename):
        # 定义文件扩展名到中文描述的映射
        extension_map = dict_map.file_extension_map

        # 获取文件的扩展名并转换为小写
        ext = os.path.splitext(filename.lower())[1]

        # 返回对应的中文描述，如果找不到则返回"其他"
        return extension_map.get(ext, "其他")

def main():
    app = QApplication(sys.argv)
    ex = FileExplorer()
    with open('/Users/chenxing/Documents/5_AnimeProjectManager/4_qss/style.qss', 'r') as f:
        style = f.read()
    app.setStyleSheet(style)
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
