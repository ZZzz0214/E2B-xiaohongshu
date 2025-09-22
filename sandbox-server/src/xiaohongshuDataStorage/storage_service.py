"""
小红书数据存储服务
统一处理从API获取的清洗后的小红书数据存储
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from .post_repository import post_repository
from .image_repository import image_repository
from .content_unified_repository import content_unified_repository
from .user_repository import user_repository
from .connect_manager import db_manager

logger = logging.getLogger(__name__)

class XiaohongshuStorageService:
    """小红书数据存储服务"""
    
    def __init__(self):
        self.post_repo = post_repository
        self.image_repo = image_repository
        self.content_unified_repo = content_unified_repository
        self.user_repo = user_repository
    
    def store_api_response_data(self, api_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        存储API返回的清洗后数据
        
        Args:
            api_response: 清洗后的API响应数据，包含posts数组
            
        Returns:
            存储结果统计
        """
        logger.info("🗃️ 开始存储小红书数据到数据库...")
        
        start_time = datetime.now()
        
        # 提取帖子数据
        posts = api_response.get('posts', [])
        if not posts:
            logger.warning("API响应中没有找到帖子数据")
            return {
                'success': False,
                'message': '没有找到帖子数据',
                'stats': {'posts': 0, 'images': 0}
            }
        
        logger.info(f"📊 数据概览: {len(posts)} 个帖子")
        
        # 存储结果统计
        storage_stats = {
            'posts': {'total': 0, 'success': 0, 'error': 0},
            'images': {'total': 0, 'success': 0, 'error': 0},
            'execution_time': 0,
            'api_metadata': {
                'total_likes': api_response.get('total_likes', 0),
                'video_count': api_response.get('video_count', 0),
                'image_count': api_response.get('image_count', 0),
                'total_images': api_response.get('total_images', 0)
            }
        }
        
        # 批量存储帖子数据
        try:
            posts_result = self.store_posts(posts)
            storage_stats['posts'] = posts_result
        except Exception as e:
            logger.error(f"帖子存储失败: {e}")
            storage_stats['posts']['error'] = len(posts)
        
        # 批量存储图片数据
        try:
            images_result = self.store_images_for_posts(posts)
            storage_stats['images'] = images_result
        except Exception as e:
            logger.error(f"图片存储失败: {e}")
            # 统计总图片数
            total_images = sum(len(post.get('images', [])) for post in posts)
            storage_stats['images']['total'] = total_images
            storage_stats['images']['error'] = total_images
        
        # 计算执行时间
        execution_time = (datetime.now() - start_time).total_seconds()
        storage_stats['execution_time'] = round(execution_time, 2)
        
        # 生成存储报告
        success = (storage_stats['posts']['error'] == 0 and 
                  storage_stats['images']['error'] == 0)
        
        storage_report = {
            'success': success,
            'message': self._generate_storage_message(storage_stats),
            'stats': storage_stats,
            'stored_at': datetime.now().isoformat()
        }
        
        logger.info(f"✅ 数据存储完成: {storage_report['message']}")
        return storage_report
    
    def store_posts(self, posts: List[Dict[str, Any]]) -> Dict[str, int]:
        """存储帖子数据"""
        logger.info(f"📝 开始存储 {len(posts)} 个帖子...")
        return self.post_repo.batch_insert_posts(posts)
    
    def store_images_for_posts(self, posts: List[Dict[str, Any]]) -> Dict[str, int]:
        """为所有帖子存储图片数据"""
        total_images = 0
        success_images = 0
        error_images = 0
        
        for post in posts:
            post_id = post.get('post_id')
            images = post.get('images', [])
            
            if not images:
                continue
            
            total_images += len(images)
            
            # 存储这个帖子的图片
            try:
                result = self.image_repo.batch_insert_images(post_id, images)
                success_images += result['success']
                error_images += result['error']
            except Exception as e:
                logger.error(f"帖子 {post_id} 图片存储失败: {e}")
                error_images += len(images)
        
        result = {
            'total': total_images,
            'success': success_images,
            'error': error_images
        }
        
        logger.info(f"🖼️ 图片存储完成: {result}")
        return result
    
    def store_single_post_with_images(self, post_data: Dict[str, Any]) -> Dict[str, Any]:
        """存储单个帖子及其图片"""
        post_id = post_data.get('post_id')
        logger.info(f"📝 存储单个帖子: {post_id}")
        
        result = {
            'post_id': post_id,
            'post_stored': False,
            'images_stored': 0,
            'images_failed': 0
        }
        
        # 存储帖子
        try:
            result['post_stored'] = self.post_repo.insert_post(post_data)
        except Exception as e:
            logger.error(f"帖子存储失败: {post_id}, 错误: {e}")
        
        # 存储图片
        images = post_data.get('images', [])
        if images:
            try:
                images_result = self.image_repo.batch_insert_images(post_id, images)
                result['images_stored'] = images_result['success']
                result['images_failed'] = images_result['error']
            except Exception as e:
                logger.error(f"图片存储失败: {post_id}, 错误: {e}")
                result['images_failed'] = len(images)
        
        return result
    
    def get_storage_statistics(self) -> Dict[str, Any]:
        """获取数据库存储统计信息"""
        logger.info("📊 获取数据库统计信息...")
        
        try:
            # 获取帖子统计
            posts_stats = self.post_repo.get_posts_stats()
            
            # 获取图片统计  
            images_stats = self.image_repo.get_images_stats()
            
            # 合并统计信息
            combined_stats = {
                'posts': posts_stats,
                'images': images_stats,
                'summary': {
                    'total_posts': posts_stats.get('total_posts', 0),
                    'total_images': images_stats.get('total_images', 0),
                    'avg_images_per_post': round(
                        images_stats.get('total_images', 0) / max(posts_stats.get('total_posts', 1), 1), 2
                    ),
                    'unique_authors': posts_stats.get('unique_authors', 0)
                },
                'generated_at': datetime.now().isoformat()
            }
            
            return combined_stats
            
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {'error': str(e)}
    
    def get_recent_posts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取最近存储的帖子"""
        try:
            sql = """
            SELECT p.*, 
                   COUNT(i.id) as actual_image_count
            FROM xiaohongshu_posts p
            LEFT JOIN xiaohongshu_post_images i ON p.post_id = i.post_id
            GROUP BY p.id
            ORDER BY p.crawl_time DESC
            LIMIT %s
            """
            return db_manager.execute_query(sql, (limit,))
        except Exception as e:
            logger.error(f"查询最近帖子失败: {e}")
            return []
    
    def delete_post_completely(self, post_id: str) -> bool:
        """完全删除帖子及其图片"""
        logger.info(f"🗑️ 删除帖子及图片: {post_id}")
        
        try:
            # 删除图片
            images_deleted = self.image_repo.delete_images_by_post_id(post_id)
            
            # 删除帖子
            post_deleted = self.post_repo.delete_post(post_id)
            
            success = images_deleted and post_deleted
            logger.info(f"删除{'成功' if success else '失败'}: {post_id}")
            return success
            
        except Exception as e:
            logger.error(f"删除帖子失败: {post_id}, 错误: {e}")
            return False
    
    def _generate_storage_message(self, stats: Dict[str, Any]) -> str:
        """生成存储结果消息"""
        posts_success = stats['posts']['success']
        posts_total = stats['posts']['total']
        images_success = stats['images']['success']  
        images_total = stats['images']['total']
        execution_time = stats['execution_time']
        
        if stats['posts']['error'] == 0 and stats['images']['error'] == 0:
            return f"✅ 全部存储成功: {posts_success} 个帖子, {images_success} 张图片, 耗时 {execution_time}s"
        else:
            return f"⚠️ 部分存储成功: 帖子 {posts_success}/{posts_total}, 图片 {images_success}/{images_total}, 耗时 {execution_time}s"
    
    def store_post_detail_data(self, api_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        存储帖子详情和评论数据
        
        Args:
            api_response: API返回的帖子详情数据，包含author_post和comments
            
        Returns:
            存储结果统计
        """
        logger.info("🗃️ 开始存储小红书帖子详情和评论数据...")
        
        start_time = datetime.now()
        
        # 提取帖子详情数据
        author_post = api_response.get('author_post')
        comments = api_response.get('comments', [])
        
        if not author_post:
            logger.warning("API响应中没有找到帖子详情数据")
            return {
                'success': False,
                'message': '没有找到帖子详情数据',
                'stats': {'post': 0, 'comments': 0}
            }
        
        post_id = author_post.get('post_id')
        logger.info(f"📊 数据概览: 1 个帖子详情, {len(comments)} 条评论")
        
        # 存储结果统计
        storage_stats = {
            'post': {'total': 0, 'success': 0, 'error': 0},
            'comments': {'total': 0, 'success': 0, 'error': 0},
            'execution_time': 0
        }
        
        try:
            # 1. 存储帖子详情内容
            logger.info(f"📝 存储帖子详情: {post_id}")
            post_result = self.content_unified_repo.store_post_content(author_post)
            
            if post_result['success']:
                storage_stats['post']['success'] = 1
                logger.info(f"✅ 帖子详情存储成功: {post_id}")
            else:
                storage_stats['post']['error'] = 1
                logger.error(f"❌ 帖子详情存储失败: {post_result.get('error')}")
            
            storage_stats['post']['total'] = 1
            
            # 2. 存储评论数据
            if comments:
                logger.info(f"💬 存储 {len(comments)} 条评论...")
                comments_result = self.content_unified_repo.store_comments(post_id, comments)
                
                storage_stats['comments'] = comments_result['stats']
                
                if comments_result['success']:
                    logger.info(f"✅ 评论存储完成: {comments_result['stats']['success']} 成功, {comments_result['stats']['error']} 失败")
                else:
                    logger.warning(f"⚠️ 评论存储部分失败: {comments_result['stats']['success']} 成功, {comments_result['stats']['error']} 失败")
            
            # 3. 计算执行时间
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            storage_stats['execution_time'] = round(execution_time, 2)
            
            # 4. 构建返回结果
            total_success = storage_stats['post']['success'] + storage_stats['comments']['success']
            total_records = storage_stats['post']['total'] + storage_stats['comments']['total']
            total_errors = storage_stats['post']['error'] + storage_stats['comments']['error']
            
            success = total_errors == 0
            message = f"✅ 全部存储成功: {total_success} 条记录, 耗时 {execution_time:.2f}s" if success else f"⚠️ 部分存储成功: {total_success}/{total_records}, 错误 {total_errors} 条, 耗时 {execution_time:.2f}s"
            
            logger.info(f"🎯 帖子详情存储完成: {message}")
            
            return {
                'success': success,
                'message': message,
                'stats': storage_stats,
                'stored_at': datetime.now().isoformat(),
                'post_id': post_id
            }
            
        except Exception as e:
            logger.error(f"存储帖子详情数据时发生异常: {e}", exc_info=True)
            return {
                'success': False,
                'message': f'存储失败: {str(e)}',
                'stats': storage_stats,
                'error': str(e)
            }
    
    def get_unified_content_statistics(self, post_id: Optional[str] = None) -> Dict[str, Any]:
        """
        获取统一内容表统计信息
        
        Args:
            post_id: 指定帖子ID，为None时返回全局统计
            
        Returns:
            统计信息
        """
        try:
            stats_result = self.content_unified_repo.get_content_stats(post_id)
            
            if stats_result['success']:
                return {
                    'success': True,
                    'statistics': stats_result['stats'],
                    'post_id': post_id,
                    'generated_at': datetime.now().isoformat()
                }
            else:
                return {
                    'success': False,
                    'error': stats_result['error'],
                    'message': '获取统计信息失败'
                }
                
        except Exception as e:
            logger.error(f"获取统一内容统计失败: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'message': '获取统计信息时发生异常'
            }

    def store_user_profile_data(self, user_profile_data: Dict[str, Any], source_post_id: str = None, source_comment_id: str = None) -> Dict[str, Any]:
        """
        存储用户个人信息数据
        
        Args:
            user_profile_data: 用户个人信息数据
            source_post_id: 来源帖子ID（可选）
            source_comment_id: 来源评论ID（可选）
            
        Returns:
            存储结果
        """
        try:
            username = user_profile_data.get('username', 'Unknown')
            logger.info(f"🧑 开始存储用户个人信息: {username}")
            
            # 记录来源信息
            if source_post_id or source_comment_id:
                logger.info(f"📍 用户来源 - 帖子ID: {source_post_id}, 评论ID: {source_comment_id}")
            
            # 调用用户仓库的存储方法，传递来源信息
            result = self.user_repo.store_user_profile_data(user_profile_data, source_post_id, source_comment_id)
            
            if result.get('success', False):
                logger.info(f"✅ 用户信息存储成功: {username} ({user_profile_data.get('user_id')})")
            else:
                logger.warning(f"⚠️ 用户信息存储失败: {result.get('message', 'Unknown error')}")

            return result
            
        except Exception as e:
            logger.error(f"❌ 存储用户个人信息异常: {str(e)}")
            return {
                'success': False,
                'message': f'存储失败: {str(e)}',
                'error': str(e)
            }

    def close_connections(self):
        """关闭数据库连接"""
        try:
            db_manager.close()
            logger.info("数据库连接已关闭")
        except Exception as e:
            logger.error(f"关闭数据库连接失败: {e}")

# 全局存储服务实例
storage_service = XiaohongshuStorageService()
