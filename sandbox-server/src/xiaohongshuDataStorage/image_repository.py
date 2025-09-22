"""
图片数据仓库
负责小红书帖子图片数据的数据库操作
"""
import logging
from typing import Dict, Any, List, Optional

from .connect_manager import db_manager

logger = logging.getLogger(__name__)

class ImageRepository:
    """图片数据仓库"""
    
    def __init__(self):
        self.table_name = "xiaohongshu_post_images"
    
    def parse_image_size(self, size_str: str) -> Dict[str, Optional[int]]:
        """解析图片尺寸字符串"""
        try:
            if size_str and 'x' in size_str:
                width_str, height_str = size_str.split('x')
                return {
                    'width': int(width_str.strip()),
                    'height': int(height_str.strip())
                }
        except (ValueError, AttributeError):
            logger.warning(f"无法解析图片尺寸: {size_str}")
        
        return {'width': 0, 'height': 0}
    
    def insert_image(self, post_id: str, image_data: Dict[str, Any], image_index: int) -> bool:
        """插入或更新单张图片"""
        try:
            # 解析图片尺寸
            size_info = self.parse_image_size(image_data.get('size', ''))
            
            # 优先使用API返回的宽高，如果没有则使用解析的
            image_width = image_data.get('width', size_info['width'])
            image_height = image_data.get('height', size_info['height'])
            
            sql = """
            INSERT INTO xiaohongshu_post_images (
                post_id, image_index, image_url, alternative_url,
                image_width, image_height, image_size
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s, %s
            )
            ON DUPLICATE KEY UPDATE
                image_url = VALUES(image_url),
                alternative_url = VALUES(alternative_url),
                image_width = VALUES(image_width),
                image_height = VALUES(image_height),
                image_size = VALUES(image_size)
            """
            
            params = (
                post_id,
                image_index,
                image_data.get('url'),
                image_data.get('alternative_url'),
                image_width,
                image_height,
                image_data.get('size')
            )
            
            db_manager.execute_insert(sql, params)
            logger.debug(f"图片插入成功: {post_id} - 第{image_index}张")
            return True
            
        except Exception as e:
            logger.error(f"图片插入失败: {post_id} - 第{image_index}张, 错误: {e}")
            return False
    
    def batch_insert_images(self, post_id: str, images_list: List[Dict[str, Any]]) -> Dict[str, int]:
        """批量插入帖子的所有图片"""
        success_count = 0
        error_count = 0
        
        logger.info(f"开始为帖子 {post_id} 插入 {len(images_list)} 张图片")
        
        for index, image_data in enumerate(images_list, 1):
            try:
                if self.insert_image(post_id, image_data, index):
                    success_count += 1
                else:
                    error_count += 1
            except Exception as e:
                error_count += 1
                logger.error(f"批量插入图片失败: {e}")
        
        result = {
            'post_id': post_id,
            'total': len(images_list),
            'success': success_count,
            'error': error_count
        }
        
        logger.info(f"帖子图片插入完成: {result}")
        return result
    
    def get_images_by_post_id(self, post_id: str) -> List[Dict[str, Any]]:
        """根据帖子ID查询所有图片"""
        try:
            sql = """
            SELECT * FROM xiaohongshu_post_images 
            WHERE post_id = %s 
            ORDER BY image_index
            """
            return db_manager.execute_query(sql, (post_id,))
        except Exception as e:
            logger.error(f"查询帖子图片失败: {post_id}, 错误: {e}")
            return []
    
    def get_image_by_post_and_index(self, post_id: str, image_index: int) -> Optional[Dict[str, Any]]:
        """根据帖子ID和图片索引查询特定图片"""
        try:
            sql = """
            SELECT * FROM xiaohongshu_post_images 
            WHERE post_id = %s AND image_index = %s
            """
            results = db_manager.execute_query(sql, (post_id, image_index))
            return results[0] if results else None
        except Exception as e:
            logger.error(f"查询特定图片失败: {post_id}-{image_index}, 错误: {e}")
            return None
    
    def get_images_stats(self) -> Dict[str, Any]:
        """获取图片统计信息"""
        try:
            sql = """
            SELECT 
                COUNT(*) as total_images,
                COUNT(DISTINCT post_id) as posts_with_images,
                AVG(image_width) as avg_width,
                AVG(image_height) as avg_height,
                MAX(image_width) as max_width,
                MAX(image_height) as max_height,
                COUNT(CASE WHEN alternative_url IS NOT NULL THEN 1 END) as images_with_alt
            FROM xiaohongshu_post_images
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
            logger.error(f"获取图片统计信息失败: {e}")
            return {}
    
    def get_large_images(self, min_width: int = 3000, limit: int = 20) -> List[Dict[str, Any]]:
        """获取高清大图"""
        try:
            sql = """
            SELECT * FROM xiaohongshu_post_images 
            WHERE image_width >= %s 
            ORDER BY image_width DESC, image_height DESC 
            LIMIT %s
            """
            return db_manager.execute_query(sql, (min_width, limit))
        except Exception as e:
            logger.error(f"查询高清图片失败: {e}")
            return []
    
    def delete_images_by_post_id(self, post_id: str) -> bool:
        """删除帖子的所有图片"""
        try:
            sql = "DELETE FROM xiaohongshu_post_images WHERE post_id = %s"
            db_manager.execute_insert(sql, (post_id,))
            logger.info(f"帖子图片删除成功: {post_id}")
            return True
        except Exception as e:
            logger.error(f"帖子图片删除失败: {post_id}, 错误: {e}")
            return False
    
    def delete_image(self, post_id: str, image_index: int) -> bool:
        """删除特定图片"""
        try:
            sql = "DELETE FROM xiaohongshu_post_images WHERE post_id = %s AND image_index = %s"
            db_manager.execute_insert(sql, (post_id, image_index))
            logger.info(f"图片删除成功: {post_id}-{image_index}")
            return True
        except Exception as e:
            logger.error(f"图片删除失败: {post_id}-{image_index}, 错误: {e}")
            return False
    
    def update_image_url(self, post_id: str, image_index: int, new_url: str) -> bool:
        """更新图片URL"""
        try:
            sql = """
            UPDATE xiaohongshu_post_images 
            SET image_url = %s 
            WHERE post_id = %s AND image_index = %s
            """
            db_manager.execute_insert(sql, (new_url, post_id, image_index))
            logger.info(f"图片URL更新成功: {post_id}-{image_index}")
            return True
        except Exception as e:
            logger.error(f"图片URL更新失败: {post_id}-{image_index}, 错误: {e}")
            return False

# 全局图片仓库实例
image_repository = ImageRepository()
