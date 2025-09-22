#!/usr/bin/env python3
"""
小红书分析器 - 专用于小红书平台的数据提取和分析
基于虚拟滚动突破技术，实现完整的帖子和评论分析
"""

import json
import asyncio
import logging
from typing import Dict, Any, List, Optional

# 导入标签页管理相关类型
try:
    from .tab_manager import TabType
except ImportError:
    # 如果tab_manager不可用，定义一个空的TabType占位符
    class TabType:
        USER_PROFILE = "user_profile"

class XiaohongshuAnalyzer:
    """小红书专用分析器 - 直接依赖 BrowserService 基础能力"""
    
    def __init__(self, browser_service):
        self.browser = browser_service  # 依赖简化的 BrowserService
        self.logger = logging.getLogger(__name__)
    
    def generate_auto_scroll_script(self) -> str:
        """生成自动滚动脚本，加载所有帖子到全局状态"""
        return """
// === 小红书自动滚动加载所有帖子 ===
async function autoScrollLoadAllPosts() {
    console.log("🚀 开始小红书自动滚动加载所有帖子...");
    
    let lastCount = 0;
    let noNewContentCount = 0;
    const maxNoNewRounds = 3;
    let totalScrolls = 0;
    const maxScrolls = 50; // 防止无限滚动
    
    try {
        while (noNewContentCount < maxNoNewRounds && totalScrolls < maxScrolls) {
            // 滚动到底部
            window.scrollTo(0, document.body.scrollHeight);
            totalScrolls++;
            
            // 等待加载
            await new Promise(resolve => setTimeout(resolve, 2000));
            
            // 检查帖子数量
            try {
                // 尝试从全局状态获取
                let currentPosts = [];
                let currentCount = 0;
                
                // 方法1: 尝试从window.__INITIAL_STATE__获取
                if (window.__INITIAL_STATE__ && 
                    window.__INITIAL_STATE__.search && 
                    window.__INITIAL_STATE__.search.feeds && 
                    window.__INITIAL_STATE__.search.feeds._rawValue) {
                    currentPosts = window.__INITIAL_STATE__.search.feeds._rawValue;
                    currentCount = currentPosts.length;
                    console.log(`📊 [全局状态] 当前帖子数: ${currentCount} (新增: ${currentCount - lastCount})`);
                } 
                // 方法2: 从DOM计算
                else {
                    const noteElements = document.querySelectorAll('.note-item, section.note-item, [data-index]');
                    currentCount = noteElements.length;
                    console.log(`📊 [DOM计算] 当前帖子数: ${currentCount} (新增: ${currentCount - lastCount})`);
                }
                
                if (currentCount === lastCount) {
                    noNewContentCount++;
                    console.log(`⏳ 无新增内容 (${noNewContentCount}/${maxNoNewRounds}) - 滚动次数: ${totalScrolls}`);
                } else {
                    noNewContentCount = 0;
                    console.log(`✅ 新增了 ${currentCount - lastCount} 个帖子 - 滚动次数: ${totalScrolls}`);
                }
                
                lastCount = currentCount;
                
            } catch (error) {
                console.log("❌ 获取帖子数据失败:", error);
                noNewContentCount++;
            }
        }
        
        console.log(`🎯 滚动完成，总共加载了 ${lastCount} 个帖子，总滚动次数: ${totalScrolls}`);
        
        const result = {
            success: true,
            total_posts: lastCount,
            total_scrolls: totalScrolls,
            message: "成功加载 " + lastCount + " 个帖子 (滚动" + totalScrolls + "次)"
        };
        console.log("📤 准备返回结果:", JSON.stringify(result));
        return result;
        
    } catch (error) {
        console.log("❌ 自动滚动过程中发生错误:", error);
        let errorMessage = '未知错误';
        try {
            errorMessage = error.message || error.toString() || '未知错误';
        } catch (e) {
            errorMessage = '错误处理异常';
        }
        
        const result = {
            success: false,
            message: "滚动失败: " + errorMessage,
            total_posts: (typeof lastCount !== 'undefined') ? lastCount : 0,
            total_scrolls: (typeof totalScrolls !== 'undefined') ? totalScrolls : 0
        };
        console.log("📤 准备返回错误结果:", JSON.stringify(result));
        return result;
    }
}

// 执行滚动并返回结果
(async function() {
    return await autoScrollLoadAllPosts();
})();
        """
    
    def generate_click_post_script(self, title: str) -> str:
        """生成通过标题点击帖子的脚本（支持搜索页面和用户主页）"""
        # 转义标题中的引号和特殊字符
        escaped_title = title.replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`')
        return f"""
// === 通用版：通过标题点击小红书帖子（支持搜索页面和用户主页）===
async function clickPostByTitle(targetTitle) {{
    console.log(`🎯 尝试点击标题为 "${{targetTitle}}" 的帖子`);
    
    try {{
        // 第一步：根据页面类型获取帖子数据
        let allPosts = [];
        const currentUrl = window.location.href;
        
        console.log("📍 当前页面:", currentUrl);
        
        if (currentUrl.includes('/search')) {{
            // 搜索页面逻辑
            console.log("🔍 检测到搜索页面，使用搜索数据源");
            if (window.__INITIAL_STATE__ && 
                window.__INITIAL_STATE__.search && 
                window.__INITIAL_STATE__.search.feeds && 
                window.__INITIAL_STATE__.search.feeds._rawValue) {{
                
                allPosts = window.__INITIAL_STATE__.search.feeds._rawValue;
                console.log(`📊 [搜索页面] 总帖子数: ${{allPosts.length}}`);
            }} else {{
                return {{
                    success: false,
                    message: "无法获取搜索页面数据"
                }};
            }}
        }} else if (currentUrl.includes('/user/profile/')) {{
            // 用户主页逻辑  
            console.log("👤 检测到用户主页，使用用户数据源");
            if (window.__INITIAL_STATE__ && 
                window.__INITIAL_STATE__.user && 
                window.__INITIAL_STATE__.user.notes) {{
                
                const notesData = window.__INITIAL_STATE__.user.notes._rawValue || window.__INITIAL_STATE__.user.notes;
                
                // 用户主页的特殊数据结构：notes[0]才是实际帖子数组
                if (Array.isArray(notesData) && notesData.length > 0 && Array.isArray(notesData[0])) {{
                    allPosts = notesData[0];
                    console.log(`📊 [用户主页] 总帖子数: ${{allPosts.length}}`);
                }} else {{
                    return {{
                        success: false,
                        message: "用户主页帖子数据结构异常"
                    }};
                }}
            }} else {{
                return {{
                    success: false,
                    message: "无法获取用户主页数据"
                }};
            }}
        }} else {{
            return {{
                success: false,
                message: "不支持的页面类型，请在搜索页面或用户主页使用"
            }};
        }}
        
        if (allPosts.length === 0) {{
            return {{
                success: false,
                message: "帖子数据为空"
            }};
        }}
        
        // 第二步：精确匹配查找标题
        let matchedIndex = -1;
        
        console.log("🔍 开始精确匹配查找帖子...");
        
        for (let i = 0; i < allPosts.length; i++) {{
            const post = allPosts[i];
            let postTitle = '';
            
            // 获取帖子标题
            if (post.noteCard && post.noteCard.displayTitle) {{
                postTitle = post.noteCard.displayTitle;
            }}
            
            if (postTitle) {{
                console.log(`📄 帖子 ${{i}}: "${{postTitle}}"`);
                
                // 精确匹配
                if (postTitle === targetTitle) {{
                    matchedIndex = i;
                    console.log(`✅ 精确匹配找到帖子: "${{postTitle}}"`);
                    break;
                }}
            }}
        }}
        
        if (matchedIndex === -1) {{
            console.log(`❌ 未找到精确匹配 "${{targetTitle}}" 的帖子`);
            return {{
                success: false,
                message: `未找到精确匹配的帖子: "${{targetTitle}}"`
            }};
        }}
        
        console.log(`📍 匹配的帖子全局索引: ${{matchedIndex}}`);
        
        // 第三步：使用现有的索引点击逻辑
        return await clickPostByGlobalIndex(matchedIndex, targetTitle, allPosts.length);
        
    }} catch (error) {{
        console.log(`❌ 通过标题点击帖子失败: ${{error.message}}`);
        return {{
            success: false,
            message: `通过标题点击帖子失败: ${{error.message}}`
        }};
    }}
}}

// === 索引点击逻辑（支持搜索页面和用户主页）===
async function clickPostByGlobalIndex(globalIndex, targetTitle = null, totalPosts = null) {{
    console.log(`🎯 尝试点击全局索引 ${{globalIndex}} 的帖子`);
    
    try {{
        // 如果没有传入totalPosts，则根据页面类型重新获取
        if (totalPosts === null) {{
            const currentUrl = window.location.href;
            
            if (currentUrl.includes('/search')) {{
                if (window.__INITIAL_STATE__ && 
                    window.__INITIAL_STATE__.search && 
                    window.__INITIAL_STATE__.search.feeds && 
                    window.__INITIAL_STATE__.search.feeds._rawValue) {{
                    totalPosts = window.__INITIAL_STATE__.search.feeds._rawValue.length;
                }}
            }} else if (currentUrl.includes('/user/profile/')) {{
                if (window.__INITIAL_STATE__ && 
                    window.__INITIAL_STATE__.user && 
                    window.__INITIAL_STATE__.user.notes) {{
                    const notesData = window.__INITIAL_STATE__.user.notes._rawValue || window.__INITIAL_STATE__.user.notes;
                    if (Array.isArray(notesData) && notesData.length > 0 && Array.isArray(notesData[0])) {{
                        totalPosts = notesData[0].length;
                    }}
                }}
            }}
            
            if (!totalPosts) {{
                return {{
                    success: false,
                    message: "无法获取帖子总数"
                }};
            }}
        }}
        
        console.log(`📊 [通用] 总帖子数: ${{totalPosts}}`);
        
        if (globalIndex >= totalPosts) {{
            return {{
                success: false,
                message: `索引超出范围: ${{globalIndex}} >= ${{totalPosts}}`
            }};
        }}
        
        // 计算目标位置并滚动
        const scrollPercent = globalIndex / Math.max(totalPosts, 1);
        const targetScrollPosition = scrollPercent * document.body.scrollHeight;
        
        console.log(`📍 目标位置: ${{(scrollPercent * 100).toFixed(2)}}% (${{targetScrollPosition}}px)`);
        
        // 滚动到目标位置
        window.scrollTo({{
            top: targetScrollPosition,
            behavior: 'smooth'
        }});
        
        // 等待滚动完成和DOM更新
        await new Promise(resolve => setTimeout(resolve, 3000));
        
        // 查找目标帖子并点击
        const noteElements = document.querySelectorAll('.note-item, section.note-item, [data-index]');
        console.log(`📋 当前DOM中有 ${{noteElements.length}} 个帖子元素`);
        
        // 通过data-index属性精确查找
        for (let element of noteElements) {{
            const domIndex = parseInt(element.getAttribute('data-index'));
            if (domIndex === globalIndex) {{
                console.log(`✅ 找到目标帖子 (data-index=${{domIndex}})！`);
                
                // 滚动到目标元素
                element.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                await new Promise(resolve => setTimeout(resolve, 500));
                
                // 点击图片（已验证的有效策略）
                const imgElement = element.querySelector('img');
                if (imgElement) {{
                    console.log(`🖼️ 点击帖子图片`);
                    
                    // 记录当前URL
                    const currentUrl = window.location.href;
                    console.log(`📍 点击前URL: ${{currentUrl}}`);
                    
                    imgElement.click();
                    
                    // 等待详情页加载并检测URL变化
                    let urlChanged = false;
                    for (let i = 0; i < 10; i++) {{
                        await new Promise(resolve => setTimeout(resolve, 500));
                        if (window.location.href !== currentUrl) {{
                            urlChanged = true;
                            console.log(`🎯 URL已变化: ${{window.location.href}}`);
                            break;
                        }}
                        console.log(`⏳ 等待URL变化... (${{i + 1}}/10)`);
                    }}
                    
                    if (urlChanged) {{
                        console.log(`✅ 成功跳转到帖子详情页`);
                        return {{
                            success: true,
                            message: targetTitle ? 
                                `成功点击标题为 "${{targetTitle}}" 的帖子并跳转` :
                                `成功点击索引 ${{globalIndex}} 的帖子并跳转`,
                            global_index: globalIndex,
                            dom_index: domIndex,
                            title: targetTitle || '',
                            new_url: window.location.href
                        }};
                    }} else {{
                        console.log(`⚠️ 点击了图片但未检测到页面跳转`);
                        return {{
                            success: true,
                            message: targetTitle ? 
                                `点击了标题为 "${{targetTitle}}" 的帖子，但未检测到页面跳转` :
                                `点击了索引 ${{globalIndex}} 的帖子，但未检测到页面跳转`,
                            global_index: globalIndex,
                            dom_index: domIndex,
                            title: targetTitle || '',
                            warning: "未检测到URL变化"
                        }};
                    }}
                }} else {{
                    console.log(`❌ 找到帖子但无法找到图片元素`);
                    return {{
                        success: false,
                        message: `找到帖子但无法找到图片元素`
                    }};
                }}
            }}
        }}
        
        console.log(`❌ 无法找到data-index为 ${{globalIndex}} 的帖子`);
        return {{
            success: false,
            message: `无法找到data-index为 ${{globalIndex}} 的帖子`
        }};
        
    }} catch (error) {{
        console.log(`❌ 点击帖子失败: ${{error.message}}`);
        return {{
            success: false,
            message: `点击帖子失败: ${{error.message}}`
        }};
    }}
}}

// 执行点击
(async function() {{
    return await clickPostByTitle("{escaped_title}");
}})();
        """
    
    def generate_expand_comments_script(self) -> str:
        """生成展开所有评论的脚本"""
        return """
// === 修正版：使用正确的滚动容器 ===
async function expandAllComments() {
    console.log("🎯 开始修正版展开评论策略...");
    
    let totalExpandedButtons = 0;
    let currentRound = 1;
    const maxRounds = 5;
    
    try {
        // 第一步：找到真正的滚动容器
        console.log("🔍 查找真正的滚动容器...");
        
        let commentContainer = null;
        
        // 查找 note-scroller（这是真正的滚动容器）
        const noteScroller = document.querySelector('.note-scroller');
        if (noteScroller && noteScroller.scrollHeight > noteScroller.clientHeight) {
            commentContainer = noteScroller;
            console.log("✅ 找到主滚动容器: .note-scroller");
        } else {
            // 如果没找到 note-scroller，使用整个文档
            console.log("⚠️ 未找到 .note-scroller，使用document.documentElement");
            commentContainer = document.documentElement;
        }
        
        console.log(`📦 使用容器:`, commentContainer);
        console.log(`📏 容器滚动高度: ${commentContainer.scrollHeight}, 可见高度: ${commentContainer.clientHeight}`);
        console.log(`📏 初始滚动位置: ${commentContainer.scrollTop}`);
        
        while (currentRound <= maxRounds) {
            console.log(`\n🔄 ===== 第 ${currentRound} 轮展开 =====`);
            
            // 核心改进：智能滚动到真正的底部（处理懒加载）
            console.log("📜 智能滚动到底部...");
            
            let scrollRound = 1;
            let lastScrollHeight = commentContainer.scrollHeight;
            
            // 多轮滚动直到真正到底部
            while (scrollRound <= 5) {
                console.log(`📜 第 ${scrollRound} 轮滚动...`);
                
                // 计算当前目标位置
                const targetScrollTop = commentContainer.scrollHeight - commentContainer.clientHeight;
                console.log(`🎯 目标位置: ${targetScrollTop}`);
                
                // 滚动到底部
                commentContainer.scrollTop = targetScrollTop;
                await new Promise(resolve => setTimeout(resolve, 2000));
                
                // 检查状态
                const currentScrollTop = commentContainer.scrollTop;
                const currentScrollHeight = commentContainer.scrollHeight;
                const distanceFromBottom = currentScrollHeight - currentScrollTop - commentContainer.clientHeight;
                
                console.log(`📍 滚动后位置: ${currentScrollTop}/${currentScrollHeight}`);
                console.log(`📏 距离底部: ${distanceFromBottom}px`);
                
                // 检查是否到底了
                if (distanceFromBottom <= 10) {
                    console.log("🎉 已经滚动到底部！");
                    break;
                }
                
                // 检查内容是否还在增长（懒加载）
                if (currentScrollHeight === lastScrollHeight) {
                    console.log("📏 内容高度未变化，停止滚动");
                    break;
                }
                
                console.log(`📈 内容高度从 ${lastScrollHeight} 增长到 ${currentScrollHeight}，继续滚动`);
                lastScrollHeight = currentScrollHeight;
                scrollRound++;
            }
            
            console.log("✅ 滚动完成，开始查找展开按钮...");
            
            // 在整个容器内查找展开按钮（不仅仅是可见区域）
            const expandButtons = commentContainer.querySelectorAll(
                'button, span[role="button"], div[role="button"], [onclick], ' +
                '.show-more, .expand-btn, [class*="expand"], [class*="more"], [class*="reply"]'
            );
            
            console.log(`📋 第 ${currentRound} 轮在容器内找到 ${expandButtons.length} 个潜在按钮`);
            
            let roundClickCount = 0;
            let foundExpandableButtons = [];
            
            // 筛选展开按钮
            for (let button of expandButtons) {
                const buttonText = button.textContent.trim();
                
                const isExpandButton = (
                    (buttonText.includes('展开') && (buttonText.includes('回复') || buttonText.includes('条'))) ||
                    buttonText.includes('查看更多回复') ||
                    buttonText.includes('更多回复') ||
                    /展开\s*\d+\s*条/.test(buttonText) ||
                    /\d+\s*条回复/.test(buttonText) ||
                    buttonText === '展开更多回复'
                );
                
                if (isExpandButton && 
                    buttonText.length > 2 && 
                    buttonText.length < 50 && 
                    button.offsetWidth > 0 && 
                    button.offsetHeight > 0) {
                    
                    foundExpandableButtons.push({
                        element: button,
                        text: buttonText
                    });
                }
            }
            
            console.log(`🎯 第 ${currentRound} 轮筛选出 ${foundExpandableButtons.length} 个展开按钮`);
            
            if (foundExpandableButtons.length === 0) {
                console.log(`✅ 第 ${currentRound} 轮没有找到展开按钮，展开完成！`);
                break;
            }
            
            // 点击展开按钮
            for (let j = 0; j < foundExpandableButtons.length; j++) {
                const { element, text } = foundExpandableButtons[j];
                console.log(`🖱️ 第 ${currentRound} 轮点击第 ${j + 1} 个: "${text}"`);
                
                try {
                    // 确保按钮在可见区域内
                    element.scrollIntoView({ 
                        behavior: 'smooth', 
                        block: 'center',
                        inline: 'center'
                    });
                    await new Promise(resolve => setTimeout(resolve, 500));
                    
                    // 点击按钮
                    element.click();
                    await new Promise(resolve => setTimeout(resolve, 1500));
                    
                    roundClickCount++;
                    totalExpandedButtons++;
                    console.log(`✅ "${text}" 点击成功`);
                    
                } catch (error) {
                    console.log(`❌ "${text}" 点击失败:`, error);
                }
            }
            
            console.log(`📊 第 ${currentRound} 轮完成，成功点击 ${roundClickCount} 个按钮`);
            
            if (roundClickCount === 0) {
                console.log(`⚠️ 第 ${currentRound} 轮没有成功点击任何按钮，展开完成！`);
                break;
            }
            
            console.log(`⏳ 等待新内容加载...`);
            await new Promise(resolve => setTimeout(resolve, 3000));
            
            currentRound++;
        }
        
        console.log(`\n🏁 ===== 展开完成 =====`);
        console.log(`📊 总共进行了 ${currentRound - 1} 轮展开`);
        console.log(`📊 总共成功点击了 ${totalExpandedButtons} 个按钮`);
        
        return {
            success: true,
            message: `成功进行 ${currentRound - 1} 轮展开，点击 ${totalExpandedButtons} 个按钮`,
            expanded_buttons: totalExpandedButtons,
            total_rounds: currentRound - 1,
            container_used: commentContainer.className || commentContainer.tagName || 'unknown'
        };
        
    } catch (error) {
        return {
            success: false,
            message: `展开评论失败: ${error.message}`,
            expanded_buttons: totalExpandedButtons
        };
    }
}

// 执行展开
(async function() {
    return await expandAllComments();
})();
        """
    
    def generate_close_post_script(self) -> str:
        """生成关闭小红书帖子详情页的脚本"""
        return r"""
// === 关闭小红书帖子详情页 ===
async function closePostDetail() {
    console.log("🔒 开始关闭小红书帖子详情页...");
    
    try {
        // 查找左上角关闭圆圈按钮
        const closeSelector = 'div.close-circle';
        console.log(`🔍 查找关闭按钮: ${closeSelector}`);
        
        const closeElement = document.querySelector(closeSelector);
        
        if (!closeElement) {
            console.log("❌ 未找到关闭按钮");
            return {
                success: false,
                message: "未找到关闭按钮",
                selector: closeSelector
            };
        }
        
        // 检查按钮是否可见
        const rect = closeElement.getBoundingClientRect();
        const isVisible = rect.width > 0 && rect.height > 0;
        
        console.log(`📍 找到关闭按钮: 位置(${Math.round(rect.left)},${Math.round(rect.top)}), 大小(${Math.round(rect.width)}x${Math.round(rect.height)}), 可见: ${isVisible}`);
        
        if (!isVisible) {
            console.log("❌ 关闭按钮不可见");
            return {
                success: false,
                message: "关闭按钮不可见",
                selector: closeSelector
            };
        }
        
        // 记录点击前状态
        const beforeUrl = window.location.href;
        const beforeTitle = document.title;
        
        console.log(`📍 点击前URL: ${beforeUrl}`);
        console.log(`📄 点击前标题: ${beforeTitle}`);
        
        // 执行点击
        console.log("🖱️ 点击关闭按钮...");
        closeElement.click();
        
        // 等待页面响应
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        // 检查结果
        const afterUrl = window.location.href;
        const afterTitle = document.title;
        
        console.log(`📍 点击后URL: ${afterUrl}`);
        console.log(`📄 点击后标题: ${afterTitle}`);
        
        const urlChanged = beforeUrl !== afterUrl;
        const titleChanged = beforeTitle !== afterTitle;
        
        if (urlChanged || titleChanged) {
            console.log("✅ 成功关闭帖子详情页");
            return {
                success: true,
                message: "成功关闭帖子详情页",
                method: "左上角关闭按钮",
                selector: closeSelector,
                before_url: beforeUrl,
                after_url: afterUrl,
                before_title: beforeTitle,
                after_title: afterTitle,
                url_changed: urlChanged,
                title_changed: titleChanged
            };
        } else {
            console.log("⚠️ 点击后页面未发生变化");
            return {
                success: false,
                message: "点击后页面未发生变化，可能页面结构发生了变化",
                selector: closeSelector,
                before_url: beforeUrl,
                after_url: afterUrl
            };
        }
        
    } catch (error) {
        console.error("❌ 关闭帖子详情页时发生错误:", error);
        return {
            success: false,
            message: `关闭帖子详情页失败: ${error.message}`,
            error: error.toString()
        };
    }
}

// 执行关闭
(async function() {
    return await closePostDetail();
})();
        """
    
    def generate_extract_all_posts_script(self, limit: int = None) -> str:
        """生成提取关键词页面帖子内容的脚本"""
        limit_js = f"const extractLimit = {limit};" if limit else "const extractLimit = null;"
        return f"{limit_js}\n" + """
// === 提取小红书关键词页面帖子内容 ===
function extractAllPostsForDatabase() {
    console.log("🎯 提取数据插入...");
    
    try {
        const posts = window.__INITIAL_STATE__.search.feeds._rawValue;
        console.log(`📊 找到 ${posts.length} 个帖子`);
        
        // 根据limit参数限制处理的帖子数量
        const postsToProcess = extractLimit ? posts.slice(0, extractLimit) : posts;
        console.log(`📋 将处理 ${postsToProcess.length} 个帖子 ${extractLimit ? `(限制前${extractLimit}个)` : '(全部)'}`);
        
        const results = [];
        
        postsToProcess.forEach((post, index) => {
            const postId = post.id || 'unknown';
            const noteCard = post.noteCard || {};
            const user = noteCard.user || {};
            const interactInfo = noteCard.interactInfo || {};
            
            // 提取发布时间
            let publishTime = null;
            let fullPublishTime = null;
            if (noteCard.cornerTagInfo && Array.isArray(noteCard.cornerTagInfo)) {
                const timeTag = noteCard.cornerTagInfo.find(tag => tag.type === 'publish_time');
                if (timeTag && timeTag.text) {
                    publishTime = timeTag.text; // "07-02"
                    // 推断年份
                    const currentYear = new Date().getFullYear();
                    const timeParts = timeTag.text.split('-');
                    if (timeParts.length >= 2) {
                        const month = timeParts[0];
                        const day = timeParts[1];
                        if (month && day) {
                            const currentMonth = new Date().getMonth() + 1;
                            const year = parseInt(month) > currentMonth ? currentYear - 1 : currentYear;
                            fullPublishTime = `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`;
                        }
                    }
                }
            }
            
            // 提取所有图片URL（仅主URL）
            const imageUrls = [];
            if (noteCard.imageList && Array.isArray(noteCard.imageList)) {
                noteCard.imageList.forEach((img) => {
                    if (img.infoList && img.infoList.length > 0) {
                        imageUrls.push({
                            url: img.infoList[0].url,
                            width: img.width || 0,
                            height: img.height || 0,
                            size: `${img.width || 0}x${img.height || 0}`,
                            alternative_url: img.infoList.length > 1 ? img.infoList[1].url : null
                        });
                    }
                });
            }
            
            const postData = {
                // xiaohongshu_posts 表字段
                post_id: postId,
                author_id: user.userId || 'unknown',
                author_name: user.nickname || user.nickName || '未知作者',
                title: noteCard.displayTitle || '无标题',
                like_count: parseInt(interactInfo.likedCount || 0),
                collect_count: parseInt(interactInfo.collectedCount || 0),
                comment_count: parseInt(interactInfo.commentCount || 0),
                share_count: parseInt(interactInfo.sharedCount || 0),
                post_type: noteCard.type || 'normal',
                is_video: (noteCard.type === 'video'),
                image_count: imageUrls.length,
                publish_time_raw: publishTime,
                post_created_at: fullPublishTime,
                
                // xiaohongshu_post_images 表数据（数组格式）
                images: imageUrls
            };
            
            // 有效性检查
            const isValid = (
                postData.title && postData.title !== '无标题' && postData.title.trim().length > 0 &&
                postData.author_name && postData.author_name !== '未知作者' && postData.author_name.trim().length > 0
            );
            
            if (isValid) {
                results.push(postData);
                
                // 🎯 显示完整的原始数据结构 - 不省略任何内容
                console.log(`\\n=============== 帖子${index + 1}完整数据 ===============`);
                console.log("📋 完整帖子对象:");
                console.log(postData);
                
                console.log("\\n📝 字段详情:");
                console.log(`post_id: "${postData.post_id}"`);
                console.log(`author_id: "${postData.author_id}"`);
                console.log(`author_name: "${postData.author_name}"`);
                console.log(`title: "${postData.title}"`);
                console.log(`like_count: ${postData.like_count}`);
                console.log(`collect_count: ${postData.collect_count}`);
                console.log(`comment_count: ${postData.comment_count}`);
                console.log(`share_count: ${postData.share_count}`);
                console.log(`post_type: "${postData.post_type}"`);
                console.log(`is_video: ${postData.is_video}`);
                console.log(`image_count: ${postData.image_count}`);
                console.log(`publish_time_raw: ${postData.publish_time_raw}`);
                console.log(`post_created_at: "${postData.post_created_at}"`);
                
                console.log("\\n🖼️ 完整图片数组:");
                console.log("images:", postData.images);
                
                if (postData.images.length > 0) {
                    console.log("\\n📷 每张图片的完整数据:");
                    postData.images.forEach((img, imgIdx) => {
                        console.log(`图片${imgIdx + 1}:`, img);
                        console.log(`  url: ${img.url}`);
                        console.log(`  width: ${img.width}`);
                        console.log(`  height: ${img.height}`);
                        console.log(`  size: "${img.size}"`);
                        console.log(`  alternative_url: ${img.alternative_url}`);
                    });
                }
                console.log(`=============== 帖子${index + 1}数据结束 ===============\\n`);
                
            } else {
                console.log(`❌ 跳过无效帖子${index + 1}: ${postData.title}`);
            }
        });
        
        // 统计信息
        const videoCount = results.filter(p => p.is_video).length;
        const imageCount = results.length - videoCount;
        const totalImages = results.reduce((sum, p) => sum + p.image_count, 0);
        const totalLikes = results.reduce((sum, p) => sum + p.like_count, 0);
        
        console.log(`\\n🎯 ========== 最终提取结果 ==========`);
        console.log(`📊 提取统计:`);
        console.log(`   ✅ 有效帖子: ${results.length} 个`);
        console.log(`   📹 视频帖子: ${videoCount} 个`);
        console.log(`   🖼️ 图片帖子: ${imageCount} 个`);
        console.log(`   📸 总图片数: ${totalImages} 张`);
        console.log(`   ❤️ 总点赞数: ${totalLikes} 个`);
        
        console.log(`\\n📋 完整数据数组 (results):`);
        console.log("完整提取结果:", results);
        
        const limitMessage = extractLimit ? `前${extractLimit}个` : '所有';
        const finalResult = {
            success: true,
            message: `成功提取 ${limitMessage} 帖子共${results.length}个用于数据库存储`,
            data: {
                total_count: results.length,
                video_count: videoCount,
                image_count: imageCount,
                total_images: totalImages,
                total_likes: totalLikes,
                posts: results,
                extraction_source: 'global_state_mysql_format'
            }
        };
        
        console.log(`\\n🎯 ========== 返回的完整对象 ==========`);
        console.log("最终返回对象:", finalResult);
        
        return finalResult;
        
    } catch (error) {
        console.log("❌ 提取失败:", error);
        return {
            success: false,
            message: `提取失败: ${error.message}`
        };
    }
}

// 执行提取
extractAllPostsForDatabase();
        """
    
    def generate_reply_to_comment_script(self, target_user_id: str, target_username: str, target_content: str, reply_content: str) -> str:
        """生成回复评论的脚本"""
        return f"""
// === 小红书三参数智能回复功能 ===
async function replyToComment() {{
    console.log("🎯 三参数回复功能启动...");
    
    // 回复参数
    const replyParams = {{
        target_user_id: '{target_user_id}',
        target_username: '{target_username}',
        target_content: '{target_content}',
        reply_content: '{reply_content}'
    }};
    
    try {{
        // 第一步：获取页面评论数据
        console.log("📋 正在获取页面评论数据...");
        const currentUrl = window.location.href;
        const urlMatch = currentUrl.match(/\\/explore\\/([a-f0-9]+)/i);
        const currentNoteId = urlMatch[1];
        const noteDetailMap = window.__INITIAL_STATE__.note.noteDetailMap;
        const authorUserId = noteDetailMap[currentNoteId].note?.user?.userId || '';
        const commentsData = noteDetailMap[currentNoteId].comments;
        const mainComments = commentsData.list;
        
        console.log(`📊 页面帖子ID: ${{currentNoteId}}`);
        console.log(`👤 作者ID: ${{authorUserId}}`);
        
        // 第二步：构建评论列表
        const allComments = [];
        let globalIndex = 1;
        
        mainComments.forEach((comment, mainIndex) => {{
            const isAuthorComment = comment.userInfo?.userId === authorUserId;
            
            // 主评论
            const mainComment = {{
                global_index: globalIndex++,
                comment_id: comment.id,
                user_id: comment.userInfo?.userId || '',
                username: comment.userInfo?.nickname || '未知用户',
                content: comment.content || '',
                type: 'main',
                is_author: isAuthorComment,
                reply_button_index: mainIndex + 1
            }};
            allComments.push(mainComment);
            
            // 回复评论
            if (comment.subComments && comment.subComments.length > 0) {{
                comment.subComments.forEach((reply) => {{
                    const isAuthorReply = reply.userInfo?.userId === authorUserId;
                    
                    const replyComment = {{
                        global_index: globalIndex++,
                        comment_id: reply.id,
                        user_id: reply.userInfo?.userId || '',
                        username: reply.userInfo?.nickname || '未知用户',
                        content: reply.content || '',
                        type: 'reply',
                        is_author: isAuthorReply,
                        parent_comment_id: comment.id,
                        reply_button_index: mainIndex + 1
                    }};
                    allComments.push(replyComment);
                }});
            }}
        }});
        
        console.log(`📊 构建了 ${{allComments.length}} 条评论数据`);
        
        // 第三步：匹配目标评论（三重验证）
        console.log("🔍 开始匹配目标评论...");
        console.log(`   目标用户ID: ${{replyParams.target_user_id}}`);
        console.log(`   目标用户名: ${{replyParams.target_username}}`);
        console.log(`   目标内容: ${{replyParams.target_content}}`);
        
        const targetComment = allComments.find(comment => {{
            const userIdMatch = comment.user_id === replyParams.target_user_id;
            const usernameMatch = comment.username === replyParams.target_username;
            const contentMatch = comment.content.includes(replyParams.target_content);
            
            console.log(`   检查评论 ${{comment.global_index}}: 用户ID(${{userIdMatch}}) 用户名(${{usernameMatch}}) 内容(${{contentMatch}})`);
            
            return userIdMatch && usernameMatch && contentMatch;
        }});
        
        if (!targetComment) {{
            console.log("❌ 未找到匹配的评论");
            console.log("📋 所有评论列表:");
            allComments.forEach(comment => {{
                console.log(`   ${{comment.global_index}}: ${{comment.username}}(${{comment.user_id}}) - ${{comment.content.substring(0, 30)}}...`);
            }});
            throw new Error("未找到匹配的评论，请检查参数");
        }}
        
        console.log(`✅ 找到目标评论:`);
        console.log(`   索引: ${{targetComment.global_index}}`);
        console.log(`   ID: ${{targetComment.comment_id}}`);
        console.log(`   用户: ${{targetComment.username}}`);
        console.log(`   用户ID: ${{targetComment.user_id}}`);
        console.log(`   内容: ${{targetComment.content}}`);
        console.log(`   类型: ${{targetComment.type}}`);
        console.log(`   回复按钮索引: ${{targetComment.reply_button_index}}`);
        
        // 第四步：点击回复按钮
        const allButtons = document.querySelectorAll('button, span[role="button"], [class*="reply"]');
        const realReplyButtons = Array.from(allButtons).filter(btn => {{
            const text = btn.textContent.trim();
            return text === '回复' && btn.className.includes('reply icon-container');
        }});
        
        console.log(`📋 找到 ${{realReplyButtons.length}} 个回复按钮`);
        
        if (targetComment.reply_button_index > realReplyButtons.length) {{
            throw new Error(`回复按钮索引超出范围: ${{targetComment.reply_button_index}}`);
        }}
        
        const targetButton = realReplyButtons[targetComment.reply_button_index - 1];
        targetButton.click();
        console.log(`✅ 已点击第 ${{targetComment.reply_button_index}} 个回复按钮`);
        
        // 第五步：输入回复内容
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        const inputBox = document.querySelector('p.content-input[contenteditable="true"]');
        if (!inputBox) {{
            throw new Error("未找到输入框");
        }}
        
        inputBox.focus();
        inputBox.textContent = replyParams.reply_content;
        inputBox.dispatchEvent(new Event('input', {{ bubbles: true }}));
        console.log(`✅ 回复内容已输入: "${{replyParams.reply_content}}"`);
        
        // 第六步：发送回复
        await new Promise(resolve => setTimeout(resolve, 500));
        
        const buttons = document.querySelectorAll('button');
        let sendButton = null;
        
        buttons.forEach((btn) => {{
            const text = btn.textContent.trim();
            const isVisible = btn.offsetWidth > 0 && btn.offsetHeight > 0;
            
            if (text === '发送' && isVisible) {{
                sendButton = btn;
            }}
        }});
        
        if (sendButton) {{
            console.log("🚀 点击发送按钮...");
            sendButton.click();
            
            return {{
                success: true,
                message: `成功回复用户 ${{targetComment.username}} 的评论`,
                data: {{
                    target_comment: {{
                        comment_id: targetComment.comment_id,
                        user_id: targetComment.user_id,
                        username: targetComment.username,
                        content: targetComment.content,
                        type: targetComment.type,
                        global_index: targetComment.global_index
                    }},
                    reply_content: replyParams.reply_content,
                    reply_button_index: targetComment.reply_button_index,
                    sent: true
                }}
            }};
        }} else {{
            return {{
                success: false,
                message: "回复内容已输入，但未找到发送按钮",
                data: {{
                    target_comment: {{
                        comment_id: targetComment.comment_id,
                        user_id: targetComment.user_id,
                        username: targetComment.username,
                        content: targetComment.content
                    }},
                    reply_content: replyParams.reply_content,
                    sent: false
                }}
            }};
        }}
        
    }} catch (error) {{
        console.log("❌ 三参数回复失败:", error);
        return {{
            success: false,
            message: `三参数回复失败: ${{error.message}}`,
            data: {{
                target_user_id: replyParams.target_user_id,
                target_username: replyParams.target_username,
                target_content: replyParams.target_content,
                reply_content: replyParams.reply_content,
                error: error.message
            }}
        }};
    }}
}}

// 执行回复
replyToComment();
        """
    
    def generate_extract_comments_script(self) -> str:
        """生成提取所有评论的脚本（从全局状态提取）"""
        return """
// === 从全局状态提取小红书评论内容 ===
function extractAllComments() {
    console.log("🎯 从全局状态提取小红书评论内容...");
    
    try {
        // 🔧 修复：从当前页面URL获取帖子ID
        const currentUrl = window.location.href;
        console.log("📋 当前页面URL:", currentUrl);
        
        // 从URL中提取帖子ID
        let currentNoteId = null;
        const urlMatch = currentUrl.match(/\\/explore\\/([a-f0-9]+)/i) || currentUrl.match(/\\/discovery\\/item\\/([a-f0-9]+)/i);
        if (urlMatch) {
            currentNoteId = urlMatch[1];
        }
        
        console.log("📋 从URL提取的帖子ID:", currentNoteId);
        
        const noteDetailMap = window.__INITIAL_STATE__.note.noteDetailMap;
        
        // 如果URL中没有找到ID，再从全局状态中查找
        if (!currentNoteId) {
            const noteIds = Object.keys(noteDetailMap).filter(id => id && id !== 'undefined' && id !== '');
            console.log("📋 全局状态中的所有帖子ID:", noteIds);
            if (noteIds.length === 0) {
                throw new Error("未找到有效的帖子ID");
            }
            currentNoteId = noteIds[0]; // 兜底方案
            console.log("📋 使用兜底帖子ID:", currentNoteId);
        }
        
        // 检查这个帖子ID是否在全局状态中存在
        if (!noteDetailMap[currentNoteId]) {
            console.log("❌ 当前帖子ID在全局状态中不存在");
            console.log("📋 可用的帖子ID:", Object.keys(noteDetailMap));
            throw new Error(`帖子 ${currentNoteId} 的数据未加载`);
        }
        
        console.log("✅ 确认当前帖子ID:", currentNoteId);
        
        // 🎯 获取作者信息用于判断
        const noteData = noteDetailMap[currentNoteId].note;
        const authorUserId = noteData?.user?.userId || '';
        const authorName = noteData?.user?.nickname || '';
        console.log("📝 作者信息 - ID:", authorUserId, "名称:", authorName);
        
        let authorPost = null;
        
        if (noteData) {
            console.log("📝 开始提取作者发布的帖子内容...");
            
            // 提取描述
            const description = noteData.desc || '';
            console.log("📄 帖子描述:", description);
            
            // 提取标题
            const title = noteData.title || '';
            console.log("📌 帖子标题:", title);
            
            // 提取标签
            const tags = [];
            if (noteData.tagList && Array.isArray(noteData.tagList)) {
                noteData.tagList.forEach(tag => {
                    if (tag.name) {
                        tags.push({
                            id: tag.id || '',
                            name: tag.name,
                            type: tag.type || 'topic'
                        });
                    }
                });
            }
            console.log("🏷️ 帖子标签:", tags.map(t => t.name).join(', '));
            
            // 提取作者信息
            const author = {
                user_id: authorUserId,
                nickname: authorName,
                avatar: noteData.user?.avatar || ''
            };
            console.log("👤 作者信息:", author.nickname);
            
            authorPost = {
                post_id: currentNoteId,
                title: title,
                description: description,
                tags: tags,
                author: author,
                publish_time: noteData.time || '',
                last_update_time: noteData.lastUpdateTime || '',
                source: 'global_state'
            };
            
            console.log("✅ 成功提取作者发布内容");
        } else {
            console.log("⚠️ 未找到作者发布的帖子内容数据");
        }
        
        // 原有的评论提取逻辑
        const commentsData = noteDetailMap[currentNoteId].comments;
        if (!commentsData || !commentsData.list) {
            throw new Error("未找到评论数据");
        }
        
        const mainComments = commentsData.list;
        console.log("✅ 找到主评论:", mainComments.length, "条");
        
        const allComments = [];
        let commentIndex = 1;
        
        // 处理主评论
        mainComments.forEach((comment, index) => {
            // 🔧 修复：使用userId判断作者
            const isAuthorComment = comment.userInfo?.userId === authorUserId;
            
            // 提取主评论的有效信息
            const mainComment = {
                index: commentIndex++,
                id: comment.id,
                user: comment.userInfo?.nickname || '未知用户',
                user_id: comment.userInfo?.userId || '',
                content: comment.content || '',
                type: 'main',
                is_author: isAuthorComment, // 🔧 使用修复后的判断
                time: new Date(comment.createTime).toLocaleString('zh-CN') || '',
                location: comment.ipLocation || '',
                like_count: comment.likeCount || '0',
                reply_count: comment.subCommentCount || 0,
                source: 'global_state'
            };
            
            allComments.push(mainComment);
            
            const authorIndicator = isAuthorComment ? " [作者]" : "";
            console.log(`主评论${index + 1}: ${mainComment.user}${authorIndicator} - ${mainComment.content}`);
            
            // 处理回复评论
            if (comment.subComments && comment.subComments.length > 0) {
                comment.subComments.forEach((reply, replyIndex) => {
                    // 🔧 修复：使用userId判断作者
                    const isAuthorReply = reply.userInfo?.userId === authorUserId;
                    
                    const replyComment = {
                        index: commentIndex++,
                        id: reply.id,
                        user: reply.userInfo?.nickname || '未知用户',
                        user_id: reply.userInfo?.userId || '',
                        content: reply.content || '',
                        type: 'reply',
                        parent_comment_id: comment.id,
                        is_author: isAuthorReply, // 🔧 使用修复后的判断
                        time: new Date(reply.createTime).toLocaleString('zh-CN') || '',
                        location: reply.ipLocation || '',
                        like_count: reply.likeCount || '0',
                        reply_count: 0, // 回复通常不再有子回复
                        source: 'global_state'
                    };
                    
                    allComments.push(replyComment);
                    
                    const authorReplyIndicator = isAuthorReply ? " [作者]" : "";
                    console.log(`  └─ 回复${replyIndex + 1}: ${replyComment.user}${authorReplyIndicator} - ${replyComment.content}`);
                });
            }
        });
        
        // 统计信息
        const mainCommentsCount = allComments.filter(c => c.type === 'main').length;
        const replyCommentsCount = allComments.filter(c => c.type === 'reply').length;
        const authorCommentsCount = allComments.filter(c => c.is_author).length;
        
        console.log(`📊 提取完成 - 总数: ${allComments.length}, 主评论: ${mainCommentsCount}, 回复: ${replyCommentsCount}, 作者评论: ${authorCommentsCount}`);
        
        return {
            success: true,
            message: `从全局状态提取到 ${allComments.length} 条评论和作者帖子内容`,
            data: {
                // 🎯 新增：作者帖子内容
                author_post: authorPost,
                
                // 原有评论数据
                total_count: allComments.length,
                main_comments_count: mainCommentsCount,
                reply_comments_count: replyCommentsCount,
                author_comments_count: authorCommentsCount,
                comments: allComments,
                note_id: currentNoteId,
                extraction_source: 'global_state'
            }
        };
        
    } catch (error) {
        console.log("❌ 提取失败:", error);
        return {
            success: false,
            message: "全局状态提取失败: " + error.message
        };
    }
}

// 执行提取
extractAllComments();
        """
    def generate_click_author_avatar_and_extract_script(self, userid: str, username: str) -> str:
        """生成点击作者头像并提取用户信息的脚本"""
        return f"""
// === 点击作者头像并获取用户信息 ===
async function clickAuthorAvatarAndExtractProfile() {{
    console.log("🎯 开始获取用户信息: userid={userid}, username={username}");
    
    try {{
        const userid = "{userid}";
        const username = "{username}";
        
        // 1. 直接查找头像元素（最常用的选择器）
        console.log("🔍 查找头像...");
        let avatar = document.querySelector(`[href*="${{userid}}"]`);
        
        if (!avatar) {{
            return {{
                success: false,
                message: `未找到用户 ${{username}} 的头像`,
                userid: userid,
                username: username
            }};
        }}
        
        console.log("✅ 找到头像，准备点击");
        
        // 2. 点击头像打开用户主页
        avatar.click();
        console.log("⏳ 等待页面加载...");
        await new Promise(resolve => setTimeout(resolve, 4000));
        
        // 3. 检查是否在新标签页中打开（原页面状态不变是正常的）
        console.log("📍 头像点击完成，用户主页已在新标签页中打开");
        
        return {{
            success: true,
            message: "成功点击头像，用户主页已在新标签页中打开",
            userid: userid,
            username: username,
            note: "请在新打开的用户主页标签页中运行数据提取脚本",
            timestamp: new Date().toISOString()
        }};
        
    }} catch (error) {{
        console.error("❌ 点击头像失败:", error);
        return {{
            success: false,
            message: `点击头像失败: ${{error.message}}`,
            userid: "{userid}",
            username: "{username}",
            error: error.toString()
        }};
    }}
}}

// 执行点击
(async function() {{
    return await clickAuthorAvatarAndExtractProfile();
}})();
        """
    
    def generate_extract_user_profile_script(self) -> str:
        """生成用户个人主页信息提取脚本 """
        return """
// === 用户主页信息提取 ===
async function extractUserProfile() {
    console.log("📊 开始提取用户个人主页信息...");
    
    try {
        // 检查是否在用户主页
        if (!window.location.href.includes('/user/profile/')) {
            return {
                success: false,
                message: "当前不在用户个人主页"
            };
        }
        
        const userData = {};
        
        // 1. 基础信息提取
        console.log("📋 提取基础信息...");
        userData.profile_url = window.location.href;
        userData.user_id = window.location.href.match(/\\/user\\/profile\\/([^\\/?]+)/)[1];
        userData.extraction_time = new Date().toISOString();
        
        // 用户名
        const nameElement = document.querySelector('.user-nickname, .user-name, h1, [class*="name"]');
        userData.username = nameElement ? nameElement.textContent.trim() : '';
        console.log(`👤 用户名: ${userData.username}`);
        
        // 小红书号
        const userInfoArea = document.querySelector('.user-info, .info, .basic-info');
        const userInfoText = userInfoArea ? userInfoArea.textContent : document.body.textContent;
        const idMatch = userInfoText.match(/小红书号[：:\\s]*(\\d+)/);
        userData.xiaohongshu_id = idMatch ? idMatch[1] : '';
        console.log(`🆔 小红书号: ${userData.xiaohongshu_id}`);
        
        // 个人简介
        const bioElement = document.querySelector('.bio, .description, [class*="desc"]');
        userData.bio = bioElement ? bioElement.textContent.trim() : '';
        
        // 头像
        const avatarElement = document.querySelector('img[src*="avatar"]');
        userData.avatar_url = avatarElement ? avatarElement.src : '';
        
        // IP位置
        const ipMatch = userInfoText.match(/IP属地[：:\\s]*(北京|上海|广东|浙江|江苏|山东|河南|四川|湖北|湖南|河北|安徽|福建|江西|山西|辽宁|吉林|黑龙江|内蒙古|广西|海南|重庆|贵州|云南|西藏|陕西|甘肃|青海|宁夏|新疆|台湾|香港|澳门|天津)/);
        userData.ip_location = ipMatch ? ipMatch[1] : '';
        console.log(`📍 IP位置: ${userData.ip_location}`);
        
        // 2. 统计数据提取
        console.log("📊 提取统计数据...");
        const dataContainer = document.querySelector('.data-info');
        if (dataContainer) {
            const counts = Array.from(dataContainer.querySelectorAll('.count')).map(el => {
                const text = el.textContent.trim();
                if (text.includes('万')) {
                    return Math.round(parseFloat(text.replace('万', '')) * 10000);
                } else if (text.toLowerCase().includes('k')) {
                    return Math.round(parseFloat(text.toLowerCase().replace('k', '')) * 1000);
                } else {
                    return parseInt(text.replace(/[^\\d]/g, '')) || 0;
                }
            });
            
            if (counts.length >= 3) {
                userData.following_count = counts[0];
                userData.followers_count = counts[1];
                userData.likes_collections_count = counts[2];
                console.log(`📊 统计数据: 关注${counts[0]} 粉丝${counts[1]} 获赞${counts[2]}`);
            }
        }
        
        // 3. 通过全局状态检查用户是否有帖子
        console.log("🔍 通过全局状态检查用户是否有发表帖子...");
        
        let userNotes = [];
        let hasNotes = false;
        
        // 尝试从全局状态获取用户帖子数据
        try {
            if (window.__INITIAL_STATE__ && 
                window.__INITIAL_STATE__.user && 
                window.__INITIAL_STATE__.user.notes) {
                
                const notesArray = window.__INITIAL_STATE__.user.notes._rawValue || window.__INITIAL_STATE__.user.notes || [];
                
                // 关键：真正的帖子数据在 notes[0] 中
                if (Array.isArray(notesArray) && notesArray.length > 0 && Array.isArray(notesArray[0])) {
                    userNotes = notesArray[0];
                    hasNotes = userNotes.length > 0;
                    console.log(`📊 [全局状态] 初始帖子数量: ${userNotes.length}`);
                } else {
                    console.log(`📊 [全局状态] 数据结构异常`);
                    userNotes = [];
                    hasNotes = false;
                }
            } else {
                // 全局状态不可用，直接设为无帖子
                userNotes = [];
                hasNotes = false;
                console.log(`❌ 无法获取用户帖子全局状态数据`);
            }
        } catch (error) {
            console.log(`⚠️ 全局状态检查失败: ${error.message}`);
            hasNotes = false;
        }
        
        userData.has_notes = hasNotes;
        
        if (hasNotes) {
            console.log("✅ 用户有发表帖子，开始滑动获取所有帖子信息...");
            
            let lastCount = userNotes.length || 0;
            let noNewCount = 0;
            let scrollRounds = 0;
            const maxScrollRounds = 15; // 最多滑动15轮
            
            console.log(`📊 开始滑动前的帖子数量: ${lastCount}`);
            
            while (noNewCount < 5 && scrollRounds < maxScrollRounds) { // 增加到5轮无新增才停止
                scrollRounds++;
                console.log(`📜 第${scrollRounds}轮滑动...`);
                
                const currentScrollTop = window.pageYOffset;
                // 滑动到底部
                window.scrollTo(0, document.body.scrollHeight);
                await new Promise(resolve => setTimeout(resolve, 3000)); // 增加等待时间确保加载完成
                
                // 通过全局状态检查帖子数量
                let currentCount = lastCount;
                try {
                    if (window.__INITIAL_STATE__ && 
                        window.__INITIAL_STATE__.user && 
                        window.__INITIAL_STATE__.user.notes) {
                        
                        const currentNotesArray = window.__INITIAL_STATE__.user.notes._rawValue || 
                                                 window.__INITIAL_STATE__.user.notes || [];
                        
                        // 关键：真正的帖子数据在 notes[0] 中
                        if (Array.isArray(currentNotesArray) && currentNotesArray.length > 0 && Array.isArray(currentNotesArray[0])) {
                            const currentNotes = currentNotesArray[0];
                            currentCount = currentNotes.length;
                            userNotes = currentNotes; // 更新帖子数组
                        }
                    }
                } catch (error) {
                    console.log(`⚠️ 获取全局状态帖子失败: ${error.message}`);
                }
                
                console.log(`📊 当前帖子数量: ${currentCount} (上轮: ${lastCount})`);
                
                if (currentCount === lastCount) {
                    noNewCount++;
                    console.log(`⏳ 无新增帖子 (${noNewCount}/3)`);
                    
                    const newScrollTop = window.pageYOffset;
                    if (newScrollTop === currentScrollTop) {
                        console.log("📍 页面滚动位置未变化，可能已到底部");
                    }
                } else {
                    noNewCount = 0;
                    console.log(`✅ 新增了 ${currentCount - lastCount} 个帖子`);
                    lastCount = currentCount;
                }
            }
            
            userData.notes_count = lastCount;
            console.log(`📊 滑动完成！总共获取了 ${lastCount} 个帖子 (滑动${scrollRounds}轮)`);
            
            // 提取所有帖子的详细信息
            if (userNotes.length > 0) {
                console.log(`📋 获取到所有帖子，开始处理 ${userNotes.length} 个帖子...`);
                
                // 显示前5个作为示例
                console.log(`📋 帖子示例 (前5个):`);
                userNotes.slice(0, 5).forEach((note, index) => {
                    const noteCard = note.noteCard || {};
                    const title = (noteCard.displayTitle || '无标题').trim();
                    const likedCount = noteCard.interactInfo?.likedCount || '0';
                    const type = noteCard.type || '';
                    console.log(`   ${index + 1}. [${type}] ${title} (👍${likedCount})`);
                });
                
                console.log(`📊 正在处理所有 ${userNotes.length} 个帖子的详细信息...`);
                
                // 保存所有帖子的详细信息
                userData.notes_all = userNotes.map(note => {
                    const noteCard = note.noteCard || {};
                    const interactInfo = noteCard.interactInfo || {};
                    const cover = noteCard.cover || {};
                    const user = noteCard.user || {};
                    
                    return {
                        title: (noteCard.displayTitle || '无标题').trim(),
                        note_id: noteCard.noteId || '',
                        type: noteCard.type || '',
                        liked_count: parseInt(interactInfo.likedCount || '0'),
                        is_liked: interactInfo.liked || false,
                        is_sticky: interactInfo.sticky || false,
                        cover_url: cover.urlDefault || cover.urlPre || '',
                        author: {
                            user_id: user.userId || '',
                            username: user.nickName || user.nickname || '',
                            avatar: user.avatar || ''
                        }
                    };
                });
                
                // 统计信息（基于所有帖子）
                const totalLikes = userData.notes_all.reduce((sum, note) => sum + (note.liked_count || 0), 0);
                const videoCount = userData.notes_all.filter(note => note.type === 'video').length;
                const imageCount = userData.notes_all.filter(note => note.type === 'normal').length;
                
                console.log(`📊 完整帖子统计: 总共${userNotes.length}个帖子 | 视频${videoCount}个, 图文${imageCount}个, 总点赞数${totalLikes}`);
                
                userData.notes_stats = {
                    total_likes: totalLikes,
                    video_count: videoCount,
                    image_count: imageCount
                };
            }
            
        } else {
            console.log("ℹ️ 用户没有发表帖子，跳过滑动");
            userData.notes_count = 0;
        }
        
        console.log("✅ 用户信息提取完成:", userData);
        
        return {
            success: true,
            message: "用户信息提取成功",
            data: userData,
            note: `已获取该用户的所有${userData.notes_count || 0}个帖子信息。点赞数`
        };
        
    } catch (error) {
        console.error("❌ 用户信息提取失败:", error);
        return {
            success: false,
            message: `用户信息提取失败: ${error.message}`,
            error: error.toString()
        };
    }
}

// 执行提取
(async function() {
    return await extractUserProfile();
})();
        """
    
    
    # ==================== 小红书业务逻辑方法 ====================
    
    async def auto_scroll_load_posts(self):
        """使用基础能力执行小红书自动滚动（支持多标签页）"""
        
        async def _execute_scroll_script(page, **kwargs):
            """实际执行滚动脚本的函数"""
            script = self.generate_auto_scroll_script()
            browser_result = await self.browser.execute_script(script)
            
            if browser_result.success:
                # 解析JavaScript返回的结果
                if browser_result.content:
                    import json
                    try:
                        js_result = json.loads(browser_result.content)
                        return js_result
                    except json.JSONDecodeError:
                        return {"success": False, "message": "JavaScript结果解析失败"}
                else:
                    return {"success": False, "message": "JavaScript执行成功但无返回内容"}
            else:
                return {"success": False, "message": f"浏览器脚本执行失败: {browser_result.message}"}
        
        try:
            self.logger.info("开始小红书自动滚动加载")
            
            # 使用上下文切换执行操作
            if hasattr(self.browser, 'execute_with_context'):
                return await self.browser.execute_with_context(
                    "xiaohongshu_auto_scroll", 
                    _execute_scroll_script
                )
            else:
                # 回退到原始逻辑
                return await _execute_scroll_script(None)
                
        except Exception as e:
            self.logger.error(f"自动滚动失败: {str(e)}")
            return {"success": False, "message": f"自动滚动失败: {str(e)}"}
    
    async def extract_all_posts(self, limit: int = None):
        """使用基础能力提取帖子信息"""
        try:
            if limit:
                self.logger.info(f"开始提取小红书前{limit}个帖子信息")
            else:
                self.logger.info("开始提取小红书所有帖子信息")
            script = self.generate_extract_all_posts_script(limit)
            browser_result = await self.browser.execute_script(script)
            
            if browser_result.success:
                if browser_result.content:
                    try:
                        js_result = json.loads(browser_result.content)
                        return js_result
                    except json.JSONDecodeError:
                        return {"success": False, "message": "JavaScript结果解析失败"}
                else:
                    return {"success": False, "message": "JavaScript执行成功但无返回内容"}
            else:
                return {"success": False, "message": f"浏览器脚本执行失败: {browser_result.message}"}
                
        except Exception as e:
            self.logger.error(f"提取帖子失败: {str(e)}")
            return {"success": False, "message": f"提取帖子失败: {str(e)}"}
    
    async def click_post_by_title(self, title: str):
        """使用基础能力通过标题点击帖子"""
        try:
            self.logger.info(f"开始点击标题为 '{title}' 的帖子")
            script = self.generate_click_post_script(title)
            browser_result = await self.browser.execute_script(script)
            
            if browser_result.success:
                if browser_result.content:
                    try:
                        js_result = json.loads(browser_result.content)
                        return js_result
                    except json.JSONDecodeError:
                        return {"success": False, "message": "JavaScript结果解析失败"}
                else:
                    return {"success": False, "message": "JavaScript执行成功但无返回内容"}
            else:
                return {"success": False, "message": f"浏览器脚本执行失败: {browser_result.message}"}
                
        except Exception as e:
            self.logger.error(f"通过标题点击帖子失败: {str(e)}")
            return {"success": False, "message": f"通过标题点击帖子失败: {str(e)}"}
    
    async def close_post(self):
        """关闭小红书帖子详情页"""
        try:
            self.logger.info("开始关闭小红书帖子详情页")
            script = self.generate_close_post_script()
            browser_result = await self.browser.execute_script(script)
            
            if browser_result.success:
                if browser_result.content:
                    try:
                        js_result = json.loads(browser_result.content)
                        
                        if js_result.get('success'):
                            self.logger.info(f"成功关闭帖子详情页: {js_result.get('message')}")
                        else:
                            self.logger.warning(f"关闭帖子详情页失败: {js_result.get('message')}")
                        
                        return js_result
                    except json.JSONDecodeError:
                        self.logger.error("JavaScript结果解析失败")
                        return {"success": False, "message": "JavaScript结果解析失败"}
                else:
                    self.logger.warning("JavaScript执行成功但无返回内容")
                    return {"success": False, "message": "JavaScript执行成功但无返回内容"}
            else:
                self.logger.error(f"浏览器脚本执行失败: {browser_result.message}")
                return {"success": False, "message": f"浏览器脚本执行失败: {browser_result.message}"}
                
        except Exception as e:
            self.logger.error(f"关闭帖子详情页失败: {str(e)}")
            return {"success": False, "message": f"关闭帖子详情页失败: {str(e)}"}
    
    async def close_page(self):
        """关闭当前页面 - 优先使用TabManager，回退到直接关闭"""
        try:
            self.logger.info("开始关闭当前页面")
            
            # 优先使用 TabManager 的可靠关闭方式
            if hasattr(self.browser, 'tab_manager') and self.browser.tab_manager:
                tab_manager = self.browser.tab_manager
                
                # 获取当前活跃页面
                current_page = await tab_manager.get_active_page()
                if current_page:
                    # 找到当前页面对应的标签页ID
                    for tab_id, tab_info in tab_manager.tabs.items():
                        if tab_info.page == current_page:
                            self.logger.info(f"使用TabManager关闭标签页: {tab_id}")
                            success = await tab_manager.close_tab(tab_id)
                            
                            if success:
                                self.logger.info("TabManager成功关闭页面")
                                return {"success": True, "message": "页面关闭成功"}
                            else:
                                self.logger.warning("TabManager关闭失败，尝试直接关闭")
                                break
                    
                    # 如果在tabs中没找到当前页面，直接关闭
                    try:
                        await current_page.close()
                        self.logger.info("直接关闭页面成功")
                        return {"success": True, "message": "页面关闭成功"}
                    except Exception as e:
                        self.logger.error(f"直接关闭页面失败: {e}")
                        return {"success": False, "message": f"页面关闭失败: {str(e)}"}
            
            # 回退方式：直接获取当前页面并关闭
            else:
                self.logger.info("TabManager不可用，使用回退方式关闭页面")
                try:
                    current_page = await self.browser.get_current_page()
                    await current_page.close()
                    self.logger.info("回退方式关闭页面成功")
                    return {"success": True, "message": "页面关闭成功"}
                except Exception as e:
                    self.logger.error(f"回退方式关闭页面失败: {e}")
                    return {"success": False, "message": f"页面关闭失败: {str(e)}"}
                
        except Exception as e:
            self.logger.error(f"关闭页面失败: {str(e)}")
            return {"success": False, "message": f"关闭页面失败: {str(e)}"}
    
    async def click_author_avatar_and_extract_profile(self, userid: str, username: str):
        """点击作者头像并提取用户完整信息（支持多标签页）"""
        
        async def _execute_click_and_extract(page, **kwargs):
            """实际执行点击头像和提取信息的函数"""
            import asyncio
            # 第一步：点击头像（这会创建新标签页）
            script = self.generate_click_author_avatar_and_extract_script(userid, username)
            browser_result = await self.browser.execute_script(script)
            
            if browser_result.success:
                if browser_result.content:
                    try:
                        js_result = json.loads(browser_result.content)
                        
                        # 如果点击成功，检查是否有新标签页
                        if js_result.get('success') and hasattr(self.browser, 'tab_manager'):
                            # 发现新标签页
                            new_tabs = await self.browser.tab_manager.discover_new_tabs()
                            self.logger.info(f"发现新标签页: {new_tabs}")
                            
                            # 切换到用户资料页
                            if new_tabs:
                                # 等待页面加载
                                await asyncio.sleep(3)
                                
                                # 查找用户资料页标签
                                user_tab = await self.browser.tab_manager.find_tab_by_type(TabType.USER_PROFILE)
                                if user_tab:
                                    await self.browser.tab_manager.switch_to_tab(user_tab)
                                    self.logger.info(f"切换到用户资料页标签: {user_tab}")
                                    
                                    # 现在在用户资料页提取信息
                                    profile_result = await self.extract_user_profile()
                                    if profile_result.get('success'):
                                        js_result['userData'] = profile_result.get('userData', {})
                                        self.logger.info("成功从新标签页提取用户信息")
                        
                        if js_result.get('success'):
                            self.logger.info(f"成功获取用户信息: {js_result.get('message')}")
                            user_data = js_result.get('userData', {})
                            if user_data and not user_data.get('error'):
                                self.logger.info(f"用户数据: {user_data}")
                        else:
                            self.logger.warning(f"获取用户信息失败: {js_result.get('message')}")
                        
                        return js_result
                    except json.JSONDecodeError:
                        self.logger.error("JavaScript结果解析失败")
                        return {"success": False, "message": "JavaScript结果解析失败"}
                else:
                    self.logger.warning("JavaScript执行成功但无返回内容")
                    return {"success": False, "message": "JavaScript执行成功但无返回内容"}
            else:
                self.logger.error(f"浏览器脚本执行失败: {browser_result.message}")
                return {"success": False, "message": f"浏览器脚本执行失败: {browser_result.message}"}
        
        try:
            self.logger.info(f"开始点击作者头像并获取用户信息: userid={userid}, username={username}")
            
            # 使用上下文切换执行操作
            if hasattr(self.browser, 'execute_with_context'):
                return await self.browser.execute_with_context(
                    "xiaohongshu_click_author_avatar", 
                    _execute_click_and_extract,
                    userid=userid,
                    username=username
                )
            else:
                # 回退到原始逻辑
                return await _execute_click_and_extract(None, userid=userid, username=username)
                
        except Exception as e:
            self.logger.error(f"点击头像获取用户信息失败: {str(e)}")
            return {"success": False, "message": f"点击头像获取用户信息失败: {str(e)}"}
    
    async def extract_user_profile(self):
        """提取用户个人主页信息（支持多标签页）"""
        
        async def _execute_extract_script(page, **kwargs):
            """实际执行提取脚本的函数"""
            script = self.generate_extract_user_profile_script()
            browser_result = await self.browser.execute_script(script)
            
            if browser_result.success:
                if browser_result.content:
                    try:
                        js_result = json.loads(browser_result.content)
                        
                        if js_result.get('success'):
                            self.logger.info(f"成功提取用户信息: {js_result.get('message')}")
                            # 记录提取到的数据
                            user_data = js_result.get('data', {})
                            if user_data:
                                self.logger.info(f"用户数据: 用户名={user_data.get('username')}, "
                                               f"帖子数={user_data.get('notes_count', 0)}, "
                                               f"粉丝数={user_data.get('followers_count', 0)}")
                        else:
                            self.logger.warning(f"提取用户信息失败: {js_result.get('message')}")
                        
                        return js_result
                    except json.JSONDecodeError:
                        self.logger.error("JavaScript结果解析失败")
                        return {"success": False, "message": "JavaScript结果解析失败"}
                else:
                    self.logger.warning("JavaScript执行成功但无返回内容")
                    return {"success": False, "message": "JavaScript执行成功但无返回内容"}
            else:
                self.logger.error(f"浏览器脚本执行失败: {browser_result.message}")
                return {"success": False, "message": f"浏览器脚本执行失败: {browser_result.message}"}
        
        try:
            self.logger.info("开始提取用户个人主页信息")
            
            # 使用上下文切换执行操作
            if hasattr(self.browser, 'execute_with_context'):
                return await self.browser.execute_with_context(
                    "xiaohongshu_extract_user_profile", 
                    _execute_extract_script
                )
            else:
                # 回退到原始逻辑
                return await _execute_extract_script(None)
                
        except Exception as e:
            self.logger.error(f"提取用户主页信息失败: {str(e)}")
            return {"success": False, "message": f"提取用户主页信息失败: {str(e)}"}
    
    async def expand_all_comments(self):
        """使用基础能力展开所有评论（支持多标签页）"""
        
        async def _execute_expand_script(page, **kwargs):
            """实际执行展开评论脚本的函数"""
            script = self.generate_expand_comments_script()
            browser_result = await self.browser.execute_script(script)
            
            if browser_result.success:
                if browser_result.content:
                    try:
                        js_result = json.loads(browser_result.content)
                        return js_result
                    except json.JSONDecodeError:
                        return {"success": False, "message": "JavaScript结果解析失败"}
                else:
                    return {"success": False, "message": "JavaScript执行成功但无返回内容"}
            else:
                return {"success": False, "message": f"浏览器脚本执行失败: {browser_result.message}"}
        
        try:
            self.logger.info("开始展开所有评论")
            
            # 使用上下文切换执行操作
            if hasattr(self.browser, 'execute_with_context'):
                return await self.browser.execute_with_context(
                    "xiaohongshu_expand_comments", 
                    _execute_expand_script
                )
            else:
                # 回退到原始逻辑
                return await _execute_expand_script(None)
                
        except Exception as e:
            self.logger.error(f"展开评论失败: {str(e)}")
            return {"success": False, "message": f"展开评论失败: {str(e)}"}
    
    async def extract_all_comments(self):
        """使用基础能力提取所有评论"""
        try:
            self.logger.info("开始提取所有评论")
            script = self.generate_extract_comments_script()
            browser_result = await self.browser.execute_script(script)
            
            if browser_result.success:
                if browser_result.content:
                    try:
                        js_result = json.loads(browser_result.content)
                        return js_result
                    except json.JSONDecodeError as e:
                        self.logger.error(f"JSON解析失败: {str(e)}, 内容: {browser_result.content[:200]}...")
                        return {"success": False, "message": "JavaScript结果解析失败"}
                else:
                    self.logger.warning("JavaScript执行成功但无返回内容")
                    return {"success": False, "message": "JavaScript执行成功但无返回内容"}
            else:
                self.logger.error(f"浏览器脚本执行失败: {browser_result.message}")
                return {"success": False, "message": f"浏览器脚本执行失败: {browser_result.message}"}
                
        except Exception as e:
            self.logger.error(f"提取评论失败: {str(e)}")
            return {"success": False, "message": f"提取评论失败: {str(e)}"}
    
    async def reply_to_comment(self, target_user_id: str, target_username: str, target_content: str, reply_content: str):
        """使用基础能力回复指定评论"""
        try:
            self.logger.info(f"开始回复用户 {target_username} 的评论: {target_content[:30]}...")
            script = self.generate_reply_to_comment_script(target_user_id, target_username, target_content, reply_content)
            browser_result = await self.browser.execute_script(script)
            
            if browser_result.success:
                if browser_result.content:
                    try:
                        js_result = json.loads(browser_result.content)
                        return js_result
                    except json.JSONDecodeError as e:
                        self.logger.error(f"JSON解析失败: {str(e)}, 内容: {browser_result.content[:200]}...")
                        return {"success": False, "message": "JavaScript结果解析失败"}
                else:
                    self.logger.warning("JavaScript执行成功但无返回内容")
                    return {"success": False, "message": "JavaScript执行成功但无返回内容"}
            else:
                self.logger.error(f"浏览器脚本执行失败: {browser_result.message}")
                return {"success": False, "message": f"浏览器脚本执行失败: {browser_result.message}"}
                
        except Exception as e:
            self.logger.error(f"回复评论失败: {str(e)}")
            return {"success": False, "message": f"回复评论失败: {str(e)}"}
    
    
    async def analyze_post_complete(self, global_index: int):
        """完整的小红书帖子分析流程 - 组合基础能力"""
        try:
            self.logger.info(f"开始完整分析小红书全局索引 {global_index} 的帖子")
            
            # 第一步：滚动加载所有帖子
            scroll_result = await self.auto_scroll_load_posts()
            if not scroll_result.get("success"):
                return {"success": False, "message": f"滚动失败: {scroll_result.get('message')}"}
            
            # 第二步：从索引获取标题，然后点击目标帖子
            extract_result = await self.extract_all_posts()
            if not extract_result.get("success"):
                return {"success": False, "message": f"提取帖子信息失败: {extract_result.get('message')}"}
            
            posts_data = extract_result.get("data", {}).get("posts", [])
            if global_index >= len(posts_data):
                return {"success": False, "message": f"索引超出范围: {global_index} >= {len(posts_data)}"}
            
            target_post = posts_data[global_index]
            title = target_post.get("title", "")
            if not title:
                return {"success": False, "message": f"索引 {global_index} 的帖子没有标题"}
            
            click_result = await self.click_post_by_title(title)
            if not click_result.get("success"):
                return {"success": False, "message": f"点击帖子失败: {click_result.get('message')}"}
            
            # 第三步：展开评论
            expand_result = await self.expand_all_comments()
            # 展开失败不影响继续提取
            
            # 第四步：提取评论
            comments_result = await self.extract_all_comments()
            
            # 组合结果
            result_data = {
                "global_index": global_index,
                "scroll_result": scroll_result,
                "click_result": click_result,
                "expand_result": expand_result,
                "comments_result": comments_result,
                "image_extraction_note": "图片信息已在帖子提取步骤中包含，请使用 extract_all_posts 获取完整帖子+图片数据",
                "analysis_summary": {
                    "total_comments": comments_result.get("data", {}).get("total_count", 0),
                    "image_extraction_method": "integrated_with_post_extraction"
                }
            }
            
            return {
                "success": True,
                "message": f"成功完整分析小红书帖子 {global_index}",
                "data": result_data
            }
            
        except Exception as e:
            self.logger.error(f"完整分析失败: {str(e)}")
            return {"success": False, "message": f"完整分析失败: {str(e)}"} 