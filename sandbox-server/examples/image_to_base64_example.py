"""
图片转base64接口测试示例
"""
import asyncio
import httpx
import json
from typing import Optional

# API配置
API_BASE_URL = "http://localhost:8000"  # 根据实际部署调整
IMAGE_API_URL = f"{API_BASE_URL}/api/image"

# 测试图片URL（使用您提供的小红书图片链接）
TEST_IMAGE_URL = "https://xiaohongshu-images.bj.bcebos.com/shared/28/282c1ae75091e244f83b23661aa82a56.jpg?authorization=bce-auth-v1/5ac46f52990e11f090f3d3e7f345b0d9/2025-09-24T06%3A18%3A57Z/300/host/8133b2ec0cdc165cf511ee13890f1a044f3e6ef20cc5853949f8f85bec175c5a&x-bce-security-token=ZjkyZmQ2YmQxZTQ3NDcyNjk0ZTg1ZjYyYjlkZjNjODB8AAAAAAGHAADIE%2BPRQSpRgGMnUerzLrv5e4De9oTnPayu0OcasWL3MjEsJ%2BwRhLTNQa6H6BpVXe4CpaO0DhLCLgZPzi8tSVEwRyUI5Uhv5U7cFFNY6NUMO9r%2BkwxMCzCQDVvd2lewG%2BUlH%2BLZtgujkCfZEtkWpj8WH3YnbvJagDOwKSFD03RWc39USAkvPUSor5GxsxxnCcgsSadalFBhpOVWyaGbaU9fPAXQ9ZMjd6ZbL6OhbCw0wMEAp4NtjZMDw8MCVjyNtaa162k6GaHYmmwM8rFUdpgBXYRLIWzOe0dr5gO/2aIpALs7FzC/5guJs%2Bd3PihKttPTmUu4nlU4MstWZF4KKstPP0c4Euj/eq3nODpao4MPhUSTUcHRjrtGsFl3eHKaZgKhapRe%2BPJGg4M8O1oU46bvPO9/1uY6yFYSTLFfEmW91bQacTn2J6nIvzrpQNQq%2BpNxIq2SNSgHGPLv9JkRLV/yz99w179BhqVDRVZuHKVOsGXbZlpZ9F6d4x3ibv4E%2BMYu%2BgG2VoHLNACTrstq4kh5YNG422WUMqmOgOPQNfgDNNfKe9NMVFeNkMVUg1Y6prtWauS8sbZpO7k0umQu3vsi"

async def test_image_to_base64(
    image_url: str = TEST_IMAGE_URL,
    output_format: str = "PNG",
    max_size: Optional[int] = None,
    quality: int = 95
):
    """
    测试图片转base64接口
    
    Args:
        image_url: 图片URL
        output_format: 输出格式 (PNG, JPEG, WEBP)
        max_size: 最大尺寸限制
        quality: JPEG质量
    """
    print("🖼️ 图片转base64接口测试")
    print(f"📎 图片URL: {image_url[:100]}...")
    print(f"🎨 输出格式: {output_format}")
    print(f"📏 最大尺寸: {max_size or '无限制'}")
    print(f"🎯 质量设置: {quality}")
    print("-" * 60)
    
    # 构建请求数据
    request_data = {
        "image_url": image_url,
        "format": output_format,
        "quality": quality,
        "timeout": 30
    }
    
    if max_size:
        request_data["max_size"] = max_size
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            print("⏳ 发送请求...")
            response = await client.post(
                f"{IMAGE_API_URL}/url-to-base64",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )
            
            print(f"📡 HTTP状态码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print("✅ 转换成功!")
                
                # 显示结果信息
                if result.get("success"):
                    data = result.get("data", {})
                    image_info = data.get("image_info", {})
                    
                    print(f"⏱️  执行时间: {result.get('execution_time', 0):.2f}秒")
                    print(f"📊 原始格式: {image_info.get('original_format', 'Unknown')}")
                    print(f"📐 原始尺寸: {image_info.get('original_size', 'Unknown')}")
                    print(f"🎨 最终格式: {image_info.get('final_format', 'Unknown')}")
                    print(f"📏 最终尺寸: {image_info.get('final_size', 'Unknown')}")
                    print(f"💾 文件大小: {image_info.get('file_size_bytes', 0):,} bytes")
                    
                    # Base64相关信息
                    base64_data = data.get("base64_data", "")
                    base64_length = len(base64_data)
                    
                    print(f"📝 Base64长度: {base64_length:,} 字符")
                    print(f"🔗 Data URL前缀: {base64_data[:50]}...")
                    
                    # 显示部分base64数据（用于验证）
                    print("\n📋 Base64示例（前200字符）:")
                    print(base64_data[:200] + "...")
                    
                    return {
                        "success": True,
                        "base64_data": base64_data,
                        "image_info": image_info
                    }
                else:
                    print(f"❌ 转换失败: {result.get('message', 'Unknown error')}")
                    return {"success": False, "error": result.get("message")}
            else:
                print(f"❌ HTTP请求失败: {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"错误详情: {error_detail}")
                except:
                    print(f"响应内容: {response.text}")
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
    except Exception as e:
        print(f"❌ 请求异常: {str(e)}")
        return {"success": False, "error": str(e)}

async def test_supported_formats():
    """测试获取支持格式的接口"""
    print("\n🎨 获取支持的图片格式...")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{IMAGE_API_URL}/supported-formats")
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    data = result.get("data", {})
                    print("✅ 支持的格式:")
                    
                    for format_info in data.get("output_formats", []):
                        format_name = format_info.get("format")
                        description = format_info.get("description")
                        transparency = "✓" if format_info.get("supports_transparency") else "✗"
                        quality = "✓" if format_info.get("supports_quality") else "✗"
                        
                        print(f"  • {format_name}: {description}")
                        print(f"    透明度支持: {transparency}, 质量控制: {quality}")
                else:
                    print(f"❌ 获取格式失败: {result.get('message')}")
            else:
                print(f"❌ HTTP请求失败: {response.status_code}")
                
    except Exception as e:
        print(f"❌ 请求异常: {str(e)}")

async def test_health_check():
    """测试健康检查接口"""
    print("\n💚 图片服务健康检查...")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{IMAGE_API_URL}/health")
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    data = result.get("data", {})
                    print(f"✅ 服务状态: {data.get('status', 'Unknown')}")
                    print(f"🏷️  服务版本: {data.get('version', 'Unknown')}")
                    print(f"⭐ 支持功能: {', '.join(data.get('features', []))}")
                else:
                    print(f"❌ 健康检查失败: {result.get('message')}")
            else:
                print(f"❌ HTTP请求失败: {response.status_code}")
                
    except Exception as e:
        print(f"❌ 请求异常: {str(e)}")

async def run_comprehensive_test():
    """运行综合测试"""
    print("🚀 开始图片转base64接口综合测试\n")
    
    # 1. 健康检查
    await test_health_check()
    
    # 2. 获取支持的格式
    await test_supported_formats()
    
    # 3. 测试PNG格式转换（默认）
    print("\n" + "="*60)
    print("测试 1: PNG格式转换（推荐用于图片质量）")
    result1 = await test_image_to_base64(
        image_url=TEST_IMAGE_URL,
        output_format="PNG",
        max_size=1920
    )
    
    # 4. 测试JPEG格式转换
    print("\n" + "="*60)
    print("测试 2: JPEG格式转换（推荐用于文件大小）")
    result2 = await test_image_to_base64(
        image_url=TEST_IMAGE_URL,
        output_format="JPEG",
        max_size=1920,
        quality=85
    )
    
    # 5. 测试小尺寸转换
    print("\n" + "="*60)
    print("测试 3: 小尺寸转换（用于缩略图）")
    result3 = await test_image_to_base64(
        image_url=TEST_IMAGE_URL,
        output_format="PNG",
        max_size=512
    )
    
    # 测试总结
    print("\n" + "="*60)
    print("🎯 测试总结:")
    tests = [
        ("PNG格式转换", result1),
        ("JPEG格式转换", result2), 
        ("小尺寸转换", result3)
    ]
    
    for test_name, result in tests:
        status = "✅ 成功" if result and result.get("success") else "❌ 失败"
        print(f"  • {test_name}: {status}")
    
    print("\n✨ 测试完成!")

if __name__ == "__main__":
    # 运行综合测试
    asyncio.run(run_comprehensive_test())
