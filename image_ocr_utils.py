# file name: image_ocr_utils.py
import os
import cv2
import numpy as np
import re
import datetime
import subprocess
import json
from collections import defaultdict

# 导入JSON管理器
try:
    from json_data_manager import JsonDataManager
    json_manager = JsonDataManager()
except ImportError:
    print("[OCR工具] 警告: JSON数据管理器导入失败")
    json_manager = None

# 导入商品匹配器
try:
    from product_matcher import get_product_matcher
    product_matcher = get_product_matcher()
    HAS_PRODUCT_MATCHER = True
    print("[OCR工具] 商品匹配器加载成功")
except ImportError:
    HAS_PRODUCT_MATCHER = False
    print("[OCR工具] 警告: 商品匹配器导入失败，将使用原始OCR结果")

def save_debug_images_with_exclusion(image_path, cell_rects, cluster_x, cluster_y, excluded_cells=None):
    """保存调试图片 - 支持排除特定区域"""
    if excluded_cells is None:
        excluded_cells = []
    
    excluded_set = set(excluded_cells)
    
    full_img = cv2.imread(image_path)
    if full_img is None:
        print(f"图片读取失败: {image_path}")
        return ""
    
    height, width = full_img.shape[:2]
    
    debug_dir = 'debug_cells'
    if not os.path.exists(debug_dir):
        os.makedirs(debug_dir)
    
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    
    print(f"保存调试图片到: {debug_dir}")
    print(f"时间戳: {timestamp}")
    print(f"排除区域数: {len(excluded_set)}")
    
    saved_count = 0
    skipped_count = 0
    
    for idx, rect in enumerate(cell_rects):
        row = rect['row']
        col = rect['col']
        
        if (row, col) in excluded_set:
            print(f"  跳过排除区域: 第{row+1}行第{col+1}列")
            skipped_count += 1
            continue
        
        row_display = row + 1
        col_display = col + 1
        
        # 商品名称区域坐标
        text_rel_x = max(0, min(rect['text_rect']['x'] - cluster_x, width - 1))
        text_rel_y = max(0, min(rect['text_rect']['y'] - cluster_y, height - 1))
        
        # 单价区域坐标
        price_rel_x = max(0, min(rect['price_rect']['x'] - cluster_x, width - 1))
        price_rel_y = max(0, min(rect['price_rect']['y'] - cluster_y, height - 1))
        
        # 1. 保存文本区域
        text_region = full_img[
            text_rel_y:min(text_rel_y + rect['text_rect']['height'], height),
            text_rel_x:min(text_rel_x + rect['text_rect']['width'], width)
        ]
        if text_region.size > 0:
            text_filename = f"{timestamp}_text_{row_display}_{col_display}.png"
            text_path = os.path.join(debug_dir, text_filename)
            cv2.imwrite(text_path, text_region)
            saved_count += 1
            print(f"  保存文本区域: {text_filename}")
        
        # 2. 保存单价区域
        price_region = full_img[
            price_rel_y:min(price_rel_y + rect['price_rect']['height'], height),
            price_rel_x:min(price_rel_x + rect['price_rect']['width'], width)
        ]
        if price_region.size > 0:
            price_filename = f"{timestamp}_price_{row_display}_{col_display}.png"
            price_path = os.path.join(debug_dir, price_filename)
            cv2.imwrite(price_path, price_region)
            saved_count += 1
            
            # 记录单价框类型
            price_type = rect.get('price_rect_type', 'default')
            print(f"  保存单价区域: {price_filename} (类型: {price_type})")
    
    print(f"调试图片保存完成: {saved_count}个文件, 跳过{skipped_count}个排除区域")
    return timestamp

# 保持向后兼容
def save_debug_images(image_path, cell_rects, cluster_x, cluster_y):
    return save_debug_images_with_exclusion(image_path, cell_rects, cluster_x, cluster_y, None)

def ocr_price_with_tesseract_cmd(img_path):
    """使用Tesseract命令行OCR识别价格（只识别数字）"""
    if not os.path.exists(img_path):
        print(f"图像不存在: {img_path}")
        return ""
    
    try:
        # Tesseract命令行参数
        # --psm 7: 将图像视为单个文本行
        # -c tessedit_char_whitelist=0123456789: 只识别数字
        cmd = ['tesseract', img_path, 'stdout', '--psm', '7', '-c', 'tessedit_char_whitelist=0123456789']
        
        print(f"执行Tesseract价格识别: {' '.join(cmd)}")
        
        # 运行Tesseract
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',
            timeout=10  # 10秒超时
        )
        
        if result.returncode == 0:
            text = result.stdout.strip()
            # 清理文本：移除所有非数字字符
            numbers = re.findall(r'\d+', text)
            if numbers:
                # 如果有多个数字块，拼接起来
                clean_text = ''.join(numbers)
                print(f"  价格识别结果: {clean_text}")
                return clean_text
            else:
                print(f"  未识别到价格数字")
                return ""
        else:
            print(f"  Tesseract价格识别错误: {result.stderr}")
            return ""
            
    except subprocess.TimeoutExpired:
        print(f"  价格识别超时")
        return ""
    except Exception as e:
        print(f"  价格识别异常: {e}")
        return ""

def ocr_chinese_with_tesseract_cmd(img_path):
    """使用Tesseract命令行OCR识别中文（商品名称）"""
    if not os.path.exists(img_path):
        print(f"图像不存在: {img_path}")
        return ""
    
    try:
        # Tesseract命令行参数 - 中文识别
        # --psm 7: 将图像视为单个文本行
        # -l chi_sim: 简体中文语言包
        # 移除字符白名单限制，允许识别所有字符
        cmd = ['tesseract', img_path, 'stdout', '--psm', '7', '-l', 'chi_sim']
        
        print(f"执行Tesseract中文识别: {' '.join(cmd)}")
        
        # 运行Tesseract
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',
            timeout=10  # 10秒超时
        )
        
        if result.returncode == 0:
            text = result.stdout.strip()
            # 清理中文文本
            if text:
                # 移除多余空格和换行
                text = re.sub(r'\s+', '', text)
                # 只保留中文、数字和常用标点
                text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9，。！？、：；""\'\'（）《》【】]', '', text)
                print(f"  中文识别结果: {text}")
                return text
            else:
                print(f"  未识别到中文文本")
                return ""
        else:
            print(f"  Tesseract中文识别错误: {result.stderr}")
            return ""
            
    except subprocess.TimeoutExpired:
        print(f"  中文识别超时")
        return ""
    except Exception as e:
        print(f"  中文识别异常: {e}")
        return ""

def safe_parse_filename(filename):
    """安全解析文件名"""
    pattern = r'(\d{8}_\d{6})_([a-z]+)_(\d+)_(\d+)\.png'
    match = re.match(pattern, filename)
    
    if match:
        try:
            return {
                'timestamp': match.group(1),
                'type': match.group(2),  # text 或 price
                'row': int(match.group(3)),
                'col': int(match.group(4)),
                'is_valid': True
            }
        except (ValueError, IndexError):
            pass
    
    print(f"警告: 无法解析文件名: {filename}")
    return {
        'timestamp': 'unknown',
        'type': 'unknown',
        'row': 0,
        'col': 0,
        'is_valid': False
    }

def process_upscaled_debug_images(upscaled_dir='debug_cells_x', friend_name=None):
    """处理放大后的图片，使用Tesseract命令行，保存JSON数据"""
    results = []
    product_data = {}
    
    if not os.path.exists(upscaled_dir):
        print(f"目录不存在: {upscaled_dir}")
        return results, product_data
    
    import glob
    
    all_files = glob.glob(os.path.join(upscaled_dir, "*.png"))
    print(f"在目录 {upscaled_dir} 中找到文件总数: {len(all_files)} 个")
    
    if not all_files:
        print("没有找到任何PNG文件")
        return results, product_data
    
    # 按时间戳分组处理
    file_groups = defaultdict(list)
    
    # 收集所有文件按时间戳分组
    for file_path in all_files:
        filename = os.path.basename(file_path)
        file_info = safe_parse_filename(filename)
        
        if not file_info['is_valid']:
            continue
        
        timestamp = file_info['timestamp']
        file_type = file_info['type']
        row = file_info['row']
        col = file_info['col']
        
        # 计算商品序号: (行-1)*7 + 列
        product_index = (row - 1) * 7 + col
        product_key = f"商品{product_index}"
        
        file_groups[timestamp].append({
            'file_path': file_path,
            'filename': filename,
            'row': row,
            'col': col,
            'type': file_type,  # text 或 price
            'product_key': product_key
        })
    
    # 处理每个时间戳组
    for timestamp, files in file_groups.items():
        print(f"\n处理时间戳组: {timestamp}")
        
        # 按商品序号排序
        files.sort(key=lambda x: x['product_key'])
        
        # 按类型分组：先处理text文件获取商品名称
        text_files = [f for f in files if f['type'] == 'text']
        price_files = [f for f in files if f['type'] == 'price']
        
        print(f"  text文件数量: {len(text_files)}")
        print(f"  price文件数量: {len(price_files)}")
        
        # 初始化所有商品的数据结构
        for file_info in files:
            product_key = file_info['product_key']
            if product_key not in product_data:
                product_data[product_key] = {
                    "name": "",        # 商品名称（将进行纠正）
                    "price": "",       # 单价
                    "name_raw": "",    # 原始OCR结果（用于调试）
                    "name_corrected": False  # 是否经过纠正
                }
        
        # 1. 先处理text文件（商品名称）
        for file_info in text_files:
            file_path = file_info['file_path']
            row = file_info['row']
            col = file_info['col']
            product_key = file_info['product_key']
            
            print(f"  处理商品名称: {product_key} (行{row},列{col})")
            
            # 使用Tesseract命令行OCR识别中文
            raw_chinese_text = ocr_chinese_with_tesseract_cmd(file_path)
            
            # 保存原始OCR结果
            product_data[product_key]["name_raw"] = raw_chinese_text
            
            # 商品名称纠正
            final_name = raw_chinese_text
            corrected = False
            
            if HAS_PRODUCT_MATCHER and raw_chinese_text:
                corrected_name, confidence = product_matcher.correct_product_name(raw_chinese_text)
                if corrected_name:
                    final_name = corrected_name
                    corrected = True
                    print(f"    原始: '{raw_chinese_text}' → 纠正: '{corrected_name}' (置信度: {confidence:.2f})")
                else:
                    print(f"    原始: '{raw_chinese_text}' → 无法匹配纠正")
            else:
                print(f"    原始结果: '{raw_chinese_text}'")
            
            # 更新商品数据
            product_data[product_key]["name"] = final_name
            product_data[product_key]["name_corrected"] = corrected
        
        # 2. 再处理price文件（单价）
        for file_info in price_files:
            file_path = file_info['file_path']
            row = file_info['row']
            col = file_info['col']
            product_key = file_info['product_key']
            
            print(f"  处理商品单价: {product_key} (行{row},列{col})")
            
            # 使用Tesseract命令行OCR识别价格
            price_text = ocr_price_with_tesseract_cmd(file_path)
            
            # 更新商品数据
            product_data[product_key]["price"] = price_text
            
            # 构建结果（不再包含combined字段）
            results.append({
                'timestamp': timestamp,
                'row': row,
                'col': col,
                'text': product_data[product_key]["name"],  # 纠正后的商品名称
                'price': price_text,  # 单价
                'product_key': product_key,
                'name_raw': product_data[product_key]["name_raw"],  # 原始OCR结果
                'name_corrected': product_data[product_key]["name_corrected"]  # 是否纠正
            })
    
    # 按行列排序结果
    results.sort(key=lambda x: (x['row'], x['col']))
    
    # 统计纠正效果
    corrected_count = sum(1 for p in product_data.values() if p["name_corrected"])
    raw_text_count = sum(1 for p in product_data.values() if p["name_raw"].strip())
    final_text_count = sum(1 for p in product_data.values() if p["name"].strip())
    price_count = sum(1 for p in product_data.values() if p["price"].strip())
    
    print(f"\n处理完成统计:")
    print(f"  总商品数: {len(product_data)}")
    print(f"  原始OCR识别: {raw_text_count}个")
    print(f"  商品名称纠正: {corrected_count}个")
    print(f"  最终商品名称: {final_text_count}个")
    print(f"  成功识别单价: {price_count}个")
    print(f"  完整数据: {sum(1 for p in product_data.values() if p['name'].strip() and p['price'].strip())}")
    
    # 显示纠正详情（前几个）
    if corrected_count > 0:
        print(f"\n纠正详情:")
        count = 0
        for key, data in product_data.items():
            if data["name_corrected"] and count < 5:  # 只显示前5个
                print(f"  {key}: '{data['name_raw']}' → '{data['name']}'")
                count += 1
    
    # 清理数据结构（移除调试字段，如果需要）
    clean_product_data = {}
    for key, data in product_data.items():
        clean_product_data[key] = {
            "name": data["name"],
            "price": data["price"]
        }
    
    # 如果有好友名，保存JSON数据
    if friend_name and clean_product_data and json_manager:
        try:
            json_filename = json_manager.save_product_data(friend_name, clean_product_data, timestamp)
            if json_filename:
                print(f"[OCR工具] JSON数据已保存: {json_filename}")
                print(f"[OCR工具] 数据结构: {len(clean_product_data)}个商品")
                
                # 显示前几个商品的纠正效果
                print(f"[OCR工具] 商品纠正统计: {corrected_count}/{len(product_data)}")
                for i in range(1, min(4, len(clean_product_data) + 1)):
                    key = f"商品{i}"
                    if key in clean_product_data:
                        name = clean_product_data[key]['name']
                        price = clean_product_data[key]['price']
                        if key in product_data and product_data[key]['name_corrected']:
                            raw = product_data[key]['name_raw']
                            print(f"  {key}: '{raw}' → '{name}' | 价格: {price}")
                        else:
                            print(f"  {key}: {name} | 价格: {price}")
            else:
                print(f"[OCR工具] JSON数据保存失败")
        except Exception as e:
            print(f"[OCR工具] 保存JSON数据失败: {e}")
            import traceback
            traceback.print_exc()
    
    return results, clean_product_data

def process_custom_directory(directory):
    """处理指定目录下的所有图片 - 兼容旧版本（不保存JSON）"""
    return process_upscaled_debug_images(directory, None)[0]

def clear_debug_directory():
    """清空调试目录（不删除目录本身）"""
    debug_dir = 'debug_cells'
    if os.path.exists(debug_dir):
        import shutil
        for item in os.listdir(debug_dir):
            item_path = os.path.join(debug_dir, item)
            try:
                if os.path.isfile(item_path) or os.path.islink(item_path):
                    os.unlink(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
            except Exception as e:
                print(f"清理 {item_path} 时出错: {e}")
        print(f"已清空调试目录内容: {debug_dir}")
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
                print(f"清理 {item_path} 时出错: {e}")
        print(f"已清空放大目录内容: {upscaled_dir}")

# 保持向后兼容的函数
def process_all_debug_images():
    """处理debug_cells目录下的所有图片 - 使用安全的文件名解析"""
    return process_custom_directory('debug_cells')

def ocr_image_with_merge(img_path, region_type='text'):
    """旧版本的OCR函数，保持向后兼容"""
    if region_type == 'price':
        return ocr_price_with_tesseract_cmd(img_path)
    else:
        return ocr_chinese_with_tesseract_cmd(img_path)

# 导出必要的函数
__all__ = [
    'save_debug_images_with_exclusion',
    'save_debug_images',
    'ocr_price_with_tesseract_cmd',
    'ocr_chinese_with_tesseract_cmd',
    'process_upscaled_debug_images',
    'process_custom_directory',
    'clear_debug_directory',
    'process_all_debug_images',
    'ocr_image_with_merge'
]