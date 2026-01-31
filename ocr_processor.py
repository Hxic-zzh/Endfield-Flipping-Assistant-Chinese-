# file name: ocr_processor.py
import os
import cv2
import numpy as np
import pytesseract
from PIL import Image
import re
from collections import defaultdict

class OCRProcessor:
    def __init__(self):
        self.debug_dir = 'debug_cells'
        
    def process_single_image(self, image_path):
        """处理单个调试图像"""
        if not os.path.exists(image_path):
            print(f"图像不存在: {image_path}")
            return None
        
        # 从文件名解析信息
        filename = os.path.basename(image_path)
        parts = filename.replace('.png', '').split('_')
        
        # 解析文件名格式: timestamp_type_row_col.png
        result = {
            'file_path': image_path,
            'filename': filename,
            'timestamp': parts[0] if len(parts) > 0 else '',
            'cell_row': 0,
            'cell_col': 0,
            'region_type': 'unknown',
            'text': ''
        }
        
        # 解析区域类型和行列
        for i, part in enumerate(parts):
            if part in ['cell', 'text', 'price']:
                result['region_type'] = part
                if i+2 < len(parts):
                    try:
                        result['cell_row'] = int(parts[i+1])
                        result['cell_col'] = int(parts[i+2])
                    except ValueError:
                        pass
        
        # 读取并预处理图像
        img = cv2.imread(image_path)
        if img is None:
            print(f"无法读取图像: {image_path}")
            return result
        
        # OCR识别
        processed_img = self.preprocess_image(img, result['region_type'])
        text = self.ocr_image(processed_img, result['region_type'])
        
        result['text'] = text
        return result
    
    def preprocess_image(self, img, region_type):
        """预处理图像"""
        if img is None or img.size == 0:
            return None
        
        # 转换为灰度图
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img.copy()
        
        # 根据区域类型使用不同的预处理
        if region_type == 'price':
            # 价格区域 - 优化数字识别
            # 增强对比度
            gray = cv2.equalizeHist(gray)
            # 二值化
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            # 去噪
            kernel = np.ones((2, 2), np.uint8)
            processed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        elif region_type == 'text':
            # 文本区域 - 优化中文识别
            # CLAHE增强对比度
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)
            # 自适应阈值
            processed = cv2.adaptiveThreshold(
                enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 11, 2
            )
        else:
            # 单元格区域 - 简单处理
            processed = gray
        
        return processed
    
    def ocr_image(self, processed_img, region_type):
        """OCR识别图像"""
        if processed_img is None or processed_img.size == 0:
            return ""
        
        try:
            if region_type == 'price':
                # 价格识别 - 只识别数字
                config = r'--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789'
                lang = 'eng'
            else:
                # 文本识别 - 中文
                config = r'--oem 3 --psm 7'
                lang = 'chi_sim'
            
            # 执行OCR
            text = pytesseract.image_to_string(
                Image.fromarray(processed_img),
                lang=lang,
                config=config
            )
            
            # 清理文本
            text = text.strip()
            
            # 价格特殊处理
            if region_type == 'price':
                numbers = re.findall(r'\d+', text)
                if numbers:
                    # 取最大的数字（通常是完整价格）
                    text = str(max([int(n) for n in numbers]))
                else:
                    text = ""
            
            return text
            
        except Exception as e:
            print(f"OCR识别失败: {e}")
            return ""
    
    def process_debug_directory(self, friend_name):
        """处理指定好友的调试目录"""
        results = []
        
        # 构建调试目录路径
        debug_path = os.path.join(self.debug_dir, friend_name)
        if not os.path.exists(debug_path):
            print(f"调试目录不存在: {debug_path}")
            return results
        
        print(f"处理调试目录: {debug_path}")
        
        # 按时间戳分组处理
        timestamp_groups = defaultdict(list)
        
        # 收集所有调试图像
        for file in os.listdir(debug_path):
            if file.endswith('.png'):
                file_path = os.path.join(debug_path, file)
                
                # 从文件名提取时间戳
                parts = file.replace('.png', '').split('_')
                if len(parts) > 0:
                    timestamp = parts[0]
                    timestamp_groups[timestamp].append(file_path)
        
        # 按时间戳处理
        for timestamp, files in timestamp_groups.items():
            print(f"\n处理时间戳: {timestamp}")
            print(f"文件数量: {len(files)}")
            
            # 按单元格分组
            cell_results = defaultdict(lambda: {'text': '', 'price': ''})
            
            for file_path in files:
                result = self.process_single_image(file_path)
                if result:
                    cell_key = f"{result['cell_row']}_{result['cell_col']}"
                    
                    if result['region_type'] == 'text':
                        cell_results[cell_key]['text'] = result['text']
                        print(f"  单元格 {cell_key} 文本: {result['text']}")
                    elif result['region_type'] == 'price':
                        cell_results[cell_key]['price'] = result['text']
                        print(f"  单元格 {cell_key} 价格: {result['text']}")
            
            # 整理结果
            for cell_key, data in cell_results.items():
                row, col = map(int, cell_key.split('_'))
                combined_text = f"{data['text']} {data['price']}".strip()
                
                results.append({
                    'timestamp': timestamp,
                    'row': row,
                    'col': col,
                    'text': data['text'],
                    'price': data['price'],
                    'combined_text': combined_text,
                    'cell_key': f"{row}-{col}"
                })
        
        # 按行列排序
        results.sort(key=lambda x: (x['row'], x['col']))
        
        print(f"\n处理完成，共识别 {len(results)} 个单元格")
        return results

def process_debug_images_simple(friend_name):
    """简化版调试图像处理器"""
    processor = OCRProcessor()
    return processor.process_debug_directory(friend_name)

def test_single_image(image_path):
    """测试单个图像"""
    processor = OCRProcessor()
    result = processor.process_single_image(image_path)
    print(f"文件名: {result['filename']}")
    print(f"区域类型: {result['region_type']}")
    print(f"行列: {result['cell_row']}-{result['cell_col']}")
    print(f"识别文本: {result['text']}")
    return result