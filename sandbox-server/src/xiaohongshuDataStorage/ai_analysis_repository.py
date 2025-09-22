"""
AI分析数据仓库
负责xiaohongshu_ai_analysis表的数据库操作
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from .connect_manager import db_manager

logger = logging.getLogger(__name__)

class AIAnalysisRepository:
    """AI分析数据仓库"""
    
    def __init__(self):
        self.table_name = "xiaohongshu_ai_analysis"
    
    def get_content_unified_id_by_comment_id(self, comment_id: str) -> Optional[int]:
        """
        根据comment_id查找对应的content_unified_id
        
        Args:
            comment_id: 评论ID
            
        Returns:
            content_unified_id或None
        """
        try:
            with db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    sql = """
                    SELECT id as content_unified_id 
                    FROM xiaohongshu_content_unified 
                    WHERE content_id = %s AND content_type IN ('comment', 'reply')
                    """
                    cursor.execute(sql, (comment_id,))
                    result = cursor.fetchone()
                    
                    if result:
                        return result['content_unified_id']
                    else:
                        logger.warning(f"未找到comment_id对应的content_unified_id: {comment_id}")
                        return None
                        
        except Exception as e:
            logger.error(f"查询content_unified_id失败: {comment_id} - {e}")
            return None
    
    def get_classification_id_by_post_id(self, post_id: str) -> Optional[int]:
        """
        根据post_id查找对应的classification_id
        
        Args:
            post_id: 帖子ID
            
        Returns:
            classification_id或None
        """
        try:
            with db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    sql = """
                    SELECT id as classification_id 
                    FROM xiaohongshu_content_classification 
                    WHERE post_id = %s
                    """
                    cursor.execute(sql, (post_id,))
                    result = cursor.fetchone()
                    
                    if result:
                        return result['classification_id']
                    else:
                        logger.warning(f"未找到post_id对应的classification_id: {post_id}")
                        return None
                        
        except Exception as e:
            logger.error(f"查询classification_id失败: {post_id} - {e}")
            return None
    
    def insert_comment_analysis(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        插入评论分析结果
        
        Args:
            analysis_data: 分析数据字典
            
        Returns:
            操作结果
        """
        try:
            comment_id = analysis_data.get('comment_id')
            
            # 获取content_unified_id
            content_unified_id = self.get_content_unified_id_by_comment_id(comment_id)
            if content_unified_id is None:
                return {
                    'success': False,
                    'error': f'找不到comment_id对应的原始数据: {comment_id}',
                    'comment_id': comment_id
                }
            
            # 获取classification_id（通过帖子ID推断）
            # 由于我们没有直接的post_id，我们先查找这个评论所属的帖子
            post_id = self.get_post_id_by_comment_id(comment_id)
            if post_id is None:
                return {
                    'success': False,
                    'error': f'找不到comment_id对应的post_id: {comment_id}',
                    'comment_id': comment_id
                }
            
            classification_id = self.get_classification_id_by_post_id(post_id)
            if classification_id is None:
                return {
                    'success': False,
                    'error': f'找不到post_id对应的classification_id: {post_id}',
                    'comment_id': comment_id
                }
            
            # 准备插入数据
            sql = """
            INSERT INTO xiaohongshu_ai_analysis 
            (classification_id, content_unified_id, post_id, is_valid, confidence,
             product_category, functional_needs, user_profile, size_info, 
             user_pain_points, brands, intent_type, intent_level, business_value,
             follow_up_action, sentiment, analysis_batch, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                is_valid = VALUES(is_valid),
                confidence = VALUES(confidence),
                intent_type = VALUES(intent_type),
                intent_level = VALUES(intent_level),
                sentiment = VALUES(sentiment),
                business_value = VALUES(business_value),
                follow_up_action = VALUES(follow_up_action)
            """
            
            # 从key_features中提取字段
            key_features = analysis_data.get('key_features', {})
            
            params = (
                classification_id,
                content_unified_id,
                post_id,
                analysis_data.get('is_valid', True),
                analysis_data.get('confidence', 0.8),
                key_features.get('product_category'),
                key_features.get('functional_needs'),
                key_features.get('user_profile'),
                key_features.get('size_info'),
                None,  # user_pain_points - 数据中没有
                None,  # brands - 数据中没有
                analysis_data.get('intent_type'),
                analysis_data.get('intent_level'),
                analysis_data.get('business_value'),
                analysis_data.get('follow_up_action'),
                analysis_data.get('sentiment'),
                f"batch_{int(datetime.now().timestamp())}",  # analysis_batch
                datetime.now()
            )
            
            with db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, params)
                    conn.commit()
                    
                    affected_rows = cursor.rowcount
                    
                    if affected_rows == 1:
                        logger.debug(f"✅ 评论分析插入成功: {comment_id}")
                        operation = "inserted"
                    elif affected_rows == 2:
                        logger.debug(f"🔄 评论分析更新成功: {comment_id}")
                        operation = "updated"
                    else:
                        logger.debug(f"📋 评论分析无变化: {comment_id}")
                        operation = "no_change"
                    
                    return {
                        'success': True,
                        'comment_id': comment_id,
                        'content_unified_id': content_unified_id,
                        'classification_id': classification_id,
                        'operation': operation
                    }
                    
        except Exception as e:
            logger.error(f"❌ 评论分析插入失败: {comment_id} - {e}")
            return {
                'success': False,
                'error': str(e),
                'comment_id': comment_id
            }
    
    def get_post_id_by_comment_id(self, comment_id: str) -> Optional[str]:
        """
        根据comment_id查找所属的post_id
        
        Args:
            comment_id: 评论ID
            
        Returns:
            post_id或None
        """
        try:
            with db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    sql = """
                    SELECT post_id 
                    FROM xiaohongshu_content_unified 
                    WHERE content_id = %s AND content_type IN ('comment', 'reply')
                    """
                    cursor.execute(sql, (comment_id,))
                    result = cursor.fetchone()
                    
                    if result:
                        return result['post_id']
                    else:
                        return None
                        
        except Exception as e:
            logger.error(f"查询post_id失败: {comment_id} - {e}")
            return None
    
    def batch_insert_comment_analysis(self, analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        批量插入评论分析结果
        
        Args:
            analyses: 分析数据列表
            
        Returns:
            批量操作结果
        """
        start_time = datetime.now()
        
        stored_comments = []
        failed_comments = []
        
        logger.info(f"📊 开始批量插入评论分析: {len(analyses)} 条")
        
        for analysis in analyses:
            result = self.insert_comment_analysis(analysis)
            
            if result['success']:
                stored_comments.append({
                    'comment_id': result['comment_id'],
                    'content_unified_id': result['content_unified_id'],
                    'classification_id': result['classification_id'],
                    'operation': result['operation']
                })
            else:
                failed_comments.append({
                    'comment_id': result['comment_id'],
                    'error': result['error']
                })
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        result = {
            'success': len(stored_comments) > 0,
            'total_count': len(analyses),
            'stored_count': len(stored_comments),
            'failed_count': len(failed_comments),
            'stored_comments': stored_comments,
            'failed_comments': failed_comments,
            'execution_time': execution_time,
            'stored_at': datetime.now().isoformat()
        }
        
        logger.info(f"✅ 批量插入完成: {len(stored_comments)} 成功, {len(failed_comments)} 失败, 耗时 {execution_time:.2f}s")
        
        return result

# 创建全局实例
ai_analysis_repository = AIAnalysisRepository()
