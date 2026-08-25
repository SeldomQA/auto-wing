import json
from collections import defaultdict, Counter
from typing import List, Dict, Any, Tuple
from datetime import datetime
import re


class UsagePatternAnalyzer:
    """
    Analyze user usage patterns and identify common operation patterns and context features
    """
    
    def __init__(self):
        self.pattern_history = []
        self.context_features = defaultdict(list)
        self.operation_sequences = []
        self.current_sequence = []
        
    def record_operation(self, prompt: str, context: Dict[str, Any], response: Any, execution_time: float):
        """
        Record an operation for pattern analysis
        
        Args:
            prompt: User prompt
            context: Context information
            response: LLM response
            execution_time: Execution time
        """
        operation_record = {
            'timestamp': datetime.now().isoformat(),
            'prompt': prompt,
            'context': context,
            'response': response,
            'execution_time': execution_time,
            'features': self._extract_features(prompt, context)
        }
        
        self.pattern_history.append(operation_record)
        self.current_sequence.append(operation_record)
        
        # 保持历史记录在合理范围内
        if len(self.pattern_history) > 1000:
            self.pattern_history = self.pattern_history[-1000:]
            
    def _extract_features(self, prompt: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract features from prompt and context
        
        Returns:
            Dictionary containing various features
        """
        features = {}
        
        # 提示词特征
        features['prompt_length'] = len(prompt)
        features['prompt_keywords'] = self._extract_keywords(prompt)
        features['action_type'] = self._classify_action(prompt)
        features['complexity_score'] = self._calculate_complexity(prompt)
        
        # 上下文特征
        features['url_domain'] = self._extract_domain(context.get('url', ''))
        features['page_title_length'] = len(context.get('title', ''))
        features['element_count'] = len(context.get('elements', []))
        features['element_types'] = self._count_element_types(context.get('elements', []))
        
        return features
        
    def _extract_keywords(self, prompt: str) -> List[str]:
        """Extract keywords from the prompt"""
        # 移除标点符号并分割
        words = re.findall(r'\b\w+\b', prompt.lower())
        # 过滤常见停用词
        stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        return [word for word in words if word not in stop_words and len(word) > 2]
        
    def _classify_action(self, prompt: str) -> str:
        """Classify action type"""
        prompt_lower = prompt.lower()
        
        if any(keyword in prompt_lower for keyword in ['click', '点击', 'press', '按下']):
            return 'click'
        elif any(keyword in prompt_lower for keyword in ['fill', '输入', 'type', '填写']):
            return 'fill'
        elif any(keyword in prompt_lower for keyword in ['search', '搜索', 'find', '查找']):
            return 'search'
        elif any(keyword in prompt_lower for keyword in ['assert', '验证', 'check', '检查']):
            return 'assert'
        elif any(keyword in prompt_lower for keyword in ['query', '查询', 'get', '获取']):
            return 'query'
        else:
            return 'other'
            
    def _calculate_complexity(self, prompt: str) -> int:
        """Calculate prompt complexity"""
        # 基于句子长度、子句数量等计算
        sentences = re.split(r'[.!?]+', prompt)
        return len(sentences) + prompt.count(',') + prompt.count('，')
        
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        if not url:
            return ''
        # 简单的域名提取
        match = re.search(r'https?://([^/]+)', url)
        return match.group(1) if match else url
        
    def _count_element_types(self, elements: List[Dict]) -> Dict[str, int]:
        """Count element types"""
        type_counts = defaultdict(int)
        for element in elements:
            tag = element.get('tag', '').lower()
            type_counts[tag] += 1
        return dict(type_counts)
        
    def get_common_patterns(self, min_frequency: int = 3) -> List[Dict[str, Any]]:
        """
        Get frequently used patterns
        
        Args:
            min_frequency: Minimum occurrence frequency
            
        Returns:
            List of common patterns
        """
        if len(self.pattern_history) < min_frequency:
            return []
            
        # 统计操作类型频率
        action_counter = Counter(record['features']['action_type'] 
                               for record in self.pattern_history)
        
        # 统计关键词频率
        all_keywords = []
        for record in self.pattern_history:
            all_keywords.extend(record['features']['prompt_keywords'])
        keyword_counter = Counter(all_keywords)
        
        # 统计域名频率
        domain_counter = Counter(record['features']['url_domain'] 
                               for record in self.pattern_history 
                               if record['features']['url_domain'])
        
        return [
            {
                'type': 'action_frequency',
                'data': dict(action_counter),
                'threshold': min_frequency
            },
            {
                'type': 'keyword_frequency',
                'data': dict(keyword_counter.most_common(20)),
                'threshold': min_frequency
            },
            {
                'type': 'domain_frequency',
                'data': dict(domain_counter),
                'threshold': min_frequency
            }
        ]
        
    def predict_next_operation(self) -> Dict[str, Any]:
        """
        Predict the next possible operation based on current sequence
        
        Returns:
            Prediction result and confidence
        """
        if len(self.current_sequence) < 2:
            return {'prediction': None, 'confidence': 0.0}
            
        # 简单的序列模式匹配
        last_actions = [record['features']['action_type'] 
                       for record in self.current_sequence[-3:]]
        
        # 查找历史中相似的序列
        similar_sequences = []
        for i in range(len(self.pattern_history) - len(last_actions)):
            history_segment = self.pattern_history[i:i+len(last_actions)]
            history_actions = [record['features']['action_type'] 
                             for record in history_segment]
            
            if history_actions == last_actions:
                # 获取下一个操作
                if i + len(last_actions) < len(self.pattern_history):
                    next_op = self.pattern_history[i + len(last_actions)]
                    similar_sequences.append(next_op['features']['action_type'])
        
        if similar_sequences:
            counter = Counter(similar_sequences)
            most_common = counter.most_common(1)[0]
            return {
                'prediction': most_common[0],
                'confidence': most_common[1] / len(similar_sequences),
                'based_on_samples': len(similar_sequences)
            }
            
        return {'prediction': None, 'confidence': 0.0}
        
    def reset_sequence(self):
        """Reset current operation sequence"""
        self.current_sequence = []
        
    def get_statistics(self) -> Dict[str, Any]:
        """Get usage statistics"""
        if not self.pattern_history:
            return {}
            
        execution_times = [record['execution_time'] for record in self.pattern_history]
        
        return {
            'total_operations': len(self.pattern_history),
            'avg_execution_time': sum(execution_times) / len(execution_times),
            'min_execution_time': min(execution_times),
            'max_execution_time': max(execution_times),
            'operation_sequences_count': len(self.operation_sequences),
            'current_sequence_length': len(self.current_sequence)
        }
