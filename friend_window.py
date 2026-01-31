# file name: friend_window.py
import os
import json
import keyboard
import subprocess
import shutil
from PyQt5.QtWidgets import QWidget, QLabel, QPushButton, QMessageBox, QTableWidget, QTableWidgetItem, QComboBox, QHeaderView, QApplication, QListWidget, QHBoxLayout, QVBoxLayout, QSplitter
from PyQt5.QtCore import QRect, QTimer, Qt, QPoint
from PyQt5.QtGui import QColor
import datetime
import cv2
import re

from image_ocr_utils import save_debug_images, process_upscaled_debug_images
from capture_overlay import CaptureOverlay

class FriendData:
    def __init__(self, name, screenshot_path=''):
        self.name = name
        self.screenshot_path = screenshot_path
        self.cell_rects = []
        self.excluded_cells = []  # 新增：存储排除区域信息
    
    def to_dict(self):
        return {
            'name': self.name,
            'screenshot_path': self.screenshot_path,
            'cell_rects': self.cell_rects,
            'excluded_cells': self.excluded_cells  # 新增
        }
    
    @staticmethod
    def from_dict(d):
        data = FriendData(
            name=d.get('name', ''),
            screenshot_path=d.get('screenshot_path', '')
        )
        data.cell_rects = d.get('cell_rects', [])
        data.excluded_cells = d.get('excluded_cells', [])  # 新增
        return data

class FriendWindow(QWidget):
    def __init__(self, friend_data, parent=None):
        super().__init__(parent)
        self.friend_data = friend_data
        
        # 初始化变量
        self.selected_cell = None
        self.selected_product = None
        
        # 1. 清空调试目录（防止数据污染）
        self.clear_debug_directories()
        
        # 2. 加载历史数据
        self.load_historical_data()
        
        # 3. 设置界面
        self.setup_ui()
        
    def clear_debug_directories(self):
        """清空调试目录（debug_cells和debug_cells_x）"""
        print(f"[{self.friend_data.name}] 清空调试目录...")
        directories = ['debug_cells', 'debug_cells_x']
        
        for dir_name in directories:
            if os.path.exists(dir_name):
                try:
                    # 遍历目录中的所有文件和子目录
                    for item in os.listdir(dir_name):
                        item_path = os.path.join(dir_name, item)
                        try:
                            if os.path.isfile(item_path) or os.path.islink(item_path):
                                os.unlink(item_path)
                            elif os.path.isdir(item_path):
                                shutil.rmtree(item_path)
                        except Exception as e:
                            print(f"[{self.friend_data.name}] 清理 {item_path} 时出错: {e}")
                    print(f"[{self.friend_data.name}] 已清空目录: {dir_name}")
                except Exception as e:
                    print(f"[{self.friend_data.name}] 清空目录 {dir_name} 失败: {e}")
            else:
                # 如果目录不存在，创建它
                os.makedirs(dir_name, exist_ok=True)
                print(f"[{self.friend_data.name}] 创建目录: {dir_name}")
        
        # 同时清空排除区域列表
        self.excluded_cells = []
        self.friend_data.excluded_cells = []
    
    def load_historical_data(self):
        """加载该好友的历史识别数据"""
        print(f"[{self.friend_data.name}] 加载历史数据...")
        
        try:
            # 导入JSON管理器
            from json_data_manager import JsonDataManager
            json_manager = JsonDataManager()
            
            # 获取该好友的数据
            product_data = json_manager.get_friend_data(self.friend_data.name)
            
            if product_data:
                print(f"[{self.friend_data.name}] 找到历史数据，共 {len(product_data)} 个商品")
                
                # 存储加载的数据
                self.historical_product_data = product_data
                
                # 获取映射信息
                mapping = json_manager.list_all_friends()
                if self.friend_data.name in mapping and mapping[self.friend_data.name]:
                    self.json_filename = mapping[self.friend_data.name]
                    print(f"[{self.friend_data.name}] 数据文件: {self.json_filename}")
                else:
                    self.json_filename = None
            else:
                print(f"[{self.friend_data.name}] 无历史数据")
                self.historical_product_data = {}
                self.json_filename = None
                
        except Exception as e:
            print(f"[{self.friend_data.name}] 加载历史数据失败: {e}")
            self.historical_product_data = {}
            self.json_filename = None
    
    def setup_ui(self):
        """设置界面UI"""
        self.setWindowTitle(f'好友：{self.friend_data.name}')
        self.setFixedSize(1200, 600)  # 加宽窗口
        
        # 使用水平布局
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # 左侧面板
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)
        
        # 截图状态
        status_text = '截图状态：未截图'
        if hasattr(self, 'json_filename') and self.json_filename:
            status_text = f'截图状态：已保存数据 ({self.json_filename})'
        self.label_status = QLabel(status_text)
        
        # 按钮行
        button_layout = QHBoxLayout()
        self.btn_capture = QPushButton('F6截图')
        self.btn_save_debug = QPushButton('保存调试图片')
        self.btn_ocr_debug = QPushButton('识别调试图片')
        self.btn_clear_debug = QPushButton('清空调试目录')
        self.btn_update_data = QPushButton('修改数据')
        self.btn_validate_names = QPushButton('验证商品名称')
        
        # 设置按钮宽度
        for btn in [self.btn_capture, self.btn_save_debug, self.btn_ocr_debug, 
                   self.btn_clear_debug, self.btn_update_data, self.btn_validate_names]:
            btn.setMinimumWidth(100)
        
        button_layout.addWidget(self.btn_capture)
        button_layout.addWidget(self.btn_save_debug)
        button_layout.addWidget(self.btn_ocr_debug)
        button_layout.addWidget(self.btn_clear_debug)
        button_layout.addWidget(self.btn_update_data)
        button_layout.addWidget(self.btn_validate_names)
        
        # 识别结果表格
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(['行', '列', '商品名称', '单价'])
        self.table.setRowCount(0)
        
        # 设置表格列宽
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        
        # 设置表格编辑策略：禁止所有编辑
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        # 添加到左侧布局
        left_layout.addWidget(self.label_status)
        left_layout.addLayout(button_layout)
        left_layout.addWidget(self.table)
        
        # 右侧面板
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)
        
        # 商品列表标题
        self.label_product_list = QLabel('商品列表')
        self.label_product_list.setAlignment(Qt.AlignCenter)
        self.label_product_list.setStyleSheet("font-weight: bold; font-size: 14px;")
        
        # 商品列表
        self.list_products = QListWidget()
        
        # 加载预设商品列表
        self.load_product_list()
        
        # 当前选中显示
        self.label_selected_info = QLabel('当前选中: 无')
        self.label_selected_info.setAlignment(Qt.AlignCenter)
        self.label_selected_info.setStyleSheet("font-weight: bold; color: blue;")
        
        # 操作按钮
        self.btn_select_product = QPushButton('应用选择')
        self.btn_clear_selection = QPushButton('清空选择')
        
        # 操作说明
        self.label_instruction = QLabel(
            '操作步骤:\n'
            '1. 在左侧表格点击要修改的商品\n'
            '2. 在右侧列表点击要选择的商品\n'
            '3. 点击"应用选择"按钮确认修改\n'
            '重复的商品会自动检测并阻止'
        )
        self.label_instruction.setStyleSheet("color: gray; font-size: 12px;")
        
        # 添加到右侧布局
        right_layout.addWidget(self.label_product_list)
        right_layout.addWidget(self.list_products)
        right_layout.addWidget(self.label_selected_info)
        right_layout.addWidget(self.btn_select_product)
        right_layout.addWidget(self.btn_clear_selection)
        right_layout.addWidget(self.label_instruction)
        
        # 添加到主布局
        main_layout.addWidget(left_panel, 2)  # 2份宽度
        main_layout.addWidget(right_panel, 1)  # 1份宽度
        
        # 设置布局
        self.setLayout(main_layout)
        
        # 连接信号
        self.setup_connections()
        
        # 设置全局热键 F6
        self.f6_hook = None
        self.setup_global_hotkey()
        
        # images目录
        self.images_dir = os.path.join(os.getcwd(), 'images')
        if not os.path.exists(self.images_dir):
            os.makedirs(self.images_dir)
            
        # 覆盖层实例
        self.overlay = None
        self.overlay_visible = False
        
        # 集群坐标
        self.cluster_x = 0
        self.cluster_y = 0
        
        # 排除区域列表
        self.excluded_cells = []
        
        # 填充历史数据到表格
        self.populate_historical_data()
    
    def setup_connections(self):
        """设置信号连接"""
        # 按钮连接
        self.btn_capture.clicked.connect(self.show_f6_instruction)
        self.btn_save_debug.clicked.connect(self.save_debug_images)
        self.btn_ocr_debug.clicked.connect(self.ocr_debug_images_with_upscale)
        self.btn_clear_debug.clicked.connect(self.clear_debug_directory)
        self.btn_update_data.clicked.connect(self.update_json_data)
        self.btn_validate_names.clicked.connect(self.validate_product_names)
        
        # 表格连接
        self.table.cellClicked.connect(self.on_table_cell_clicked)
        
        # 列表连接
        self.list_products.itemClicked.connect(self.on_product_item_clicked)
        
        # 操作按钮连接
        self.btn_select_product.clicked.connect(self.apply_product_selection)
        self.btn_clear_selection.clicked.connect(self.clear_selection)
    
    def load_product_list(self):
        """加载预设商品列表"""
        self.product_list = [
            "锚点厨具货组",
            "悬空鼷兽骨雕货组", 
            "巫术矿钻货组",
            "天使罐头货组",
            "谷地水培肉货组",
            "团结牌口服液货组",
            "源石树幼苗货组",
            "赛什卡髀石货组",
            "警戒者矿镐货组",
            "硬脑壳头盔货组",
            "边角料积木货组",
            "星体晶块货组"
        ]
        
        # 清空列表并添加商品
        self.list_products.clear()
        for product in self.product_list:
            self.list_products.addItem(product)
    
    def populate_historical_data(self):
        """将历史数据填充到表格中"""
        if not self.historical_product_data:
            return
        
        print(f"[{self.friend_data.name}] 填充历史数据到表格...")
        
        try:
            # 清空表格
            self.table.setRowCount(0)
            
            # 按商品序号排序
            sorted_keys = sorted(self.historical_product_data.keys(), 
                               key=lambda x: int(x.replace('商品', '')))
            
            row_index = 0
            for key in sorted_keys:
                data = self.historical_product_data[key]
                name = data.get('name', '')
                price = data.get('price', '')
                
                # 从商品序号计算行列
                try:
                    product_num = int(key.replace('商品', ''))
                    row = 1 if product_num <= 7 else 2
                    col = product_num if product_num <= 7 else product_num - 7
                except:
                    row = 0
                    col = 0
                
                # 添加行
                self.table.insertRow(row_index)
                
                # 填充数据
                # 行、列
                self.table.setItem(row_index, 0, QTableWidgetItem(str(row)))
                self.table.setItem(row_index, 1, QTableWidgetItem(str(col)))
                
                # 商品名称 - 设置为不可直接编辑
                name_item = QTableWidgetItem(name)
                name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)  # 禁止编辑
                if name and name not in self.product_list:
                    name_item.setBackground(QColor(255, 200, 150))  # 浅橙色，错误
                self.table.setItem(row_index, 2, name_item)
                
                # 单价 - 允许编辑
                price_item = QTableWidgetItem(price)
                price_item.setFlags(price_item.flags() | Qt.ItemIsEditable)  # 允许编辑
                self.table.setItem(row_index, 3, price_item)
                
                row_index += 1
            
            print(f"[{self.friend_data.name}] 填充完成，共 {row_index} 行数据")
            
            # 更新状态标签
            if self.json_filename:
                self.label_status.setText(f'截图状态：已加载数据 ({self.json_filename})')
                
        except Exception as e:
            print(f"[{self.friend_data.name}] 填充历史数据失败: {e}")
    
    def setup_global_hotkey(self):
        """设置全局热键 F6"""
        try:
            # 移除之前的热键
            self.remove_global_hotkey()
            
            # 设置F6热键
            self.f6_hook = keyboard.add_hotkey('f6', self.on_f6_pressed)
            
            print(f"[{self.friend_data.name}] 全局热键已设置: F6=显示截图覆盖层")
            
        except Exception as e:
            print(f"[{self.friend_data.name}] 设置全局热键失败: {e}")
            QTimer.singleShot(1000, self.setup_global_hotkey)
    
    def remove_global_hotkey(self):
        """移除全局热键"""
        try:
            if self.f6_hook:
                keyboard.remove_hotkey('f6')
                self.f6_hook = None
        except:
            pass
    
    # ================== 商品修改功能 ==================
    
    def on_table_cell_clicked(self, row, column):
        """当表格单元格被点击时触发"""
        if column == 2:  # 商品名称列
            name_item = self.table.item(row, column)
            if name_item:
                # 记录选中的单元格
                self.selected_cell = (row, column)
                
                # 高亮显示选中的行
                self.highlight_selected_row(row)
                
                current_name = name_item.text().strip()
                print(f"选中表格单元格: 第{row+1}行, 商品名称: '{current_name}'")
                
                # 更新选中信息
                self.update_selected_info()
        elif column == 3:  # 价格列 - 允许直接编辑
            price_item = self.table.item(row, column)
            if price_item:
                # 设置可编辑
                price_item.setFlags(price_item.flags() | Qt.ItemIsEditable)
                # 触发编辑模式
                self.table.editItem(price_item)
    
    def on_product_item_clicked(self, item):
        """当商品列表项被点击时触发"""
        if item:
            self.selected_product = item.text()
            print(f"选中商品: '{self.selected_product}'")
            
            # 更新选中信息
            self.update_selected_info()
    
    def update_selected_info(self):
        """更新选中信息显示"""
        info_text = "当前选中: "
        
        if self.selected_cell:
            row, col = self.selected_cell
            name_item = self.table.item(row, col)
            current_name = name_item.text().strip() if name_item else ""
            info_text += f"表格第{row+1}行 ('{current_name}')"
        
        if self.selected_product:
            if self.selected_cell:
                info_text += " | "
            info_text += f"商品 '{self.selected_product}'"
        
        if not self.selected_cell and not self.selected_product:
            info_text += "无"
        
        self.label_selected_info.setText(info_text)
    
    def apply_product_selection(self):
        """应用商品选择到表格"""
        if not self.selected_cell:
            QMessageBox.warning(self, "未选择表格项", "请先在表格中点击要修改的商品")
            return
        
        if not self.selected_product:
            QMessageBox.warning(self, "未选择商品", "请在右侧列表中选择一个商品")
            return
        
        row, col = self.selected_cell
        
        # 检查是否已经存在相同的商品
        if self.is_product_duplicate(self.selected_product, row):
            QMessageBox.warning(
                self,
                "重复商品",
                f"商品 '{self.selected_product}' 已经存在，不能重复选择！"
            )
            return
        
        # 更新表格
        self.update_table_cell(row, col, self.selected_product)
        
        print(f"应用选择: 第{row+1}行 → '{self.selected_product}'")
        
        # 清除选中状态
        self.clear_selection()
        
        # 重新验证所有商品名称
        QTimer.singleShot(100, self.validate_product_names)
    
    def clear_selection(self):
        """清除所有选中状态"""
        self.selected_cell = None
        self.selected_product = None
        
        # 清除表格高亮
        self.clear_table_highlight()
        
        # 更新选中信息
        self.update_selected_info()
        
        print("已清除所有选中状态")
    
    def highlight_selected_row(self, row):
        """高亮显示选中的行"""
        # 清除之前的高亮
        self.clear_table_highlight()
        
        # 高亮当前行
        for col in range(self.table.columnCount()):
            item = self.table.item(row, col)
            if item:
                item.setBackground(QColor(200, 230, 255))  # 浅蓝色高亮
    
    def clear_table_highlight(self):
        """清除表格高亮"""
        for row in range(self.table.rowCount()):
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item:
                    # 根据商品名称正确性设置背景色
                    if col == 2:  # 商品名称列
                        name = item.text().strip()
                        if name and name not in self.product_list:
                            item.setBackground(QColor(255, 200, 150))  # 浅橙色，错误
                        else:
                            item.setBackground(QColor(255, 255, 255))  # 白色
                    else:
                        item.setBackground(QColor(255, 255, 255))  # 白色
    
    def update_table_cell(self, row, col, value):
        """安全更新表格单元格"""
        if 0 <= row < self.table.rowCount() and 0 <= col < self.table.columnCount():
            # 临时断开表格的信号，避免触发其他事件
            self.table.blockSignals(True)
            
            item = self.table.item(row, col)
            if not item:
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)  # 禁止编辑
                self.table.setItem(row, col, item)
            else:
                item.setText(value)
            
            # 设置背景色
            if value and value in self.product_list:
                item.setBackground(QColor(255, 255, 255))  # 白色，正确
            elif value:
                item.setBackground(QColor(255, 200, 150))  # 浅橙色，错误
            else:
                item.setBackground(QColor(255, 255, 255))  # 白色
            
            # 恢复表格信号
            self.table.blockSignals(False)
            
            # 强制表格更新显示
            self.table.viewport().update()
            
            print(f"更新表格: 第{row+1}行第{col+1}列 = '{value}'")
    
    def is_product_duplicate(self, product_name, exclude_row):
        """检查商品是否重复（排除指定行）"""
        if not product_name:
            return False
            
        for row in range(self.table.rowCount()):
            if row == exclude_row:  # 跳过当前行
                continue
                
            name_item = self.table.item(row, 2)
            if name_item and name_item.text().strip() == product_name:
                return True
        
        return False
    
    def validate_product_names(self):
        """验证所有商品名称是否正确"""
        print(f"[{self.friend_data.name}] 开始验证商品名称...")
        
        # 检查每个单元格
        for row in range(self.table.rowCount()):
            name_item = self.table.item(row, 2)
            if not name_item:
                continue
                
            name = name_item.text().strip()
            
            if not name:  # 空单元格
                name_item.setBackground(QColor(255, 255, 255))  # 白色
                continue
                
            # 检查是否在预设列表中
            if name in self.product_list:
                name_item.setBackground(QColor(255, 255, 255))  # 白色，正确
                print(f"  第{row+1}行: '{name}' ✓ 正确")
            else:
                name_item.setBackground(QColor(255, 200, 150))  # 浅橙色，错误
                print(f"  第{row+1}行: '{name}' ✗ 不在预设列表中")
        
        # 检查重复项
        self.check_duplicate_names()
        
        print(f"[{self.friend_data.name}] 商品名称验证完成")
    
    def check_duplicate_names(self):
        """检查是否有重复的商品名称"""
        name_count = {}
        
        # 统计每个商品名称出现的次数
        for row in range(self.table.rowCount()):
            name_item = self.table.item(row, 2)
            if name_item:
                name = name_item.text().strip()
                if name:
                    if name in name_count:
                        name_count[name] += 1
                    else:
                        name_count[name] = 1
        
        # 标记重复项为红色
        for row in range(self.table.rowCount()):
            name_item = self.table.item(row, 2)
            if name_item:
                name = name_item.text().strip()
                if name and name_count.get(name, 0) > 1:
                    name_item.setBackground(QColor(255, 150, 150))  # 红色，重复
                    print(f"  警告: 第{row+1}行的'{name}'是重复项")
    
    # ================== 原有功能（保持不变） ==================
    
    def show_f6_instruction(self):
        """显示F6使用提示"""
        QMessageBox.information(
            self,
            '使用说明',
            '按 F6 键开始截图（全局热键，无需切换窗口）\n\n'
            '在覆盖层中：\n'
            '• F7键或点击"截图"按钮：执行截图\n'
            '• ESC键或点击"取消"按钮：取消截图\n'
            '• 鼠标点击空白商品区域：标记为红色（不处理）\n\n'
            '文件命名规范：\n'
            'YYYYMMDD_HHMMSS_[type]_[行]_[列].png\n'
            'type: text(商品名称) 或 price(单价)'
        )
    
    def on_f6_pressed(self):
        """F6键按下时的处理"""
        print(f"[{self.friend_data.name}] 检测到F6键按下，显示覆盖层")
        QTimer.singleShot(0, self.show_capture_overlay)
    
    def show_capture_overlay(self):
        """显示截图引导覆盖层"""
        print(f"[{self.friend_data.name}] 准备显示覆盖层")
        
        if self.overlay and self.overlay.isVisible():
            print(f"[{self.friend_data.name}] 覆盖层已显示，先关闭")
            self.overlay.close()
        
        try:
            self.overlay = CaptureOverlay()
            if self.overlay:
                self.overlay.capture_completed.connect(self.on_capture_completed)
                self.overlay.closed.connect(self.on_overlay_closed)
                self.overlay.show()
                self.overlay_visible = True
                print(f"[{self.friend_data.name}] 覆盖层显示成功")
                self.overlay.activateWindow()
                self.overlay.raise_()
            else:
                print(f"[{self.friend_data.name}] 创建覆盖层失败")
                
        except Exception as e:
            print(f"[{self.friend_data.name}] 显示覆盖层时出错: {e}")
            import traceback
            traceback.print_exc()
    
    def on_overlay_closed(self):
        """覆盖层关闭时的处理"""
        print(f"[{self.friend_data.name}] 覆盖层关闭信号收到")
        self.overlay_visible = False
    
    def on_capture_completed(self, image_path, cell_rects, cluster_x, cluster_y, excluded_cells):
        """截图完成后的处理 - 新增excluded_cells参数"""
        print(f"[{self.friend_data.name}] 截图完成信号收到: {image_path}")
        print(f"[{self.friend_data.name}] 排除区域列表: {excluded_cells}")
        
        if not image_path or not os.path.exists(image_path):
            print(f"[{self.friend_data.name}] 截图文件不存在")
            QMessageBox.warning(self, '错误', '截图文件保存失败')
            return
        
        # 保存数据
        self.friend_data.cell_rects = cell_rects
        self.friend_data.excluded_cells = excluded_cells  # 保存排除区域
        self.cluster_x = cluster_x
        self.cluster_y = cluster_y
        self.excluded_cells = excluded_cells
        
        # 生成安全文件名
        now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_name = re.sub(r'[^a-zA-Z0-9]', '_', self.friend_data.name)
        if not safe_name.strip('_'):
            safe_name = 'friend'
        filename = f'{safe_name}_{now}.png'
        save_path = os.path.join(self.images_dir, filename)
        
        try:
            # 移动文件
            if image_path != save_path:
                import shutil
                if os.path.exists(save_path):
                    os.remove(save_path)
                shutil.move(image_path, save_path)
                print(f"[{self.friend_data.name}] 文件已移动: {image_path} -> {save_path}")
            
            # 更新数据
            self.friend_data.screenshot_path = save_path
            status_text = f'截图状态：已截图 {now}'
            if excluded_cells:
                status_text += f' (排除{len(excluded_cells)}个区域)'
            self.label_status.setText(status_text)
            
            print(f"[{self.friend_data.name}] 截图保存成功: {save_path}")
            print(f"[{self.friend_data.name}] 排除区域数: {len(excluded_cells)}")
            
            QTimer.singleShot(300, lambda: self.show_capture_success(save_path, excluded_cells))
            
        except Exception as e:
            print(f"[{self.friend_data.name}] 保存截图失败: {e}")
            QMessageBox.warning(self, '错误', f'保存截图失败: {str(e)}')
    
    def show_capture_success(self, save_path, excluded_cells):
        """显示截图成功消息"""
        message = f'截图已保存到:\n{save_path}\n\n'
        message += f'文件命名规范:\nYYYYMMDD_HHMMSS_[type]_[行]_[列].png\n\n'
        
        if excluded_cells:
            excluded_str = ', '.join([f'{r+1}-{c+1}' for r, c in excluded_cells])
            message += f'已标记排除区域: {excluded_str}\n\n'
        
        message += f'现在可以点击"保存调试图片"按钮保存区域图像。\n'
        message += f'（排除的区域将不会被保存）'
        
        QMessageBox.information(
            self, 
            '截图完成', 
            message
        )
    
    def save_debug_images(self):
        """保存调试图片 - 新增excluded_cells参数"""
        if not self.friend_data.screenshot_path:
            QMessageBox.warning(self, '提示', '请先按F6截图')
            return
        
        if not self.friend_data.cell_rects:
            QMessageBox.warning(self, '提示', '没有单元格位置信息，请先截图')
            return
        
        try:
            # 导入更新后的函数
            from image_ocr_utils import save_debug_images_with_exclusion
            
            timestamp = save_debug_images_with_exclusion(
                self.friend_data.screenshot_path,
                self.friend_data.cell_rects,
                self.cluster_x,
                self.cluster_y,
                self.friend_data.excluded_cells  # 传递排除区域
            )
            
            if timestamp:
                message = f'调试图片已保存到: debug_cells/\n'
                message += f'时间戳: {timestamp}\n'
                message += f'命名格式: {timestamp}_text_[行]_[列].png\n'
                message += f'命名格式: {timestamp}_price_[行]_[列].png\n\n'
                
                if self.friend_data.excluded_cells:
                    excluded_count = len(self.friend_data.excluded_cells)
                    total_cells = len(self.friend_data.cell_rects)
                    processed_count = total_cells - excluded_count
                    message += f'处理统计:\n'
                    message += f'• 总单元格数: {total_cells}\n'
                    message += f'• 排除区域数: {excluded_count}\n'
                    message += f'• 实际处理: {processed_count}个单元格\n\n'
                
                message += f'现在可以点击"识别调试图片"按钮进行OCR识别（将自动放大图片）。'
                
                QMessageBox.information(
                    self, 
                    '调试图片已保存',
                    message
                )
            else:
                QMessageBox.warning(self, '错误', '保存调试图片失败')
            
        except Exception as e:
            QMessageBox.warning(self, '错误', f'保存调试图片失败: {str(e)}')
            import traceback
            traceback.print_exc()
    
    def ocr_debug_images_with_upscale(self):
        """识别调试图片（使用Tesseract命令行，保存JSON数据）"""
        try:
            # 检查原始调试目录是否存在
            debug_dir = 'debug_cells'
            if not os.path.exists(debug_dir):
                QMessageBox.warning(self, '提示', '请先点击"保存调试图片"按钮生成调试图片')
                return
            
            # 检查放大工具是否存在
            upscale_tool_path = os.path.join('realesrgan-ncnn-vulkan', 'realesrgan-ncnn-vulkan.exe')
            if not os.path.exists(upscale_tool_path):
                QMessageBox.warning(
                    self,
                    '工具缺失',
                    f'找不到放大工具:\n{upscale_tool_path}\n\n'
                    f'请将 realesrgan-ncnn-vulkan.exe 放在指定目录。'
                )
                return
            
            # 创建放大后的目录
            upscaled_dir = 'debug_cells_x'
            if os.path.exists(upscaled_dir):
                # 清空现有目录内容
                shutil.rmtree(upscaled_dir)
                print(f"[{self.friend_data.name}] 已清空现有目录: {upscaled_dir}")
            
            os.makedirs(upscaled_dir, exist_ok=True)
            print(f"[{self.friend_data.name}] 创建放大目录: {upscaled_dir}")
            
            # 获取所有需要放大的图片文件
            image_files = []
            for file in os.listdir(debug_dir):
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.webp')):
                    image_files.append(file)
            
            if not image_files:
                QMessageBox.warning(self, '提示', 'debug_cells目录中没有找到图片文件')
                return
            
            total_files = len(image_files)
            print(f"[{self.friend_data.name}] 找到 {total_files} 张图片需要放大")
            
            # 进度提示
            self.label_status.setText(f'正在放大图片: 0/{total_files}')
            message = f'开始批量放大图片\n\n'
            message += f'原始目录: {debug_dir}\n'
            message += f'放大目录: {upscaled_dir}\n'
            message += f'图片数量: {total_files}\n\n'
            message += f'处理需要一些时间，请稍候...'
            
            QMessageBox.information(self, '开始放大处理', message)
            
            # 批量放大图片
            processed_count = 0
            failed_files = []
            
            for i, filename in enumerate(image_files):
                try:
                    input_path = os.path.join(debug_dir, filename)
                    output_path = os.path.join(upscaled_dir, filename)
                    
                    # 更新状态
                    self.label_status.setText(f'正在放大图片: {i+1}/{total_files} ({filename})')
                    
                    # 执行放大命令
                    cmd = [
                        upscale_tool_path,
                        '-i', input_path,
                        '-o', output_path,
                        '-n', 'realesrgan-x4plus'
                    ]
                    
                    print(f"[{self.friend_data.name}] 执行命令: {' '.join(cmd)}")
                    
                    # 运行放大工具
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=60  # 每张图片最多60秒
                    )
                    
                    if result.returncode == 0 and os.path.exists(output_path):
                        print(f"[{self.friend_data.name}] ✓ 图片放大成功: {filename}")
                        processed_count += 1
                    else:
                        error_msg = result.stderr if result.stderr else "未知错误"
                        print(f"[{self.friend_data.name}] ✗ 图片放大失败 {filename}: {error_msg}")
                        failed_files.append(filename)
                        
                        # 如果放大失败，复制原始文件到输出目录作为备用
                        shutil.copy2(input_path, output_path)
                        print(f"[{self.friend_data.name}]   已复制原始文件作为备用: {filename}")
                
                except subprocess.TimeoutExpired:
                    print(f"[{self.friend_data.name}] ✗ 图片处理超时: {filename}")
                    failed_files.append(filename)
                    
                    # 超时情况下也复制原始文件
                    shutil.copy2(input_path, output_path)
                    print(f"[{self.friend_data.name}]   已复制原始文件（超时）: {filename}")
                
                except Exception as e:
                    print(f"[{self.friend_data.name}] ✗ 处理图片时出错 {filename}: {e}")
                    failed_files.append(filename)
                    
                    # 出错情况下也复制原始文件
                    shutil.copy2(input_path, output_path)
                    print(f"[{self.friend_data.name}]   已复制原始文件（出错）: {filename}")
            
            # 放大完成统计
            print(f"[{self.friend_data.name}] 放大处理完成统计:")
            print(f"  总图片数: {total_files}")
            print(f"  成功放大: {processed_count}")
            print(f"  失败/备用: {len(failed_files)}")
            
            if failed_files:
                print(f"[{self.friend_data.name}]   失败文件列表: {failed_files[:5]}")  # 只显示前5个
            
            self.label_status.setText(f'图片放大完成: {processed_count}/{total_files} 成功')
            
            # 开始OCR识别（使用放大后的图片）
            print(f"[{self.friend_data.name}] 开始OCR识别（使用放大后的图片）...")
            self.label_status.setText(f'开始OCR识别...')
            
            # 调用处理放大目录的函数，传入好友名
            from image_ocr_utils import process_upscaled_debug_images
            results, product_data = process_upscaled_debug_images(
                upscaled_dir, 
                self.friend_data.name  # 传递好友名
            )
            
            if not results:
                QMessageBox.warning(self, '识别结果', '未识别到任何内容')
                return
            
            # 清空表格
            self.table.setRowCount(len(results))
            
            # 填充表格（只有4列，不再有"完整文本"列）
            for i, result in enumerate(results):
                name = result['text']
                price = result['price']
                
                # 行、列
                self.table.setItem(i, 0, QTableWidgetItem(str(result['row'])))
                self.table.setItem(i, 1, QTableWidgetItem(str(result['col'])))
                
                # 商品名称 - 设置为不可直接编辑
                name_item = QTableWidgetItem(name)
                name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)  # 禁止编辑
                if name and name not in self.product_list:
                    name_item.setBackground(QColor(255, 200, 150))  # 浅橙色，错误
                self.table.setItem(i, 2, name_item)
                
                # 单价 - 允许编辑
                price_item = QTableWidgetItem(price)
                price_item.setFlags(price_item.flags() | Qt.ItemIsEditable)  # 允许编辑
                self.table.setItem(i, 3, price_item)
            
            # 统计
            text_count = sum(1 for r in results if r['text'].strip())
            price_count = sum(1 for r in results if r['price'].strip())
            corrected_count = sum(1 for r in results if r.get('name_corrected', False))
            raw_text_count = sum(1 for r in results if r.get('name_raw', '').strip())
            
            # 显示处理结果
            success_msg = f'处理完成！\n\n'
            success_msg += f'图片放大: {processed_count}/{total_files} 成功\n'
            
            if failed_files:
                success_msg += f'（{len(failed_files)} 张使用原始图片）\n\n'
            else:
                success_msg += '\n'
            
            success_msg += f'OCR识别结果:\n'
            success_msg += f'• 原始商品名称识别: {raw_text_count}个\n'
            success_msg += f'• 商品名称自动纠正: {corrected_count}个\n'
            success_msg += f'• 最终商品名称: {text_count}个\n'
            success_msg += f'• 成功识别单价: {price_count}个\n'
            success_msg += f'• 总单元格数: {len(results)}个\n\n'
            
            # 如果有排除区域，显示排除信息
            if hasattr(self.friend_data, 'excluded_cells') and self.friend_data.excluded_cells:
                excluded_count = len(self.friend_data.excluded_cells)
                success_msg += f'• 已排除区域: {excluded_count}个\n\n'
            
            # 显示纠正示例
            if corrected_count > 0:
                success_msg += f'纠正示例:\n'
                example_count = 0
                for result in results:
                    if result.get('name_corrected', False) and example_count < 3:  # 只显示3个示例
                        success_msg += f'  {result["product_key"]}: "{result.get("name_raw", "")}" → "{result["text"]}"\n'
                        example_count += 1
            
            # 显示JSON保存信息
            success_msg += f'\n数据已保存到JSON文件\n'
            success_msg += f'• 好友: {self.friend_data.name}\n'
            success_msg += f'• 商品数量: {len(product_data)}个\n'
            success_msg += f'• 格式: {{"商品1": {{"name": "", "price": "123"}}, ...}}\n'
            success_msg += f'• 目录: tempJson/\n'
            
            QMessageBox.information(self, '处理完成', success_msg)
            
            self.label_status.setText(f'识别完成: {text_count}个商品, {price_count}个单价')
            
            # 更新历史数据
            self.historical_product_data = product_data
            
            # 更新状态显示
            try:
                from json_data_manager import JsonDataManager
                json_manager = JsonDataManager()
                mapping = json_manager.list_all_friends()
                if self.friend_data.name in mapping and mapping[self.friend_data.name]:
                    self.json_filename = mapping[self.friend_data.name]
                    self.label_status.setText(f'截图状态：已保存数据 ({self.json_filename})')
            except:
                pass
            
        except Exception as e:
            error_msg = f'处理过程中出错: {str(e)}'
            print(error_msg)
            import traceback
            traceback.print_exc()
            
            QMessageBox.warning(self, '处理错误', error_msg)
            self.label_status.setText('处理出错')
    
    def ocr_debug_images(self):
        """原有的OCR识别函数（已弃用，保留用于兼容）"""
        QMessageBox.information(
            self,
            '功能已更新',
            '原"识别调试图片"功能已升级为"先放大再识别"。\n\n'
            '请使用新的处理流程。'
        )
        # 调用新的函数
        self.ocr_debug_images_with_upscale()
    
    def clear_debug_directory(self):
        """清空调试目录（包括原始和放大后的目录）"""
        try:
            from image_ocr_utils import clear_debug_directory
            # 清空原始调试目录
            clear_debug_directory()
            # 清空放大后的目录内容（不删除目录本身）
            upscaled_dir = 'debug_cells_x'
            if os.path.exists(upscaled_dir):
                for item in os.listdir(upscaled_dir):
                    item_path = os.path.join(upscaled_dir, item)
                    try:
                        if os.path.isfile(item_path) or os.path.islink(item_path):
                            os.unlink(item_path)
                        elif os.path.isdir(item_path):
                            shutil.rmtree(item_path)
                    except Exception as e:
                        print(f"[{self.friend_data.name}] 清理 {item_path} 时出错: {e}")
                print(f"[{self.friend_data.name}] 已清空放大目录内容: {upscaled_dir}")
            # 重置排除区域
            self.excluded_cells = []
            if hasattr(self.friend_data, 'excluded_cells'):
                self.friend_data.excluded_cells = []
            QMessageBox.information(self, '清空成功', '已清空所有调试目录内容（包括放大目录）')
        except Exception as e:
            QMessageBox.warning(self, '清空失败', f'清空调试目录失败: {str(e)}')
    
    def update_json_data(self):
        """将修改后的数据更新到JSON文件"""
        print(f"[{self.friend_data.name}] 开始更新JSON数据...")
        
        try:
            # 验证所有商品名称
            self.validate_product_names()
            
            # 检查是否有错误的商品名称
            has_error = False
            error_rows = []
            
            for row in range(self.table.rowCount()):
                name_item = self.table.item(row, 2)
                if name_item:
                    name = name_item.text().strip()
                    if name and name not in self.product_list:
                        has_error = True
                        error_rows.append(row + 1)
            
            if has_error:
                reply = QMessageBox.question(
                    self,
                    "存在错误商品名称",
                    f"第 {', '.join(map(str, error_rows))} 行的商品名称不在预设列表中。\n\n是否继续更新？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if reply == QMessageBox.No:
                    return
            
            # 检查重复项
            duplicate_check = self.check_duplicate_names_in_table()
            if duplicate_check['has_duplicate']:
                duplicate_msg = "存在重复的商品名称：\n"
                for name, rows in duplicate_check['duplicates'].items():
                    duplicate_msg += f"  '{name}'：第{', '.join(map(str, rows))}行\n"
                
                reply = QMessageBox.question(
                    self,
                    "存在重复商品名称",
                    duplicate_msg + "\n是否继续更新？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if reply == QMessageBox.No:
                    return
            
            # 构建新的商品数据
            product_data = {}
            
            for row in range(self.table.rowCount()):
                # 获取商品序号
                row_item = self.table.item(row, 0)  # 第0列是行号
                col_item = self.table.item(row, 1)  # 第1列是列号
                
                if row_item and col_item:
                    try:
                        row_num = int(row_item.text())
                        col_num = int(col_item.text())
                        product_index = (row_num - 1) * 7 + col_num
                        product_key = f"商品{product_index}"
                    except:
                        continue
                else:
                    # 如果行号列号为空，按行序计算
                    product_key = f"商品{row+1}"
                
                # 获取商品名称和价格
                name_item = self.table.item(row, 2)
                price_item = self.table.item(row, 3)
                
                name = name_item.text().strip() if name_item else ""
                price = price_item.text().strip() if price_item else ""
                
                product_data[product_key] = {
                    "name": name,
                    "price": price
                }
            
            # 保存到JSON
            from json_data_manager import JsonDataManager
            json_manager = JsonDataManager()
            
            if json_manager:
                json_filename = json_manager.save_product_data(
                    self.friend_data.name, 
                    product_data, 
                    self.generate_timestamp()
                )
                
                if json_filename:
                    self.label_status.setText(f'截图状态：数据已更新 ({json_filename})')
                    QMessageBox.information(
                        self,
                        "更新成功",
                        f"JSON数据已更新\n\n文件: {json_filename}\n商品数量: {len(product_data)}"
                    )
                    print(f"[{self.friend_data.name}] JSON数据更新成功: {json_filename}")
                    
                    # 更新内存中的数据
                    self.historical_product_data = product_data
                else:
                    QMessageBox.warning(self, "更新失败", "保存JSON文件失败")
            else:
                QMessageBox.warning(self, "更新失败", "JSON管理器未初始化")
                
        except Exception as e:
            QMessageBox.warning(self, "更新失败", f"更新JSON数据时出错:\n{str(e)}")
            print(f"[{self.friend_data.name}] 更新JSON数据失败: {e}")
            import traceback
            traceback.print_exc()
    
    def check_duplicate_names_in_table(self):
        """检查表格中的重复商品名称，返回详细信息"""
        name_rows = {}  # 商品名称 -> [行号列表]
        
        for row in range(self.table.rowCount()):
            name_item = self.table.item(row, 2)
            if name_item:
                name = name_item.text().strip()
                if name:
                    if name in name_rows:
                        name_rows[name].append(row + 1)
                    else:
                        name_rows[name] = [row + 1]
        
        # 找出重复的商品名称
        duplicates = {}
        for name, rows in name_rows.items():
            if len(rows) > 1:
                duplicates[name] = rows
        
        return {
            'has_duplicate': len(duplicates) > 0,
            'duplicates': duplicates
        }
    
    def generate_timestamp(self):
        """生成时间戳"""
        from datetime import datetime
        return datetime.now().strftime('%Y%m%d_%H%M%S')
    
    def focusOutEvent(self, event):
        """当下拉菜单失去焦点时隐藏"""
        super().focusOutEvent(event)
    
    def closeEvent(self, event):
        """关闭窗口时清理热键"""
        print(f"[{self.friend_data.name}] 关闭好友窗口，清理热键")
        self.remove_global_hotkey()
        
        if self.overlay and self.overlay.isVisible():
            self.overlay.close()
        
        super().closeEvent(event)
    
    def to_json(self):
        return json.dumps(self.friend_data.to_dict(), ensure_ascii=False)
    
    @staticmethod
    def from_json(json_str):
        d = json.loads(json_str)
        return FriendData.from_dict(d)