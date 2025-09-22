"""
客户洞察数据仓库
负责xiaohongshu_customer_insights表的数据库操作
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from .connect_manager import db_manager

logger = logging.getLogger(__name__)

class CustomerInsightsRepository:
    """客户洞察数据仓库"""
    
    def __init__(self):
        self.table_name = "xiaohongshu_customer_insights"
    
    def get_user_insights(self, user_id: str) -> List[Dict[str, Any]]:
        """
        获取用户的所有客户洞察记录
        
        Args:
            user_id: 用户ID
            
        Returns:
            用户洞察记录列表
        """
        try:
            with db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    sql = f"""
                    SELECT * FROM {self.table_name} 
                    WHERE user_id = %s
                    ORDER BY last_updated_at DESC
                    """
                    cursor.execute(sql, (user_id,))
                    results = cursor.fetchall()
                    
                    return [dict(row) for row in results] if results else []
                    
        except Exception as e:
            logger.error(f"查询用户洞察失败: {user_id} - {e}")
            return []
    
    def insert_customer_insights(self, user_id: str, insights_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        插入客户洞察分析结果 - 每用户一条记录
        
        Args:
            user_id: 用户ID
            insights_data: 洞察数据，包含latest_intent_level, latest_intent_type, customer_status等
            
        Returns:
            操作结果
        """
        try:
            with db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 先删除该用户的旧记录（如果存在）
                    delete_sql = f"DELETE FROM {self.table_name} WHERE user_id = %s"
                    cursor.execute(delete_sql, (user_id,))
                    
                    # 处理标签数据
                    primary_tags = insights_data.get('primary_tags', [])
                    
                    # 生成标签概览字符串（所有标签名称用逗号分隔）
                    tags_overview = insights_data.get('tags_overview', '')
                    if not tags_overview and primary_tags:
                        tags_overview = ', '.join([tag.get('tag_name', '') for tag in primary_tags])
                    
                    # 获取主要标签（第一个标签）的详细信息
                    main_tag = primary_tags[0] if primary_tags else {}
                    
                    # 插入单条完整记录
                    insert_sql = f"""
                    INSERT INTO {self.table_name} (
                        user_id, platform, latest_intent_level, latest_intent_type,
                        first_discovered_at, last_updated_at, customer_status, 
                        tags_overview, tag_name, tag_category, confidence, source_content
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    
                    values = (
                        user_id,
                        'xiaohongshu',
                        insights_data.get('latest_intent_level'),
                        insights_data.get('latest_intent_type'), 
                        datetime.now(),  # first_discovered_at
                        datetime.now(),  # last_updated_at
                        insights_data.get('customer_status'),
                        tags_overview,  # 所有标签的概览
                        main_tag.get('tag_name'),  # 主要标签名称
                        main_tag.get('tag_category'),  # 主要标签分类
                        main_tag.get('confidence'),  # 主要标签置信度
                        (main_tag.get('source_content', '') or '')[:200]  # 主要标签来源，限制长度
                    )
                    
                    cursor.execute(insert_sql, values)
                    conn.commit()
                    
                    logger.info(f"成功存储用户客户洞察: {user_id}, 标签概览: {tags_overview}")
                    
                    return {
                        'success': True,
                        'user_id': user_id,
                        'tags_count': len(primary_tags),
                        'tags_overview': tags_overview,
                        'message': f'成功存储客户洞察，包含{len(primary_tags)}个标签'
                    }
                    
        except Exception as e:
            logger.error(f"存储客户洞察失败: {user_id} - {e}")
            return {
                'success': False,
                'user_id': user_id,
                'error': str(e),
                'message': '存储客户洞察失败'
            }
    
    def update_user_intent(self, user_id: str, intent_level: str, intent_type: str) -> Dict[str, Any]:
        """
        更新用户的最新意向信息
        
        Args:
            user_id: 用户ID
            intent_level: 意向等级
            intent_type: 意向类型
            
        Returns:
            操作结果
        """
        try:
            with db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    sql = f"""
                    UPDATE {self.table_name} 
                    SET latest_intent_level = %s, latest_intent_type = %s, last_updated_at = %s
                    WHERE user_id = %s
                    """
                    
                    cursor.execute(sql, (intent_level, intent_type, datetime.now(), user_id))
                    conn.commit()
                    
                    affected_rows = cursor.rowcount
                    
                    if affected_rows > 0:
                        logger.info(f"成功更新用户意向: {user_id} -> {intent_level}/{intent_type}")
                        return {
                            'success': True,
                            'user_id': user_id,
                            'affected_rows': affected_rows,
                            'message': '成功更新用户意向'
                        }
                    else:
                        logger.warning(f"未找到用户记录，无法更新意向: {user_id}")
                        return {
                            'success': False,
                            'user_id': user_id,
                            'message': '未找到用户记录'
                        }
                        
        except Exception as e:
            logger.error(f"更新用户意向失败: {user_id} - {e}")
            return {
                'success': False,
                'user_id': user_id,
                'error': str(e),
                'message': '更新用户意向失败'
            }
    
    def get_high_value_customers(self, intent_level: str = 'HIGH', limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取高价值客户列表
        
        Args:
            intent_level: 意向等级过滤
            limit: 返回数量限制
            
        Returns:
            高价值客户列表
        """
        try:
            with db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    sql = f"""
                    SELECT user_id, latest_intent_level, latest_intent_type, customer_status,
                           tags_overview, last_updated_at,
                           GROUP_CONCAT(tag_name) as all_tags
                    FROM {self.table_name}
                    WHERE latest_intent_level = %s
                    GROUP BY user_id
                    ORDER BY last_updated_at DESC
                    LIMIT %s
                    """
                    
                    cursor.execute(sql, (intent_level, limit))
                    results = cursor.fetchall()
                    
                    return [dict(row) for row in results] if results else []
                    
        except Exception as e:
            logger.error(f"查询高价值客户失败: {e}")
            return []
    
    def batch_insert_insights(self, insights_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        批量插入客户洞察数据 - 每用户一条记录
        
        Args:
            insights_list: 洞察数据列表，每项包含user_id和insights_data
            
        Returns:
            批量操作结果
        """
        success_count = 0
        error_count = 0
        errors = []
        
        for item in insights_list:
            user_id = item.get('user_id')
            insights_data = item.get('insights_data', {})
            
            result = self.insert_customer_insights(user_id, insights_data)
            
            if result.get('success'):
                success_count += 1
                logger.debug(f"批量处理成功: {user_id} - {result.get('tags_overview', '')}")
            else:
                error_count += 1
                errors.append({
                    'user_id': user_id,
                    'error': result.get('error', '未知错误')
                })
                logger.warning(f"批量处理失败: {user_id} - {result.get('error', '')}")
        
        logger.info(f"批量插入客户洞察完成: 成功{success_count}个用户, 失败{error_count}个用户")
        
        return {
            'success': error_count == 0,
            'total': len(insights_list),
            'success_count': success_count,
            'error_count': error_count,
            'errors': errors,
            'message': f'批量处理完成: 成功{success_count}个用户, 失败{error_count}个用户'
        }

# 创建全局实例
customer_insights_repository = CustomerInsightsRepository()
