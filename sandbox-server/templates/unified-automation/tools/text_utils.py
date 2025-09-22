"""精简的文本处理工具 - 通用功能类"""
import re
import json
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

class TextUtils:
    """精简的文本处理工具类"""
    
    def parse_html(self, html_content):
        """解析HTML并返回结构化数据"""
        try:
            if not html_content:
                return {"success": False, "message": "HTML内容为空"}
            
            soup = BeautifulSoup(html_content, 'lxml')
            
            # 提取各种结构化信息
            parsed_data = {
                    "title": soup.title.string if soup.title else "",
                "meta_description": "",
                "headings": [],
                "paragraphs": [],
                "links": [],
                "images": [],
                "text_content": soup.get_text(strip=True),
                "stats": {
                    "text_length": len(soup.get_text()),
                    "links_count": len(soup.find_all('a')),
                    "images_count": len(soup.find_all('img')),
                    "headings_count": len(soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']))
                }
            }
            
            # 提取meta描述
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc:
                parsed_data["meta_description"] = meta_desc.get('content', '')
            
            # 提取标题
            for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                parsed_data["headings"].append({
                    "level": heading.name,
                    "text": heading.get_text(strip=True)
                })
            
            # 提取段落
            for p in soup.find_all('p'):
                text = p.get_text(strip=True)
                if text:
                    parsed_data["paragraphs"].append(text)
            
            # 提取链接
            for link in soup.find_all('a', href=True):
                parsed_data["links"].append({
                    "text": link.get_text(strip=True),
                    "href": link['href']
                })
            
            # 提取图片
            for img in soup.find_all('img'):
                parsed_data["images"].append({
                    "src": img.get('src', ''),
                    "alt": img.get('alt', ''),
                    "title": img.get('title', '')
                })
            
            return {
                "success": True,
                "message": "HTML解析成功",
                "data": parsed_data
            }
        except Exception as e:
            return {"success": False, "message": f"HTML解析失败: {str(e)}"}
    
    def extract_text(self, html_content, selector):
        """通过CSS选择器提取文本"""
        try:
            soup = BeautifulSoup(html_content, 'lxml')
            elements = soup.select(selector)
            
            if not elements:
                return {
                    "success": True,
                    "message": f"未找到匹配的元素: {selector}",
                    "data": [],
                    "count": 0
                }
            
            # 提取文本内容
            texts = []
            for element in elements:
                text = element.get_text(strip=True)
                if text:  # 只保留非空文本
                    texts.append(text)
            
            return {
                "success": True,
                "message": f"文本提取成功: {len(texts)}条",
                "data": texts,
                "count": len(texts),
                "selector": selector
            }
        except Exception as e:
            return {"success": False, "message": f"文本提取失败: {str(e)}"}
    
    def filter_content(self, text_list, keywords, mode='any'):
        """根据关键词筛选内容"""
        try:
            if not text_list:
                return {
                    "success": True,
                    "message": "输入列表为空",
                    "data": [],
                    "count": 0
                }
            
            if not keywords:
                return {
                    "success": True,
                    "message": "关键词为空，返回全部内容",
                    "data": text_list,
                    "count": len(text_list)
                }
            
            filtered_results = []
            
            for text in text_list:
                text_lower = text.lower()
                keywords_lower = [kw.lower() for kw in keywords]
                
                if mode == 'any':
                    # 包含任意一个关键词
                    if any(keyword in text_lower for keyword in keywords_lower):
                        filtered_results.append(text)
                elif mode == 'all':
                    # 包含所有关键词
                    if all(keyword in text_lower for keyword in keywords_lower):
                        filtered_results.append(text)
                elif mode == 'exact':
                    # 精确匹配任意关键词
                    if any(keyword == text_lower for keyword in keywords_lower):
                        filtered_results.append(text)
                else:
                    return {"success": False, "message": f"不支持的筛选模式: {mode}"}
            
            return {
                "success": True,
                "message": f"内容筛选完成: {len(filtered_results)}/{len(text_list)}",
                "data": filtered_results,
                "count": len(filtered_results),
                "keywords": keywords,
                "mode": mode
            }
        except Exception as e:
            return {"success": False, "message": f"内容筛选失败: {str(e)}"}
    
    def clean_text(self, text):
        """清理和标准化文本"""
        try:
            if not text:
                return {
                    "success": True,
                    "message": "文本为空",
                    "data": "",
                    "changes": []
                }
            
            original_text = text
            changes = []
            
            # 1. 去除HTML标签
            if '<' in text and '>' in text:
                clean_text = BeautifulSoup(text, 'lxml').get_text()
                if clean_text != text:
                    changes.append("移除HTML标签")
                    text = clean_text
            
            # 2. 标准化空白字符
            # 将多个空白字符替换为单个空格
            original_whitespace = text
            text = re.sub(r'\s+', ' ', text)
            if text != original_whitespace:
                changes.append("标准化空白字符")
            
            # 3. 去除首尾空白
            text = text.strip()
            if text != original_whitespace.strip():
                changes.append("去除首尾空白")
            
            # 4. 去除特殊控制字符
            control_chars = re.compile(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]')
            cleaned = control_chars.sub('', text)
            if cleaned != text:
                changes.append("移除控制字符")
                text = cleaned
            
            # 5. 标准化引号
            text = text.replace('"', '"').replace('"', '"')
            text = text.replace(''', "'").replace(''', "'")
            
            return {
                "success": True,
                "message": "文本清理完成",
                "data": text,
                "original_length": len(original_text),
                "cleaned_length": len(text),
                "changes": changes
            }
        except Exception as e:
            return {"success": False, "message": f"文本清理失败: {str(e)}"}
    
    def extract_links(self, html_content, base_url=None):
        """提取页面中的所有链接"""
        try:
            soup = BeautifulSoup(html_content, 'lxml')
            links = []
            
            # 提取所有<a>标签的href属性
            for link_element in soup.find_all('a', href=True):
                href = link_element['href']
                text = link_element.get_text(strip=True)
                
                # 处理相对链接
                if base_url and href:
                    try:
                        absolute_url = urljoin(base_url, href)
                    except:
                        absolute_url = href
                else:
                    absolute_url = href
                
                link_info = {
                    "url": absolute_url,
                    "text": text,
                    "original_href": href,
                    "is_external": self._is_external_link(absolute_url, base_url) if base_url else False
                }
                links.append(link_info)
            
            # 去重（基于URL）
            unique_links = []
            seen_urls = set()
            for link in links:
                if link["url"] not in seen_urls:
                    unique_links.append(link)
                    seen_urls.add(link["url"])
            
            return {
                "success": True,
                "message": f"链接提取完成: {len(unique_links)}个唯一链接",
                "data": unique_links,
                "count": len(unique_links),
                "total_found": len(links),
                "duplicates_removed": len(links) - len(unique_links)
            }
        except Exception as e:
            return {"success": False, "message": f"链接提取失败: {str(e)}"}
    
    def analyze_text(self, text):
        """基础文本分析：字数、关键信息等"""
        try:
            if not text:
                return {
                    "success": True,
                    "message": "文本为空",
                    "data": {
                        "char_count": 0,
                        "word_count": 0,
                        "line_count": 0,
                        "paragraph_count": 0
                    }
                }
            
            # 基础统计
            char_count = len(text)
            word_count = len(text.split())
            line_count = len(text.split('\n'))
            paragraph_count = len([p for p in text.split('\n\n') if p.strip()])
            
            # 提取数字
            numbers = re.findall(r'\d+', text)
            
            # 提取邮箱
            emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
            
            # 提取URL
            urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', text)
            
            # 提取中文字符数
            chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
            
            # 提取英文单词数
            english_words = len(re.findall(r'\b[A-Za-z]+\b', text))
            
            # 常见词频分析（简单版本）
            words = re.findall(r'\b\w+\b', text.lower())
            word_freq = {}
            for word in words:
                if len(word) > 2:  # 只统计长度大于2的词
                    word_freq[word] = word_freq.get(word, 0) + 1
            
            # 取频率最高的10个词
            top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]
            
            analysis_result = {
                "basic_stats": {
                    "char_count": char_count,
                    "word_count": word_count,
                    "line_count": line_count,
                    "paragraph_count": paragraph_count,
                    "chinese_chars": chinese_chars,
                    "english_words": english_words
                },
                "extracted_info": {
                    "numbers": numbers[:20],  # 最多返回20个数字
                    "emails": emails[:10],    # 最多返回10个邮箱
                    "urls": urls[:10],        # 最多返回10个URL
                },
                "word_frequency": {
                    "top_words": top_words,
                    "unique_words": len(word_freq)
                },
                "text_metrics": {
                    "avg_word_length": sum(len(word) for word in words) / len(words) if words else 0,
                    "avg_sentence_length": char_count / max(text.count('.') + text.count('!') + text.count('?'), 1)
                }
            }
            
            return {
                "success": True,
                "message": "文本分析完成",
                "data": analysis_result
            }
        except Exception as e:
            return {"success": False, "message": f"文本分析失败: {str(e)}"}
    
    def _is_external_link(self, url, base_url):
        """判断是否为外部链接"""
        try:
            if not url or not base_url:
                return False
            
            url_domain = urlparse(url).netloc
            base_domain = urlparse(base_url).netloc
            
            return url_domain != base_domain and url_domain != ""
        except:
            return False