"""
小红书数据存储组件
提供完整的数据库存储解决方案
"""

from .storage_service import storage_service, XiaohongshuStorageService
from .post_repository import post_repository, PostRepository
from .image_repository import image_repository, ImageRepository
from .content_unified_repository import content_unified_repository, ContentUnifiedRepository
from .user_repository import user_repository, UserRepository
from .connect_manager import db_manager, DatabaseManager

__version__ = "1.0.0"

__all__ = [
    # 主要服务（推荐使用）
    'storage_service',
    
    # 服务类（用于自定义实例）
    'XiaohongshuStorageService',
    'PostRepository', 
    'ImageRepository',
    'ContentUnifiedRepository',
    'UserRepository',
    'DatabaseManager',
    
    # 仓库实例（高级用法）
    'post_repository',
    'image_repository',
    'content_unified_repository',
    'user_repository',
    'db_manager'
] 