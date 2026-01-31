# file name: config.py
import os

class Config:
    # 路径配置
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    IMAGES_DIR = os.path.join(DATA_DIR, 'images')
    TEMPLATES_DIR = os.path.join(DATA_DIR, 'templates')
    
    # 覆盖层配置
    OVERLAY_CLUSTER_X = 377      # 集群左上角X坐标
    OVERLAY_CLUSTER_Y = 576      # 集群左上角Y坐标
    OVERLAY_CELL_WIDTH = 287     # 每个区域宽度
    OVERLAY_CELL_HEIGHT = 395    # 每个区域高度
    OVERLAY_ROWS = 2            # 行数
    OVERLAY_COLS = 7            # 列数
    
    # OCR配置
    OCR_LANGUAGE = 'chi_sim'    # 中文简体
    OCR_CONFIDENCE_THRESHOLD = 40  # 置信度阈值
    
    # 图像处理配置
    BASE_RESOLUTION = (2560, 1440)  # 基准分辨率
    
    @classmethod
    def ensure_directories(cls):
        """确保所有必要的目录都存在"""
        directories = [
            cls.DATA_DIR,
            cls.IMAGES_DIR,
            cls.TEMPLATES_DIR
        ]
        
        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory)
                print(f"创建目录: {directory}")

    # ============================================
    # 单价框配置 - 4种格式（按Ctrl+右键循环切换）
    # ============================================
    
    # 格式1：默认单价框（原始位置）
    PRICE_RECT_FORMAT_1 = {
        'x': 167,    
        'y': 273,    
        'width': 107,   
        'height': 40   
    }
    
    # 格式2：备选单价框（新位置1）
    PRICE_RECT_FORMAT_2 = {
        'x': 173,    
        'y': 273,    
        'width': 102,   
        'height': 40   
    }
    
    # 格式3：备选单价框（新位置2）
    PRICE_RECT_FORMAT_3 = {
        'x': 178,    
        'y': 273,    
        'width': 99,   
        'height': 40   
    }
    
    # 格式4：备选单价框（新位置3）
    PRICE_RECT_FORMAT_4 = {
        'x': 185,    
        'y': 273,    
        'width': 94,   
        'height': 40   
    }
    
    # 获取所有格式的列表（按顺序）
    @classmethod
    def get_price_formats(cls):
        return [
            cls.PRICE_RECT_FORMAT_1,
            cls.PRICE_RECT_FORMAT_2,
            cls.PRICE_RECT_FORMAT_3,
            cls.PRICE_RECT_FORMAT_4
        ]