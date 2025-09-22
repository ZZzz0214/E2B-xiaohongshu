"""
小红书数据清洗器 - API层面数据格式转换
在外部API返回前对沙盒数据进行清洗和格式化
"""
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class XiaohongshuDataCleaner:
    """小红书数据清洗器 - 转换沙盒原始数据为业务需求格式"""
    
    @staticmethod
    def should_clean(batch_result: Dict[str, Any]) -> bool:
        """判断是否需要清洗数据（检查是否包含小红书操作）"""
        if not batch_result.get("success") or not batch_result.get("results"):
            return False
            
        # 检查是否包含小红书相关操作
        xiaohongshu_actions = [
            "xiaohongshu_extract_all_posts", 
            "xiaohongshu_extract_comments",
            "xiaohongshu_click_post",
            "xiaohongshu_expand_comments",
            "xiaohongshu_extract_user_profile",
            "xhs_extract_user_profile"
        ]
        
        for result in batch_result["results"]:
            if result.get("action") in xiaohongshu_actions:
                return True
        return False
    
    @staticmethod
    def clean_batch_result(batch_result: Dict[str, Any]) -> Dict[str, Any]:
        """清洗批量操作结果"""
        if not XiaohongshuDataCleaner.should_clean(batch_result):
            return batch_result
            
        logger.info("🧹 开始清洗小红书数据...")
        
        # 保留原始元数据
        cleaned_result = {
            "success": batch_result.get("success"),
            "message": batch_result.get("message"),
            "total_operations": batch_result.get("total_operations"),
            "successful_operations": batch_result.get("successful_operations"),
            "execution_time": batch_result.get("execution_time"),
            "persistent_id": batch_result.get("persistent_id"),
            "e2b_sandbox_id": batch_result.get("e2b_sandbox_id"),
            "vnc_access": batch_result.get("vnc_access"),
            "total_execution_time": batch_result.get("total_execution_time"),
            "sandbox_created": batch_result.get("sandbox_created")
        }
        
        # 分析和清洗数据 - 直接提取小红书数据
        xiaohongshu_data = XiaohongshuDataCleaner._extract_xiaohongshu_data(
            batch_result.get("results", [])
        )
        
        # 🔄 混合格式：保持results兼容性 + 添加直接访问
        # 1. 保留原始的results数组（兼容BrowserAutomationResponse模型）
        cleaned_result["results"] = batch_result.get("results", [])
        
        # 2. 添加小红书业务数据到根级别（直接访问）
        for key, value in xiaohongshu_data.items():
            cleaned_result[key] = value
        
        # 3. 为LLM分析添加便捷字段
        if "posts" in xiaohongshu_data:
            cleaned_result["extracted_posts"] = xiaohongshu_data["posts"]
        
        logger.info("✅ 数据清洗完成")
        return cleaned_result
    
    @staticmethod
    def _extract_xiaohongshu_data(results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """提取小红书数据并直接返回"""
        xiaohongshu_data = {}
        
        for result in results:
            action = result.get("action")
            
            # 处理帖子提取数据
            if action == "xiaohongshu_extract_all_posts" and result.get("success"):
                posts_data = XiaohongshuDataCleaner._extract_posts_data(result)
                xiaohongshu_data.update(posts_data)
            
            # 处理评论提取数据  
            elif action == "xiaohongshu_extract_comments" and result.get("success"):
                comments_data = XiaohongshuDataCleaner._extract_comments_data(result)
                xiaohongshu_data.update(comments_data)
            
            # 处理用户个人信息提取数据
            elif action in ["xiaohongshu_extract_user_profile", "xhs_extract_user_profile"] and result.get("success"):
                user_data = XiaohongshuDataCleaner._extract_user_profile_data(result)
                xiaohongshu_data.update(user_data)
                
        return xiaohongshu_data
    
    @staticmethod
    def _extract_posts_data(extract_result: Dict[str, Any]) -> Dict[str, Any]:
        """提取帖子数据 - 直接返回原始格式"""
        # 深度提取数据 (处理嵌套的data结构)
        data = extract_result.get("data", {})
        while isinstance(data.get("data"), dict):
            data = data["data"]
            
        # 🎯 直接返回帖子数据，保持原始结构
        posts_info = {
            "posts_count": data.get("total_count", 0),  # 改名避免冲突
            "video_count": data.get("video_count", 0),
            "image_count": data.get("image_count", 0),
            "total_images": data.get("total_images", 0),
            "total_likes": data.get("total_likes", 0),
            "posts": data.get("posts", [])
        }
        
        return posts_info
    
    @staticmethod
    def _extract_comments_data(extract_result: Dict[str, Any]) -> Dict[str, Any]:
        """提取评论数据 - 直接返回原始格式"""
        # 深度提取数据 (处理嵌套的data结构)
        data = extract_result.get("data", {})
        while isinstance(data.get("data"), dict):
            data = data["data"]
            
        # 🎯 直接返回评论数据，保持原始结构
        comments_info = {
            "author_post": data.get("author_post", {}),
            "comments_count": data.get("total_count", 0),  # 改名避免冲突
            "main_comments_count": data.get("main_comments_count", 0),
            "reply_comments_count": data.get("reply_comments_count", 0),
            "author_comments_count": data.get("author_comments_count", 0),
            "comments": data.get("comments", []),
            "note_id": data.get("note_id", "")
        }
        
        return comments_info
    
    @staticmethod
    def _extract_user_profile_data(extract_result: Dict[str, Any]) -> Dict[str, Any]:
        """提取用户个人信息数据 - 直接返回原始格式"""
        # 深度提取数据 (处理嵌套的data结构)
        data = extract_result.get("data", {})
        while isinstance(data.get("data"), dict):
            data = data["data"]
            
        # 🎯 直接返回用户信息数据，保持原始结构
        user_profile_info = {
            "user_profile": data,  # 包含完整的用户信息数据
            "user_id": data.get("user_id", ""),
            "username": data.get("username", ""),
            "extraction_type": "user_profile"
        }
        
        return user_profile_info