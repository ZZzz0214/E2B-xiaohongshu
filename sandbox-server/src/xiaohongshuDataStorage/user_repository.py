"""
用户数据仓库
负责小红书用户数据的数据库操作，包括用户画像和帖子概览
"""
import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from .connect_manager import db_manager

logger = logging.getLogger(__name__)

class UserRepository:
    """用户数据仓库"""
    
    def __init__(self):
        self.table_name = "xiaohongshu_users"
    
    def upsert_user(self, user_data: Dict[str, Any]) -> bool:
        """插入或更新用户数据"""
        try:
            # 构建基础字段
            base_fields = {
                'user_id': user_data['user_id'],
                'username': user_data.get('username'),
                'xiaohongshu_id': user_data.get('xiaohongshu_id'),
                'bio': user_data.get('bio'),
                'avatar_url': user_data.get('avatar_url'),
                'following_count': user_data.get('following_count', 0),
                'followers_count': user_data.get('followers_count', 0),
                'likes_collections_count': user_data.get('likes_collections_count', 0),
                'notes_count': user_data.get('notes_count', 0),
                'is_content_creator': user_data.get('is_content_creator', False),
                'is_active_commenter': user_data.get('is_active_commenter', False),
                'profile_extracted': user_data.get('profile_extracted', False),
                'extraction_source': user_data.get('extraction_source', 'discovered'),
                'profile_updated_at': user_data.get('profile_updated_at'),
                # 新增来源字段
                'source_post_id': user_data.get('source_post_id'),
                'source_comment_id': user_data.get('source_comment_id')
            }
            
            # 处理posts_overview JSON字段
            if 'posts_overview' in user_data:
                posts_overview = user_data['posts_overview']
                if isinstance(posts_overview, dict):
                    base_fields['posts_overview'] = json.dumps(posts_overview, ensure_ascii=False)
                    base_fields['posts_overview_updated_at'] = datetime.now()
                elif isinstance(posts_overview, str):
                    base_fields['posts_overview'] = posts_overview
                    base_fields['posts_overview_updated_at'] = datetime.now()
            
            # 构建SQL语句
            insert_fields = [k for k, v in base_fields.items() if v is not None]
            insert_values = [base_fields[k] for k in insert_fields]
            
            # 构建更新字段（排除主键）
            update_fields = [k for k in insert_fields if k != 'user_id']
            
            sql = f"""
            INSERT INTO {self.table_name} ({', '.join(insert_fields)})
            VALUES ({', '.join(['%s'] * len(insert_values))})
            ON DUPLICATE KEY UPDATE
            {', '.join([f'{field} = VALUES({field})' for field in update_fields])}
            """
            
            with db_manager.get_connection() as conn, conn.cursor() as cursor:
                cursor.execute(sql, insert_values)
                conn.commit()
                
            logger.info(f"✅ 成功存储用户数据: {user_data['user_id']}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 存储用户数据失败: {e}")
            logger.error(f"用户数据: {user_data}")
            return False
    
    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户信息"""
        try:
            sql = f"SELECT * FROM {self.table_name} WHERE user_id = %s"
            
            with db_manager.get_connection() as conn, conn.cursor() as cursor:
                cursor.execute(sql, (user_id,))
                result = cursor.fetchone()
                
                if result and result.get('posts_overview'):
                    # 解析JSON字段
                    try:
                        result['posts_overview'] = json.loads(result['posts_overview'])
                    except json.JSONDecodeError:
                        logger.warning(f"解析用户 {user_id} 的posts_overview JSON失败")
                        result['posts_overview'] = None
                
                return result
                
        except Exception as e:
            logger.error(f"❌ 获取用户数据失败: {e}")
            return None
    
    def update_posts_overview(self, user_id: str, posts_data: List[Dict[str, Any]]) -> bool:
        """更新用户帖子概览"""
        try:
            # 分析帖子数据，识别高价值内容
            high_value_posts = []
            total_likes = 0
            
            for post in posts_data:
                liked_count = post.get('liked_count', 0)
                total_likes += liked_count
                
                # 高赞帖子（>1000赞）或置顶帖子标记为高价值
                if liked_count > 1000 or post.get('is_sticky', False):
                    high_value_posts.append(post['note_id'])
            
            # 构建posts_overview数据结构
            posts_overview = {
                "version": "1.0",
                "total_posts": len(posts_data),
                "last_extracted_at": datetime.now().isoformat(),
                "extraction_stats": {
                    "success_count": len(posts_data),
                    "failed_count": 0,
                    "total_likes": total_likes,
                    "avg_likes": total_likes / len(posts_data) if posts_data else 0
                },
                "posts": posts_data,
                "high_value_posts": high_value_posts,
                "analytics": {
                    "video_count": len([p for p in posts_data if p.get('type') == 'video']),
                    "normal_count": len([p for p in posts_data if p.get('type') == 'normal']),
                    "sticky_count": len([p for p in posts_data if p.get('is_sticky', False)])
                }
            }
            
            sql = f"""
            UPDATE {self.table_name} 
            SET posts_overview = %s, 
                posts_overview_updated_at = %s
            WHERE user_id = %s
            """
            
            with db_manager.get_connection() as conn, conn.cursor() as cursor:
                cursor.execute(sql, (
                    json.dumps(posts_overview, ensure_ascii=False),
                    datetime.now(),
                    user_id
                ))
                conn.commit()
                
            logger.info(f"✅ 更新用户帖子概览: {user_id}, 共{len(posts_data)}个帖子, {len(high_value_posts)}个高价值帖子")
            return True
            
        except Exception as e:
            logger.error(f"❌ 更新用户帖子概览失败: {e}")
            return False
    
    def mark_user_as_content_creator(self, user_id: str) -> bool:
        """标记用户为内容创作者"""
        return self.update_user_field(user_id, 'is_content_creator', True)
    
    def mark_user_as_active_commenter(self, user_id: str) -> bool:
        """标记用户为活跃评论者"""
        return self.update_user_field(user_id, 'is_active_commenter', True)
    
    def update_user_field(self, user_id: str, field: str, value: Any) -> bool:
        """更新用户单个字段"""
        try:
            sql = f"UPDATE {self.table_name} SET {field} = %s WHERE user_id = %s"
            
            with db_manager.get_connection() as conn, conn.cursor() as cursor:
                cursor.execute(sql, (value, user_id))
                conn.commit()
                
            return cursor.rowcount > 0
            
        except Exception as e:
            logger.error(f"❌ 更新用户字段失败: {e}")
            return False
    
    def get_users_by_condition(self, conditions: Dict[str, Any], limit: int = 100) -> List[Dict[str, Any]]:
        """根据条件查询用户"""
        try:
            where_clauses = []
            params = []
            
            for field, value in conditions.items():
                where_clauses.append(f"{field} = %s")
                params.append(value)
            
            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
            sql = f"SELECT * FROM {self.table_name} WHERE {where_sql} LIMIT %s"
            params.append(limit)
            
            with db_manager.get_connection() as conn, conn.cursor() as cursor:
                cursor.execute(sql, params)
                results = cursor.fetchall()
                
                # 解析JSON字段
                for result in results:
                    if result.get('posts_overview'):
                        try:
                            result['posts_overview'] = json.loads(result['posts_overview'])
                        except json.JSONDecodeError:
                            result['posts_overview'] = None
                
                return results
                
        except Exception as e:
            logger.error(f"❌ 查询用户失败: {e}")
            return []
    
    def get_high_value_users(self, min_followers: int = 100, limit: int = 50) -> List[Dict[str, Any]]:
        """获取高价值用户（用于5节点处理）"""
        try:
            sql = f"""
            SELECT user_id, username, followers_count, notes_count, 
                   is_content_creator, is_active_commenter, posts_overview
            FROM {self.table_name}
            WHERE profile_extracted = TRUE 
              AND (followers_count >= %s OR 
                   (is_content_creator = TRUE AND notes_count > 10) OR
                   JSON_LENGTH(posts_overview->'$.high_value_posts') > 0)
            ORDER BY followers_count DESC, notes_count DESC
            LIMIT %s
            """
            
            with db_manager.get_connection() as conn, conn.cursor() as cursor:
                cursor.execute(sql, (min_followers, limit))
                results = cursor.fetchall()
                
                # 解析JSON字段
                for result in results:
                    if result.get('posts_overview'):
                        try:
                            result['posts_overview'] = json.loads(result['posts_overview'])
                        except json.JSONDecodeError:
                            result['posts_overview'] = None
                
                return results
                
        except Exception as e:
            logger.error(f"❌ 获取高价值用户失败: {e}")
            return []
    
    def store_user_profile_data(self, profile_data: Dict[str, Any], source_post_id: str = None, source_comment_id: str = None) -> Dict[str, Any]:
        """存储用户完整画像数据（主要接口）"""
        try:
            user_id = profile_data['user_id']
            
            # 构建用户基础数据
            user_data = {
                'user_id': user_id,
                'username': profile_data.get('username'),
                'xiaohongshu_id': profile_data.get('xiaohongshu_id'),
                'bio': profile_data.get('bio', ''),
                'avatar_url': profile_data.get('avatar_url'),
                'following_count': profile_data.get('following_count', 0),
                'followers_count': profile_data.get('followers_count', 0),
                'likes_collections_count': profile_data.get('likes_collections_count', 0),
                'notes_count': profile_data.get('notes_count', 0),
                'is_content_creator': profile_data.get('notes_count', 0) > 0,  # 有帖子就是创作者
                'profile_extracted': True,
                'extraction_source': 'clicked',
                'profile_updated_at': datetime.now(),
                # 添加来源信息
                'source_post_id': source_post_id or profile_data.get('source_post_id'),
                'source_comment_id': source_comment_id or profile_data.get('source_comment_id')
            }
            
            # 存储用户基础信息
            success = self.upsert_user(user_data)
            
            if success and 'notes_all' in profile_data:
                # 更新帖子概览
                posts_data = profile_data['notes_all']
                self.update_posts_overview(user_id, posts_data)
            
            return {
                'success': success,
                'message': f'用户画像存储{"成功" if success else "失败"}',
                'user_id': user_id,
                'posts_count': len(profile_data.get('notes_all', [])),
                'stored_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ 存储用户画像数据失败: {e}")
            return {
                'success': False,
                'message': f'存储失败: {str(e)}',
                'error': str(e)
            }

# 全局用户仓库实例
user_repository = UserRepository()
