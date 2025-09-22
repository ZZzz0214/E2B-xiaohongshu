"""
帖子分类数据仓库
负责xiaohongshu_content_classification表的数据库操作
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from .connect_manager import db_manager

logger = logging.getLogger(__name__)

class ClassificationRepository:
    """帖子分类数据仓库"""
    
    def __init__(self):
        self.table_name = "xiaohongshu_content_classification"
    
    def get_post_info_by_post_id(self, post_id: str) -> Optional[Dict[str, Any]]:
        """
        根据post_id从xiaohongshu_posts表查找帖子信息
        
        Args:
            post_id: 帖子ID
            
        Returns:
            帖子信息字典或None
        """
        try:
            with db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    sql = """
                    SELECT post_id, author_id, author_name, title 
                    FROM xiaohongshu_posts 
                    WHERE post_id = %s
                    """
                    cursor.execute(sql, (post_id,))
                    result = cursor.fetchone()
                    
                    if result:
                        return dict(result)
                    else:
                        logger.warning(f"未找到post_id在xiaohongshu_posts表中: {post_id}")
                        return None
                        
        except Exception as e:
            logger.error(f"查询帖子信息失败: {post_id} - {e}")
            return None
    
    def insert_classification(self, classification_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        插入帖子分类结果
        
        Args:
            classification_data: 分类数据字典
            
        Returns:
            操作结果
        """
        try:
            # 首先从xiaohongshu_posts表获取帖子信息
            post_id = classification_data.get('post_id')
            post_info = self.get_post_info_by_post_id(post_id)
            
            if post_info is None:
                return {
                    'success': False,
                    'error': f'找不到post_id在xiaohongshu_posts表中: {post_id}',
                    'post_id': post_id
                }
            
            # 准备插入数据 - 使用数据库中的真实信息
            sql = """
            INSERT INTO xiaohongshu_content_classification 
            (content_unified_id, post_id, author_id, author_name, title, 
             classification, confidence_score, reasoning, commercial_value, 
             need_ai_analysis, analysis_model, analysis_version, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                classification = VALUES(classification),
                confidence_score = VALUES(confidence_score),
                reasoning = VALUES(reasoning),
                commercial_value = VALUES(commercial_value),
                need_ai_analysis = VALUES(need_ai_analysis),
                updated_at = CURRENT_TIMESTAMP
            """
            
            params = (
                None,  # content_unified_id 设为 NULL，帖子分类不需要依赖 content_unified 表
                post_info['post_id'],              # 使用数据库中的 post_id
                post_info['author_id'],            # 使用数据库中的 author_id
                post_info['author_name'],          # 使用数据库中的 author_name  
                post_info['title'],                # 使用数据库中的 title
                classification_data.get('classification'),
                classification_data.get('confidence_score'),
                classification_data.get('reasoning'),
                classification_data.get('commercial_value'),
                classification_data.get('need_ai_analysis', True),
                'dify-llm',
                '1.0',
                datetime.now()
            )
            
            with db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, params)
                    conn.commit()
                    
                    affected_rows = cursor.rowcount
                    
                    if affected_rows == 1:
                        logger.debug(f"✅ 帖子分类插入成功: {post_id}")
                        operation = "inserted"
                    elif affected_rows == 2:
                        logger.debug(f"🔄 帖子分类更新成功: {post_id}")
                        operation = "updated"
                    else:
                        logger.debug(f"📋 帖子分类无变化: {post_id}")
                        operation = "no_change"
                    
                    return {
                        'success': True,
                        'post_id': post_id,
                        'author_id': post_info['author_id'],
                        'author_name': post_info['author_name'],
                        'operation': operation
                    }
                    
        except Exception as e:
            logger.error(f"❌ 帖子分类插入失败: {post_id} - {e}")
            return {
                'success': False,
                'error': str(e),
                'post_id': post_id
            }
    
    def batch_insert_classifications(self, classifications: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        批量插入帖子分类结果
        
        Args:
            classifications: 分类数据列表
            
        Returns:
            批量操作结果
        """
        start_time = datetime.now()
        
        stored_posts = []
        failed_posts = []
        
        logger.info(f"📝 开始批量插入帖子分类: {len(classifications)} 个")
        
        for classification in classifications:
            result = self.insert_classification(classification)
            
            if result['success']:
                stored_posts.append({
                    'post_id': result['post_id'],
                    'author_id': result['author_id'],
                    'author_name': result['author_name'],
                    'operation': result['operation']
                })
            else:
                failed_posts.append({
                    'post_id': result['post_id'],
                    'error': result['error']
                })
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        result = {
            'success': len(stored_posts) > 0,
            'total_count': len(classifications),
            'stored_count': len(stored_posts),
            'failed_count': len(failed_posts),
            'stored_posts': stored_posts,
            'failed_posts': failed_posts,
            'execution_time': execution_time,
            'stored_at': datetime.now().isoformat()
        }
        
        logger.info(f"✅ 批量插入完成: {len(stored_posts)} 成功, {len(failed_posts)} 失败, 耗时 {execution_time:.2f}s")
        
        return result
    
    def get_classification_by_post_id(self, post_id: str) -> Optional[Dict[str, Any]]:
        """
        根据post_id查询分类结果
        
        Args:
            post_id: 帖子ID
            
        Returns:
            分类结果或None
        """
        try:
            with db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    sql = """
                    SELECT * FROM xiaohongshu_content_classification 
                    WHERE post_id = %s
                    """
                    cursor.execute(sql, (post_id,))
                    result = cursor.fetchone()
                    
                    if result:
                        return dict(result)
                    else:
                        return None
                        
        except Exception as e:
            logger.error(f"查询帖子分类失败: {post_id} - {e}")
            return None

# 创建全局实例
classification_repository = ClassificationRepository()
