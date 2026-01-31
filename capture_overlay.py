# file name: capture_overlay.py
from PyQt5.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout
from PyQt5.QtCore import Qt, QRect, pyqtSignal, QTimer, QPoint
from PyQt5.QtGui import QPainter, QPen, QColor, QBrush
import time

class CaptureOverlay(QWidget):
    """截图引导覆盖层 - 显示红线框供用户对齐，支持标记排除区域"""
    
    # 信号定义 - 修改为传递五个参数
    capture_completed = pyqtSignal(str, list, int, int, list)  # 新增最后一个参数：排除区域列表
    closed = pyqtSignal()                # 覆盖层关闭
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 新增：记录每个单元格使用的单价框格式索引（0-3）
        # 格式: {(row, col): 0, 1, 2, 3}
        self.cell_price_formats = {}  # 0=格式1, 1=格式2, 2=格式3, 3=格式4
        
        self.setup_ui()
        self.setup_overlay()
        
        # 新增：存储被用户标记为"不需要处理"的单元格索引
        self.excluded_cells = set()  # 使用集合存储，自动去重，格式: {(row1, col1), (row2, col2), ...}
        
        # 防抖处理：记录上次点击时间和位置
        self.last_click_time = 0
        self.last_click_pos = None
        self.click_debounce_ms = 300  # 300毫秒内视为同一点击
        
    def setup_ui(self):
        """设置界面"""
        # 无边框、置顶、透明背景
        self.setWindowFlags(
            Qt.FramelessWindowHint | 
            Qt.WindowStaysOnTopHint | 
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)  # 关键：允许接收鼠标事件
        # 获取屏幕尺寸，全屏显示
        screen = self.screen()
        screen_geometry = screen.geometry()
        self.setGeometry(screen_geometry)
        print(f"[覆盖层] 屏幕尺寸: {screen_geometry.width()}x{screen_geometry.height()}")
        
        # 控制面板
        self.control_panel = QWidget(self)
        self.control_panel.setStyleSheet("""
            QWidget {
                background-color: rgba(40, 40, 40, 220);
                border-radius: 10px;
                padding: 10px;
                border: 2px solid #555;
            }
            QLabel {
                color: white;
                font-size: 14px;
                padding: 5px;
                font-weight: bold;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
                margin: 5px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #45a049;
                border: 1px solid #fff;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QPushButton#cancelBtn {
                background-color: #f44336;
            }
            QPushButton#cancelBtn:hover {
                background-color: #da190b;
            }
        """)
        
        # 确保控制面板可以接收鼠标事件
        self.control_panel.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        
        # 布局
        layout = QVBoxLayout(self.control_panel)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # 说明文字 - 更新为包含标记说明
        self.label_instruction = QLabel("请将游戏中的商品列表对齐下方的红线框")
        self.label_instruction.setAlignment(Qt.AlignCenter)
        
        # 标记说明
        self.label_mark = QLabel("点击空白商品区域可标记为红色（不处理）")
        self.label_mark.setAlignment(Qt.AlignCenter)
        self.label_mark.setStyleSheet("color: #FF6B6B; font-weight: bold;")
        
        # 分辨率提示
        self.label_resolution = QLabel("确保游戏分辨率为 2560x1440")
        self.label_resolution.setAlignment(Qt.AlignCenter)
        
        # 快捷键提示 - 更新为包含标记说明
        self.label_hotkey = QLabel("快捷键: F7截图 | F8取消 | 鼠标点击标记/取消")
        self.label_hotkey.setAlignment(Qt.AlignCenter)
        
        # 新增：单价框切换提示
        self.label_price_toggle = QLabel("Ctrl+右键点击单价框：循环切换4种单价框格式")
        self.label_price_toggle.setAlignment(Qt.AlignCenter)
        self.label_price_toggle.setStyleSheet("color: #4FC3F7; font-weight: bold;")
        
        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.setSpacing(20)
        
        self.btn_capture = QPushButton("📸 截图 (F7)")
        self.btn_capture.clicked.connect(self.do_capture)
        
        self.btn_cancel = QPushButton("❌ 取消 (F8)")
        self.btn_cancel.setObjectName("cancelBtn")
        self.btn_cancel.clicked.connect(self.do_cancel)
        
        button_layout.addWidget(self.btn_capture)
        button_layout.addWidget(self.btn_cancel)
        
        # 添加到主布局
        layout.addWidget(self.label_instruction)
        layout.addWidget(self.label_mark)
        layout.addWidget(self.label_resolution)
        layout.addWidget(self.label_hotkey)
        layout.addWidget(self.label_price_toggle)
        layout.addLayout(button_layout)
        
        self.control_panel.setLayout(layout)
        
        # 设置控制面板位置（右上角）
        panel_width = 500  # 稍微加宽以容纳更多文字
        panel_height = 260
        screen_width = screen_geometry.width()
        self.control_panel.setGeometry(
            screen_width - panel_width - 30, 30, panel_width, panel_height
        )
        
        print(f"[覆盖层] 控制面板位置: {self.control_panel.geometry()}")
        
    def setup_overlay(self):
        """设置覆盖层参数"""
        # ============================================================
        # 可手动修改的起点坐标 - 在这里调整集群的左上角位置
        # ============================================================
        self.cluster_x = 75      # 集群左上角X坐标
        self.cluster_y = 446      # 集群左上角Y坐标
        # ============================================================
        
        # 单元格基础尺寸
        self.cell_width = 281     # 每个区域宽度
        self.cell_height = 382    # 每个区域高度
        
        # 行间距（纵向间距）
        self.row_spacing = 50     # 行间距（纵向间距）
        
        # 网格参数
        self.rows = 2            # 行数
        self.cols = 7            # 列数
        
        # ============================================================
        # 手动设置每个列之间的间距（单位：像素）
        # 第0-1列间距, 第1-2列间距, ..., 第5-6列间距
        # 共需要6个间距值（7列有6个间隙）
        # ============================================================
        self.col_spacings = [19, 22, 24, 24, 26, 26]  # 默认都是16像素
        
        # ============================================================
        # 内部矩形区域配置 - 从config.py加载
        # ============================================================
        from config import Config
        
        # 商品名称区域（中文文字选区）
        self.text_rect_rel = {
            'x': 2,      # 相对于单元格左上角的X偏移
            'y': 340,    # 相对于单元格左上角的Y偏移
            'width': 277,  # 宽度
            'height': 40   # 高度
        }
        
        # 单价区域 - 4种格式
        self.price_formats = Config.get_price_formats()  # 获取4种格式的列表
        
        # ============================================================
        # 计算每个单元格的精确位置（考虑不同的列间距）
        # ============================================================
        self.cell_positions = []
        self.cell_rects = []  # 存储每个单元格的(x, y, w, h)
        
        for row in range(self.rows):
            for col in range(self.cols):
                # 计算X坐标：起点 + 前面所有列的宽度 + 前面所有间距
                x = self.cluster_x
                for c in range(col):
                    x += self.cell_width + self.col_spacings[c]
                
                # 计算Y坐标
                y = self.cluster_y + row * (self.cell_height + self.row_spacing)
                
                # 存储位置信息
                self.cell_positions.append((x, y, self.cell_width, self.cell_height))
                
                # 初始所有单元格使用格式1（索引0）
                self.cell_price_formats[(row, col)] = 0
                
                # 计算内部矩形区域的绝对坐标
                text_x = x + self.text_rect_rel['x']
                text_y = y + self.text_rect_rel['y']
                
                # 使用格式1的单价框坐标
                price_format = self.price_formats[0]  # 格式1
                price_x = x + price_format['x']
                price_y = y + price_format['y']
                price_width = price_format['width']
                price_height = price_format['height']
                
                self.cell_rects.append({
                    'row': row,
                    'col': col,
                    'x': x,
                    'y': y,
                    'width': self.cell_width,
                    'height': self.cell_height,
                    'right': x + self.cell_width - 1,  # 修正为不溢出
                    'bottom': y + self.cell_height - 1,  # 修正为不溢出
                    # 内部矩形区域
                    'text_rect': {
                        'x': text_x,
                        'y': text_y,
                        'width': self.text_rect_rel['width'],
                        'height': self.text_rect_rel['height'],
                        'right': text_x + self.text_rect_rel['width'] - 1,
                        'bottom': text_y + self.text_rect_rel['height'] - 1
                    },
                    'price_rect': {
                        'x': price_x,
                        'y': price_y,
                        'width': price_width,
                        'height': price_height,
                        'right': price_x + price_width - 1,
                        'bottom': price_y + price_height - 1,
                        'format_index': 0  # 记录使用的单价框格式索引
                    }
                })
        
        # 计算集群总尺寸
        total_width = self.cell_width * self.cols
        for spacing in self.col_spacings:
            total_width += spacing
        total_height = self.cell_height * self.rows + self.row_spacing * (self.rows - 1)
        # 最终宽高+10px，防止边界误差
        self.cluster_width = total_width + 10
        self.cluster_height = total_height + 10
        print(f"[覆盖层] 集群尺寸: {self.cluster_width}x{self.cluster_height}")
        print(f"[覆盖层] 单元格数: {self.rows}行 × {self.cols}列")
        print(f"[覆盖层] 单元格尺寸: {self.cell_width}x{self.cell_height}")
        print(f"[覆盖层] 行间距: {self.row_spacing}px")
        print(f"[覆盖层] 列间距: {self.col_spacings}")
        print(f"[覆盖层] 商品名称区域: ({self.text_rect_rel['x']}, {self.text_rect_rel['y']}) - {self.text_rect_rel['width']}x{self.text_rect_rel['height']}")
        print(f"[覆盖层] 单价框格式数: {len(self.price_formats)}种")
        for i, fmt in enumerate(self.price_formats):
            print(f"  格式{i+1}: ({fmt['x']}, {fmt['y']}) - {fmt['width']}x{fmt['height']}")
        print(f"[覆盖层] 文件命名格式: YYYYMMDD_HHMMSS_[type]_[行]_[列].png")
        
        # 红线样式
        self.normal_line_color = QColor(255, 0, 0)  # 红色 - 正常区域
        self.excluded_line_color = QColor(255, 100, 100, 200)  # 半透明红色 - 排除区域
        self.excluded_fill_color = QColor(255, 100, 100, 50)  # 半透明填充 - 排除区域
        self.line_width = 2
        
        # 内部矩形颜色
        self.text_rect_color = QColor(0, 255, 0)  # 绿色 - 商品名称
        self.price_rect_color = QColor(0, 0, 255)  # 蓝色 - 单价
    
    def get_price_rect_for_cell(self, row, col):
        """获取指定单元格的单价框坐标"""
        format_index = self.cell_price_formats.get((row, col), 0)
        
        if 0 <= format_index < len(self.price_formats):
            return self.price_formats[format_index]
        else:
            return self.price_formats[0]  # 默认格式1
    
    def update_cell_price_rect(self, row, col):
        """更新单元格的单价框坐标"""
        price_rect_config = self.get_price_rect_for_cell(row, col)
        format_index = self.cell_price_formats.get((row, col), 0)
        
        for rect in self.cell_rects:
            if rect['row'] == row and rect['col'] == col:
                x = rect['x']
                y = rect['y']
                
                # 更新单价框坐标
                price_x = x + price_rect_config['x']
                price_y = y + price_rect_config['y']
                price_width = price_rect_config['width']
                price_height = price_rect_config['height']
                
                rect['price_rect'] = {
                    'x': price_x,
                    'y': price_y,
                    'width': price_width,
                    'height': price_height,
                    'right': price_x + price_width - 1,
                    'bottom': price_y + price_height - 1,
                    'format_index': format_index
                }
                break
    
    def paintEvent(self, event):
        """绘制红线框和内部矩形 - 根据排除状态使用不同颜色"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        # 画一个全屏透明遮罩，确保能接收鼠标事件
        painter.fillRect(self.rect(), QColor(0, 0, 0, 1))
        
        # 只绘制控制面板背景
        control_rect = self.control_panel.geometry()
        painter.fillRect(control_rect, QColor(40, 40, 40, 220))
        
        # 绘制所有区域的外部矩形框
        for idx, rect in enumerate(self.cell_rects):
            row = rect['row']
            col = rect['col']
            x = rect['x']
            y = rect['y']
            width = rect['width']
            height = rect['height']
            
            # 检查是否为排除区域
            is_excluded = (row, col) in self.excluded_cells
            
            if is_excluded:
                # 排除区域：半透明红色填充
                painter.setPen(QPen(self.excluded_line_color, self.line_width))
                painter.setBrush(QBrush(self.excluded_fill_color))
                painter.drawRect(x, y, width, height)
                painter.setBrush(Qt.NoBrush)  # 关键：立即恢复无填充，防止污染
            else:
                # 正常区域：红色边框，无填充
                painter.setPen(QPen(self.normal_line_color, self.line_width))
                painter.setBrush(Qt.NoBrush)
                painter.drawRect(x, y, width, height)
            
            # 在矩形左上角显示行列编号
            painter.setPen(QColor(255, 255, 0))
            cell_text = f"{row+1}-{col+1}"
            if is_excluded:
                cell_text += " (排除)"
            # 添加单价框格式标记
            format_index = self.cell_price_formats.get((row, col), 0)
            if format_index > 0:  # 如果不是格式1，显示格式编号
                cell_text += f" [F{format_index+1}]"
            painter.drawText(x + 5, y + 20, cell_text)
        
        # 绘制内部矩形区域（只绘制非排除区域）
        for rect in self.cell_rects:
            row = rect['row']
            col = rect['col']
            
            # 如果是排除区域，跳过内部矩形绘制
            if (row, col) in self.excluded_cells:
                continue
            
            # 绘制商品名称区域（绿色框）
            painter.setPen(QPen(self.text_rect_color, self.line_width))
            text_rect = rect['text_rect']
            painter.drawRect(
                text_rect['x'], text_rect['y'], 
                text_rect['width'], text_rect['height']
            )
            
            # 绘制单价区域（蓝色框）
            painter.setPen(QPen(self.price_rect_color, self.line_width))
            price_rect = rect['price_rect']
            painter.drawRect(
                price_rect['x'], price_rect['y'], 
                price_rect['width'], price_rect['height']
            )
        
        # 绘制集群外边框（黄色粗边框）
        thick_pen = QPen(QColor(255, 255, 0), 3)
        painter.setPen(thick_pen)
        painter.drawRect(
            self.cluster_x - 2, self.cluster_y - 2,
            self.cluster_width + 4, self.cluster_height + 4
        )
        
        # 绘制坐标信息（调试用）
        painter.setPen(QColor(255, 255, 0))
        info_text = f"集群位置: ({self.cluster_x}, {self.cluster_y})"
        painter.drawText(20, 40, info_text)
        
        # 绘制网格信息
        format_counts = {}
        for fmt_idx in range(len(self.price_formats)):
            count = sum(1 for v in self.cell_price_formats.values() if v == fmt_idx)
            format_counts[f"F{fmt_idx+1}"] = count
        
        format_info = " | ".join([f"{k}:{v}" for k, v in format_counts.items()])
        info_text2 = f"网格: {self.rows}行 × {self.cols}列 | 已排除: {len(self.excluded_cells)}个 | 单价格式: {format_info}"
        painter.drawText(20, 60, info_text2)
        
        # 绘制标记说明
        mark_info = "提示: 点击空白商品区域可标记为红色（不处理）"
        painter.setPen(QColor(255, 100, 100))
        painter.drawText(20, 80, mark_info)
        
        # 绘制单价框切换说明
        toggle_info = "Ctrl+右键点击单价框: 循环切换4种单价框格式 (F1→F2→F3→F4→F1...)"
        painter.setPen(QColor(100, 150, 255))
        painter.drawText(20, 100, toggle_info)
        
        # 绘制格式说明
        for i, fmt in enumerate(self.price_formats):
            fmt_info = f"格式{i+1}: ({fmt['x']},{fmt['y']}) {fmt['width']}×{fmt['height']}"
            painter.drawText(20, 120 + i * 20, fmt_info)
        
        # 绘制间距信息
        start_y = 120 + len(self.price_formats) * 20
        spacing_info = "列间距: " + ", ".join([str(s) for s in self.col_spacings]) + "px"
        painter.setPen(QColor(255, 255, 0))
        painter.drawText(20, start_y, spacing_info)
        
        # 绘制集群尺寸信息
        info_text3 = f"集群尺寸: {self.cluster_width}×{self.cluster_height}"
        painter.drawText(20, start_y + 20, info_text3)
        
        # 绘制文件命名规范
        naming_info = "命名: YYYYMMDD_HHMMSS_[type]_[行]_[列].png"
        painter.drawText(20, start_y + 40, naming_info)
        
        # 绘制内部矩形说明
        painter.setPen(self.text_rect_color)
        painter.drawText(20, start_y + 60, "绿色框: 商品名称区域 (text)")
        
        painter.setPen(self.price_rect_color)
        painter.drawText(20, start_y + 80, "蓝色框: 单价区域 (price)")
    
    def is_point_in_price_rect(self, pos):
        """检查点是否在单价框内"""
        for rect in self.cell_rects:
            price_rect = rect['price_rect']
            if (price_rect['x'] <= pos.x() <= price_rect['right'] and 
                price_rect['y'] <= pos.y() <= price_rect['bottom']):
                return rect
        return None
    
    def mousePressEvent(self, event):
        """鼠标点击事件 - 严格只允许在矩形区域内点击"""
        pos = event.pos()
        
        # 1. 先检查是否点击在控制面板上
        if self.control_panel.geometry().contains(pos):
            print("[覆盖层] 点击在控制面板上")
            # 传递给控制面板处理
            event.ignore()
            return
        
        # 2. 检查是否是Ctrl+右键点击单价框 - 这个要最优先！
        if (event.button() == Qt.RightButton and 
            event.modifiers() & Qt.ControlModifier):
            
            # 检查是否点击在单价框内
            clicked_cell = self.is_point_in_price_rect(pos)
            if clicked_cell:
                row = clicked_cell['row']
                col = clicked_cell['col']
                
                # 循环切换单价框格式 (0→1→2→3→0...)
                current_format = self.cell_price_formats.get((row, col), 0)
                next_format = (current_format + 1) % len(self.price_formats)  # 循环切换
                self.cell_price_formats[(row, col)] = next_format
                
                # 更新单元格的单价框坐标
                self.update_cell_price_rect(row, col)
                
                price_rect_config = self.price_formats[next_format]
                print(f"[覆盖层] 切换单价框: 第{row+1}行第{col+1}列 -> 格式{next_format+1}")
                print(f"[覆盖层] 坐标: ({price_rect_config['x']},{price_rect_config['y']}) 尺寸: {price_rect_config['width']}×{price_rect_config['height']}")
                
                # 强制重绘
                self.update()
                event.accept()
                return
        
        # 3. 防抖处理：检查是否在短时间内重复点击同一位置
        current_time = time.time() * 1000  # 转换为毫秒
        if (current_time - self.last_click_time < self.click_debounce_ms and 
            self.last_click_pos and 
            abs(pos.x() - self.last_click_pos.x()) < 10 and 
            abs(pos.y() - self.last_click_pos.y()) < 10):
            print("[覆盖层] 防抖：忽略重复点击")
            event.accept()  # 直接接受事件，不处理
            return
        
        # 4. 更新点击记录
        self.last_click_time = current_time
        self.last_click_pos = pos
        
        # 5. 如果是右键点击（没有Ctrl键），直接忽略
        if event.button() == Qt.RightButton:
            print(f"[覆盖层] 右键点击 (X:{pos.x()}, Y:{pos.y()})，无Ctrl键，忽略")
            event.accept()
            return
        
        # 6. 严格检查：只允许在单元格矩形区域内点击（现在只处理左键）
        if event.button() == Qt.LeftButton:
            clicked_cell = None
            for idx, rect in enumerate(self.cell_rects):
                # 使用精确的边界检查（包含右边界和下边界）
                if (rect['x'] <= pos.x() <= rect['right'] and 
                    rect['y'] <= pos.y() <= rect['bottom']):
                    clicked_cell = rect
                    break
            
            # 7. 如果点击在矩形区域内，处理标记
            if clicked_cell:
                row = clicked_cell['row']
                col = clicked_cell['col']
                cell_key = (row, col)
                
                # 切换排除状态
                if cell_key in self.excluded_cells:
                    self.excluded_cells.remove(cell_key)
                    print(f"[覆盖层] 取消排除区域: 第{row+1}行第{col+1}列")
                else:
                    self.excluded_cells.add(cell_key)
                    print(f"[覆盖层] 标记排除区域: 第{row+1}行第{col+1}列")
                
                # 强制重绘，更新显示
                self.update()
                print(f"[覆盖层] 当前排除区域数: {len(self.excluded_cells)}")
                
                # 接受事件，处理完毕
                event.accept()
                return
        
        # 8. 如果点击不在任何矩形区域内，严格拒绝
        print(f"[覆盖层] 点击在非矩形区域 (X:{pos.x()}, Y:{pos.y()})，禁止选中")
        
        # 关键：接受事件但不做任何处理，防止事件传播
        event.accept()
        
        # 可选：提供视觉反馈（灰色覆盖层表示禁用区域）
        self.show_disabled_overlay(pos)
    
    def show_disabled_overlay(self, pos):
        """显示禁用区域提示"""
        # 创建一个临时的小红点，表示点击位置
        from PyQt5.QtWidgets import QLabel
        from PyQt5.QtCore import QTimer
        
        dot = QLabel("✕", self)
        dot.setStyleSheet("""
            color: red;
            font-size: 20px;
            font-weight: bold;
            background-color: rgba(255, 255, 255, 180);
            border-radius: 10px;
            padding: 5px;
        """)
        dot.setAlignment(Qt.AlignCenter)
        dot.adjustSize()
        dot.move(pos.x() - dot.width()//2, pos.y() - dot.height()//2)
        dot.show()
        
        # 1秒后消失
        QTimer.singleShot(1000, dot.hide)
        
        # 记录日志
        print(f"[覆盖层] 非矩形区域点击位置: ({pos.x()}, {pos.y()})")
        
        # 找到最近的矩形
        nearest_cell = None
        min_distance = float('inf')
        for rect in self.cell_rects:
            # 计算点击位置到矩形中心的距离
            center_x = rect['x'] + rect['width'] // 2
            center_y = rect['y'] + rect['height'] // 2
            distance = ((pos.x() - center_x) ** 2 + (pos.y() - center_y) ** 2) ** 0.5
            if distance < min_distance:
                min_distance = distance
                nearest_cell = rect
        
        if nearest_cell:
            print(f"[覆盖层] 最近矩形: 第{nearest_cell['row']+1}行第{nearest_cell['col']+1}列，距离: {min_distance:.1f}像素")
    
    def do_capture(self):
        """执行截图"""
        print("[覆盖层] 点击了截图按钮")
        self.capture_screen()
    
    def do_cancel(self):
        """取消截图"""
        print("[覆盖层] 点击了取消按钮")
        self.close_overlay()
    
    def capture_screen(self):
        """执行截图"""
        from PIL import ImageGrab
        import datetime
        import os
        
        # 截图区域：整个集群区域
        bbox = (
            int(self.cluster_x),
            int(self.cluster_y),
            int(self.cluster_x + self.cluster_width),
            int(self.cluster_y + self.cluster_height)
        )
        
        print(f"[覆盖层] 截图区域: {bbox}")
        print(f"[覆盖层] 集群左上角: ({self.cluster_x}, {self.cluster_y})")
        print(f"[覆盖层] 集群右下角: ({self.cluster_x + self.cluster_width}, {self.cluster_y + self.cluster_height})")
        print(f"[覆盖层] 已排除区域: {sorted(list(self.excluded_cells))}")
        
        # 计算每个单元格的精确位置（调试用）
        print(f"[覆盖层] 单元格详细位置:")
        for rect in self.cell_rects:
            is_excluded = (rect['row'], rect['col']) in self.excluded_cells
            status = "排除" if is_excluded else "正常"
            format_index = self.cell_price_formats.get((rect['row'], rect['col']), 0)
            price_status = f"格式{format_index+1}"
            print(f"  第{rect['row']+1}行第{rect['col']+1}列 [{status}][单价:{price_status}]:")
            if not is_excluded:
                print(f"    外部矩形: ({rect['x']}, {rect['y']}) - ({rect['right']}, {rect['bottom']})")
                print(f"    商品名称区域: ({rect['text_rect']['x']}, {rect['text_rect']['y']}) - ({rect['text_rect']['right']}, {rect['text_rect']['bottom']})")
                print(f"    单价区域: ({rect['price_rect']['x']}, {rect['price_rect']['y']}) - ({rect['price_rect']['right']}, {rect['price_rect']['bottom']})")
            else:
                print(f"    [此区域已标记为排除，将不进行处理]")
        
        try:
            # 截图
            img = ImageGrab.grab(bbox=bbox)
            
            # 确保images目录存在
            images_dir = os.path.join(os.getcwd(), 'images')
            if not os.path.exists(images_dir):
                os.makedirs(images_dir)
            
            # 统一命名格式：YYYYMMDD_HHMMSS_cluster.png
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{timestamp}_cluster.png"
            save_path = os.path.join(images_dir, filename)
            
            # 保存图片
            img.save(save_path)
            
            print(f"[覆盖层] 截图保存到: {save_path}")
            print(f"[覆盖层] 截图尺寸: {img.size[0]}x{img.size[1]}")
            print(f"[覆盖层] 预期尺寸: {self.cluster_width}x{self.cluster_height}")
            print(f"[覆盖层] 文件命名: {timestamp}_[type]_[行]_[列].png")
            print(f"[覆盖层] 排除区域数: {len(self.excluded_cells)}")
            
            # 将排除集合转换为列表以便传递
            excluded_list = sorted(list(self.excluded_cells))
            
            # 传递单价框格式信息给后续处理
            for rect in self.cell_rects:
                rect['price_format_index'] = self.cell_price_formats.get((rect['row'], rect['col']), 0)
            
            # 发射信号，传递截图路径、cell_rects、集群起点坐标和排除区域列表
            self.capture_completed.emit(save_path, self.cell_rects, self.cluster_x, self.cluster_y, excluded_list)
            
            # 关闭覆盖层
            self.close_overlay()
            
        except Exception as e:
            print(f"[覆盖层] 截图失败: {e}")
            import traceback
            traceback.print_exc()
    
    def close_overlay(self):
        """关闭覆盖层"""
        print("[覆盖层] 关闭覆盖层")
        self.closed.emit()
        self.close()
    
    def keyPressEvent(self, event):
        """键盘事件"""
        if event.key() == Qt.Key_Escape or event.key() == Qt.Key_F8:
            print("[覆盖层] 按下了退出键")
            self.close_overlay()
        elif event.key() == Qt.Key_F7:
            print("[覆盖层] 按下了F7键")
            self.capture_screen()
        else:
            # 其他按键传递给父窗口
            super().keyPressEvent(event)
    
    def showEvent(self, event):
        """显示事件"""
        super().showEvent(event)
        print("[覆盖层] 覆盖层显示")
        print(f"[覆盖层] 集群位置: ({self.cluster_x}, {self.cluster_y})")
        print(f"[覆盖层] 集群尺寸: {self.cluster_width}x{self.cluster_height}")
        print(f"[覆盖层] 行间距: {self.row_spacing}px")
        print(f"[覆盖层] 列间距设置: {self.col_spacings}")
        print(f"[覆盖层] 商品名称区域: 偏移({self.text_rect_rel['x']}, {self.text_rect_rel['y']}) - {self.text_rect_rel['width']}x{self.text_rect_rel['height']}")
        print(f"[覆盖层] 单价框格式数: {len(self.price_formats)}种")
        for i, fmt in enumerate(self.price_formats):
            print(f"  格式{i+1}: 偏移({fmt['x']}, {fmt['y']}) - {fmt['width']}x{fmt['height']}")
        print(f"[覆盖层] 文件命名规范: YYYYMMDD_HHMMSS_[type]_[行]_[列].png")
        print(f"[覆盖层] 操作提示: 点击空白商品区域可标记为红色（不处理）")
        print(f"[覆盖层] 操作提示: Ctrl+右键点击单价框可循环切换4种单价框格式")
        
        # 计算和显示详细尺寸信息
        expected_width = self.cell_width * self.cols + sum(self.col_spacings)
        expected_height = self.cell_height * self.rows + self.row_spacing * (self.rows - 1)
        print(f"[覆盖层] 预期集群宽度: {expected_width} (7×281 + {sum(self.col_spacings)} = 1967 + {sum(self.col_spacings)} = {expected_width})")
        print(f"[覆盖层] 预期集群高度: {expected_height} (2×382 + 1×50 = 764 + 50 = 814)")
        
        # 显示每个单元格的X坐标
        print(f"[覆盖层] 各列X坐标:")
        for rect in self.cell_rects:
            if rect['row'] == 0:  # 只显示第一行的X坐标
                format_index = self.cell_price_formats.get((rect['row'], rect['col']), 0)
                print(f"  第{rect['col']+1}列: X={rect['x']}")
                print(f"    商品名称区域X: {rect['text_rect']['x']}")
                print(f"    单价区域X: {rect['price_rect']['x']} (格式: F{format_index+1})")
    
    def closeEvent(self, event):
        """关闭事件"""
        print("[覆盖层] 覆盖层关闭")
        print(f"[覆盖层] 最终排除区域数: {len(self.excluded_cells)}")
        
        # 重置所有单价框为格式1（索引0）
        for key in self.cell_price_formats:
            self.cell_price_formats[key] = 0
        print("[覆盖层] 已重置所有单价框为格式1")
        
        super().closeEvent(event)