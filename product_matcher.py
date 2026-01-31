# file name: product_matcher.py
"""
商品名称匹配纠正器
将OCR识别出的错误商品名称纠正为正确名称
"""
import re
from typing import Dict, List, Tuple, Optional

class ProductMatcher:
    def __init__(self):
        """初始化商品数据库和特征"""
        # 正确的商品名称列表
        self.correct_products = [
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
        
        # OCR常见错误字符映射
        self.ocr_error_map = {
            '锁': '锚',      # 锁点→锚点
            '和': '货',      # 和任组→货组
            '任': '组',      # 和任组→货组
            '吴': '鼷',      # 吴胃→鼷兽
            '胃': '兽',      # 吴胃→鼷兽
            '偶': '货',      # 偶组→货组
            '蛙': '赛',      # 蛙什卡→赛什卡
            '体': '髀',      # 体石→髀石
            '旺': '晶',
            '4': '星体晶块',
            '备': '盔',
            '帝': '壳'
            # 更多错误映射可以根据实际情况添加
        }
        
        # 构建每个商品的特征组合
        self.product_features = self._extract_product_features()
        
        # 构建快速查找索引
        self.feature_to_product = self._build_feature_index()
    
    def _extract_product_features(self) -> Dict[str, List[Tuple[str, str]]]:
        """为每个商品提取特征字组合"""
        features = {}
        
        for product in self.correct_products:
            product_features = []
            chars = list(product)
            length = len(chars)
            
            # 提取所有相邻两字组合
            for i in range(length - 1):
                char1 = chars[i]
                char2 = chars[i + 1]
                # 跳过通用后缀"货组"
                if char1 == "货" and char2 == "组":
                    continue
                product_features.append((char1, char2))
            
            # 提取关键非相邻组合（第一个字和最后一个特征字）
            if length >= 3:
                key_chars = [chars[0]]
                # 找到最后一个非"货组"的字
                for i in range(length - 1, -1, -1):
                    if chars[i] not in ["货", "组"]:
                        key_chars.append(chars[i])
                        break
                if len(key_chars) == 2:
                    product_features.append((key_chars[0], key_chars[1]))
            
            features[product] = product_features
        
        return features
    
    def _build_feature_index(self) -> Dict[Tuple[str, str], str]:
        """构建特征组合到商品的映射索引"""
        index = {}
        
        for product, features in self.product_features.items():
            for feature in features:
                # 如果这个特征组合已经存在，标记为冲突（None）
                if feature in index:
                    index[feature] = None  # 冲突标记
                else:
                    index[feature] = product
        
        # 清理冲突的特征
        for feature, product in list(index.items()):
            if product is None:
                del index[feature]
        
        return index
    
    def _preprocess_text(self, text: str) -> str:
        """预处理文本：清理和错误字符修正"""
        if not text:
            return ""
        
        # 移除空格和标点
        text = re.sub(r'[\s\W]+', '', text)
        
        # 应用OCR错误修正
        for wrong_char, correct_char in self.ocr_error_map.items():
            text = text.replace(wrong_char, correct_char)
        
        return text
    
    def _extract_features_from_text(self, text: str) -> List[Tuple[str, str]]:
        """从文本中提取特征组合"""
        if not text or len(text) < 2:
            return []
        
        features = []
        chars = list(text)
        
        # 提取所有相邻两字组合
        for i in range(len(chars) - 1):
            features.append((chars[i], chars[i + 1]))
        
        return features
    
    def _calculate_match_score(self, text_features: List[Tuple[str, str]], 
                              product_features: List[Tuple[str, str]]) -> float:
        """计算文本特征与商品特征的匹配分数"""
        if not text_features or not product_features:
            return 0.0
        
        # 计算交集数量
        common_features = set(text_features) & set(product_features)
        
        # 计算匹配分数：共同特征数 / 商品特征数
        return len(common_features) / len(product_features) if product_features else 0.0
    
    def correct_product_name(self, ocr_text: str) -> Tuple[str, float]:
        """
        纠正OCR识别的商品名称
        
        Args:
            ocr_text: OCR识别出的商品名称
            
        Returns:
            Tuple[corrected_name, confidence_score]
            如果无法匹配，返回("", 0.0)
        """
        if not ocr_text or not ocr_text.strip():
            return "", 0.0
        
        # 1. 预处理文本
        processed_text = self._preprocess_text(ocr_text)
        
        # 2. 尝试完全匹配
        if processed_text in self.correct_products:
            return processed_text, 1.0
        
        # 3. 提取文本特征
        text_features = self._extract_features_from_text(processed_text)
        if not text_features:
            return "", 0.0
        
        # 4. 快速查找：检查是否有唯一匹配的特征
        for feature in text_features:
            if feature in self.feature_to_product:
                product = self.feature_to_product[feature]
                # 验证这个特征确实是该商品的特征
                if product and feature in self.product_features[product]:
                    # 计算完整匹配分数
                    score = self._calculate_match_score(text_features, 
                                                       self.product_features[product])
                    if score >= 0.3:  # 阈值可调整
                        return product, score
        
        # 5. 如果快速查找失败，进行完整匹配计算
        best_match = ""
        best_score = 0.0
        
        for product, product_feats in self.product_features.items():
            score = self._calculate_match_score(text_features, product_feats)
            if score > best_score:
                best_score = score
                best_match = product
        
        # 6. 返回结果（设置置信度阈值）
        if best_score >= 0.4:  # 需要至少40%的特征匹配
            return best_match, best_score
        else:
            return "", 0.0
    
    def batch_correct(self, ocr_texts: List[str]) -> List[Tuple[str, float]]:
        """批量纠正商品名称"""
        results = []
        for text in ocr_texts:
            results.append(self.correct_product_name(text))
        return results
    
    def validate_correction(self, ocr_text: str, corrected_text: str) -> bool:
        """验证纠正结果是否合理"""
        if not corrected_text:
            return False
        
        # 简单验证：纠正后的文本应该在商品列表中
        return corrected_text in self.correct_products


# 全局实例，方便导入使用
_product_matcher_instance = None

def get_product_matcher() -> ProductMatcher:
    """获取商品匹配器单例实例"""
    global _product_matcher_instance
    if _product_matcher_instance is None:
        _product_matcher_instance = ProductMatcher()
    return _product_matcher_instance


# 测试函数
if __name__ == "__main__":
    matcher = ProductMatcher()
    
    test_cases = [
        "锁点厨具和任组",      # 应该纠正为"锚点厨具货组"
        "悬空吴胃骨雕货组",    # 应该纠正为"悬空鼷兽骨雕货组"
        "巫术矿钻货组",        # 应该保持原样
        "天使罐头货组",        # 应该保持原样
        "谷地水培肉货组",      # 应该保持原样
        "团结牌口服液偶组",    # 应该纠正为"团结牌口服液货组"
        "源石树幼苗货组",      # 应该保持原样
        "蛙什卡体石货组",      # 应该纠正为"赛什卡髀石货组"
        "测试无效商品",        # 应该返回空
        "",                   # 空输入
    ]
    
    print("商品名称纠正测试:")
    print("-" * 50)
    for test in test_cases:
        corrected, score = matcher.correct_product_name(test)
        if corrected:
            print(f"输入: '{test}' → 纠正: '{corrected}' (置信度: {score:.2f})")
        else:
            print(f"输入: '{test}' → 无法匹配")