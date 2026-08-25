import asyncio
import json
from typing import List, Dict, Any, Callable, Optional
from datetime import datetime, timedelta
import threading
import time


class PrefetchManager:
    """
    Prefetch manager responsible for pre-loading potentially needed cache items
    """
    
    def __init__(self, cache_manager):
        self.cache_manager = cache_manager
        self.prefetch_queue = []
        self.prefetch_thread = None
        self.running = False
        self.prediction_callbacks = []
        
    def add_prediction_callback(self, callback: Callable[[str, Dict], Any]):
        """
        Add prediction callback function
        
        Args:
            callback: Function that accepts (prompt, context) and returns prediction result
        """
        self.prediction_callbacks.append(callback)
        
    def schedule_prefetch(self, prompt: str, context: Dict[str, Any], priority: int = 1):
        """
        Schedule prefetch task
        
        Args:
            prompt: Prompt text
            context: Context
            priority: Priority (smaller number means higher priority)
        """
        prefetch_item = {
            'prompt': prompt,
            'context': context,
            'priority': priority,
            'scheduled_time': datetime.now(),
            'status': 'pending'
        }
        
        # 按优先级插入队列
        inserted = False
        for i, item in enumerate(self.prefetch_queue):
            if item['priority'] > priority:
                self.prefetch_queue.insert(i, prefetch_item)
                inserted = True
                break
                
        if not inserted:
            self.prefetch_queue.append(prefetch_item)
            
    def start_prefetch_worker(self):
        """Start prefetch worker thread"""
        if self.running:
            return
            
        self.running = True
        self.prefetch_thread = threading.Thread(target=self._prefetch_worker, daemon=True)
        self.prefetch_thread.start()
        
    def stop_prefetch_worker(self):
        """Stop prefetch worker thread"""
        self.running = False
        if self.prefetch_thread:
            self.prefetch_thread.join(timeout=5)
            
    def _prefetch_worker(self):
        """Prefetch worker thread main loop"""
        while self.running:
            try:
                if self.prefetch_queue:
                    # 处理最高优先级的任务
                    item = self.prefetch_queue.pop(0)
                    
                    if item['status'] == 'pending':
                        self._execute_prefetch(item)
                else:
                    # 队列为空时短暂休眠
                    time.sleep(0.1)
                    
            except Exception as e:
                print(f"Prefetch worker error: {e}")
                time.sleep(1)
                
    def _execute_prefetch(self, item: Dict[str, Any]):
        """Execute single prefetch task"""
        try:
            item['status'] = 'processing'
            
            # 调用预测回调生成实际需要缓存的内容
            predictions = []
            for callback in self.prediction_callbacks:
                try:
                    prediction = callback(item['prompt'], item['context'])
                    if prediction:
                        predictions.append(prediction)
                except Exception as e:
                    print(f"Prediction callback error: {e}")
            
            # 将预测结果缓存
            for prediction in predictions:
                if isinstance(prediction, dict):
                    # 如果是字典格式，假设有prompt和response字段
                    pred_prompt = prediction.get('prompt', item['prompt'])
                    pred_response = prediction.get('response')
                    if pred_response:
                        self.cache_manager.set(pred_prompt, item['context'], pred_response)
                elif isinstance(prediction, str):
                    # 如果是字符串，作为响应缓存
                    self.cache_manager.set(item['prompt'], item['context'], prediction)
                    
            item['status'] = 'completed'
            item['completed_time'] = datetime.now()
            
        except Exception as e:
            item['status'] = 'failed'
            item['error'] = str(e)
            print(f"Prefetch execution error: {e}")
            
    def get_queue_status(self) -> Dict[str, Any]:
        """Get prefetch queue status"""
        pending = sum(1 for item in self.prefetch_queue if item['status'] == 'pending')
        processing = sum(1 for item in self.prefetch_queue if item['status'] == 'processing')
        completed = sum(1 for item in self.prefetch_queue if item['status'] == 'completed')
        failed = sum(1 for item in self.prefetch_queue if item['status'] == 'failed')
        
        return {
            'queue_size': len(self.prefetch_queue),
            'pending': pending,
            'processing': processing,
            'completed': completed,
            'failed': failed,
            'running': self.running
        }
        
    def clear_queue(self):
        """Clear prefetch queue"""
        self.prefetch_queue.clear()
        
    def bulk_schedule_from_patterns(self, patterns: List[Dict[str, Any]], context_template: Dict[str, Any]):
        """
        Bulk schedule prefetch based on usage patterns
        
        Args:
            patterns: Pattern list
            context_template: Context template
        """
        for pattern in patterns:
            if pattern['type'] == 'action_frequency':
                # 基于高频操作安排预取
                for action_type, frequency in pattern['data'].items():
                    if frequency >= pattern['threshold']:
                        prompt_templates = self._get_prompt_templates_for_action(action_type)
                        for template in prompt_templates:
                            self.schedule_prefetch(template, context_template.copy(), priority=2)
                            
            elif pattern['type'] == 'keyword_frequency':
                # 基于高频关键词安排预取
                for keyword, frequency in pattern['data'].items():
                    if frequency >= pattern['threshold']:
                        prompt_templates = self._get_prompt_templates_for_keyword(keyword)
                        for template in prompt_templates:
                            self.schedule_prefetch(template, context_template.copy(), priority=3)
                            
    def _get_prompt_templates_for_action(self, action_type: str) -> List[str]:
        """Get prompt templates for action type"""
        templates = {
            'click': [
                '点击页面上的按钮',
                '点击链接',
                '点击提交按钮'
            ],
            'fill': [
                '在输入框中输入文本',
                '填写表单字段',
                '输入搜索关键词'
            ],
            'search': [
                '执行搜索操作',
                '查找相关信息',
                '搜索指定内容'
            ],
            'assert': [
                '验证页面元素存在',
                '检查文本内容',
                '确认操作结果'
            ],
            'query': [
                '查询页面信息',
                '获取元素列表',
                '提取页面数据'
            ]
        }
        return templates.get(action_type, [f'执行{action_type}操作'])
        
    def _get_prompt_templates_for_keyword(self, keyword: str) -> List[str]:
        """Get prompt templates for keyword"""
        return [
            f'处理包含"{keyword}"的内容',
            f'针对"{keyword}"执行操作',
            f'查找"{keyword}"相关信息'
        ]
