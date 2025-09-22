"""
小红书专用管理器
专门处理小红书相关的数据提取和分析操作
与sandbox_manager协同工作
"""

import json
import logging
import time
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class XiaohongshuManager:
    """小红书专用操作管理器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def get_xiaohongshu_operation_mapping(self) -> Dict[str, str]:
        """获取小红书操作到API端点的映射"""
        return {
            # 自动滚动相关
            "xiaohongshu_auto_scroll": "/xiaohongshu/auto_scroll",
            "xhs_auto_scroll": "/xiaohongshu/auto_scroll",
            
            # 帖子提取相关
            "xiaohongshu_extract_all_posts": "/xiaohongshu/extract_all_posts", 
            "xhs_extract_posts": "/xiaohongshu/extract_all_posts",
            
            # 帖子点击相关
            "xiaohongshu_click_post": "/xiaohongshu/click_post_by_index",
            "xhs_click_post": "/xiaohongshu/click_post_by_index",
            
            # 评论相关
            "xiaohongshu_expand_comments": "/xiaohongshu/expand_comments",
            "xiaohongshu_extract_comments": "/xiaohongshu/extract_comments",
            "xiaohongshu_reply_comment": "/xiaohongshu/reply_comment",
            "xhs_expand_comments": "/xiaohongshu/expand_comments",
            "xhs_extract_comments": "/xiaohongshu/extract_comments",
            "xhs_reply_comment": "/xiaohongshu/reply_comment",
            
            # 帖子关闭相关
            "xiaohongshu_close_post": "/xiaohongshu/close_post",
            "xhs_close_post": "/xiaohongshu/close_post",
            
            # 页面关闭相关
            "xiaohongshu_close_page": "/xiaohongshu/close_page",
            "xhs_close_page": "/xiaohongshu/close_page",
            
            # 用户信息相关
            "xiaohongshu_click_author_avatar": "/xiaohongshu/click_author_avatar",
            "xhs_click_author_avatar": "/xiaohongshu/click_author_avatar",
            "xiaohongshu_extract_user_profile": "/xiaohongshu/extract_user_profile", 
            "xhs_extract_user_profile": "/xiaohongshu/extract_user_profile",
            
            # 完整分析
            "xiaohongshu_analyze_post": "/xiaohongshu/analyze_post",
            "xhs_analyze_post": "/xiaohongshu/analyze_post",
        }
    
    def prepare_xiaohongshu_request_data(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """准备小红书操作的请求数据"""
        if action in ["xiaohongshu_auto_scroll", "xhs_auto_scroll"]:
            return {
                "max_scrolls": params.get("max_scrolls", 10),
                "delay_between_scrolls": params.get("delay_between_scrolls", 2.0)
            }
        
        elif action in ["xiaohongshu_extract_all_posts", "xhs_extract_posts"]:
            data = {}
            if "limit" in params:
                data["limit"] = params["limit"]
            return data
        
        elif action in ["xiaohongshu_click_post", "xhs_click_post"]:
            return {
                "title": params["title"]
            }
        
        elif action in ["xiaohongshu_expand_comments", "xhs_expand_comments"]:
            return {
                "max_attempts": params.get("max_attempts", 10)
            }
        
        elif action in ["xiaohongshu_extract_comments", "xhs_extract_comments"]:
            return {
                "include_replies": params.get("include_replies", True)
            }
        
        elif action in ["xiaohongshu_reply_comment", "xhs_reply_comment"]:
            return {
                "target_user_id": params.get("target_user_id", ""),
                "target_username": params.get("target_username", ""),
                "target_content": params.get("target_content", ""),
                "reply_content": params.get("reply_content", "")
            }
        
        elif action in ["xiaohongshu_extract_images", "xhs_extract_images"]:
            return {
                "high_resolution": params.get("high_resolution", False)
            }
        
        elif action in ["xiaohongshu_analyze_post", "xhs_analyze_post"]:
            return {
                "global_index": params.get("global_index", 0),
                "include_comments": params.get("include_comments", True),
                "include_images": params.get("include_images", True)
            }
        
        elif action in ["xiaohongshu_close_post", "xhs_close_post"]:
            # 关闭帖子不需要参数
            return {}
        
        elif action in ["xiaohongshu_close_page", "xhs_close_page"]:
            # 关闭页面不需要参数
            return {}
        
        elif action in ["xiaohongshu_click_author_avatar", "xhs_click_author_avatar"]:
            return {
                "userid": params.get("userid", ""),
                "username": params.get("username", "")
            }
        
        elif action in ["xiaohongshu_extract_user_profile", "xhs_extract_user_profile"]:
            # 提取用户主页信息不需要参数
            return {}
        
        else:
            return params
    
    def is_xiaohongshu_operation(self, action: str) -> bool:
        """判断是否为小红书专用操作"""
        xiaohongshu_operations = self.get_xiaohongshu_operation_mapping()
        return action in xiaohongshu_operations
    
    def get_operation_description(self, action: str) -> str:
        """获取操作描述"""
        descriptions = {
            "xiaohongshu_auto_scroll": "自动滚动加载所有小红书帖子",
            "xhs_auto_scroll": "自动滚动加载所有小红书帖子",
            "xiaohongshu_extract_all_posts": "提取小红书页面所有帖子信息",
            "xhs_extract_posts": "提取小红书页面所有帖子信息",
            "xiaohongshu_click_post": "通过标题点击小红书帖子",
            "xhs_click_post": "通过标题点击小红书帖子",
            "xiaohongshu_expand_comments": "展开小红书帖子的所有评论",
            "xhs_expand_comments": "展开小红书帖子的所有评论",
            "xiaohongshu_extract_comments": "提取小红书帖子的所有评论",
            "xiaohongshu_reply_comment": "通过用户信息和内容智能回复小红书评论",
            "xhs_extract_comments": "提取小红书帖子的所有评论",
            "xhs_reply_comment": "通过用户信息和内容智能回复小红书评论",
            "xiaohongshu_extract_images": "提取小红书帖子的所有图片",
            "xhs_extract_images": "提取小红书帖子的所有图片",
            "xiaohongshu_analyze_post": "完整分析小红书帖子（评论+图片）",
            "xhs_analyze_post": "完整分析小红书帖子（评论+图片）",
            "xiaohongshu_close_post": "关闭小红书帖子详情页",
            "xhs_close_post": "关闭小红书帖子详情页",
            "xiaohongshu_close_page": "关闭当前页面（通用页面关闭）",
            "xhs_close_page": "关闭当前页面（通用页面关闭）",
            "xiaohongshu_click_author_avatar": "点击作者头像打开用户主页",
            "xhs_click_author_avatar": "点击作者头像打开用户主页",
            "xiaohongshu_extract_user_profile": "提取用户个人主页完整信息（含帖子滑动获取）",
            "xhs_extract_user_profile": "提取用户个人主页完整信息（含帖子滑动获取）",
        }
        return descriptions.get(action, action)

# 全局小红书管理器实例
xiaohongshu_manager = XiaohongshuManager() 