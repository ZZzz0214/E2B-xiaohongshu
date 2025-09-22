"""
帖子数据仓库
负责小红书帖子数据的数据库操作
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import re

from .connect_manager import db_manager

logger = logging.getLogger(__name__)

class PostRepository:
    """帖子数据仓库"""
    
    def __init__(self):
        self.table_name = "xiaohongshu_posts"
    
    def parse_publish_time(self, time_raw: str) -> Optional[str]:
        """解析发布时间字符串为DATE格式"""
        if not time_raw:
            return None
            
        try:
            now = datetime.now()
            
            # 处理相对时间
            if "天前" in time_raw:
                days = int(re.search(r'(\d+)天前', time_raw).group(1))
                target_date = now - timedelta(days=days)
                return target_date.strftime('%Y-%m-%d')
            
            elif "昨天" in time_raw:
                target_date = now - timedelta(days=1)
                return target_date.strftime('%Y-%m-%d')
            
            elif "今天" in time_raw or "刚刚" in time_raw or "分钟前" in time_raw or "小时前" in time_raw:
                return now.strftime('%Y-%m-%d')
            
            # 处理具体日期 如 "08-20", "02-16"
            elif re.match(r'\d{2}-\d{2}', time_raw):
                month, day = time_raw.split('-')
                # 假设是当年的日期
                year = now.year
                target_date = datetime(year, int(month), int(day))
                
                # 如果日期在未来，则认为是去年的
                if target_date > now:
                    target_date = datetime(year - 1, int(month), int(day))
                
                return target_date.strftime('%Y-%m-%d')
            
            # 处理其他格式
            else:
                logger.warning(f"无法解析时间格式: {time_raw}")
                return None
                
        except Exception as e:
            logger.error(f"时间解析失败: {time_raw}, 错误: {e}")
            return None
    
    def insert_post(self, post_data: Dict[str, Any]) -> bool:
        """插入或更新单个帖子"""
        try:
            # 解析发布时间
            post_created_at = self.parse_publish_time(post_data.get('publish_time_raw'))
            
            sql = """
            INSERT INTO xiaohongshu_posts (
                post_id, author_id, author_name, title,
                like_count, collect_count, comment_count, share_count,
                post_type, is_video, image_count,
                publish_time_raw, post_created_at, extraction_source,
                detail_extracted
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s, %s
            )
            ON DUPLICATE KEY UPDATE
                like_count = VALUES(like_count),
                collect_count = VALUES(collect_count),
                comment_count = VALUES(comment_count),
                share_count = VALUES(share_count),
                image_count = VALUES(image_count),
                detail_extracted = VALUES(detail_extracted),
                updated_at = CURRENT_TIMESTAMP
            """
            
            params = (
                post_data.get('post_id'),
                post_data.get('author_id'),
                post_data.get('author_name'),
                post_data.get('title'),
                post_data.get('like_count', 0),
                post_data.get('collect_count', 0),
                post_data.get('comment_count', 0),
                post_data.get('share_count', 0),
                post_data.get('post_type', 'normal'),
                post_data.get('is_video', False),
                post_data.get('image_count', 0),
                post_data.get('publish_time_raw'),
                post_created_at,
                'global_state_mysql_format',
                post_data.get('detail_extracted', False)  # 新增字段，默认FALSE
            )
            
            affected_rows = db_manager.execute_insert(sql, params)
            post_id = post_data.get('post_id')
            
            # 改进日志：区分插入、更新和重复情况
            if affected_rows == 1:
                logger.debug(f"✅ 帖子插入成功: {post_id}")
            elif affected_rows == 2:
                logger.debug(f"🔄 帖子更新成功: {post_id}")
            elif affected_rows == 0:
                logger.debug(f"📋 帖子已存在且数据相同，无需更新: {post_id}")
            
            return True
            
        except Exception as e:
            error_msg = str(e)
            post_id = post_data.get('post_id', 'Unknown')
            
            # 改进错误处理：只记录真正的错误
            if error_msg and error_msg != "(0, '')" and not error_msg.startswith("(0,"):
                logger.error(f"❌ 帖子插入失败: {post_id}, 错误: {error_msg}")
                return False
            else:
                # (0, '') 表示重复数据，不是真正的错误
                logger.debug(f"📋 帖子已存在: {post_id}")
                return True
    
    def batch_insert_posts(self, posts_list: List[Dict[str, Any]]) -> Dict[str, int]:
        """批量插入帖子"""
        success_count = 0
        error_count = 0
        
        logger.info(f"开始批量插入 {len(posts_list)} 个帖子")
        
        for post_data in posts_list:
            try:
                if self.insert_post(post_data):
                    success_count += 1
                else:
                    error_count += 1
            except Exception as e:
                error_count += 1
                logger.error(f"批量插入帖子失败: {e}")
        
        result = {
            'total': len(posts_list),
            'success': success_count,
            'error': error_count
        }
        
        logger.info(f"批量插入完成: {result}")
        return result
    
    def get_post_by_id(self, post_id: str) -> Optional[Dict[str, Any]]:
        """根据帖子ID查询帖子"""
        try:
            sql = "SELECT * FROM xiaohongshu_posts WHERE post_id = %s"
            results = db_manager.execute_query(sql, (post_id,))
            return results[0] if results else None
        except Exception as e:
            logger.error(f"查询帖子失败: {post_id}, 错误: {e}")
            return None
    
    def get_posts_by_author(self, author_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """根据作者ID查询帖子"""
        try:
            sql = """
            SELECT * FROM xiaohongshu_posts 
            WHERE author_id = %s 
            ORDER BY crawl_time DESC 
            LIMIT %s
            """
            return db_manager.execute_query(sql, (author_id, limit))
        except Exception as e:
            logger.error(f"查询作者帖子失败: {author_id}, 错误: {e}")
            return []
    
    def get_top_posts(self, limit: int = 20) -> List[Dict[str, Any]]:
        """获取热门帖子"""
        try:
            sql = """
            SELECT * FROM xiaohongshu_posts 
            ORDER BY like_count DESC 
            LIMIT %s
            """
            return db_manager.execute_query(sql, (limit,))
        except Exception as e:
            logger.error(f"查询热门帖子失败: {e}")
            return []
    
    def get_posts_stats(self) -> Dict[str, Any]:
        """获取帖子统计信息"""
        try:
            sql = """
            SELECT 
                COUNT(*) as total_posts,
                COUNT(DISTINCT author_id) as unique_authors,
                AVG(like_count) as avg_likes,
                MAX(like_count) as max_likes,
                SUM(CASE WHEN is_video = 1 THEN 1 ELSE 0 END) as video_count,
                SUM(image_count) as total_images
            FROM xiaohongshu_posts
            """
            results = db_manager.execute_query(sql)
            if results:
                # 转换Decimal类型为float，方便JSON序列化
                stats = results[0]
                for key, value in stats.items():
                    if hasattr(value, '__float__'):  # Decimal类型
                        stats[key] = float(value) if value is not None else 0.0
                return stats
            return {}
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {}
    
    def delete_post(self, post_id: str) -> bool:
        """删除帖子"""
        try:
            sql = "DELETE FROM xiaohongshu_posts WHERE post_id = %s"
            db_manager.execute_insert(sql, (post_id,))
            logger.info(f"帖子删除成功: {post_id}")
            return True
        except Exception as e:
            logger.error(f"帖子删除失败: {post_id}, 错误: {e}")
            return False
    
    def get_posts_by_condition(self, condition: str, limit: int = 50) -> List[Dict]:
        """根据条件查询帖子"""
        try:
            sql = f"""
            SELECT post_id, title, author_name, author_id, like_count, comment_count, 
                   collect_count, share_count, post_type, is_video, image_count,
                   publish_time_raw, post_created_at, crawl_time, detail_extracted
            FROM xiaohongshu_posts 
            WHERE {condition}
            ORDER BY crawl_time DESC
            LIMIT %s
            """
            
            results = db_manager.execute_query(sql, (limit,))
            posts = []
            
            for row in results:
                post = {
                    'post_id': row['post_id'],
                    'title': row['title'],
                    'author_name': row['author_name'], 
                    'author_id': row['author_id'],
                    'like_count': row['like_count'],
                    'comment_count': row['comment_count'],
                    'collect_count': row['collect_count'], 
                    'share_count': row['share_count'],
                    'post_type': row['post_type'],
                    'is_video': row['is_video'],
                    'image_count': row['image_count'],
                    'publish_time_raw': row['publish_time_raw'],
                    'post_created_at': row['post_created_at'],
                    'crawl_time': row['crawl_time'],
                    'detail_extracted': row['detail_extracted']
                }
                posts.append(post)
            
            logger.info(f"根据条件查询到 {len(posts)} 个帖子: {condition}")
            return posts
            
        except Exception as e:
            logger.error(f"根据条件查询帖子失败: {condition}, 错误: {e}")
            return []
    
    def update_post_status(self, post_id: str, status_updates: Dict) -> bool:
        """更新帖子状态"""
        try:
            # 构建SET子句
            set_clauses = []
            values = []
            
            for field, value in status_updates.items():
                set_clauses.append(f"{field} = %s")
                values.append(value)
            
            if not set_clauses:
                return False
            
            # 添加post_id到values最后
            values.append(post_id)
            
            sql = f"""
            UPDATE xiaohongshu_posts 
            SET {', '.join(set_clauses)}
            WHERE post_id = %s
            """
            
            db_manager.execute_insert(sql, tuple(values))
            logger.info(f"帖子状态更新成功: {post_id}, 更新字段: {list(status_updates.keys())}")
            return True
            
        except Exception as e:
            logger.error(f"帖子状态更新失败: {post_id}, 错误: {e}")
            return False

# 全局帖子仓库实例
post_repository = PostRepository()
