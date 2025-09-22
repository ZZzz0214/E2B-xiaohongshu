"""
E2B 浏览器自动化 API - 清理版本
只保留核心接口：automation 和 batch_process_from_database
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List, Union
import logging
import asyncio

from core.sandbox_manager import sandbox_manager
from models.request_models import BatchBrowserRequest, BatchProcessFromDatabaseRequest
from models.llm_models import (
    PostClassificationItem, PostClassificationRequest,
    CommentAnalysisRequest,
    CustomerInsightsItem, convert_customer_insight_to_db_format
)
from utils.xiaohongshu_data_cleaner import XiaohongshuDataCleaner
from utils.api_response_builder import ApiResponseBuilder, ApiTimer
from xiaohongshuDataStorage import storage_service, post_repository
from xiaohongshuDataStorage.classification_repository import classification_repository
from xiaohongshuDataStorage.ai_analysis_repository import ai_analysis_repository
from xiaohongshuDataStorage.customer_insights_repository import customer_insights_repository

logger = logging.getLogger(__name__)
browser_router = APIRouter()

# ==================== 核心API ====================

@browser_router.post("/automation", response_model=Dict[str, Any])
async def browser_automation(request: BatchBrowserRequest):
    """
    浏览器自动化主接口 - E2B云端版本
    自动创建E2B沙盒并执行浏览器操作
    支持单操作和批量操作两种格式
    """
    # 🚀 使用新的时间管理器
    timer = ApiTimer.start()
    
    try:
        # 🎯 使用pydantic模型验证和解析操作数据
        operations = request.get_operations_list()
        
        if not operations:
            raise HTTPException(
                status_code=400,
                detail="请求格式错误：必须包含'action'或'operations'字段"
            )
        
        logger.info(f"🚀 开始浏览器自动化: {len(operations)} 个操作")
        
        # 1. 获取或创建E2B沙盒
        sandbox_result = await sandbox_manager.get_or_create_sandbox(request.persistent_id)
        
        if not sandbox_result["success"]:
            return {
                "success": False,
                "message": f"沙盒创建失败: {sandbox_result.get('message', 'Unknown error')}",
                "execution_time": timer.elapsed()
            }
        
        persistent_id = sandbox_result["persistent_id"]
        e2b_sandbox_id = sandbox_result["e2b_sandbox_id"]
        vnc_access = sandbox_result["vnc_access"]
        
        logger.info(f"✅ 沙盒准备就绪: {e2b_sandbox_id}")
        
        # 2. 在E2B沙盒中执行浏览器操作
        execution_result = await sandbox_manager.execute_browser_operations(
            persistent_id, operations
        )
        
        # 3. 合并结果
        final_result = {
            **execution_result,
            "persistent_id": persistent_id,
            "e2b_sandbox_id": e2b_sandbox_id,
            "vnc_access": vnc_access,
            "total_execution_time": timer.elapsed(),
            "sandbox_created": not sandbox_result.get("existing", False)
        }
        
        # 4. 数据清洗 (针对小红书数据)
        if XiaohongshuDataCleaner.should_clean(final_result):
            logger.info("🧹 开始清洗小红书数据...")
            final_result = XiaohongshuDataCleaner.clean_batch_result(final_result)
            
        # 5. 数据存储 (存储清洗后的小红书数据)
        try:
            logger.info("💾 开始存储小红书数据到数据库...")
            
            # 检查是否为用户个人信息数据
            if 'user_profile' in final_result and final_result.get('extraction_type') == 'user_profile':
                logger.info("🧑 检测到用户个人信息数据，使用用户信息存储...")
                
                # 获取来源信息（从请求或结果中）
                source_post_id = request.source_post_id or final_result.get('source_post_id')
                source_comment_id = request.source_comment_id or final_result.get('source_comment_id')
                
                # 如果没有提供来源信息，尝试从用户头像点击操作中获取
                if not source_post_id and not source_comment_id:
                    # 确保 operations 存在且不为空
                    if request.operations:
                        for operation in request.operations:
                            if operation.action in ['xiaohongshu_click_author_avatar', 'click_author_avatar']:
                                params = operation.params or {}
                                source_post_id = params.get('source_post_id')
                                source_comment_id = params.get('source_comment_id')
                                break
                
                storage_result = storage_service.store_user_profile_data(
                    final_result.get('user_profile', {}), 
                    source_post_id, 
                    source_comment_id
                )
            # 检查是否为帖子详情数据（包含author_post和comments）
            elif 'author_post' in final_result and 'comments' in final_result:
                logger.info("📝 检测到帖子详情数据，使用统一内容表存储...")
                storage_result = storage_service.store_post_detail_data(final_result)
            else:
                # 使用原有的批量帖子存储方法
                logger.info("📄 检测到批量帖子数据，使用传统存储方法...")
                storage_result = storage_service.store_api_response_data(final_result)
            
            # 记录数据存储完成日志（数据清洗器已确保数据格式正确）
            posts_data = final_result.get('posts', [])
            if posts_data:
                logger.info(f"🎯 数据存储完成，Dify可获取 {len(posts_data)} 个清洗后帖子")
            
            # 统一处理存储结果格式
            if 'user_profile' in final_result and final_result.get('extraction_type') == 'user_profile':
                # 用户信息存储结果格式
                final_result["storage_result"] = {
                    "success": storage_result["success"],
                    "message": storage_result["message"],
                    "user_id": storage_result.get("user_id"),
                    "posts_count": storage_result.get("posts_count", 0),
                    "stored_at": storage_result.get("stored_at")
                }
            else:
                # 帖子/评论数据存储结果格式
                final_result["storage_result"] = {
                    "success": storage_result["success"],
                    "message": storage_result["message"],
                    "stats": storage_result.get("stats", {}),
                    "stored_at": storage_result.get("stored_at")
                }
            logger.info(f"💾 数据存储完成: {storage_result['message']}")
        except Exception as e:
            logger.error(f"💾 数据存储失败: {e}")
            final_result["storage_result"] = {
                "success": False, 
                "error": str(e),
                "message": "数据存储失败"
            }
        
        # 6. 可选的自动清理
        if request.auto_cleanup and final_result.get("success", False):
            logger.info("🧹 自动清理沙盒...")
            cleanup_result = await sandbox_manager.cleanup_sandbox(persistent_id)
            final_result["cleanup_result"] = cleanup_result
        
        logger.info(f"🎯 自动化完成，总耗时: {final_result['total_execution_time']:.2f}秒")
        return final_result
        
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        logger.error(f"❌ 自动化失败: {e}")
        return ApiResponseBuilder.build_error_response(
            error_msg=f"浏览器自动化失败: {str(e)}",
            timer_or_start_time=timer,
            total_execution_time=timer.elapsed()
        )

# ==================== 数据库驱动的批量处理功能 ====================

async def get_unprocessed_posts_from_database(condition: str, limit: int) -> List[Dict]:
    """从数据库查询待处理的帖子列表"""
    try:
        logger.info(f"🔍 查询数据库：condition='{condition}', limit={limit}")
        
        # 使用现有的post_repository查询数据库
        posts = post_repository.get_posts_by_condition(condition, limit)
        
        logger.info(f"📊 查询结果：找到 {len(posts)} 个待处理帖子")
        return posts
        
    except Exception as e:
        logger.error(f"❌ 数据库查询失败: {e}")
        return []

async def mark_posts_as_processed(post_ids: List[str]) -> bool:
    """标记帖子为已处理"""
    try:
        for post_id in post_ids:
            post_repository.update_post_status(post_id, {"detail_extracted": True})
        logger.info(f"✅ 已标记 {len(post_ids)} 个帖子为已处理")
        return True
    except Exception as e:
        logger.error(f"❌ 标记帖子状态失败: {e}")
        return False

@browser_router.post("/batch_process_from_database")
async def batch_process_posts_from_database(request: BatchProcessFromDatabaseRequest):
    """
    数据库驱动的批量帖子处理工作流
    前提条件：沙盒已运行，浏览器已打开，已在小红书关键词页面
    功能：从数据库查询待处理帖子，逐个点击提取详细信息
    """
    # 🚀 使用新的时间管理器
    timer = ApiTimer.start()
    
    try:
        logger.info(f"🚀 开始数据库驱动的批量处理: limit={request.limit}")
        
        # 1. 验证沙盒是否存在
        persistent_id = request.persistent_id
        if persistent_id not in sandbox_manager.active_sandboxes:
            return {
                "success": False,
                "message": f"沙盒 {persistent_id} 不存在，请先确保沙盒已创建并运行",
                "total_execution_time": timer.elapsed()
            }
        
        sandbox = sandbox_manager.active_sandboxes[persistent_id]
        e2b_sandbox_id = sandbox.sandbox_id
        vnc_access = {
            "vnc_web_url": f"https://6080-{e2b_sandbox_id}.e2b.app",
            "vnc_direct_url": f"vnc://5901-{e2b_sandbox_id}.e2b.app",
            "display": ":1",
            "note": "通过VNC Web URL可实时观察浏览器操作"
        }
        
        logger.info(f"✅ 使用现有沙盒: {e2b_sandbox_id}")
        
        # 2. 从数据库查询待处理帖子
        posts = await get_unprocessed_posts_from_database(
            request.query_condition, 
            request.limit
        )
        
        if not posts:
            return {
                "success": False,
                "message": "没有找到待处理的帖子",
                "total_execution_time": timer.elapsed()
            }
        
        logger.info(f"📋 找到 {len(posts)} 个待处理帖子")
        
        # 3. 先滚动页面加载更多帖子，确保目标帖子在页面上
        logger.info("📜 开始滚动页面加载更多帖子，确保目标帖子可见...")
        scroll_operations = [
            {
                "action": "xiaohongshu_auto_scroll",
                "params": {"max_scrolls": 20, "delay_between_scrolls": 1.5},
                "description": "滚动页面加载更多帖子"
            }
        ]
        
        scroll_result = await sandbox_manager.execute_browser_operations(
            persistent_id, scroll_operations
        )
        
        if scroll_result.get("success", False):
            scroll_data = scroll_result.get("data", {})
            total_loaded_posts = scroll_data.get("total_posts", 0)
            total_scrolls = scroll_data.get("total_scrolls", 0)
            logger.info(f"✅ 滚动完成：加载了 {total_loaded_posts} 个帖子 (滚动 {total_scrolls} 次)")
        else:
            logger.warning(f"⚠️ 页面滚动失败，继续处理: {scroll_result.get('message', '')}")

        # 4. 逐个处理帖子（核心循环）
        processed_posts = []
        failed_posts = []
        
        for i, post in enumerate(posts):
            try:
                post_title = post.get('title', post.get('post_id', 'Unknown'))
                logger.info(f"🎯 处理帖子 {i+1}/{len(posts)}: {post_title}")
                
                # 构造单个帖子的处理操作序列（完整闭环）
                post_operations = [
                    {
                        "action": "xiaohongshu_click_post",
                        "params": {"title": post.get('title', '')},
                        "description": "步骤1: 点击进入帖子详情页"
                    },
                    {
                        "action": "xiaohongshu_expand_comments",
                        "params": {"max_attempts": 10},
                        "description": "步骤2: 展开所有评论"
                    },
                    {
                        "action": "xiaohongshu_extract_comments",
                        "params": {"include_replies": True},
                        "description": "步骤3: 提取帖子内容和所有评论数据"
                    },
                    {
                        "action": "xiaohongshu_close_post",
                        "params": {},
                        "description": "步骤4: 关闭帖子详情页，返回帖子列表"
                    }
                ]
                
                # 执行操作序列
                post_result = await sandbox_manager.execute_browser_operations(
                    persistent_id, post_operations
                )
                
                logger.info(f"🔍 帖子操作结果: success={post_result.get('success', False)}, message='{post_result.get('message', '')}'")
                
                if post_result.get("success", False):
                    logger.info(f"📋 开始数据处理流程: {post_title}")
                    
                    # 数据清洗检查
                    should_clean = XiaohongshuDataCleaner.should_clean(post_result)
                    logger.info(f"🧹 数据清洗检查: should_clean={should_clean}")
                    
                    if should_clean:
                        cleaned_result = XiaohongshuDataCleaner.clean_batch_result(post_result)
                        logger.info(f"🧹 数据清洗完成: author_post={('author_post' in cleaned_result)}, comments={('comments' in cleaned_result)}")
                        
                        # 存储详细数据
                        if 'author_post' in cleaned_result and 'comments' in cleaned_result:
                            logger.info(f"📊 数据格式正确，开始存储: {post_title}")
                            storage_result = storage_service.store_post_detail_data(cleaned_result)
                            logger.info(f"💾 存储结果: success={storage_result.get('success', False)}")
                            
                            if storage_result["success"]:
                                # 标记为已处理
                                await mark_posts_as_processed([post.get('post_id')])
                                processed_posts.append(post.get('post_id'))
                                logger.info(f"✅ 帖子处理成功: {post_title}")
                            else:
                                failed_posts.append(post.get('post_id'))
                                logger.error(f"❌ 数据存储失败: {post_title} - {storage_result.get('message', '')}")
                        else:
                            failed_posts.append(post.get('post_id'))
                            logger.error(f"❌ 数据格式不正确: {post_title} - author_post存在: {'author_post' in cleaned_result}, comments存在: {'comments' in cleaned_result}")
                    else:
                        failed_posts.append(post.get('post_id'))
                        logger.error(f"❌ 数据清洗检查失败: {post_title}")
                        logger.error(f"❌ post_result内容预览: {str(post_result)[:200]}...")
                else:
                    failed_posts.append(post.get('post_id'))
                    logger.error(f"❌ 帖子操作失败: {post_title} - {post_result.get('message', '')}")
                    logger.error(f"❌ post_result详情: {str(post_result)[:300]}...")
                
                # 处理完一个帖子后，导航回列表页（重要！）
                if request.base_url:
                    # 如果提供了基础URL，直接导航回去（推荐）
                    back_operation = [{
                        "action": "navigate",
                        "params": {"url": request.base_url},
                        "description": "返回小红书关键词页面"
                    }]
                else:
                    # 否则尝试浏览器后退
                    back_operation = [{
                        "action": "execute_script",
                        "params": {"script": "window.history.back(); await new Promise(resolve => setTimeout(resolve, 1000));"},
                        "description": "浏览器后退到列表页"
                    }]
                await sandbox_manager.execute_browser_operations(persistent_id, back_operation)
                
                # 帖子间延迟
                if request.delay_between_posts > 0:
                    await asyncio.sleep(request.delay_between_posts)
                    
                # 定期输出进度
                if (i + 1) % 10 == 0:
                    logger.info(f"📊 进度更新: 已处理 {i+1}/{len(posts)} 个帖子，成功 {len(processed_posts)} 个")
                    
            except Exception as e:
                failed_posts.append(post.get('post_id'))
                logger.error(f"❌ 处理帖子异常: {post_title} - {str(e)}")
        
        # 4. 构建最终结果
        total_execution_time = timer.elapsed()
        success_rate = len(processed_posts) / len(posts) if posts else 0
        
        final_result = {
            "success": len(processed_posts) > 0,
            "message": f"批量处理完成: {len(processed_posts)}/{len(posts)} 个帖子成功处理",
            "statistics": {
                "total_posts": len(posts),
                "processed_posts": len(processed_posts),
                "failed_posts": len(failed_posts),
                "success_rate": f"{success_rate:.2%}"
            },
            "processed_post_ids": processed_posts,
            "failed_post_ids": failed_posts,
            "execution_details": {
                "total_execution_time": total_execution_time,
                "average_time_per_post": total_execution_time / len(posts) if posts else 0,
                "persistent_id": persistent_id,
                "e2b_sandbox_id": e2b_sandbox_id,
                "vnc_access": vnc_access
            }
        }
        
        logger.info(f"🎉 批量处理完成: {final_result['message']}, 总耗时: {total_execution_time:.2f}秒")
        return final_result
        
    except Exception as e:
        logger.error(f"❌ 批量处理异常: {e}")
        return ApiResponseBuilder.build_error_response(
            error_msg=f"批量处理失败: {str(e)}",
            timer_or_start_time=timer,
            total_execution_time=timer.elapsed()
        )

# ==================== LLM分析结果存储API ====================

@browser_router.post("/store-post-classification")
async def store_post_classification(request: Union[PostClassificationRequest, List[PostClassificationItem]]):
    """
    存储LLM帖子分类结果 - 支持两种格式：
    1. 包装格式：{"post_classification": [...]}
    2. 直接数组格式：[{...}, {...}, ...]
    """
    # 🚀 使用新的时间管理器
    timer = ApiTimer.start()
    
    try:
        # 🎯 判断请求格式并提取帖子列表
        if isinstance(request, list):
            # 直接数组格式
            post_items = request
            logger.info(f"📝 开始批量存储帖子分类结果 (直接数组格式): {len(post_items)} 个帖子")
        else:
            # 包装格式
            post_items = request.post_classification
            logger.info(f"📝 开始批量存储帖子分类结果 (包装格式): {len(post_items)} 个帖子")
        
        # 转换API数据为数据库格式
        classifications = []
        for post in post_items:
            classification_data = {
                'post_id': post.post_id,
                'classification': post.classification,
                'confidence_score': post.confidence_score,
                'reasoning': post.reasoning,
                'commercial_value': post.commercial_value,
                'need_ai_analysis': post.need_ai_analysis
            }
            classifications.append(classification_data)
        
        # 执行真实的数据库存储
        storage_result = classification_repository.batch_insert_classifications(classifications)
        
        # 🎯 使用时间管理器构建响应
        result = ApiResponseBuilder.build_batch_api_response(
            storage_result=storage_result,
            timer_or_start_time=timer,
            success_template="批量帖子分类存储完成: {stored_count}/{total_count} 个成功",
            failure_template="批量帖子分类存储失败: {failed_count}/{total_count} 个失败",
            extra_data={"total_posts": len(post_items)}
        )
        
        logger.info(f"✅ 批量帖子分类存储完成: {storage_result['stored_count']} 个成功, {storage_result['failed_count']} 个失败")
        return result
        
    except Exception as e:
        logger.error(f"❌ 批量帖子分类存储异常: {e}")
        
        # 计算帖子总数（支持两种格式）
        total_posts = 0
        try:
            if isinstance(request, list):
                total_posts = len(request)
            elif hasattr(request, 'post_classification') and request.post_classification:
                total_posts = len(request.post_classification)
        except Exception:
            total_posts = 0
        
        return ApiResponseBuilder.build_error_response(
            error_msg=f"批量帖子分类存储失败: {str(e)}",
            timer_or_start_time=timer,
            total_posts=total_posts
        )


@browser_router.post("/store-comment-analysis")
async def store_comment_analysis(request: CommentAnalysisRequest):
    """
    存储LLM评论分析结果（节点3输出）
    接收LLM包装格式：{"comment_analysis": [...]}
    """
    # 🚀 使用新的时间管理器
    timer = ApiTimer.start()
    
    try:
        logger.info(f"📊 开始存储评论分析结果: {len(request.comment_analysis)} 条评论")
        
        # 转换API数据为数据库格式
        analyses = []
        for comment in request.comment_analysis:
            analysis_data = {
                'comment_id': comment.comment_id,
                'user_id': comment.user_id,
                'username': comment.username,
                'content': comment.content,
                'is_valid': comment.is_valid,
                'intent_type': comment.intent_type,
                'intent_level': comment.intent_level,
                'sentiment': comment.sentiment,
                'confidence': comment.confidence,
                'key_features': {
                    'product_category': comment.key_features.product_category,
                    'functional_needs': comment.key_features.functional_needs,
                    'user_profile': comment.key_features.user_profile,
                    'size_info': comment.key_features.size_info
                },
                'business_value': comment.business_value,
                'follow_up_action': comment.follow_up_action
            }
            analyses.append(analysis_data)
        
        # 执行真实的数据库存储
        storage_result = ai_analysis_repository.batch_insert_comment_analysis(analyses)
        
        # 🎯 使用时间管理器构建响应
        result = ApiResponseBuilder.build_batch_api_response(
            storage_result=storage_result,
            timer_or_start_time=timer,
            success_template="评论分析结果存储完成: {stored_count}/{total_count} 条成功",
            failure_template="评论分析结果存储失败: {failed_count}/{total_count} 条失败",
            extra_data={"total_comments": storage_result['total_count']}
        )
        
        logger.info(f"✅ 评论分析存储完成: {storage_result['stored_count']} 条成功, {storage_result['failed_count']} 条失败")
        return result
        
    except Exception as e:
        logger.error(f"❌ 评论分析存储异常: {e}")
        return ApiResponseBuilder.build_error_response(
            error_msg=f"评论分析存储失败: {str(e)}",
            timer_or_start_time=timer,
            total_comments=len(request.comment_analysis) if request and request.comment_analysis else 0
        )

# ==================== 客户洞察分析存储API ====================

@browser_router.post("/store-customer-insights")
async def store_customer_insights(insights: Union[CustomerInsightsItem, List[CustomerInsightsItem]]):
    """
    存储客户洞察分析结果 - 支持单个或批量处理
    
    参数格式:
    - 单个客户: CustomerInsightsItem 对象
    - 多个客户: List[CustomerInsightsItem] 数组
    
    接收大模型分析的客户洞察数据并存储到xiaohongshu_customer_insights表
    """
    timer = ApiTimer.start()
    
    try:
        # 🎯 判断是单个还是批量处理
        is_batch = isinstance(insights, list)
        insights_list = insights if is_batch else [insights]
        
        logger.info(f"🧠 开始存储客户洞察: {'批量' if is_batch else '单个'} - {len(insights_list)} 个用户")
        
        if is_batch:
            # 📦 批量处理逻辑
            batch_data = [
                {
                    'user_id': insight.user_id,
                    'insights_data': convert_customer_insight_to_db_format(insight)
                }
                for insight in insights_list
            ]
            
            # 执行批量存储
            batch_result = customer_insights_repository.batch_insert_insights(batch_data)
            
            # 构建批量响应
            result = ApiResponseBuilder.build_batch_insights_api_response(
                batch_result=batch_result,
                timer_or_start_time=timer
            )
            
            logger.info(f"✅ 批量客户洞察存储完成: {batch_result['success_count']} 个用户成功, {batch_result['error_count']} 个用户失败")
            
        else:
            # 👤 单个处理逻辑
            single_insight = insights_list[0]
            
            # 转换API数据为数据库格式
            insights_data = convert_customer_insight_to_db_format(single_insight)
            
            # 执行单个存储
            storage_result = customer_insights_repository.insert_customer_insights(
                single_insight.user_id, 
                insights_data
            )
            
            # 构建单个响应
            result = ApiResponseBuilder.build_insights_api_response(
                storage_result=storage_result,
                timer_or_start_time=timer,
                user_id=single_insight.user_id,
                tags_count=len(single_insight.primary_tags),
                intent_level=single_insight.latest_intent_level,
                intent_type=single_insight.latest_intent_type
            )
            
            logger.info(f"✅ 客户洞察存储完成: 用户 {single_insight.user_id}, 标签概览: {storage_result.get('tags_overview', '')}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ 客户洞察存储异常: {e}")
        
        # 错误响应处理
        if isinstance(insights, list):
            return ApiResponseBuilder.build_error_response(
                error_msg=f"批量客户洞察存储失败: {str(e)}",
                timer_or_start_time=timer,
                total_users=len(insights)
            )
        else:
            return ApiResponseBuilder.build_error_response(
                error_msg=f"客户洞察存储失败: {str(e)}",
                timer_or_start_time=timer,
                user_id=insights.user_id if insights else "unknown"
            )