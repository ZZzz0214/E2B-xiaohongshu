"""
小红书痛点分析数据仓库
负责痛点分析相关数据的数据库操作
"""
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import uuid

from .connect_manager import db_manager

logger = logging.getLogger(__name__)

class PainAnalysisRepository:
    """痛点分析数据仓库"""
    
    def __init__(self):
        self.main_table = "xiaohongshu_pain_analysis"
        
        # 子表映射
        self.tables = {
            'pain_points': 'xiaohongshu_pain_points',
            'solved_problems': 'xiaohongshu_solved_problems', 
            'user_needs': 'xiaohongshu_user_needs',
            'usage_scenarios': 'xiaohongshu_usage_scenarios',
            'brand_mentions': 'xiaohongshu_brand_mentions',
            'product_models': 'xiaohongshu_product_models',
            'emotional_keywords': 'xiaohongshu_emotional_keywords',
            'post_tags': 'xiaohongshu_post_tags',
            'summary_insights': 'xiaohongshu_summary_insights'
        }
    
    def store_pain_analysis_data(self, analysis_data: List[Dict[str, Any]], 
                                analysis_batch: Optional[str] = None) -> Dict[str, Any]:
        """
        存储痛点分析数据
        
        Args:
            analysis_data: 痛点分析数据列表
            analysis_batch: 分析批次标识
        
        Returns:
            存储结果统计
        """
        logger.info(f"🗃️ 开始存储痛点分析数据: {len(analysis_data)} 条记录")
        
        if not analysis_batch:
            analysis_batch = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        start_time = datetime.now()
        
        # 存储统计
        stats = {
            'analysis_batch': analysis_batch,
            'main_records': {'total': 0, 'success': 0, 'error': 0},
            'sub_records': {
                'pain_points': {'total': 0, 'success': 0, 'error': 0},
                'solved_problems': {'total': 0, 'success': 0, 'error': 0},
                'user_needs': {'total': 0, 'success': 0, 'error': 0},
                'usage_scenarios': {'total': 0, 'success': 0, 'error': 0},
                'brand_mentions': {'total': 0, 'success': 0, 'error': 0},
                'product_models': {'total': 0, 'success': 0, 'error': 0},
                'emotional_keywords': {'total': 0, 'success': 0, 'error': 0},
                'post_tags': {'total': 0, 'success': 0, 'error': 0}
            },
            'execution_time': 0
        }
        
        try:
            with db_manager.transaction() as cursor:
                # 存储主表数据
                main_success, main_error = self._store_main_analysis_data(
                    cursor, analysis_data, analysis_batch
                )
                
                stats['main_records'] = {
                    'total': len(analysis_data),
                    'success': main_success,
                    'error': main_error
                }
                
                # 存储子表数据
                for content in analysis_data:
                    content_id = content['content_id']
                    
                    # 存储痛点数据
                    self._store_pain_points(cursor, content_id, content.get('identified_pain_points', []), stats)
                    
                    # 存储解决方案数据
                    self._store_solved_problems(cursor, content_id, content.get('solved_problems', []), stats)
                    
                    # 存储用户需求数据
                    self._store_user_needs(cursor, content_id, content.get('user_needs', []), stats)
                    
                    # 存储使用场景数据
                    self._store_usage_scenarios(cursor, content_id, content.get('usage_scenarios', []), stats)
                    
                    # 存储品牌提及数据
                    self._store_brand_mentions(cursor, content_id, content.get('brand_mentions', []), stats)
                    
                    # 存储产品型号数据
                    self._store_product_models(cursor, content_id, content.get('product_models', []), stats)
                    
                    # 存储情感关键词数据
                    emotional_keywords = content.get('emotional_analysis', {}).get('emotional_keywords', [])
                    self._store_emotional_keywords(cursor, content_id, emotional_keywords, stats)
                    
                    # 存储帖子标签数据（仅适用于帖子）
                    if content.get('content_type') == 'post':
                        self._store_post_tags(cursor, content_id, content.get('tags', []), stats)
                
                # 计算执行时间
                execution_time = (datetime.now() - start_time).total_seconds()
                stats['execution_time'] = round(execution_time, 2)
                
                logger.info(f"✅ 痛点分析数据存储完成: 批次 {analysis_batch}")
                
                return {
                    'success': True,
                    'message': f'痛点分析数据存储成功，批次: {analysis_batch}',
                    'stats': stats
                }
        
        except Exception as e:
            logger.error(f"❌ 痛点分析数据存储失败: {e}", exc_info=True)
            return {
                'success': False,
                'message': f'存储失败: {str(e)}',
                'stats': stats,
                'error': str(e)
            }
    
    def _store_main_analysis_data(self, cursor, analysis_data: List[Dict[str, Any]], 
                                analysis_batch: str) -> Tuple[int, int]:
        """存储主表数据"""
        success_count = 0
        error_count = 0
        
        sql = f"""
        INSERT INTO {self.main_table} (
            content_id, content_type, user_name, content_snippet,
            overall_sentiment, intensity_score, user_satisfaction,
            purchase_intent, recommendation_likelihood, competitor_comparison, price_sensitivity,
            analysis_batch
        ) VALUES (
            %s, %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s, %s, %s
        ) ON DUPLICATE KEY UPDATE
            content_type = VALUES(content_type),
            user_name = VALUES(user_name), 
            content_snippet = VALUES(content_snippet),
            overall_sentiment = VALUES(overall_sentiment),
            intensity_score = VALUES(intensity_score),
            user_satisfaction = VALUES(user_satisfaction),
            purchase_intent = VALUES(purchase_intent),
            recommendation_likelihood = VALUES(recommendation_likelihood),
            competitor_comparison = VALUES(competitor_comparison),
            price_sensitivity = VALUES(price_sensitivity),
            analysis_batch = VALUES(analysis_batch),
            updated_at = CURRENT_TIMESTAMP
        """
        
        for content in analysis_data:
            try:
                emotional_analysis = content.get('emotional_analysis', {})
                commercial_insights = content.get('commercial_insights', {})
                
                params = (
                    content['content_id'],
                    content['content_type'],
                    content.get('user_name'),
                    content.get('content_snippet'),
                    emotional_analysis.get('overall_sentiment'),
                    emotional_analysis.get('intensity_score'),
                    emotional_analysis.get('user_satisfaction'),
                    commercial_insights.get('purchase_intent'),
                    commercial_insights.get('recommendation_likelihood'),
                    commercial_insights.get('competitor_comparison'),
                    commercial_insights.get('price_sensitivity'),
                    analysis_batch
                )
                
                cursor.execute(sql, params)
                success_count += 1
                
            except Exception as e:
                logger.error(f"存储主表记录失败: {content.get('content_id')}, 错误: {e}")
                error_count += 1
        
        return success_count, error_count
    
    def _store_pain_points(self, cursor, content_id: str, pain_points: List[Dict[str, Any]], stats: Dict):
        """存储痛点数据"""
        if not pain_points:
            return
            
        sql = f"""
        INSERT INTO {self.tables['pain_points']} (
            content_id, pain_point, category, severity, evidence
        ) VALUES (%s, %s, %s, %s, %s)
        """
        
        stats['sub_records']['pain_points']['total'] += len(pain_points)
        
        for pain_point in pain_points:
            try:
                params = (
                    content_id,
                    pain_point['pain_point'],
                    pain_point['category'], 
                    pain_point['severity'],
                    pain_point['evidence']
                )
                cursor.execute(sql, params)
                stats['sub_records']['pain_points']['success'] += 1
                
            except Exception as e:
                logger.error(f"存储痛点失败: {content_id}, 错误: {e}")
                stats['sub_records']['pain_points']['error'] += 1
    
    def _store_solved_problems(self, cursor, content_id: str, solved_problems: List[Dict[str, Any]], stats: Dict):
        """存储解决方案数据"""
        if not solved_problems:
            return
            
        sql = f"""
        INSERT INTO {self.tables['solved_problems']} (
            content_id, problem, solution, satisfaction
        ) VALUES (%s, %s, %s, %s)
        """
        
        stats['sub_records']['solved_problems']['total'] += len(solved_problems)
        
        for problem in solved_problems:
            try:
                params = (
                    content_id,
                    problem['problem'],
                    problem['solution'],
                    problem['satisfaction']
                )
                cursor.execute(sql, params)
                stats['sub_records']['solved_problems']['success'] += 1
                
            except Exception as e:
                logger.error(f"存储解决方案失败: {content_id}, 错误: {e}")
                stats['sub_records']['solved_problems']['error'] += 1
    
    def _store_user_needs(self, cursor, content_id: str, user_needs: List[Dict[str, Any]], stats: Dict):
        """存储用户需求数据"""
        if not user_needs:
            return
            
        sql = f"""
        INSERT INTO {self.tables['user_needs']} (
            content_id, need, priority, need_type
        ) VALUES (%s, %s, %s, %s)
        """
        
        stats['sub_records']['user_needs']['total'] += len(user_needs)
        
        for need in user_needs:
            try:
                params = (
                    content_id,
                    need['need'],
                    need['priority'],
                    need['type']  # 注意这里使用 'type' 而不是 'need_type'
                )
                cursor.execute(sql, params)
                stats['sub_records']['user_needs']['success'] += 1
                
            except Exception as e:
                logger.error(f"存储用户需求失败: {content_id}, 错误: {e}")
                stats['sub_records']['user_needs']['error'] += 1
    
    def _store_usage_scenarios(self, cursor, content_id: str, usage_scenarios: List[Dict[str, Any]], stats: Dict):
        """存储使用场景数据"""
        if not usage_scenarios:
            return
            
        sql = f"""
        INSERT INTO {self.tables['usage_scenarios']} (
            content_id, scenario
        ) VALUES (%s, %s)
        """
        
        stats['sub_records']['usage_scenarios']['total'] += len(usage_scenarios)
        
        for scenario in usage_scenarios:
            try:
                # 只存储 scenario 字段，忽略 frequency 和 pain_intensity
                params = (
                    content_id,
                    scenario['scenario']
                )
                cursor.execute(sql, params)
                stats['sub_records']['usage_scenarios']['success'] += 1
                
                # 记录被忽略的字段（用于调试）
                ignored_fields = []
                if 'frequency' in scenario:
                    ignored_fields.append('frequency')
                if 'pain_intensity' in scenario:
                    ignored_fields.append('pain_intensity')
                    
                if ignored_fields:
                    logger.debug(f"使用场景 {content_id} 忽略了字段: {ignored_fields}")
                
            except Exception as e:
                logger.error(f"存储使用场景失败: {content_id}, 错误: {e}")
                stats['sub_records']['usage_scenarios']['error'] += 1
    
    def _store_brand_mentions(self, cursor, content_id: str, brands: List[str], stats: Dict):
        """存储品牌提及数据"""
        if not brands:
            return
            
        sql = f"""
        INSERT INTO {self.tables['brand_mentions']} (
            content_id, brand_name, mention_order
        ) VALUES (%s, %s, %s)
        """
        
        stats['sub_records']['brand_mentions']['total'] += len(brands)
        
        for i, brand in enumerate(brands, 1):
            try:
                params = (content_id, brand, i)
                cursor.execute(sql, params)
                stats['sub_records']['brand_mentions']['success'] += 1
                
            except Exception as e:
                logger.error(f"存储品牌提及失败: {content_id}, 错误: {e}")
                stats['sub_records']['brand_mentions']['error'] += 1
    
    def _store_product_models(self, cursor, content_id: str, models: List[str], stats: Dict):
        """存储产品型号数据"""
        if not models:
            return
            
        sql = f"""
        INSERT INTO {self.tables['product_models']} (
            content_id, product_model, mention_order
        ) VALUES (%s, %s, %s)
        """
        
        stats['sub_records']['product_models']['total'] += len(models)
        
        for i, model in enumerate(models, 1):
            try:
                params = (content_id, model, i)
                cursor.execute(sql, params)
                stats['sub_records']['product_models']['success'] += 1
                
            except Exception as e:
                logger.error(f"存储产品型号失败: {content_id}, 错误: {e}")
                stats['sub_records']['product_models']['error'] += 1
    
    def _store_emotional_keywords(self, cursor, content_id: str, keywords: List[str], stats: Dict):
        """存储情感关键词数据"""
        if not keywords:
            return
            
        sql = f"""
        INSERT INTO {self.tables['emotional_keywords']} (
            content_id, keyword, keyword_order
        ) VALUES (%s, %s, %s)
        """
        
        stats['sub_records']['emotional_keywords']['total'] += len(keywords)
        
        for i, keyword in enumerate(keywords, 1):
            try:
                params = (content_id, keyword, i)
                cursor.execute(sql, params)
                stats['sub_records']['emotional_keywords']['success'] += 1
                
            except Exception as e:
                logger.error(f"存储情感关键词失败: {content_id}, 错误: {e}")
                stats['sub_records']['emotional_keywords']['error'] += 1
    
    def _store_post_tags(self, cursor, content_id: str, tags: List[str], stats: Dict):
        """存储帖子标签数据"""
        if not tags:
            return
            
        sql = f"""
        INSERT INTO {self.tables['post_tags']} (
            content_id, tag_name, tag_order
        ) VALUES (%s, %s, %s)
        """
        
        stats['sub_records']['post_tags']['total'] += len(tags)
        
        for i, tag in enumerate(tags, 1):
            try:
                params = (content_id, tag, i)
                cursor.execute(sql, params)
                stats['sub_records']['post_tags']['success'] += 1
                
            except Exception as e:
                logger.error(f"存储帖子标签失败: {content_id}, 错误: {e}")
                stats['sub_records']['post_tags']['error'] += 1
    
    def get_pain_analysis_stats(self, analysis_batch: Optional[str] = None) -> Dict[str, Any]:
        """获取痛点分析统计信息"""
        try:
            where_clause = ""
            params = ()
            
            if analysis_batch:
                where_clause = " WHERE analysis_batch = %s"
                params = (analysis_batch,)
            
            # 基础统计
            main_stats_sql = f"""
            SELECT 
                COUNT(*) as total_contents,
                SUM(CASE WHEN content_type = 'post' THEN 1 ELSE 0 END) as posts_count,
                SUM(CASE WHEN content_type = 'comment' THEN 1 ELSE 0 END) as comments_count,
                SUM(CASE WHEN overall_sentiment = '正面' THEN 1 ELSE 0 END) as positive_sentiment_count,
                SUM(CASE WHEN overall_sentiment = '负面' THEN 1 ELSE 0 END) as negative_sentiment_count,
                SUM(CASE WHEN overall_sentiment = '中性' THEN 1 ELSE 0 END) as neutral_sentiment_count
            FROM {self.main_table} {where_clause}
            """
            
            main_stats = db_manager.execute_query(main_stats_sql, params)
            
            if not main_stats:
                return {'error': '获取统计信息失败'}
            
            result = main_stats[0]
            
            # 获取痛点统计
            pain_stats_sql = f"""
            SELECT COUNT(*) as total_pain_points
            FROM {self.tables['pain_points']} pp
            JOIN {self.main_table} pa ON pp.content_id = pa.content_id
            {where_clause}
            """
            
            pain_stats = db_manager.execute_query(pain_stats_sql, params)
            result['total_pain_points'] = pain_stats[0]['total_pain_points'] if pain_stats else 0
            
            # 获取高优先级需求统计
            need_stats_sql = f"""
            SELECT COUNT(*) as high_priority_needs
            FROM {self.tables['user_needs']} un
            JOIN {self.main_table} pa ON un.content_id = pa.content_id
            WHERE un.priority = '高' {' AND ' + where_clause[7:] if where_clause else ''}
            """
            
            need_stats = db_manager.execute_query(need_stats_sql, params)
            result['high_priority_needs'] = need_stats[0]['high_priority_needs'] if need_stats else 0
            
            result['generated_at'] = datetime.now().isoformat()
            
            return result
            
        except Exception as e:
            logger.error(f"获取痛点分析统计信息失败: {e}")
            return {'error': str(e)}
    
    def query_pain_analysis(self, conditions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """查询痛点分析数据"""
        try:
            where_conditions = []
            params = []
            
            # 构建WHERE条件
            if conditions.get('analysis_batch'):
                where_conditions.append("pa.analysis_batch = %s")
                params.append(conditions['analysis_batch'])
            
            if conditions.get('content_type'):
                where_conditions.append("pa.content_type = %s")
                params.append(conditions['content_type'])
            
            if conditions.get('sentiment'):
                where_conditions.append("pa.overall_sentiment = %s")
                params.append(conditions['sentiment'])
            
            where_clause = ""
            if where_conditions:
                where_clause = " WHERE " + " AND ".join(where_conditions)
            
            # 主查询
            sql = f"""
            SELECT pa.*, 
                   COUNT(pp.id) as pain_points_count,
                   COUNT(sp.id) as solved_problems_count,
                   COUNT(un.id) as user_needs_count
            FROM {self.main_table} pa
            LEFT JOIN {self.tables['pain_points']} pp ON pa.content_id = pp.content_id
            LEFT JOIN {self.tables['solved_problems']} sp ON pa.content_id = sp.content_id
            LEFT JOIN {self.tables['user_needs']} un ON pa.content_id = un.content_id
            {where_clause}
            GROUP BY pa.id
            ORDER BY pa.created_at DESC
            LIMIT %s OFFSET %s
            """
            
            limit = conditions.get('limit', 50)
            offset = conditions.get('offset', 0)
            params.extend([limit, offset])
            
            results = db_manager.execute_query(sql, params)
            
            return results
            
        except Exception as e:
            logger.error(f"查询痛点分析数据失败: {e}")
            return []
    
    def delete_analysis_batch(self, analysis_batch: str) -> bool:
        """删除指定批次的分析数据"""
        try:
            with db_manager.transaction() as cursor:
                # 获取该批次的所有content_id
                cursor.execute(f"SELECT content_id FROM {self.main_table} WHERE analysis_batch = %s", 
                              (analysis_batch,))
                content_ids = [row['content_id'] for row in cursor.fetchall()]
                
                if not content_ids:
                    logger.warning(f"批次 {analysis_batch} 不存在")
                    return False
                
                # 删除子表数据
                for table_name in self.tables.values():
                    if table_name != self.tables['summary_insights']:  # summary_insights 表单独处理
                        placeholders = ','.join(['%s'] * len(content_ids))
                        cursor.execute(f"DELETE FROM {table_name} WHERE content_id IN ({placeholders})",
                                     content_ids)
                
                # 删除主表数据
                cursor.execute(f"DELETE FROM {self.main_table} WHERE analysis_batch = %s", 
                              (analysis_batch,))
                
                logger.info(f"成功删除批次 {analysis_batch} 的所有数据")
                return True
                
        except Exception as e:
            logger.error(f"删除批次 {analysis_batch} 失败: {e}")
            return False

# 全局仓库实例
pain_analysis_repository = PainAnalysisRepository()
