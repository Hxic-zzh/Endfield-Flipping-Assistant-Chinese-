# file name: json_data_manager.py
import os
import json
from datetime import datetime

class JsonDataManager:
    def __init__(self):
        self.base_dir = os.getcwd()
        self.temp_json_dir = os.path.join(self.base_dir, 'tempJson')
        self.mapping_file = os.path.join(self.base_dir, 'friend_mapping.json')
        
        # 确保目录存在
        self._ensure_directories()
    
    def _ensure_directories(self):
        """确保必要的目录存在"""
        # 创建tempJson目录
        if not os.path.exists(self.temp_json_dir):
            os.makedirs(self.temp_json_dir)
        
        # 初始化映射文件（确保不为空）
        if not os.path.exists(self.mapping_file):
            print(f"[JSON管理器] 创建新的映射文件")
            self._write_mapping({})
        else:
            # 检查文件是否为空
            try:
                with open(self.mapping_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if not content:
                        print(f"[JSON管理器] 映射文件为空，重新初始化")
                        self._write_mapping({})
            except:
                print(f"[JSON管理器] 读取映射文件失败，重新创建")
                self._write_mapping({})
    
    def _write_mapping(self, mapping_dict):
        """写入映射表"""
        with open(self.mapping_file, 'w', encoding='utf-8') as f:
            json.dump(mapping_dict, f, ensure_ascii=False, indent=2)
    
    def generate_timestamp(self):
        """生成时间戳"""
        return datetime.now().strftime('%Y%m%d_%H%M%S')
    
    def save_product_data(self, friend_name, product_data, timestamp=None):
        """保存商品数据到JSON文件"""
        if timestamp is None:
            timestamp = self.generate_timestamp()
        
        # 1. 保存商品数据
        json_filename = f"{timestamp}.json"
        json_path = os.path.join(self.temp_json_dir, json_filename)
        
        try:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(product_data, f, ensure_ascii=False, indent=2)
            print(f"[JSON管理器] 商品数据已保存: {json_path}")
        except Exception as e:
            print(f"[JSON管理器] 保存商品数据失败: {e}")
            return None
        
        # 2. 更新好友映射
        success = self.update_friend_mapping(friend_name, json_filename)
        
        if success:
            print(f"[JSON管理器] 好友映射已更新: {friend_name} -> {json_filename}")
            return json_filename
        else:
            print(f"[JSON管理器] 好友映射更新失败")
            return None
    
    def update_friend_mapping(self, friend_name, json_filename):
        """更新好友到JSON文件的映射"""
        try:
            # 读取现有映射
            if os.path.exists(self.mapping_file):
                with open(self.mapping_file, 'r', encoding='utf-8') as f:
                    mapping = json.load(f)
            else:
                mapping = {}
            
            # 更新映射（覆盖旧的）
            mapping[friend_name] = json_filename
            
            # 保存回文件
            self._write_mapping(mapping)
            return True
                
        except Exception as e:
            print(f"[JSON管理器] 更新映射表失败: {e}")
            # 如果失败，尝试重新创建文件
            try:
                self._write_mapping({friend_name: json_filename})
                print(f"[JSON管理器] 重新创建映射文件成功")
                return True
            except:
                print(f"[JSON管理器] 重新创建映射文件也失败")
                return False
    
    def get_friend_data(self, friend_name):
        """获取指定好友的最新数据"""
        try:
            if not os.path.exists(self.mapping_file):
                return None
            
            with open(self.mapping_file, 'r', encoding='utf-8') as f:
                mapping = json.load(f)
            
            if friend_name in mapping:
                json_filename = mapping[friend_name]
                # 如果映射值为空字符串，表示该好友无JSON数据
                if not json_filename:
                    return None
                    
                json_path = os.path.join(self.temp_json_dir, json_filename)
                
                if os.path.exists(json_path):
                    with open(json_path, 'r', encoding='utf-8') as f:
                        return json.load(f)
                else:
                    print(f"[JSON管理器] 数据文件不存在: {json_path}")
                    return None
            else:
                print(f"[JSON管理器] 好友不存在: {friend_name}")
                return None
                
        except Exception as e:
            print(f"[JSON管理器] 读取数据失败: {e}")
            return None
    
    def list_all_friends(self):
        """列出所有好友及其数据文件"""
        try:
            if not os.path.exists(self.mapping_file):
                return {}
            
            with open(self.mapping_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}