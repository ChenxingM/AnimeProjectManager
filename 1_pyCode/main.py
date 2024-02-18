import re
import pandas as pd
import chardet
import os
import dict_map
from pprint import pprint
import shutil
import sys
import subprocess
from datetime import datetime
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel,
                               QPushButton, QTextEdit, QComboBox, QTreeView, QFileDialog, QTreeWidgetItem, QTreeWidget, QTreeWidgetItemIterator, QMessageBox, QMenu)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap,QDragEnterEvent, QDropEvent
import xml.etree.ElementTree as ET
from xml.dom import minidom

title = "AKM"
default_file_path = "/Users/chenxing/Documents/5_AnimeProjectManager/1_pyCode/進捗整理_納品管理_收集结果.csv"
cut_folder_path = "/Users/chenxing/Documents/卒制/0_CutFolder"
default_upload_folder_path = "/Users/chenxing/Documents/5_AnimeProjectManager/1_pyCode/進捗整理-收集表-收集结果_附件"
conte_csv = "/Users/chenxing/Documents/5_AnimeProjectManager/1_pyCode/output.csv"
xml_path = []
input_widgets = {}
current_running_folder = []

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

    def previewFile(self):
        selected_item = self.currentItem()
        if selected_item:
            file_path = selected_item.text(0)
            if sys.platform == 'win32':
                os.startfile(file_path)
            elif sys.platform == 'darwin':  # macOS
                subprocess.Popen(['open', file_path])

class FileExplorer(QWidget):
    def __init__(self):
        super().__init__()
        self.isTreeExpanded = False
        self.initUI()

    def initUI(self):
        # 主垂直布局
        mainLayout = QVBoxLayout(self)

        # 创建树状视图
        self.treeWidget = rightClickMenu()
        self.treeWidget.setHeaderLabels(["文件名", "在动画中", "类型", "修改日期", "创建日期"])
        self.treeWidget.setColumnWidth(0, 200)
        self.treeWidget.setMinimumHeight(300)
        self.treeWidget.setMinimumWidth(500)
        mainLayout.addWidget(self.treeWidget)


        buttonLayout = QHBoxLayout()

        self.openFolderBtn = QPushButton("打开文件夹")
        self.openFolderBtn.clicked.connect(self.openFolderDialog)
        buttonLayout.addWidget(self.openFolderBtn)

        self.toggleTreeViewBtn = QPushButton("展开/折叠")
        self.toggleTreeViewBtn.clicked.connect(self.toggleTreeView)
        buttonLayout.addWidget(self.toggleTreeViewBtn)

        self.openLocationBtn = QPushButton("打开文件位置")
        self.openLocationBtn.clicked.connect(self.openSelectedFileLocation)
        buttonLayout.addWidget(self.openLocationBtn)

        mainLayout.addLayout(buttonLayout)

        self.searchBar = QLineEdit(self)
        self.searchBar.setPlaceholderText("搜索...")
        self.searchBar.textChanged.connect(self.onSearchTextChanged)

        self.searchTypeComboBox = QComboBox(self)
        self.searchTypeComboBox.addItems(["按名称", "按类型", "按动画工程"])

        self.matchTypeComboBox = QComboBox(self)
        self.matchTypeComboBox.addItems(["全部匹配", "部分匹配"])
        self.matchTypeComboBox.currentIndexChanged.connect(self.onSearchTextChanged)  # 当选择改变时更新搜索

        searchLayout = QHBoxLayout()
        searchLayout.addWidget(self.searchBar)
        searchLayout.addWidget(self.searchTypeComboBox)
        searchLayout.addWidget(self.matchTypeComboBox)
        mainLayout.insertLayout(0, searchLayout)  # 在布局的顶部添加


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

            filePath = os.path.join(path, name)

            if os.path.islink(filePath) or filePath.endswith('.fcpbundle'):
                fileItem = QTreeWidgetItem(parentItem, [name, "", "FCPX工程", "", ""])
                continue

            if os.path.isdir(filePath):
                dirItem = QTreeWidgetItem(parentItem, [name])
                dirItem.setData(0, Qt.UserRole, filePath)
                self.addTreeItems(dirItem, filePath)
            else:
                fileType = self.getFileTags(name)
                inAnimation = self.getInAnimationTags(name)
                modified = datetime.fromtimestamp(os.path.getmtime(filePath)).strftime('%Y-%m-%d %H:%M:%S')
                created = datetime.fromtimestamp(os.path.getctime(filePath)).strftime('%Y-%m-%d %H:%M:%S')
                fileItem = QTreeWidgetItem(parentItem, [name, inAnimation, fileType, modified, created])
                fileItem.setData(0, Qt.UserRole, filePath)

    def onSearchTextChanged(self, _):
        text = self.searchBar.text()
        search_type = self.searchTypeComboBox.currentText()
        match_type = self.matchTypeComboBox.currentText()
        self.filterTreeItems(text, search_type, match_type)

    def filterTreeItems(self, text, search_type, match_type):
        iterator = QTreeWidgetItemIterator(self.treeWidget)
        while iterator.value():
            item = iterator.value()
            item_full_text = item.text(0)
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


def update_info(text):
    current_time = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    current_text = debug_text_edit.toPlainText()
    new_message = f"{current_time} {text}\n"
    updated_text = current_text + new_message
    debug_text_edit.setPlainText(updated_text)

def detect_encoding(file_path):
    with open(file_path, 'rb') as f:
        result = chardet.detect(f.read())
    return result['encoding']


def format_cut_no(cut_no):
    combined_use = False
    if str(cut_no).startswith('c'):
        formatted_cut_no = str(cut_no)
        prats = formatted_cut_no.split('_')
        if len(prats) > 1:
            combined_use = True
    else:
        parts = str(cut_no).split('_')
        if len(parts) > 1:
            combined_use = True
            formatted_parts = [part.zfill(3) for part in parts]
            formatted_cut_no = 'c' + '_'.join(formatted_parts)
        else:
            combined_use = False
            formatted_cut_no = 'c' + parts[0].zfill(3)
    return formatted_cut_no, combined_use


def process_files(data, cut_folder_path, upload_folder_path, title):
    for key, value in data.items():
        print(value['currentStep'])
        print(value['loStep'])
        if (value['currentStep'] == 'lo' and not value['loStep'] == 'notLO') or value['currentStep'] == 'bg':
            # 处理lo步骤的文件和文件夹
            process_lo_step(cut_folder_path, upload_folder_path, key, value, title)
        elif value['currentStep'] == '2gen' or value['currentStep'] == 'douga':
            # 处理2gen和douga步骤的文件和文件夹
            process_2gen_douga_step(cut_folder_path, upload_folder_path, key, value, title)
        elif value['currentStep'] == 'paint':
            pass
            # 处理paint步骤的文件和文件夹
            #process_paint_step(cut_folder_path, upload_folder_path, key, value, title)
        else:
            raise ValueError(f"Unknown currentStep: {value['currentStep']}")


def process_2gen_douga_step(cut_folder_path, upload_folder_path, key, value, title):
    global current_running_folder
    base_folder_name = f"{title}_{value['cutNo']}"
    print(base_folder_name)
    target_folder_path, folder_name = douga_2gen_folder(cut_folder_path, base_folder_name, value)
    print(target_folder_path, folder_name)
    # 处理文件的移动和重命名
    for file_name in os.listdir(upload_folder_path):
        if file_name.startswith(f"{key}."):
            file_path = os.path.join(upload_folder_path, file_name)
            douga_2gen_files(file_path, target_folder_path, file_name, folder_name, value['cutNo'], value['currentStep'])
            current_running_folder.append(target_folder_path)

def douga_2gen_folder(cut_folder_path, base_folder_name, value):
    # 定义步骤的顺序
    lo_step_order = ['lo', 'en', 'ks', 's', '2gen', 'douga']

    # 初始化返回值
    target_folder_path = None
    folder_name = None

    existing_folders = [folder for folder in os.listdir(cut_folder_path) if folder.startswith(base_folder_name)]
    for folder in existing_folders:
        folder_path = os.path.join(cut_folder_path, folder)
        # 分解文件夹名 获取当前步骤
        parts = folder.split('_')
        current_lo_steps = parts[3:]

        # 如果当前文件夹已经包含value['currentStep']，直接返回当前文件夹路径，不重命名
        if value['currentStep'] in current_lo_steps:
            update_info(f"文件夹 {folder} 已经含有 '{value['currentStep']}'步骤, 无需改变，仅替换新文件.")
            target_folder_path = folder_path
            folder_name = os.path.basename(folder_path)
            break  # 跳出循环

        # 检查是否可以添加新的currentStep
        if value['currentStep'] in lo_step_order:
            new_lo_step_index = lo_step_order.index(value['currentStep'])

            if current_lo_steps:
                # currentStep是否顺序正确
                last_lo_step_index = max(
                    (lo_step_order.index(step) for step in current_lo_steps if step in lo_step_order), default=-1)
                if new_lo_step_index <= last_lo_step_index:
                    update_info(f"无法将 {folder} 添加 '{value['currentStep']}'步骤，违反了工程顺序.")
                    raise ValueError(
                        f"无法将 {folder} 添加 '{value['currentStep']}'步骤，违反了工程顺序.")
                # 生成新的文件夹名
                new_folder_name = '_'.join(parts[:3] + [value['currentStep']])

            new_folder_path = os.path.join(cut_folder_path, new_folder_name)
            # 尝试重命名文件夹
            try:
                os.rename(folder_path, new_folder_path)
                update_info(f"文件夹从 {folder} 重命名为 {new_folder_name}")
                target_folder_path = new_folder_path
                folder_name = new_folder_name
                if value['currentStep'] == '2gen':
                    os.mkdir(os.path.join(new_folder_path, "_1gen"))
                    update_info(f"创建文件夹 {new_folder_path}/_1gen")
                elif value['currentStep'] == 'douga':
                    os.mkdir(os.path.join(new_folder_path, "_genga"))
                    update_info(f"创建文件夹 {new_folder_path}/_genga")
                break  # 成功重命名后跳出循环
            except Exception as e:
                update_info(f"重命名 {folder} 到 {new_folder_name}发生错误: {e}")
                # 如果重命名失败，使用原始路径和名称
                target_folder_path = folder_path
                folder_name = os.path.basename(folder_path)
                break  # 跳出循环

    return target_folder_path, folder_name

def douga_2gen_files(file_path, target_folder, file_name, folder_name, cut_no, current_step):
    global xml_path
    # 确保目标文件夹存在
    if not os.path.exists(target_folder):
        os.makedirs(target_folder)

    # 根据文件类型确定新的文件名和目标子文件夹
    if  file_name.endswith('.clip'):
        new_file_name = f"{folder_name}.clip"  # 文件名现在直接使用文件夹名
        dest_subfolder = "_clip"
    elif file_name.endswith('.psd'):
        new_file_name = f"{folder_name}_bg.psd"
        dest_subfolder = "_bg"
    else:
        new_file_name = file_name  # 保持其他类型文件不变
        dest_subfolder = "_pool"

    dest_folder = os.path.join(target_folder, dest_subfolder)
    pool_folder = os.path.join(target_folder, "_pool")  # 定义_pool文件夹路径
    gen1_folder = os.path.join(target_folder, "_1gen")
    genga_folder = os.path.join(target_folder, "_genga")

    # 确保_clip和_pool文件夹存在
    if not os.path.exists(dest_folder):
        os.makedirs(dest_folder)
    if not os.path.exists(pool_folder):
        os.makedirs(pool_folder)

    # 如果目标是_clip文件夹，先移动里面的所有文件到_pool
    if current_step == "2gen" and dest_subfolder == "_clip":
        for existing_file in os.listdir(dest_folder):
            existing_file_path = os.path.join(dest_folder, existing_file)
            gen1_file_path = os.path.join(gen1_folder, existing_file)
            shutil.move(existing_file_path, gen1_file_path)
            update_info(f"将已存在的 {existing_file} 移动到 {gen1_folder}")
    elif current_step == "douga" and dest_subfolder == "_clip":
        for existing_file in os.listdir(dest_folder):
            existing_file_path = os.path.join(dest_folder, existing_file)
            genga_file_path = os.path.join(genga_folder, existing_file)
            shutil.move(existing_file_path, genga_file_path)
            update_info(f"将已存在的 {existing_file} 移动到 {genga_folder}")

    # 复制文件到目标子文件夹
    dest_file_path = os.path.join(dest_folder, new_file_name)
    shutil.copy(file_path, dest_file_path)
    update_info(f"将 {file_path} 复制到 {dest_file_path}")
    info_folder = os.path.join(target_folder, "_info")
    if not os.path.exists(info_folder):
        os.makedirs(info_folder)
    for xml in xml_path:
        if cut_no in xml:
            shutil.copy(xml, info_folder)
            # 复制后的xml路径
            xml_copied = os.path.join(info_folder, os.path.basename(xml))
            # 更新XML的cspPath
            if dest_file_path.endswith('.clip'):
                tree = ET.parse(xml_copied)
                root = tree.getroot()
                csp_path = root.find('paths').find('cspPath')
                csp_path.text = dest_file_path
                tree.write(xml_copied, encoding='utf-8', xml_declaration=True)
            elif dest_file_path.endswith('.psd'):
                tree = ET.parse(xml_copied)
                root = tree.getroot()
                bg_path = root.find('paths').find('bgPath')
                bg_path.text = dest_file_path
                tree.write(xml_copied, encoding='utf-8', xml_declaration=True)
            update_info(f"将 {xml_copied} 复制到 {info_folder}")



# 处理lo步骤的文件和文件夹
def process_lo_step(cut_folder_path, upload_folder_path, key, value, title):
    global current_running_folder
    base_folder_name = f"{title}_{value['cutNo']}"
    target_folder_path, folder_name = lo_folder(cut_folder_path, base_folder_name, value)
    # 处理文件的移动和重命名
    for file_name in os.listdir(upload_folder_path):
        if file_name.startswith(f"{key}."):
            file_path = os.path.join(upload_folder_path, file_name)
            lo_files(file_path, target_folder_path, file_name, folder_name, value['cutNo'])
            current_running_folder.append(target_folder_path)


def lo_files(file_path, target_folder, file_name, folder_name, cut_no):
    global xml_path
    # 确保目标文件夹存在
    if not os.path.exists(target_folder):
        os.makedirs(target_folder)

    # 根据文件类型确定新的文件名和目标子文件夹
    if file_name.endswith('.clip'):
        new_file_name = f"{folder_name}.clip"  # 文件名现在直接使用文件夹名
        dest_subfolder = "_clip"
    elif file_name.endswith('.psd'):
        new_file_name = f"{folder_name}_bg.psd"
        dest_subfolder = "_bg"
    else:
        new_file_name = file_name  # 保持其他类型文件不变
        dest_subfolder = "_pool"

    dest_folder = os.path.join(target_folder, dest_subfolder)
    pool_folder = os.path.join(target_folder, "_pool")  # 定义_pool文件夹路径

    # 确保_clip和_pool文件夹存在
    if not os.path.exists(dest_folder):
        os.makedirs(dest_folder)
    if not os.path.exists(pool_folder):
        os.makedirs(pool_folder)

    # 如果目标是_clip文件夹，先移动里面的所有文件到_pool
    if dest_subfolder == "_clip":
        for existing_file in os.listdir(dest_folder):
            existing_file_path = os.path.join(dest_folder, existing_file)
            pool_file_path = os.path.join(pool_folder, existing_file)
            shutil.move(existing_file_path, pool_file_path)
            update_info(f"将已存在的 {existing_file} 移动到 {pool_folder}")

    # 复制文件到目标子文件夹
    dest_file_path = os.path.join(dest_folder, new_file_name)
    shutil.copy(file_path, dest_file_path)
    update_info(f"将 {file_path} 复制到 {dest_file_path}")
    info_folder = os.path.join(target_folder, "_info")
    if not os.path.exists(info_folder):
        os.makedirs(info_folder)
    for xml in xml_path:
        if cut_no in xml:
            shutil.copy(xml, info_folder)
            # 复制后的xml路径
            xml_copied = os.path.join(info_folder, os.path.basename(xml))
            # 更新XML的cspPath
            if dest_file_path.endswith('.clip'):
                tree = ET.parse(xml_copied)
                root = tree.getroot()
                csp_path = root.find('paths').find('cspPath')
                csp_path.text = dest_file_path
                tree.write(xml_copied, encoding='utf-8', xml_declaration=True)
            elif dest_file_path.endswith('.psd'):
                tree = ET.parse(xml_copied)
                root = tree.getroot()
                bg_path = root.find('paths').find('bgPath')
                bg_path.text = dest_file_path
                tree.write(xml_copied, encoding='utf-8', xml_declaration=True)
            update_info(f"将 {xml_copied} 复制到 {info_folder}")


def lo_folder(cut_folder_path, base_folder_name, value):
    # 定义lo步骤的顺序
    lo_step_order = ['lo', 'en', 'ks', 's']

    # 初始化返回值
    target_folder_path = None
    folder_name = None
    existing_folders = [folder for folder in os.listdir(cut_folder_path) if folder.startswith(base_folder_name)]
    for folder in existing_folders:
        folder_path = os.path.join(cut_folder_path, folder)
        print(folder_path)
        # 分解文件夹名以获取当前lo步骤
        parts = folder.split('_')
        current_lo_steps = parts[3:]

        # 如果当前文件夹已经包含value['loStep']，直接返回当前文件夹路径，不重命名
        print(value['loStep'])
        if value['loStep'] in current_lo_steps:
            update_info(f"文件夹 {folder} 已经含有 '{value['loStep']}'步骤, 无需改变，仅替换新文件.")
            target_folder_path = folder_path
            folder_name = os.path.basename(folder_path)
            break  # 跳出循环

        # 检查是否可以添加新的loStep
        if value['loStep'] in lo_step_order:
            new_lo_step_index = lo_step_order.index(value['loStep'])

            if current_lo_steps:
                # 检查新的loStep是否顺序正确
                last_lo_step_index = max(
                    (lo_step_order.index(step) for step in current_lo_steps if step in lo_step_order), default=-1)
                if new_lo_step_index <= last_lo_step_index:
                    update_info(f"无法将 {folder} 添加 '{value['loStep']}'步骤，违反了工程顺序.")
                    raise ValueError(
                        f"无法将 {folder} 添加 '{value['loStep']}'步骤，违反了工程顺序.")
                # 生成新的文件夹名
                new_folder_name = '_'.join(parts[:3] + current_lo_steps + [value['loStep']])
            else:
                # 直接添加loStep
                new_folder_name = '_'.join(parts[:3] + [value['loStep']])

            new_folder_path = os.path.join(cut_folder_path, new_folder_name)
            # 尝试重命名文件夹
            try:
                os.rename(folder_path, new_folder_path)
                update_info(f"文件夹从 {folder} 重命名为 {new_folder_name}")
                target_folder_path = new_folder_path
                folder_name = new_folder_name
                break  # 成功重命名后跳出循环
            except Exception as e:
                update_info(f"重命名 {folder} 到 {new_folder_name}发生错误: {e}")
                # 如果重命名失败，使用原始路径和名称
                target_folder_path = folder_path
                folder_name = os.path.basename(folder_path)
                break  # 跳出循环

    # 确保返回文件夹的完整路径和基本名称
    print(target_folder_path, folder_name)
    return target_folder_path, folder_name


def generate_xml_files(data, title, conte_dict):
    global xml_path
    conte = conte_dict
    def prettify(elem):
        rough_string = ET.tostring(elem, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")

    for key, value in data.items():
        cut_folder = current_running_folder[key-1]
        project = ET.Element("project")

        # 检查cutNo是否包含兼用卡标识（即'_'字符）
        if '_' in value['cutNo']:
            parts = value['cutNo'].split('_')
            totalFramesText = []
            actionsText = []
            dialogText = []

            for part in parts:
                # 提取数字并转换为整数
                cut_number = int(''.join(filter(str.isdigit, part)))
                if cut_number in conte_dict:
                    totalFramesText.append(
                        f"{cut_number}:{','.join(map(str, conte_dict[cut_number]['cutTotalFrames']))}")
                    actionsText.append(f"{cut_number}:{','.join(conte_dict[cut_number]['actions'])}")
                    dialogText.append(f"{cut_number}:{','.join(map(str, conte_dict[cut_number]['dialog']))}")

            totalFramesText = "，".join(totalFramesText)
            actionsText = "，".join(actionsText)
            dialogText = "，".join(dialogText)
        else:
            cut_number = int(''.join(filter(str.isdigit, value['cutNo'])))
            totalFramesText = ",".join(
                map(str, conte_dict[cut_number]['cutTotalFrames'])) if cut_number in conte_dict else "None"
            actionsText = ",".join(conte_dict[cut_number]['actions']) if cut_number in conte_dict else "None"
            dialogText = ",".join(map(str, conte_dict[cut_number]['dialog'])) if cut_number in conte_dict else "None"

        # 添加子节点
        project.append(ET.Comment('作品名'))
        ET.SubElement(project, "title").text = title
        project.append(ET.Comment('PART'))
        ET.SubElement(project, "part").text = "A"
        project.append(ET.Comment('场景'))
        ET.SubElement(project, "scene").text = "1"
        project.append(ET.Comment('卡号'))
        ET.SubElement(project, "cut").text = value['cutNo']
        project.append(ET.Comment('兼用卡'))
        ET.SubElement(project, "combined").text = str(value['combinedCut']).lower()
        project.append(ET.Comment('时间'))
        time_element = ET.SubElement(project, "time")
        ET.SubElement(time_element, "totalFrames").text = totalFramesText
        project.append(ET.Comment('当前工程'))
        ET.SubElement(project, "currentStep").text = value['currentStep']
        project.append(ET.Comment('当前状态'))
        ET.SubElement(project, "currentStatus").text = "暂未分配"
        project.append(ET.Comment('LO工程（如果有）'))
        ET.SubElement(project, "loStep").text = value['loStep']
        project.append(ET.Comment('提交日期'))
        ET.SubElement(project, "upDate").text = value['upDate']
        project.append(ET.Comment('开始日期'))
        ET.SubElement(project, "startDate").text = value['inDate']
        project.append(ET.Comment('分镜内容'))
        ET.SubElement(project, "conteActions").text = actionsText # 静态内容
        project.append(ET.Comment('台词'))
        ET.SubElement(project, "dialog").text = dialogText  # 静态内容
        project.append(ET.Comment('注释'))
        ET.SubElement(project, "notes").text = value['msg']


        # 路径节点
        base_name = os.path.basename(cut_folder)
        project.append(ET.Comment('路径'))
        paths = ET.SubElement(project, "paths")
        paths.append(ET.Comment('CSP文件路径'))
        ET.SubElement(paths, "cspPath").text = os.path.join(cut_folder, "_clip", f"{base_name}.clip")
        paths.append(ET.Comment('背景文件路径'))
        ET.SubElement(paths, "bgPath").text = os.path.join(cut_folder, "_bg", f"{base_name}_bg.psd")
        paths.append(ET.Comment('分镜图像'))
        ET.SubElement(paths, "conteImage").text = os.path.join(cut_folder, "_conte",
                                                                 f"{title}_{value['cutNo']}_conte.jpg")
        paths.append(ET.Comment('卡文件夹路径'))
        ET.SubElement(paths, "cutFolder").text = cut_folder

        # 人员节点
        project.append(ET.Comment('负责人'))
        people = ET.SubElement(project, "people")
        roles = ["nc", "s", "ss", "en", "2gen", "douga", "bg", "paint"]
        role_elements = ["loPerson", "sPerson", "ssPerson", "enPerson", "gen2Person", "dougaPerson", "bgPerson",
                         "paintPerson"]
        role_dict = {
            "loPerson": "LO",
            "sPerson": "作监",
            "ssPerson": "总作监",
            "enPerson": "演出",
            "gen2Person": "二原",
            "dougaPerson": "动画",
            "bgPerson": "美术",
            "paintPerson": "上色"
        }
        for role, elem_name in zip(roles, role_elements):
            # 直接在需要添加子元素前添加注释
            comment_text = role_dict.get(elem_name, "未知角色")
            people.append(ET.Comment(comment_text))

            person_element = ET.SubElement(people, elem_name)
            if value['loStep'] == role or (value['currentStep'] == role and value['loStep'] == "notLO"):
                person_element.text = value['submitter']
            else:
                person_element.text = "无"

        # 文件名构造
        file_name = f"{title}_{value['cutNo']}_info.xml"

        # 检查文件存在并且action不是overwrite，则抛出错误
        this_py_folder = os.path.dirname(os.path.abspath(__file__))
        try:
            # 生成 XML 文件
            with open(file_name, "w", encoding="utf-8") as xml_file:
                xml_file.write(prettify(project))
                xml_path.append(os.path.join(this_py_folder, file_name))

            update_info(f"成功创建/更新卡信息 {file_name}")

        except ValueError as e:
            update_info(e)


def get_conte(conte_csv):
    df = pd.read_csv(conte_csv)
    conte_dict = {}
    for _, row in df.iterrows():
        cut_no = row['SequenceName']
        if cut_no not in conte_dict:
            conte_dict[cut_no] = {
                'cutTotalFrames': set(),
                'cutActionsFrames': [],
                'actionsNum': 0,
                'dialog': [],
                'actions': []
            }

        conte_dict[cut_no]['cutTotalFrames'].add(row['SceneFrames'])
        conte_dict[cut_no]['cutActionsFrames'].append(row['PanelFrames'])
        conte_dict[cut_no]['actionsNum'] = len(conte_dict[cut_no]['cutActionsFrames'])
        conte_dict[cut_no]['dialog'].append(row['对话框'])
        conte_dict[cut_no]['actions'].append(row['动作注释'])

    # 将SceneFrames的集合转换回列表
    for cut in conte_dict:
        conte_dict[cut]['cutTotalFrames'] = list(conte_dict[cut]['cutTotalFrames'])

    return conte_dict

def process_submitt_csv():
    if csv_path_edit.text():
        file_path = csv_path_edit.text()
        upload_folder_path = os.path.join(os.path.dirname(file_path), "進捗整理-收集表-收集结果_附件")
    else:
        file_path = default_file_path
        upload_folder_path = default_upload_folder_path

    encoding = detect_encoding(file_path)
    df = pd.read_csv(file_path, encoding=encoding)

    step_dict = {
        'LO（第一原画）': 'lo',
        '原画（第二原画）': '2gen',
        '动画（中割）': 'douga',
        '美术': 'bg',
        '上色': 'paint',
    }

    lo_step_dict = {
        '作画（待修正）': 'lo',
        '作监修正': 's',
        '演出修正': 'en',
        '监督修正': 'ks',
        '我提交的不是LO（第一原画）': 'notLO'
    }

    cut_info_list = {}

    # 遍历数据框，处理并存储每一行的内容
    for index, row in df.iterrows():
        formatted_cut_no, combined_use = format_cut_no(row['你要对哪一卡做出更改？'])
        current_step = step_dict.get(row['你要提交的是？'], 'unknown')
        action = "new" if row['你要对这一卡做什么？'] == '提交全新的' else (
            "ver" if row['你要对这一卡做什么？'] == '上传其他版本' else "overwrite")
        lo_step = lo_step_dict.get(row.get('如果你选择了LO（第一原画）\n你提交的是哪一个步骤？', 'notLO'), 'notLO')

        original_file_name = row['再检查一次，没什么问题就上传吧']
        file_extension = os.path.splitext(original_file_name)[1]  # 获取扩展名
        file_name = f"{row['自动编号']}{file_extension}"  # 构造新的文件名

        cut_info_list[row['自动编号']] = {
            'cutNo': formatted_cut_no,
            'combinedCut': combined_use,
            'upDate': row['提交时间'],
            'submitter': row['提交人'],
            'action': action,
            'currentStep': current_step,
            'loStep':lo_step,
            'fileName': file_name,
            'originalFileName': row['再检查一次，没什么问题就上传吧'],
            'msg': row['有什么需要传达的信息吗？'],
            'inDate': row['你是什么时候开始进行这一卡的呢']
        }
    # print(cut_info_list)
    # debug_text_edit.setPlainText(str(cut_info_list))
    conte_dict = get_conte(conte_csv)

    process_files(cut_info_list, cut_folder_path, upload_folder_path, title)
    generate_xml_files(cut_info_list, title, conte_dict)
    for key in cut_info_list:
        shutil.copy(xml_path[key-1], os.path.join(current_running_folder[key-1], "_info"))

    return cut_info_list


def on_cut_button_clicked():
    #global fileExplorer
    labels = ["PART:", "场景:", "卡号:", "时长:", "当前工程:", "现在情况？", "CSP文件名:", "上交时间:", "背景文件名:"]
    # 获取用户在卡号输入框中输入的卡号
    cut_no_input = input_widgets["卡号:"].text()
    formatted_cut_no, _ = format_cut_no(cut_no_input)

    # 在cut_folder_path中寻找包含formatted_cut_no的文件夹
    target_folder = None
    for folder in os.listdir(cut_folder_path):
        if formatted_cut_no in folder:
            # 确认文件夹名是否符合期望的模式
            fileExplorer.populateTree(os.path.join(cut_folder_path, folder))
            fileExplorer.treeWidget.expandAll()
            info_path = os.path.join(cut_folder_path, folder, "_info")
            if os.path.exists(info_path):
                target_folder = info_path
                break

    if target_folder:
        # 在目标_info文件夹中寻找XML文件
        xml_file_path = None
        for file in os.listdir(target_folder):
            if file.endswith(".xml"):
                xml_file_path = os.path.join(target_folder, file)
                break  # 找到第一个XML文件就跳出循环

        if xml_file_path:
            # 解析XML文件
            tree = ET.parse(xml_file_path)
            root = tree.getroot()
            time = root.find('time')
            total_frames = time.find('totalFrames').text

            cut_folder = os.path.basename(root.find('paths').find('cutFolder').text)

            # 映射字典
            suffix_to_text = {
                "lo": "一原",
                "ks": "监督修",
                "en": "演出修",
                "s": "作监修",
                "2gen": "二原",
                "douga": "动画"
            }

            def get_setps(cut_folder):
                # 匹配的后缀
                pattern = re.compile(r'_(lo|ks|en|s|2gen|douga)')
                matches = pattern.findall(cut_folder)

                # 转换匹配的后缀为对应的文本
                texts = [suffix_to_text[suffix] for suffix in matches if suffix in suffix_to_text]

                # 连接流程
                result_text = " → ".join(texts)

                return result_text
            steps = get_setps(cut_folder)

            # 读取并填充信息到界面上
            input_widgets["PART:"].setText(root.find('part').text)
            input_widgets["场景:"].setText(root.find('scene').text)
            input_widgets["卡号:"].setText(root.find('cut').text)
            input_widgets["时长:"].setText(total_frames)
            input_widgets["当前工程:"].setText(steps)
            input_widgets["现在情况？"].setText(root.find('currentStatus').text)
            input_widgets["CSP文件名:"].setText(os.path.basename(root.find('paths').find('cspPath').text))
            input_widgets["背景文件名:"].setText(os.path.basename(root.find('paths').find('bgPath').text) if root.find('paths').find('bgPath').text else "未上交")
            #loStep_input_widget.setText(root.find('loStep').text)
            input_widgets["上交时间:"].setText(root.find('upDate').text)
            comment_text_edit.setPlainText(root.find('notes').text)
            actionsInput.setPlainText(root.find('conteActions').text)
            dialogInput.setPlainText(root.find('dialog').text)
            conte_file = root.find('paths').find('conteImage').text
            pixmap = QPixmap(conte_file)
            imageLabel.setPixmap(pixmap.scaled(300, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation))

            update_info(f"{formatted_cut_no} 的信息已加载")
        else:
            update_info("未找到对应的XML文件")
    else:
        update_info(f"未找到包含指定卡号{formatted_cut_no}的文件夹")

def on_update_button_clicked():
    # 弹出提示框，确认是否更新
    reply = QMessageBox.question(window, '确认更新', '确认更新卡信息？', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
    if reply == QMessageBox.Yes:
        cut_no_input = input_widgets["卡号:"].text()
        formatted_cut_no, _ = format_cut_no(cut_no_input)

        # 在cut_folder_path中寻找包含formatted_cut_no的文件夹
        target_folder = None
        for folder in os.listdir(cut_folder_path):
            if formatted_cut_no in folder:
                # 进一步确认文件夹名是否符合期望的模式
                info_path = os.path.join(cut_folder_path, folder, "_info")
                if os.path.exists(info_path):
                    target_folder = info_path
                    break

        if target_folder:
            # 在目标_info文件夹中寻找XML文件
            xml_file_path = None
            for file in os.listdir(target_folder):
                if file.endswith(".xml"):
                    xml_file_path = os.path.join(target_folder, file)
                    break  # 找到第一个XML文件就跳出循环

            if xml_file_path:
                # 解析XML文件
                tree = ET.parse(xml_file_path)
                root = tree.getroot()
                print(root.find('currentStatus').text)
                print(input_widgets["现在情况？"].text())
                print(comment_text_edit.toPlainText())
                print(root.find('notes').text)
                # 打印具体更新了哪些内容
                if root.find('currentStatus').text != input_widgets["现在情况？"].text():
                    update_info(f"现在情况从 {root.find('currentStatus').text} 更新为 {input_widgets['现在情况？'].text()}")
                if root.find('notes').text != comment_text_edit.toPlainText():
                    update_info(f"注释从 {root.find('notes').text} 更新为 {comment_text_edit.toPlainText()}")
                if root.find('conteActions').text != actionsInput.toPlainText():
                    update_info(f"分镜内容从 {root.find('conteActions').text} 更新为 {actionsInput.toPlainText()}")
                if root.find('dialog').text != dialogInput.toPlainText():
                    update_info(f"台词从 {root.find('dialog').text} 更新为 {dialogInput.toPlainText()}")
                #更新XML文件中的内容
                root.find('currentStatus').text = input_widgets["现在情况？"].text()
                root.find('notes').text = comment_text_edit.toPlainText()
                root.find('conteActions').text = actionsInput.toPlainText()
                root.find('dialog').text = dialogInput.toPlainText()

                # 保存XML文件
                tree.write(xml_file_path, encoding='utf-8', xml_declaration=True)


                update_info(f"{formatted_cut_no} 的信息已更新")
            else:
                update_info("未找到对应的XML文件")
        else:
            update_info(f"未找到包含指定卡号{formatted_cut_no}的文件夹")



# 创建主应用程序
app = QApplication(sys.argv)

# 创建主窗口
window = QWidget()
window.setWindowTitle("动画文件管理系统")

# 主布局
main_layout = QHBoxLayout(window)

# 左侧布局
left_layout = QVBoxLayout()

# 右侧布局
right_layout = QVBoxLayout()

# 创建表单布局
form_layout = QVBoxLayout()
# 添加标题
title_label = QLabel("作品名")
form_layout.addWidget(title_label)

# 添加输入字段及其标签
# 定义标签和对应XML元素的映射
labels_to_xml = {
    "PART:": "part",
    "场景:": "scene",
    "卡号:": "cut",
    "时长:": "totalFrames",  # 假设XML中没有直接对应的元素
    "当前工程:": "currentStep",
    "现在情况？": "currentStatus",
    "CSP文件名:": None,  # 由于路径可能需要特殊处理，这里暂时设置为None
    "背景文件名:": None,  # 同上
    "上交时间:": "upDate"
}

labels = ["PART:", "场景:", "卡号:", "时长:", "当前工程:", "现在情况？", "CSP文件名:", "上交时间:", "背景文件名:"]
for label_text in labels:
    label = QLabel(label_text)
    input_widget = QLineEdit()

    horizontal_layout = QHBoxLayout()
    horizontal_layout.addWidget(label)
    horizontal_layout.addWidget(input_widget)
    input_widget.setMinimumWidth(200)  # 设置固定宽度

    form_layout.addLayout(horizontal_layout)

    # 将输入框存储在字典中
    input_widgets[label_text] = input_widget

# 添加注释部分
comment_label = QLabel("注释")
comment_text_edit = QTextEdit()
form_layout.addWidget(comment_label)
form_layout.addWidget(comment_text_edit)
comment_text_edit.setMinimumHeight(100)
comment_text_edit.setMinimumWidth(300)

# 添加按钮
buttons_layout = QHBoxLayout()
csv_button = QPushButton("納品CSV")
csv_button.setObjectName("csvButton")  # 设置对象名称以便在QSS中引用
cut_button = QPushButton("获取当前卡")
submit_button = QPushButton("更新信息")
submit_button.setObjectName("submitButton")  # 设置对象名称以便在QSS中引用
buttons_layout.addWidget(csv_button)
buttons_layout.addWidget(cut_button)
buttons_layout.addWidget(submit_button)


csv_button.clicked.connect(lambda :process_submitt_csv())
cut_button.clicked.connect(on_cut_button_clicked)
submit_button.clicked.connect(on_update_button_clicked)

left_layout = QVBoxLayout()
left_layout.addLayout(form_layout)
left_layout.addLayout(buttons_layout)

# QTreeView
fileExplorer = FileExplorer()
right_layout.addWidget(fileExplorer)

class FileDropLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super(FileDropLineEdit, self).__init__(parent)
        self.setAcceptDrops(True)  # 启用拖放
        self.draggedFilePath = ""  # 可以用来存储拖拽进来的文件路径

    def dragEnterEvent(self, e: QDragEnterEvent):
        if e.mimeData().hasUrls():  # 如果拖拽的数据包含URLs
            e.accept()  # 接受拖拽操作
        else:
            e.ignore()  # 否则忽略

    def dropEvent(self, e: QDropEvent):
        urls = e.mimeData().urls()  # 获取拖拽的URLs
        if urls:  # 如果存在URL
            self.draggedFilePath = urls[0].toLocalFile()  # 获取第一个URL的本地文件路径
            self.setText(self.draggedFilePath)  # 显示文件路径


# 调试标签和输入框
debug_label = QLabel("状态")
right_layout.addWidget(debug_label)  # 添加调试标签
debug_text_edit = QTextEdit()
csv_layout = QHBoxLayout()
csv_path_label = QLabel("CSV路径")
csv_path_edit = FileDropLineEdit()


right_layout.addWidget(debug_text_edit)  # 添加调试文本编辑框
csv_layout.addWidget(csv_path_label)
csv_layout.addWidget(csv_path_edit)
right_layout.addLayout(csv_layout)
debug_text_edit.setMinimumHeight(200)


horizontal_layout = QHBoxLayout()
horizontal_layout.addLayout(left_layout)
horizontal_layout.addLayout(right_layout)


conte_layout = QVBoxLayout()

imageLabel = QLabel("分镜预览")
pixmap = QPixmap("/Users/chenxing/Documents/5_AnimeProjectManager/2_footage/placeholder.png")
imageLabel.setPixmap(pixmap.scaled(300, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation))
actionsLabel = QLabel("内容")
actionsInput = QTextEdit("内容")
dialogLabel = QLabel("台词")
dialogInput = QTextEdit("台词")


conte_layout.addWidget(imageLabel)
conte_layout.addWidget(actionsLabel)
conte_layout.addWidget(actionsInput)
conte_layout.addWidget(dialogLabel)
conte_layout.addWidget(dialogInput)
imageLabel.setMinimumWidth(300)

main_layout.addLayout(horizontal_layout)
main_layout.addLayout(conte_layout)

window.setLayout(main_layout)

# QSS样式
window.setStyleSheet("""
    QWidget {
        font-size: 14px;
    }
    QLabel {
        font-weight: bold;
        min-width: 20px;  /* 确保标签宽度足够 */
    }
    QLineEdit, QTextEdit, QComboBox {
        background-color: white;
        border: 1px solid #ccc;
        border-radius: 5px;
        padding: 3px;
        min-height: 10px; /* 统一输入框和下拉框的高度 */
    }
    QComboBox::drop-down {
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 10px; /* 可以根据需要调整宽度 */
        border-left-width: 1px;
        border-left-color: darkgray;
        border-left-style: solid; /* same as the pane border */
        border-top-right-radius: 3px; /* same radius as the QComboBox */
        border-bottom-right-radius: 3px;
    }
    QComboBox::down-arrow {
        image: url('/Users/chenxing/Documents/5_AnimeProjectManager/2_footage/arrowtriangle.down.fill.png'); /* 你需要提供一个实际的图标路径 */
        
    }
    QComboBox QAbstractItemView {
        selection-background-color: #121212; /* 修改选项悬停颜色 */
    }
    QPushButton {
        background-color: #6cb8ff;
        border-radius: 5px;
        color: white;
        padding: 5px 10px;
        margin: 0px;
    }
    QPushButton#submitButton {
        background-color: #ec5b91;
    }
    QPushButton#submitButton:hover {
        background-color: #b92e62;
    }
    QPushButton#csvButton {
        background-color: #4caf50;
    }
    QPushButton#csvButton:hover {
        background-color: #267829;
    }
    QPushButton:hover {
        background-color: #367ec2;
    }
    QMainWindow {
    background-color: #f0f0f0;
    }
    QTreeWidget {
        border: 1px solid #dcdcdc;
        border-radius: 5px;
        show-decoration-selected: 1; /* 确保选择装饰在所有模式下都显示 */
    }
    QTreeWidget::item {
        padding: 2px;
        transition: background-color 0.2s, color 0.2s; /* 平滑过渡动画 */
    }
    QTreeWidget::item:hover {
        background-color: #e0e0e0; /* 鼠标悬停时的背景色 */
    }
    QTreeWidget::item:selected {
        background-color: #0078d7; /* 选中项的背景色（蓝色） */
        color: white;
    }
""")

# 显示主窗口
window.show()

# 运行应用程序
sys.exit(app.exec())


