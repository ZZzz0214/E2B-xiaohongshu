"""
小红书痛点分析API调用示例
演示如何使用痛点分析API接口存储和查询数据
"""
import requests
import json
from typing import Dict, Any

# API基础URL
BASE_URL = "http://localhost:8000/api"

class PainAnalysisAPIClient:
    """痛点分析API客户端"""
    
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
    
    def store_pain_analysis_data(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        存储痛点分析数据
        
        Args:
            analysis_data: 痛点分析数据（例子.md中的JSON格式）
        
        Returns:
            API响应结果
        """
        url = f"{self.base_url}/pain-analysis/store"
        
        try:
            response = self.session.post(
                url, 
                json=analysis_data,
                headers={'Content-Type': 'application/json'},
                timeout=60
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'API请求失败: {str(e)}',
                'status_code': getattr(e.response, 'status_code', None)
            }
    
    def get_pain_analysis_stats(self, analysis_batch: str = None) -> Dict[str, Any]:
        """获取痛点分析统计信息"""
        url = f"{self.base_url}/pain-analysis/stats"
        params = {'analysis_batch': analysis_batch} if analysis_batch else {}
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'API请求失败: {str(e)}',
                'status_code': getattr(e.response, 'status_code', None)
            }
    
    def query_pain_analysis_data(self, **kwargs) -> Dict[str, Any]:
        """查询痛点分析数据"""
        url = f"{self.base_url}/pain-analysis/query"
        
        # 过滤None值参数
        params = {k: v for k, v in kwargs.items() if v is not None}
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'API请求失败: {str(e)}',
                'status_code': getattr(e.response, 'status_code', None)
            }
    
    def get_analysis_batches(self) -> Dict[str, Any]:
        """获取所有分析批次"""
        url = f"{self.base_url}/pain-analysis/batches"
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'API请求失败: {str(e)}',
                'status_code': getattr(e.response, 'status_code', None)
            }
    
    def get_content_detail(self, content_id: str) -> Dict[str, Any]:
        """获取特定内容的详细分析数据"""
        url = f"{self.base_url}/pain-analysis/content/{content_id}"
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'API请求失败: {str(e)}',
                'status_code': getattr(e.response, 'status_code', None)
            }
    
    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        url = f"{self.base_url}/pain-analysis/health"
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'API请求失败: {str(e)}',
                'status_code': getattr(e.response, 'status_code', None)
            }

def load_example_data() -> Dict[str, Any]:
    """加载例子.md中的示例数据"""
    # 这是从例子.md中提取的推荐帖子数据
    example_data = {
        "pain_point_analysis": [
            {
                "content_id": "67d668d7000000001d01a077",
                "content_type": "post",
                "user_name": "可爱小鱼鱼.",
                "content_snippet": "巨软糯！巨舒服！超爱的神仙内裤！\n女孩子的东西都要精挑细选的\n尤其这种贴身衣物 更是要谨慎\n这次让我买到了神仙内裤！\n软软糯糯的手感也太舒服了吧\n纯棉的穿着也很安心\n弹力也蛮大的\n舒适透气 穿着也不会勒\n#女士内裤[话题]# #内裤分享[话题]# #纯棉内裤[话题]# #棉诗莼[话题]# #夏天女生穿什么内裤[话题]# #贴身衣物[话题]# #纯棉材质柔软亲肤[话题]# #女孩子专属[话题]# #有谁懂舒适的内衣👙[话题]#",
                "tags": ["女士内裤", "内裤分享", "纯棉内裤", "棉诗莼", "夏天女生穿什么内裤", "贴身衣物", "纯棉材质柔软亲肤", "女孩子专属", "有谁懂舒适的内衣👙"],
                "brand_mentions": ["棉诗莼"],
                "product_models": [],
                "identified_pain_points": [
                    {
                        "pain_point": "贴身衣物选择困难",
                        "category": "服务",
                        "severity": "中等",
                        "evidence": "尤其这种贴身衣物 更是要谨慎"
                    }
                ],
                "solved_problems": [
                    {
                        "problem": "内裤舒适度不足",
                        "solution": "纯棉材质，软糯手感，弹力大，舒适透气",
                        "satisfaction": "非常满意"
                    },
                    {
                        "problem": "内裤勒痕问题",
                        "solution": "穿着不会勒",
                        "satisfaction": "非常满意"
                    }
                ],
                "user_needs": [
                    {
                        "need": "舒适透气的内裤",
                        "priority": "高",
                        "type": "功能性"
                    },
                    {
                        "need": "安全放心的贴身衣物",
                        "priority": "高",
                        "type": "情感性"
                    }
                ],
                "usage_scenarios": [
                    {
                        "scenario": "日常穿着",
                        "frequency": "高频",
                        "pain_intensity": "弱"
                    },
                    {
                        "scenario": "夏季穿着",
                        "frequency": "中频",
                        "pain_intensity": "中"
                    }
                ],
                "emotional_analysis": {
                    "overall_sentiment": "正面",
                    "intensity_score": 0.95,
                    "emotional_keywords": ["超爱", "神仙内裤", "太舒服", "安心"],
                    "user_satisfaction": "非常满意"
                },
                "commercial_insights": {
                    "purchase_intent": "高",
                    "recommendation_likelihood": "会推荐",
                    "competitor_comparison": "无",
                    "price_sensitivity": "中等"
                }
            }
        ],
        "summary_insights": {
            "high_frequency_pain_points": ["购买渠道不明确", "材质不明确", "腰型信息不明确"],
            "scenario_pain_ranking": {
                "日常穿着": ["舒适度不足", "勒痕问题"],
                "夏季穿着": ["透气性不足"]
            },
            "brand_pain_correlation": {
                "棉诗莼": ["材质舒适度", "设计美观"]
            },
            "urgent_needs": ["便捷购买方式", "明确产品信息"],
            "market_opportunities": ["纯棉舒适内裤市场", "设计感内裤市场"]
        }
    }
    
    return example_data

def main():
    """主函数，演示API的使用"""
    print("🚀 开始痛点分析API示例演示")
    
    # 创建API客户端
    client = PainAnalysisAPIClient()
    
    # 1. 健康检查
    print("\n1️⃣ 执行健康检查...")
    health_result = client.health_check()
    print(f"健康检查结果: {health_result.get('success', False)}")
    
    if not health_result.get('success'):
        print("❌ 服务不可用，请检查服务器状态")
        return
    
    # 2. 加载示例数据
    print("\n2️⃣ 加载示例数据...")
    example_data = load_example_data()
    print(f"示例数据包含 {len(example_data['pain_point_analysis'])} 条内容分析")
    
    # 3. 存储痛点分析数据
    print("\n3️⃣ 存储痛点分析数据...")
    store_result = client.store_pain_analysis_data(example_data)
    
    if store_result.get('success'):
        print(f"✅ 数据存储成功: {store_result.get('message')}")
        analysis_batch = store_result.get('analysis_batch')
        print(f"分析批次: {analysis_batch}")
        
        # 4. 获取统计信息
        print("\n4️⃣ 获取统计信息...")
        stats_result = client.get_pain_analysis_stats(analysis_batch)
        
        if stats_result.get('success'):
            stats = stats_result['data']['statistics']
            print(f"✅ 统计信息:")
            print(f"   - 总内容数: {stats.get('total_contents', 0)}")
            print(f"   - 帖子数: {stats.get('posts_count', 0)}")
            print(f"   - 评论数: {stats.get('comments_count', 0)}")
            print(f"   - 正面情感: {stats.get('positive_sentiment_count', 0)}")
            print(f"   - 负面情感: {stats.get('negative_sentiment_count', 0)}")
            print(f"   - 中性情感: {stats.get('neutral_sentiment_count', 0)}")
        
        # 5. 查询数据
        print("\n5️⃣ 查询痛点分析数据...")
        query_result = client.query_pain_analysis_data(
            analysis_batch=analysis_batch,
            content_type="post",
            limit=5
        )
        
        if query_result.get('success'):
            results = query_result['data']['results']
            print(f"✅ 查询到 {len(results)} 条记录")
            
            # 6. 获取内容详情
            if results:
                content_id = results[0]['content_id']
                print(f"\n6️⃣ 获取内容详情: {content_id}")
                detail_result = client.get_content_detail(content_id)
                
                if detail_result.get('success'):
                    main_data = detail_result['data']['main_data']
                    related_data = detail_result['data']['related_data']
                    print(f"✅ 内容详情获取成功:")
                    print(f"   - 用户: {main_data.get('user_name')}")
                    print(f"   - 情感: {main_data.get('overall_sentiment')}")
                    print(f"   - 痛点数: {len(related_data.get('pain_points', []))}")
                    print(f"   - 需求数: {len(related_data.get('user_needs', []))}")
        
        # 7. 获取批次列表
        print("\n7️⃣ 获取分析批次列表...")
        batches_result = client.get_analysis_batches()
        
        if batches_result.get('success'):
            batches = batches_result['data']['batches']
            print(f"✅ 共有 {len(batches)} 个分析批次")
            for batch in batches[:3]:  # 显示前3个
                print(f"   - {batch['analysis_batch']}: {batch['total_contents']} 条内容")
    
    else:
        print(f"❌ 数据存储失败: {store_result.get('message')}")
    
    print("\n🎉 痛点分析API示例演示完成")

if __name__ == "__main__":
    main()
