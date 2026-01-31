# file name: ui_main.py
from PyQt5.QtWidgets import QWidget, QLabel, QLineEdit, QPushButton, QListWidget, QMessageBox, QComboBox, QTableWidget, QTableWidgetItem, QVBoxLayout, QHBoxLayout, QFrame
from PyQt5.QtCore import QRect
from PyQt5 import QtGui
from friend_window import FriendWindow, FriendData
import os
import shutil
import json

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('终末地物资助手')
        self.setFixedSize(1440, 1080)
        
        # 商品信息输入
        self.label_name = QLabel('商品名称:', self)
        self.input_name = QComboBox(self)
        self.input_name.addItems([
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
        ])
        self.label_price = QLabel('买入单价:', self)
        self.input_price = QLineEdit(self)
        self.label_amount = QLabel('买入数量:', self)
        self.input_amount = QLineEdit(self)
        
        # 好友管理
        self.label_friend = QLabel('好友名称:', self)
        self.input_friend = QLineEdit(self)
        self.btn_add_friend = QPushButton('添加好友', self)
        self.btn_add_friend.clicked.connect(self.add_friend)
        
        self.friend_list = QListWidget(self)
        
        self.btn_delete_friend = QPushButton('删除好友', self)
        self.btn_delete_friend.clicked.connect(self.delete_friend)
        
        self.btn_open_friend = QPushButton('打开子界面', self)
        self.btn_open_friend.clicked.connect(self.open_friend_window)
        
        self.btn_calc_profit = QPushButton('计算利润', self)
        self.btn_calc_profit.clicked.connect(self.calc_profit)
        
        # 新增：重置好友数据按钮
        self.btn_reset_friend = QPushButton('重置好友数据', self)
        self.btn_reset_friend.clicked.connect(self.reset_friend_data)
        
        self.btn_factory_reset = QPushButton('恢复出厂设置', self)
        self.btn_factory_reset.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:pressed {
                background-color: #b71c1c;
            }
        """)
        self.btn_factory_reset.clicked.connect(self.factory_reset)
        
        # 利润排行表格（右侧）
        self.table_profit = QTableWidget(self)
        self.table_profit.setColumnCount(4)
        self.table_profit.setHorizontalHeaderLabels(['好友', '商品', '单价', '利润'])
        self.table_profit.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_profit.setSelectionMode(QTableWidget.NoSelection)
        self.table_profit.verticalHeader().setVisible(False)
        self.table_profit.horizontalHeader().setStretchLastSection(True)
        
        # --- 新布局 ---
        # 左侧：商品信息和好友管理
        left_panel = QFrame(self)
        left_panel.setGeometry(QRect(20, 20, 600, 1050))
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        # 商品信息输入行
        info_row = QHBoxLayout()
        info_row.addWidget(self.label_name)
        info_row.addWidget(self.input_name)
        info_row.addWidget(self.label_price)
        info_row.addWidget(self.input_price)
        info_row.addWidget(self.label_amount)
        info_row.addWidget(self.input_amount)
        left_layout.addLayout(info_row)

        # 好友管理行
        friend_row = QHBoxLayout()
        friend_row.addWidget(self.label_friend)
        friend_row.addWidget(self.input_friend)
        left_layout.addLayout(friend_row)

        # 好友操作按钮列
        btn_col = QVBoxLayout()
        btn_col.setSpacing(10)
        btn_col.addWidget(self.btn_add_friend)
        btn_col.addWidget(self.btn_delete_friend)
        btn_col.addWidget(self.btn_open_friend)
        btn_col.addWidget(self.btn_reset_friend)
        btn_col.addWidget(self.btn_calc_profit)
        btn_col.addWidget(self.btn_factory_reset)
        # 让按钮列靠上
        btn_col.addStretch(1)

        # 好友列表和按钮列并排
        friend_list_row = QHBoxLayout()
        friend_list_row.addWidget(self.friend_list)
        friend_list_row.addLayout(btn_col)
        left_layout.addLayout(friend_list_row)

        # --- 利润表格放在右侧 ---
        self.table_profit.setParent(self)
        self.table_profit.setGeometry(QRect(650, 100, 750, 900))
        self.table_profit.setColumnCount(4)
        self.table_profit.setHorizontalHeaderLabels(['好友', '商品', '单价', '利润'])
        self.table_profit.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_profit.setSelectionMode(QTableWidget.NoSelection)
        self.table_profit.verticalHeader().setVisible(False)
        self.table_profit.horizontalHeader().setStretchLastSection(True)
        
        # 数据
        self.friends = []
        self.friend_data_map = {}  # 好友名->FriendData
        self.friend_windows = []   # 存储所有打开的FriendWindow实例
        
        # 启动时加载好友列表
        self.load_friends_on_startup()
    
    def load_friends_on_startup(self):
        """程序启动时从friend_mapping.json加载好友列表"""
        try:
            mapping_file = 'friend_mapping.json'
            if os.path.exists(mapping_file):
                with open(mapping_file, 'r', encoding='utf-8') as f:
                    mapping = json.load(f)
                
                # mapping中的键就是好友名
                for friend_name in mapping.keys():
                    if friend_name and friend_name not in self.friends:
                        self.friends.append(friend_name)
                        self.friend_list.addItem(friend_name)
                        # 创建FriendData对象
                        self.friend_data_map[friend_name] = FriendData(friend_name)
                
                print(f"[主窗口] 从映射文件加载了 {len(self.friends)} 个好友")
            else:
                print("[主窗口] 映射文件不存在，初始化为空列表")
        except Exception as e:
            print(f"[主窗口] 加载好友列表失败: {e}")
            # 确保friends和friend_list为空
            self.friends = []
            self.friend_list.clear()
    
    def add_friend(self):
        name = self.input_friend.text().strip()
        if name and name not in self.friends:
            self.friends.append(name)
            self.friend_list.addItem(name)
            self.input_friend.clear()
            self.friend_data_map[name] = FriendData(name)
            
            # 立即更新映射文件
            self.update_friend_mapping(name, '')
            
            print(f"[主窗口] 添加好友: {name}")
        else:
            QMessageBox.warning(self, '提示', '好友名为空或已存在')
    
    def update_friend_mapping(self, friend_name, json_filename=''):
        """更新好友映射"""
        try:
            mapping_file = 'friend_mapping.json'
            mapping = {}
            
            # 读取现有映射
            if os.path.exists(mapping_file):
                with open(mapping_file, 'r', encoding='utf-8') as f:
                    mapping = json.load(f)
            
            # 更新或添加
            if json_filename:
                mapping[friend_name] = json_filename
            else:
                # 如果没有json文件，只添加好友名（值为空字符串）
                mapping[friend_name] = ''
            
            # 写回文件
            with open(mapping_file, 'w', encoding='utf-8') as f:
                json.dump(mapping, f, ensure_ascii=False, indent=2)
                
            print(f"[主窗口] 更新映射: {friend_name} -> {json_filename if json_filename else '(空)'}")
            return True
            
        except Exception as e:
            print(f"[主窗口] 更新映射失败: {e}")
            return False
    
    def delete_friend(self):
        row = self.friend_list.currentRow()
        if row >= 0:
            name = self.friend_list.item(row).text()
            
            # 确认对话框
            reply = QMessageBox.question(
                self,
                '确认删除',
                f'确定要删除好友 "{name}" 吗？\n\n'
                '这将：\n'
                '1. 从列表中移除好友\n'
                '2. 删除该好友的JSON数据文件\n'
                '3. 更新好友映射\n'
                '4. 关闭该好友的所有窗口',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # 1. 删除JSON数据文件
                try:
                    from json_data_manager import JsonDataManager
                    json_manager = JsonDataManager()
                    friend_data = json_manager.get_friend_data(name)
                    if friend_data:
                        # 获取文件名并删除
                        mapping_file = 'friend_mapping.json'
                        if os.path.exists(mapping_file):
                            with open(mapping_file, 'r', encoding='utf-8') as f:
                                mapping = json.load(f)
                            if name in mapping and mapping[name]:
                                json_path = os.path.join('tempJson', mapping[name])
                                if os.path.exists(json_path):
                                    os.remove(json_path)
                                    print(f"[主窗口] 删除JSON文件: {json_path}")
                except Exception as e:
                    print(f"[主窗口] 删除JSON文件失败: {e}")
                
                # 2. 从映射中移除
                self.remove_friend_from_mapping(name)
                
                # 3. 从内存中移除
                self.friends.remove(name)
                self.friend_list.takeItem(row)
                if name in self.friend_data_map:
                    del self.friend_data_map[name]
                
                # 4. 关闭该好友的所有窗口
                windows_to_remove = []
                for win in self.friend_windows:
                    if win.friend_data.name == name:
                        win.close()
                        windows_to_remove.append(win)
                
                for win in windows_to_remove:
                    self.friend_windows.remove(win)
                
                print(f"[主窗口] 已删除好友: {name}")
        else:
            QMessageBox.warning(self, '提示', '请选择要删除的好友')
    
    def remove_friend_from_mapping(self, friend_name):
        """从映射文件中移除好友"""
        try:
            mapping_file = 'friend_mapping.json'
            if os.path.exists(mapping_file):
                with open(mapping_file, 'r', encoding='utf-8') as f:
                    mapping = json.load(f)
                
                if friend_name in mapping:
                    del mapping[friend_name]
                    
                    with open(mapping_file, 'w', encoding='utf-8') as f:
                        json.dump(mapping, f, ensure_ascii=False, indent=2)
                    
                    print(f"[主窗口] 从映射中移除: {friend_name}")
        except Exception as e:
            print(f"[主窗口] 从映射中移除好友失败: {e}")
    
    def open_friend_window(self):
        row = self.friend_list.currentRow()
        if row >= 0:
            name = self.friend_list.item(row).text()
            # 方法1：简单清理（每次打开时清理不可见窗口）
            self.cleanup_closed_windows()
            # 检查是否已有该好友的窗口打开
            for win in self.friend_windows:
                if win.friend_data.name == name:
                    win.raise_()
                    win.activateWindow()
                    print(f"[主窗口] 好友窗口已存在，将其置前: {name}")
                    return
            # 创建新窗口
            win = FriendWindow(self.friend_data_map[name], None)
            win.show()
            # 监听窗口关闭，自动清理引用
            self.setup_window_close_handler(win)
            self.friend_windows.append(win)
            print(f"[主窗口] 打开好友窗口: {name}")
        else:
            QMessageBox.warning(self, '提示', '请选择要打开的好友')

    def cleanup_closed_windows(self):
        """清理已关闭的窗口引用"""
        windows_to_remove = []
        for win in self.friend_windows:
            if not win.isVisible():  # 检查窗口是否可见
                windows_to_remove.append(win)
        for win in windows_to_remove:
            self.friend_windows.remove(win)
            print(f"[主窗口] 清理已关闭的窗口引用: {win.friend_data.name}")

    def setup_window_close_handler(self, window):
        """设置窗口关闭时的清理处理"""
        def on_window_closed():
            if window in self.friend_windows:
                self.friend_windows.remove(window)
                print(f"[主窗口] 自动清理已关闭的窗口: {window.friend_data.name}")
        # 使用destroyed信号，确保窗口完全销毁时清理
        window.destroyed.connect(lambda: on_window_closed())
    
    def reset_friend_data(self):
        """重置选中的好友数据（只删除JSON，保留好友名）"""
        row = self.friend_list.currentRow()
        if row >= 0:
            name = self.friend_list.item(row).text()
            
            reply = QMessageBox.question(
                self,
                '确认重置',
                f'确定要重置好友 "{name}" 的数据吗？\n\n'
                '这将：\n'
                '1. 删除该好友的所有JSON数据文件\n'
                '2. 清空好友映射中的JSON文件名（保留好友名）\n'
                '3. 关闭并重新打开该好友的窗口（如果已打开）\n\n'
                '截图文件不会被删除。',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                try:
                    # 1. 删除JSON数据文件
                    mapping_file = 'friend_mapping.json'
                    if os.path.exists(mapping_file):
                        with open(mapping_file, 'r', encoding='utf-8') as f:
                            mapping = json.load(f)
                        
                        if name in mapping and mapping[name]:
                            json_path = os.path.join('tempJson', mapping[name])
                            if os.path.exists(json_path):
                                os.remove(json_path)
                                print(f"[主窗口] 删除JSON文件: {json_path}")
                    
                    # 2. 更新映射（保留好友名，清空JSON文件名）
                    self.update_friend_mapping(name, '')
                    
                    # 3. 更新FriendData对象
                    if name in self.friend_data_map:
                        self.friend_data_map[name].screenshot_path = ''
                        self.friend_data_map[name].cell_rects = []
                        self.friend_data_map[name].excluded_cells = []
                    
                    # 4. 关闭并重新打开该好友的窗口（如果已打开）
                    for i, win in enumerate(self.friend_windows):
                        if win.friend_data.name == name:
                            # 先关闭窗口
                            win.close()
                            # 从列表中移除
                            self.friend_windows.pop(i)
                            # 重新创建窗口
                            new_win = FriendWindow(self.friend_data_map[name], None)
                            new_win.show()
                            self.friend_windows.append(new_win)
                            print(f"[主窗口] 已重新打开好友窗口: {name}")
                            break
                    
                    QMessageBox.information(self, '重置成功', f'已重置好友 "{name}" 的数据')
                    
                except Exception as e:
                    QMessageBox.warning(self, '重置失败', f'重置好友数据时出错:\n{str(e)}')
        else:
            QMessageBox.warning(self, '提示', '请选择要重置的好友')
    
    def calc_profit(self):
        """基于json数据统计所有好友的指定商品利润排行，并在右侧表格显示"""
        from json_data_manager import JsonDataManager
        json_manager = JsonDataManager()
        
        # 1. 获取所有好友及其json文件
        mapping = json_manager.list_all_friends()
        if not mapping:
            QMessageBox.warning(self, '提示', '没有任何好友数据')
            return
        
        # 2. 获取用户选择的商品名
        selected_product = self.input_name.currentText()
        if not selected_product:
            QMessageBox.warning(self, '提示', '请选择商品名称')
            return
        
        # 3. 获取用户买入价
        try:
            buy_price = float(self.input_price.text())
        except:
            QMessageBox.warning(self, '提示', '请输入正确的买入单价')
            return
        
        # 4. 遍历所有有json数据的好友，提取该商品的单价
        profit_list = []
        for friend, json_filename in mapping.items():
            if not json_filename:
                continue  # 没有数据
            json_path = os.path.join('tempJson', json_filename)
            if not os.path.exists(json_path):
                continue
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = f.read()
                    if not data.strip():
                        continue
                    product_data = json.loads(data)
            except Exception as e:
                print(f"读取{json_path}失败: {e}")
                continue
            # 兼容两种结构：dict或list
            if isinstance(product_data, dict):
                for k, v in product_data.items():
                    name = v.get('name') or v.get('name_raw')
                    price = v.get('price')
                    if name == selected_product and price:
                        try:
                            price_val = float(''.join(filter(lambda x: x.isdigit() or x == '.', str(price))))
                            profit = price_val - buy_price
                            profit_list.append({
                                'friend': friend,
                                'name': name,
                                'price': price_val,
                                'profit': profit
                            })
                        except:
                            continue
            elif isinstance(product_data, list):
                for v in product_data:
                    name = v.get('name') or v.get('name_raw')
                    price = v.get('price')
                    if name == selected_product and price:
                        try:
                            price_val = float(''.join(filter(lambda x: x.isdigit() or x == '.', str(price))))
                            profit = price_val - buy_price
                            profit_list.append({
                                'friend': friend,
                                'name': name,
                                'price': price_val,
                                'profit': profit
                            })
                        except:
                            continue
        # 5. 排序并显示到表格
        profit_list.sort(key=lambda x: x['profit'], reverse=True)
        self.table_profit.setRowCount(len(profit_list))
        max_profit = None
        max_row = -1
        for i, p in enumerate(profit_list):
            self.table_profit.setItem(i, 0, QTableWidgetItem(str(p['friend'])))
            self.table_profit.setItem(i, 1, QTableWidgetItem(str(p['name'])))
            self.table_profit.setItem(i, 2, QTableWidgetItem(str(p['price'])))
            self.table_profit.setItem(i, 3, QTableWidgetItem(f"{p['profit']:.2f}"))
            if max_profit is None or p['profit'] > max_profit:
                max_profit = p['profit']
                max_row = i
        # 橙色高亮最大利润行
        if max_row >= 0:
            for col in range(4):
                item = self.table_profit.item(max_row, col)
                if item:
                    item.setBackground(QtGui.QColor(255, 165, 0))  # 橙色
                    item.setForeground(QtGui.QColor(0, 0, 0))      # 黑字
        # 如果没有数据，清空表格
        if not profit_list:
            self.table_profit.setRowCount(0)
            QMessageBox.information(self, '利润排行', f'没有任何好友有商品“{selected_product}”的数据')
    
    def factory_reset(self):
        reply = QMessageBox.question(
            self,
            '确认恢复出厂设置',
            '确定要恢复出厂设置吗？\n\n'
            '这将执行以下操作：\n'
            '1. 清空 debug_cells 目录内容\n'
            '2. 清空 debug_cells_x 目录内容\n'
            '3. 重置 friend_mapping.json 为 {}\n'
            '4. 清空 tempJson 目录中的所有 JSON 文件\n'
            '5. 清空好友列表\n'
            '6. 关闭所有好友窗口\n\n'
            '此操作不可逆！',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                operations = []
                # 1. 清空 debug_cells 目录内容
                debug_cells_dir = 'debug_cells'
                if os.path.exists(debug_cells_dir):
                    for item in os.listdir(debug_cells_dir):
                        item_path = os.path.join(debug_cells_dir, item)
                        try:
                            if os.path.isfile(item_path) or os.path.islink(item_path):
                                os.unlink(item_path)
                            elif os.path.isdir(item_path):
                                shutil.rmtree(item_path)
                        except Exception as e:
                            print(f"清理 {item_path} 时出错: {e}")
                    operations.append(f"✓ 已清空 {debug_cells_dir} 目录")
                else:
                    os.makedirs(debug_cells_dir, exist_ok=True)
                    operations.append(f"✓ 已创建 {debug_cells_dir} 目录")
                # 2. 清空 debug_cells_x 目录内容
                debug_cells_x_dir = 'debug_cells_x'
                if os.path.exists(debug_cells_x_dir):
                    for item in os.listdir(debug_cells_x_dir):
                        item_path = os.path.join(debug_cells_x_dir, item)
                        try:
                            if os.path.isfile(item_path) or os.path.islink(item_path):
                                os.unlink(item_path)
                            elif os.path.isdir(item_path):
                                shutil.rmtree(item_path)
                        except Exception as e:
                            print(f"清理 {item_path} 时出错: {e}")
                    operations.append(f"✓ 已清空 {debug_cells_x_dir} 目录")
                else:
                    os.makedirs(debug_cells_x_dir, exist_ok=True)
                    operations.append(f"✓ 已创建 {debug_cells_x_dir} 目录")
                # 3. 重置 friend_mapping.json 为 {}
                mapping_file = 'friend_mapping.json'
                try:
                    with open(mapping_file, 'w', encoding='utf-8') as f:
                        json.dump({}, f, ensure_ascii=False, indent=2)
                    operations.append(f"✓ 已重置 {mapping_file}")
                except Exception as e:
                    operations.append(f"✗ 重置 {mapping_file} 失败: {str(e)}")
                # 4. 清空 tempJson 目录中的所有 JSON 文件
                temp_json_dir = 'tempJson'
                if os.path.exists(temp_json_dir):
                    json_files_cleared = 0
                    for item in os.listdir(temp_json_dir):
                        if item.endswith('.json'):
                            item_path = os.path.join(temp_json_dir, item)
                            try:
                                if os.path.isfile(item_path):
                                    os.unlink(item_path)
                                    json_files_cleared += 1
                            except Exception as e:
                                print(f"删除 {item_path} 时出错: {e}")
                    operations.append(f"✓ 已清空 {temp_json_dir} 目录，删除了 {json_files_cleared} 个 JSON 文件")
                else:
                    os.makedirs(temp_json_dir, exist_ok=True)
                    operations.append(f"✓ 已创建 {temp_json_dir} 目录")
                # 5. 清空好友列表
                self.friends.clear()
                self.friend_data_map.clear()
                self.friend_list.clear()
                # 6. 关闭所有好友窗口
                for win in self.friend_windows:
                    win.close()
                self.friend_windows.clear()
                # 显示操作结果
                result_msg = "恢复出厂设置完成！\n\n执行的操作：\n"
                result_msg += "\n".join(operations)
                QMessageBox.information(self, '恢复出厂设置完成', result_msg)
            except Exception as e:
                QMessageBox.critical(self, '操作失败', f'恢复出厂设置时出错:\n{str(e)}')
    
    def closeEvent(self, event):
        """重写关闭事件，确保所有子窗口都被正确关闭"""
        for win in self.friend_windows:
            win.close()
        event.accept()