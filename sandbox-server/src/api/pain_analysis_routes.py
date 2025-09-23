"""
痛点分析 API 路由
提供痛点分析数据的存储和查询接口
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
import logging
import time
from datetime import datetime
from pydantic import ValidationError

from models.pain_analysis_models import (
    PainAnalysisRequest, PainAnalysisResponse, PainAnalysisStats,
    QueryPainAnalysisRequest, ContentType, Sentiment, PainCategory, Severity
)
from models.request_models import BaseResponse
from xiaohongshuDataStorage.pain_analysis_repository import pain_analysis_repository

logger = logging.getLogger(__name__)

# 创建路由器
pain_analysis_router = APIRouter()

@pain_analysis_router.post("/store", response_model=PainAnalysisResponse)
async def store_pain_analysis_data(request: PainAnalysisRequest):
    """
    存储痛点分析数据
    
    接收例子.md中的JSON格式数据，存储到相应的数据库表中
    """
    start_time = time.time()
    
    try:
        logger.info(f"📥 接收痛点分析数据存储请求: {len(request.pain_point_analysis)} 条记录")
        
        # 转换Pydantic模型为字典格式
        analysis_data = []
        for content in request.pain_point_analysis:
            # 将Pydantic模型转换为字典
            content_dict = content.dict()
            
            # 处理嵌套字段的转换
            if content.user_needs:
                content_dict['user_needs'] = [need.dict() for need in content.user_needs]
            if content.identified_pain_points:
                content_dict['identified_pain_points'] = [pp.dict() for pp in content.identified_pain_points]
            if content.solved_problems:
                content_dict['solved_problems'] = [sp.dict() for sp in content.solved_problems]
            if content.usage_scenarios:
                content_dict['usage_scenarios'] = [us.dict() for us in content.usage_scenarios]
            
            # 添加情感分析和商业洞察
            content_dict['emotional_analysis'] = content.emotional_analysis.dict()
            content_dict['commercial_insights'] = content.commercial_insights.dict()
            
            analysis_data.append(content_dict)
        
        # 调用仓库层存储数据
        result = pain_analysis_repository.store_pain_analysis_data(
            analysis_data=analysis_data,
            analysis_batch=request.analysis_batch
        )
        
        execution_time = round(time.time() - start_time, 2)
        
        if result['success']:
            logger.info(f"✅ 痛点分析数据存储成功: {result['message']}")
            return PainAnalysisResponse(
                success=True,
                message=result['message'],
                data={
                    'total_records': len(analysis_data),
                    'execution_time': execution_time
                },
                analysis_batch=result['stats']['analysis_batch'],
                storage_stats=result['stats']
            )
        else:
            logger.error(f"❌ 痛点分析数据存储失败: {result['message']}")
            return PainAnalysisResponse(
                success=False,
                message=result['message'],
                analysis_batch=request.analysis_batch,
                storage_stats=result.get('stats')
            )
    
    except ValidationError as e:
        logger.error(f"❌ 请求数据验证失败: {e.errors()}", exc_info=True)
        raise HTTPException(
            status_code=422,
            detail={"message": "请求数据验证失败", "errors": e.errors()}
        )
    except Exception as e:
        logger.error(f"❌ 存储痛点分析数据时发生未知错误: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")

@pain_analysis_router.get("/stats", response_model=BaseResponse)
async def get_pain_analysis_stats(
    analysis_batch: Optional[str] = Query(None, description="分析批次标识")
):
    """
    获取痛点分析统计信息
    """
    try:
        logger.info(f"📊 获取痛点分析统计信息: 批次 {analysis_batch or '全部'}")
        
        stats = pain_analysis_repository.get_pain_analysis_stats(analysis_batch)
        
        if 'error' in stats:
            return BaseResponse(
                success=False,
                message=f"获取统计信息失败: {stats['error']}",
                data=None
            )
        
        return BaseResponse(
            success=True,
            message="统计信息获取成功",
            data={
                'statistics': stats,
                'analysis_batch': analysis_batch,
                'generated_at': datetime.now().isoformat()
            }
        )
    
    except Exception as e:
        logger.error(f"❌ 获取统计信息时发生异常: {str(e)}")
        return BaseResponse(
            success=False,
            message=f"获取统计信息失败: {str(e)}",
            data=None
        )

@pain_analysis_router.get("/query", response_model=BaseResponse)
async def query_pain_analysis_data(
    analysis_batch: Optional[str] = Query(None, description="分析批次标识"),
    content_type: Optional[ContentType] = Query(None, description="内容类型筛选"),
    sentiment: Optional[Sentiment] = Query(None, description="情感类型筛选"),
    pain_category: Optional[PainCategory] = Query(None, description="痛点分类筛选"),
    severity: Optional[Severity] = Query(None, description="严重程度筛选"),
    limit: int = Query(50, ge=1, le=1000, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量")
):
    """
    查询痛点分析数据
    
    支持多种筛选条件的痛点分析数据查询
    """
    try:
        logger.info(f"🔍 查询痛点分析数据: 批次 {analysis_batch}, 类型 {content_type}, 情感 {sentiment}")
        
        conditions = {
            'analysis_batch': analysis_batch,
            'content_type': content_type.value if content_type else None,
            'sentiment': sentiment.value if sentiment else None,
            'pain_category': pain_category.value if pain_category else None,
            'severity': severity.value if severity else None,
            'limit': limit,
            'offset': offset
        }
        
        # 移除None值
        conditions = {k: v for k, v in conditions.items() if v is not None}
        
        results = pain_analysis_repository.query_pain_analysis(conditions)
        
        return BaseResponse(
            success=True,
            message=f"查询成功，返回 {len(results)} 条记录",
            data={
                'results': results,
                'query_conditions': conditions,
                'total_returned': len(results),
                'queried_at': datetime.now().isoformat()
            }
        )
    
    except Exception as e:
        logger.error(f"❌ 查询痛点分析数据时发生异常: {str(e)}")
        return BaseResponse(
            success=False,
            message=f"查询失败: {str(e)}",
            data=None
        )

@pain_analysis_router.get("/batches", response_model=BaseResponse)
async def get_analysis_batches():
    """
    获取所有分析批次列表
    """
    try:
        logger.info("📋 获取分析批次列表")
        
        sql = """
        SELECT 
            analysis_batch,
            COUNT(*) as total_contents,
            MIN(created_at) as first_created,
            MAX(created_at) as last_created,
            COUNT(CASE WHEN content_type = 'post' THEN 1 END) as posts_count,
            COUNT(CASE WHEN content_type = 'comment' THEN 1 END) as comments_count
        FROM xiaohongshu_pain_analysis 
        WHERE analysis_batch IS NOT NULL
        GROUP BY analysis_batch 
        ORDER BY last_created DESC
        """
        
        from xiaohongshuDataStorage.connect_manager import db_manager
        batches = db_manager.execute_query(sql)
        
        return BaseResponse(
            success=True,
            message=f"获取到 {len(batches)} 个分析批次",
            data={
                'batches': batches,
                'total_batches': len(batches),
                'generated_at': datetime.now().isoformat()
            }
        )
    
    except Exception as e:
        logger.error(f"❌ 获取分析批次列表时发生异常: {str(e)}")
        return BaseResponse(
            success=False,
            message=f"获取批次列表失败: {str(e)}",
            data=None
        )

@pain_analysis_router.delete("/batch/{analysis_batch}", response_model=BaseResponse)
async def delete_analysis_batch(analysis_batch: str):
    """
    删除指定批次的分析数据
    """
    try:
        logger.info(f"🗑️ 删除分析批次: {analysis_batch}")
        
        success = pain_analysis_repository.delete_analysis_batch(analysis_batch)
        
        if success:
            return BaseResponse(
                success=True,
                message=f"成功删除批次 {analysis_batch} 的所有数据",
                data={'deleted_batch': analysis_batch}
            )
        else:
            return BaseResponse(
                success=False,
                message=f"删除批次 {analysis_batch} 失败，批次可能不存在",
                data=None
            )
    
    except Exception as e:
        logger.error(f"❌ 删除分析批次时发生异常: {str(e)}")
        return BaseResponse(
            success=False,
            message=f"删除批次失败: {str(e)}",
            data=None
        )

@pain_analysis_router.get("/content/{content_id}", response_model=BaseResponse)
async def get_content_detail(content_id: str):
    """
    获取特定内容的详细分析数据
    """
    try:
        logger.info(f"📄 获取内容详情: {content_id}")
        
        from xiaohongshuDataStorage.connect_manager import db_manager
        
        # 获取主要内容信息
        main_sql = "SELECT * FROM xiaohongshu_pain_analysis WHERE content_id = %s"
        main_data = db_manager.execute_query(main_sql, (content_id,))
        
        if not main_data:
            raise HTTPException(status_code=404, detail=f"内容 {content_id} 不存在")
        
        content_detail = main_data[0]
        
        # 获取相关的子表数据
        tables_data = {}
        
        # 痛点数据
        pain_points = db_manager.execute_query(
            "SELECT * FROM xiaohongshu_pain_points WHERE content_id = %s ORDER BY id",
            (content_id,)
        )
        tables_data['pain_points'] = pain_points
        
        # 解决方案数据
        solved_problems = db_manager.execute_query(
            "SELECT * FROM xiaohongshu_solved_problems WHERE content_id = %s ORDER BY id",
            (content_id,)
        )
        tables_data['solved_problems'] = solved_problems
        
        # 用户需求数据
        user_needs = db_manager.execute_query(
            "SELECT * FROM xiaohongshu_user_needs WHERE content_id = %s ORDER BY id",
            (content_id,)
        )
        tables_data['user_needs'] = user_needs
        
        # 使用场景数据
        usage_scenarios = db_manager.execute_query(
            "SELECT * FROM xiaohongshu_usage_scenarios WHERE content_id = %s ORDER BY id",
            (content_id,)
        )
        tables_data['usage_scenarios'] = usage_scenarios
        
        # 品牌提及数据
        brand_mentions = db_manager.execute_query(
            "SELECT * FROM xiaohongshu_brand_mentions WHERE content_id = %s ORDER BY mention_order",
            (content_id,)
        )
        tables_data['brand_mentions'] = brand_mentions
        
        # 产品型号数据
        product_models = db_manager.execute_query(
            "SELECT * FROM xiaohongshu_product_models WHERE content_id = %s ORDER BY mention_order",
            (content_id,)
        )
        tables_data['product_models'] = product_models
        
        # 情感关键词数据
        emotional_keywords = db_manager.execute_query(
            "SELECT * FROM xiaohongshu_emotional_keywords WHERE content_id = %s ORDER BY keyword_order",
            (content_id,)
        )
        tables_data['emotional_keywords'] = emotional_keywords
        
        # 帖子标签数据（如果是帖子）
        if content_detail['content_type'] == 'post':
            post_tags = db_manager.execute_query(
                "SELECT * FROM xiaohongshu_post_tags WHERE content_id = %s ORDER BY tag_order",
                (content_id,)
            )
            tables_data['post_tags'] = post_tags
        
        return BaseResponse(
            success=True,
            message=f"成功获取内容 {content_id} 的详细信息",
            data={
                'main_data': content_detail,
                'related_data': tables_data,
                'content_id': content_id,
                'queried_at': datetime.now().isoformat()
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取内容详情时发生异常: {str(e)}")
        return BaseResponse(
            success=False,
            message=f"获取内容详情失败: {str(e)}",
            data=None
        )

@pain_analysis_router.get("/health", response_model=BaseResponse)
async def health_check():
    """
    痛点分析模块健康检查
    """
    try:
        # 检查数据库连接
        from xiaohongshuDataStorage.connect_manager import db_manager
        health = db_manager.health_check()
        
        # 检查表是否存在
        tables_status = {}
        required_tables = [
            'xiaohongshu_pain_analysis',
            'xiaohongshu_pain_points', 
            'xiaohongshu_solved_problems',
            'xiaohongshu_user_needs',
            'xiaohongshu_usage_scenarios',
            'xiaohongshu_brand_mentions',
            'xiaohongshu_product_models',
            'xiaohongshu_emotional_keywords',
            'xiaohongshu_post_tags'
        ]
        
        for table in required_tables:
            try:
                result = db_manager.execute_query(f"SELECT COUNT(*) as count FROM {table} LIMIT 1")
                tables_status[table] = {'exists': True, 'count': result[0]['count']}
            except Exception as e:
                tables_status[table] = {'exists': False, 'error': str(e)}
        
        all_tables_exist = all(status['exists'] for status in tables_status.values())
        
        return BaseResponse(
            success=health['status'] == 'healthy' and all_tables_exist,
            message="痛点分析模块健康检查完成",
            data={
                'database_health': health,
                'tables_status': tables_status,
                'all_tables_exist': all_tables_exist,
                'checked_at': datetime.now().isoformat()
            }
        )
    
    except Exception as e:
        logger.error(f"❌ 健康检查时发生异常: {str(e)}")
        return BaseResponse(
            success=False,
            message=f"健康检查失败: {str(e)}",
            data=None
        )
