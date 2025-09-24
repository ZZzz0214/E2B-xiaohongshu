import json
import re

def main(response_body: str) -> dict:
    """
    将数据库查询结果转换为可迭代的数组格式
    """
    
    try:
        # 直接处理输入字符串，去除转义字符
        text_content = response_body.replace('\\n', '\n').replace('\\"', '"')
        
        # 提取JSON对象列表
        titles_data = []
        
        if text_content:
            # 分割文本，去除Schema信息
            lines = text_content.split('\n')
            
            for line in lines:
                line = line.strip()
                # 跳过Schema行和空行
                if not line or line.startswith("Schema:"):
                    continue
                
                # 尝试解析每行的JSON
                try:
                    json_obj = json.loads(line)
                    if isinstance(json_obj, dict) and "title" in json_obj:
                        titles_data.append({
                            "title": json_obj.get("title", ""),
                            "post_id": json_obj.get("post_id", ""),
                            "author_name": json_obj.get("author_name", ""),
                            "classification": json_obj.get("classification", ""),
                            "created_at": json_obj.get("created_at", ""),
                            "index": len(titles_data) + 1
                        })
                except json.JSONDecodeError:
                    continue
        
        # 如果没有找到数据，尝试正则匹配兜底
        if not titles_data:
            # 使用正则表达式提取JSON对象
            json_pattern = r'\{[^}]*"title"[^}]*\}'
            matches = re.findall(json_pattern, text_content)
            
            for match in matches:
                try:
                    json_obj = json.loads(match)
                    titles_data.append({
                        "title": json_obj.get("title", ""),
                        "post_id": json_obj.get("post_id", ""),
                        "author_name": json_obj.get("author_name", ""),
                        "classification": json_obj.get("classification", ""),
                        "created_at": json_obj.get("created_at", ""),
                        "index": len(titles_data) + 1
                    })
                except:
                    continue
        
        # 提取纯标题字符串列表
        titles_only = [item["title"] for item in titles_data]
        
        result = {
            "titles_array": titles_only,  # 纯字符串数组 Array[String]
            "total_count": len(titles_data),
            "status": "success" if titles_data else "no_data"
        }
        
        return result
        
    except Exception as e:
        return {
            "titles_array": [],
            "total_count": 0,
            "status": "error"
        }
