"""
小红书统一内容表操作
处理帖子详情、主评论、回复评论的统一存储
"""
import logging
import hashlib
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone
import json
import pymysql

from .connect_manager import db_manager

logger = logging.getLogger(__name__)

class ContentUnifiedRepository:
    """统一内容表数据操作类"""
    
    def __init__(self):
        self.db_manager = db_manager
    
    def _generate_content_hash(self, content: str) -> str:
        """生成内容哈希值，用于去重"""
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def _parse_timestamp(self, time_str: str) -> Optional[datetime]:
        """解析时间字符串为datetime对象"""
        if not time_str:
            return None
            
        # 处理各种时间格式
        formats = [
            "%Y/%m/%d %H:%M:%S",  # 2025/9/5 23:18:18
            "%Y-%m-%d %H:%M:%S",  # 2025-09-05 23:18:18
            "%Y/%m/%d",           # 2025/9/5
            "%Y-%m-%d"            # 2025-09-05
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(time_str, fmt)
            except ValueError:
                continue
        
        # 如果都不匹配，记录警告并返回None
        logger.warning(f"无法解析时间格式: {time_str}")
        return None
    
    def store_post_content(self, post_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        存储帖子正文内容
        
        Args:
            post_data: 帖子详情数据
            
        Returns:
            存储结果
        """
        try:
            # 提取帖子信息
            post_id = post_data.get('post_id')
            title = post_data.get('title', '')
            description = post_data.get('description', '')
            
            # 用户信息
            author = post_data.get('author', {})
            user_id = author.get('user_id') or post_data.get('author_id')
            user_name = author.get('nickname') or post_data.get('author_name', '')
            user_avatar = author.get('avatar', '')
            
            # 时间信息
            publish_time = post_data.get('publish_time')
            content_time = None
            publish_date = None
            
            if publish_time:
                try:
                    # 假设是毫秒时间戳
                    content_time = datetime.fromtimestamp(publish_time / 1000)
                    publish_date = content_time.date()
                except (ValueError, TypeError):
                    logger.warning(f"无法解析发布时间: {publish_time}")
            
            # 构建富内容JSON
            rich_content = {}
            if 'tags' in post_data:
                rich_content['tags'] = post_data['tags']
            
            # 互动数据
            interaction_stats = {}
            if 'like_count' in post_data or 'collect_count' in post_data:
                interaction_stats = {
                    'likes': post_data.get('like_count', 0),
                    'collects': post_data.get('collect_count', 0),
                    'comments': post_data.get('comment_count', 0),
                    'shares': post_data.get('share_count', 0)
                }
            
            # 构建插入数据
            insert_data = {
                'post_id': post_id,
                'content_id': post_id,  # 帖子的content_id就是post_id
                'parent_id': None,
                'content_level': 0,
                'display_order': 0,
                'thread_group': None,
                'content_type': 'post',
                'title': title,
                'content': description,
                'rich_content': json.dumps(rich_content, ensure_ascii=False) if rich_content else None,
                'user_id': user_id,
                'user_name': user_name,
                'user_avatar': user_avatar,
                'is_post_author': True,
                'interaction_stats': json.dumps(interaction_stats, ensure_ascii=False) if interaction_stats else None,
                'content_timestamp': publish_time,
                'content_time': content_time,
                'publish_date': publish_date,
                'ip_location': None,
                'content_hash': self._generate_content_hash(description),
                'extraction_source': 'global_state'
            }
            
            # 执行插入/更新
            result = self._upsert_content(insert_data)
            
            logger.info(f"✅ 帖子内容存储成功: {post_id}")
            return {
                'success': True,
                'content_id': post_id,
                'content_type': 'post',
                'operation': result['operation']
            }
            
        except Exception as e:
            logger.error(f"❌ 帖子内容存储失败: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'content_id': post_data.get('post_id'),
                'content_type': 'post'
            }
    
    def store_comments(self, post_id: str, comments_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        存储评论数据
        
        Args:
            post_id: 帖子ID
            comments_data: 评论列表
            
        Returns:
            存储结果统计
        """
        if not comments_data:
            return {
                'success': True,
                'stats': {'total': 0, 'success': 0, 'error': 0},
                'details': []
            }
        
        logger.info(f"💬 开始存储 {len(comments_data)} 条评论...")
        
        results = []
        success_count = 0
        error_count = 0
        
        for comment in comments_data:
            try:
                # 提取评论信息
                comment_id = comment.get('id')
                content = comment.get('content', '')
                raw_comment_type = comment.get('type', 'main')  # main 或 reply
                # 映射到数据库ENUM值
                comment_type = 'reply' if raw_comment_type == 'reply' else 'comment'
                parent_comment_id = comment.get('parent_comment_id')
                
                # 用户信息
                user_id = comment.get('user_id')
                user_name = comment.get('user', '')
                is_author = comment.get('is_author', False)
                
                # 时间和位置
                time_str = comment.get('time', '')
                content_time = self._parse_timestamp(time_str)
                publish_date = content_time.date() if content_time else None
                ip_location = comment.get('location')
                
                # 层级信息
                content_level = 2 if comment_type == 'reply' else 1
                display_order = comment.get('index', 0)
                thread_group = None
                
                # 如果是回复，找到所属的主评论组
                if comment_type == 'reply' and parent_comment_id:
                    thread_group = self._get_main_comment_thread_group(parent_comment_id)
                else:
                    # 主评论的thread_group就是其display_order
                    thread_group = display_order
                
                # 互动数据
                interaction_stats = {
                    'likes': int(comment.get('like_count', 0)) if comment.get('like_count', '0').isdigit() else 0,
                    'replies': int(comment.get('reply_count', 0)) if isinstance(comment.get('reply_count'), (int, str)) else 0
                }
                
                # 构建插入数据
                insert_data = {
                    'post_id': post_id,
                    'content_id': comment_id,
                    'parent_id': parent_comment_id,
                    'content_level': content_level,
                    'display_order': display_order,
                    'thread_group': thread_group,
                    'content_type': comment_type,
                    'title': None,
                    'content': content,
                    'rich_content': None,
                    'user_id': user_id,
                    'user_name': user_name,
                    'user_avatar': None,
                    'is_post_author': is_author,
                    'interaction_stats': json.dumps(interaction_stats, ensure_ascii=False),
                    'content_timestamp': None,
                    'content_time': content_time,
                    'publish_date': publish_date,
                    'ip_location': ip_location,
                    'content_hash': self._generate_content_hash(content),
                    'extraction_source': 'global_state'
                }
                
                # 执行插入/更新
                result = self._upsert_content(insert_data)
                
                results.append({
                    'success': True,
                    'content_id': comment_id,
                    'content_type': comment_type,
                    'operation': result['operation']
                })
                success_count += 1
                
                logger.debug(f"✅ 评论存储成功: {comment_id}")
                
            except Exception as e:
                logger.error(f"❌ 评论存储失败 {comment.get('id')}: {e}")
                results.append({
                    'success': False,
                    'error': str(e),
                    'content_id': comment.get('id'),
                    'content_type': comment_type if 'comment_type' in locals() else 'comment'
                })
                error_count += 1
        
        logger.info(f"💬 评论存储完成: {success_count} 成功, {error_count} 失败")
        
        return {
            'success': error_count == 0,
            'stats': {
                'total': len(comments_data),
                'success': success_count,
                'error': error_count
            },
            'details': results
        }
    
    def _get_main_comment_thread_group(self, parent_comment_id: str) -> Optional[int]:
        """获取主评论的thread_group"""
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT thread_group FROM xiaohongshu_content_unified 
                        WHERE content_id = %s AND content_level = 1
                        """,
                        (parent_comment_id,)
                    )
                    result = cursor.fetchone()
                    return result['thread_group'] if result else None
        except Exception as e:
            logger.error(f"查询主评论thread_group失败: {e}")
            return None
    
    def _upsert_content(self, data: Dict[str, Any]) -> Dict[str, str]:
        """
        插入或更新内容记录
        
        Args:
            data: 内容数据
            
        Returns:
            操作结果
        """
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 构建插入SQL
                    columns = list(data.keys())
                    placeholders = ', '.join(['%s'] * len(columns))
                    column_names = ', '.join(columns)
                    
                    # 构建ON DUPLICATE KEY UPDATE子句
                    update_clauses = []
                    for col in columns:
                        if col not in ['id', 'content_id', 'crawl_time']:  # 排除主键和唯一键
                            update_clauses.append(f"{col} = VALUES({col})")
                    
                    sql = f"""
                        INSERT INTO xiaohongshu_content_unified ({column_names})
                        VALUES ({placeholders})
                        ON DUPLICATE KEY UPDATE
                        {', '.join(update_clauses)},
                        updated_at = CURRENT_TIMESTAMP
                    """
                    
                    values = list(data.values())
                    cursor.execute(sql, values)
                    
                    # 判断是插入还是更新
                    if cursor.rowcount == 1:
                        operation = 'insert'
                    elif cursor.rowcount == 2:
                        operation = 'update'
                    else:
                        operation = 'no_change'
                    
                    conn.commit()
                    return {'operation': operation}
                    
        except Exception as e:
            logger.error(f"内容upsert操作失败: {e}")
            raise
    
    def get_content_stats(self, post_id: Optional[str] = None) -> Dict[str, Any]:
        """
        获取内容统计信息
        
        Args:
            post_id: 指定帖子ID，为None时返回全局统计
            
        Returns:
            统计信息
        """
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    where_clause = "WHERE post_id = %s" if post_id else ""
                    params = [post_id] if post_id else []
                    
                    cursor.execute(f"""
                        SELECT 
                            content_type,
                            COUNT(*) as count,
                            COUNT(CASE WHEN is_deleted = 0 THEN 1 END) as active_count
                        FROM xiaohongshu_content_unified 
                        {where_clause}
                        GROUP BY content_type
                    """, params)
                    
                    results = cursor.fetchall()
                    stats = {}
                    
                    for row in results:
                        stats[row['content_type']] = {
                            'total': int(row['count']),
                            'active': int(row['active_count'])
                        }
                    
                    return {
                        'success': True,
                        'stats': stats,
                        'post_id': post_id
                    }
                    
        except Exception as e:
            logger.error(f"获取内容统计失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }

# 创建全局实例
content_unified_repository = ContentUnifiedRepository() 