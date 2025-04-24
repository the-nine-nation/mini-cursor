/**
 * 聊天UI核心模块 - 处理基础功能和初始化
 */

const ChatUI = {
    // DOM元素
    elements: {
        messagesContainer: null,
        queryInput: null,
        sendButton: null,
    },
    
    // 当前会话状态
    state: {
        currentResponseText: '',
        currentThinkingText: '',
        responseMessageContainer: null,
        thinkingMessageContainer: null,
        lastEventWasToolCall: false,
        currentAssistantContainer: null,
        pendingToolCalls: {}, // 存储待处理的工具调用，键为工具调用ID
    },
    
    /**
     * 初始化聊天UI
     */
    init: function() {
        // 初始化DOM元素引用
        this.elements.messagesContainer = document.getElementById('messages');
        this.elements.queryInput = document.getElementById('query');
        this.elements.sendButton = document.getElementById('send-btn');
        
        // 绑定事件
        this.elements.sendButton.addEventListener('click', this.sendQuery.bind(this));
        this.elements.queryInput.addEventListener('keydown', this.handleInputKeydown.bind(this));
        
        // 添加气泡样式
        this.addToolBubbleStyles();
        
        // 添加快捷键提示
        this.addInfoMessage('提示: 使用 Alt+Enter 或 Command+Enter 发送消息, Enter 键换行');
    },
    
    /**
     * 添加工具气泡相关样式
     */
    addToolBubbleStyles: function() {
        const styleEl = document.createElement('style');
        styleEl.textContent = `
            .nested-bubble.tool-combined {
                background-color: #f7f7f7;
                border-radius: 8px;
                margin: 10px 0;
                border: 1px solid #e0e0e0;
                overflow: hidden;
            }
            
            .nested-bubble-header {
                background-color: #eaeaea;
                padding: 8px 12px;
                display: flex;
                align-items: center;
                cursor: pointer;
            }
            
            .nested-bubble-content {
                padding: 10px;
            }
            
            .tool-section {
                margin-bottom: 12px;
            }
            
            .tool-section:last-child {
                margin-bottom: 0;
            }
            
            .tool-section-header {
                font-weight: bold;
                margin-bottom: 5px;
                color: #555;
            }
            
            .tool-section pre {
                background-color: #f0f0f0;
                padding: 8px;
                border-radius: 4px;
                max-height: 300px;
                overflow: auto;
                margin: 0;
                font-family: monospace;
                white-space: pre-wrap;
                word-break: break-word;
            }
            
            .tool-section pre.error {
                background-color: #fff0f0;
                color: #e53935;
            }
            
            .tool-details-btn:hover {
                background-color: #e8e8e8;
            }
        `;
        document.head.appendChild(styleEl);
    },
    
    /**
     * 处理输入框按键事件
     * @param {Event} e - 键盘事件
     */
    handleInputKeydown: function(e) {
        if ((e.key === 'Enter' && e.altKey) || (e.key === 'Enter' && e.metaKey)) {
            e.preventDefault();
            this.sendQuery();
        }
    },
    
    /**
     * 发送查询
     */
    sendQuery: function() {
        const query = this.elements.queryInput.value.trim();
        
        if (!query) {
            return;
        }
        
        // 禁用发送按钮
        this.elements.sendButton.disabled = true;
        
        // 清空输入框
        this.elements.queryInput.value = '';
        
        // 显示用户消息
        this.addMessage(query, '', true);
        
        // 添加处理中消息
        this.addInfoMessage('处理中...');
        
        // 发送请求
        API.sendChatRequest(query)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error ${response.status}`);
                }
                
                // 移除处理中消息
                this.elements.messagesContainer.removeChild(this.elements.messagesContainer.lastChild);
                
                // 处理流式响应
                return this.processStreamResponse(response);
            })
            .catch(error => {
                console.error('Error:', error);
                this.addErrorMessage(`请求出错: ${error.message}`);
                this.elements.sendButton.disabled = false;
            });
    },
    
    /**
     * 添加信息消息
     * @param {string} content - 消息内容
     */
    addInfoMessage: function(content) {
        const infoDiv = document.createElement('div');
        infoDiv.className = 'message-info';
        infoDiv.textContent = content;
        this.elements.messagesContainer.appendChild(infoDiv);
        this.elements.messagesContainer.scrollTop = this.elements.messagesContainer.scrollHeight;
    },
    
    /**
     * 添加错误消息
     * @param {string} content - 错误内容
     */
    addErrorMessage: function(content) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'message-error';
        errorDiv.textContent = content;
        this.elements.messagesContainer.appendChild(errorDiv);
        this.elements.messagesContainer.scrollTop = this.elements.messagesContainer.scrollHeight;
    },
    
    /**
     * 转义HTML特殊字符
     * @param {string} text - 需要转义的文本
     * @returns {string} 转义后的文本
     */
    escapeHTML: function(text) {
        if (!text) return '';
        return text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    },
    
    /**
     * 处理Markdown格式的文本，支持有序列表和无序列表
     * @param {string} text - 原始文本
     * @returns {string} 处理后的HTML
     */
    processMarkdown: function(text) {
        if (!text) return '';
        
        // 首先转义HTML
        let escapedText = this.escapeHTML(text);
        
        // 处理列表
        return this.processLists(escapedText);
    },
    
    /**
     * 处理文本中的列表标记，转换为HTML列表
     * @param {string} text - 原始文本
     * @returns {string} 处理后的HTML
     */
    processLists: function(text) {
        if (!text) return '';
        
        const lines = text.split('\n');
        const result = [];
        
        // 跟踪列表状态
        let inOrderedList = false;
        let inUnorderedList = false;
        let currentOrderedNum = 0;
        
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i];
            
            // 检查无序列表项
            const ulMatch = line.match(/^([-*+]) (.*)$/);
            if (ulMatch) {
                if (!inUnorderedList) {
                    // 开始新的无序列表
                    inUnorderedList = true;
                    result.push('<ul>');
                }
                result.push(`<li>${ulMatch[2]}</li>`);
                continue;
            }
            
            // 检查有序列表项
            const olMatch = line.match(/^(\d+)\. (.*)$/);
            if (olMatch) {
                const itemNum = parseInt(olMatch[1], 10);
                
                if (!inOrderedList) {
                    // 开始新的有序列表
                    inOrderedList = true;
                    currentOrderedNum = itemNum;
                    result.push(`<ol start="${itemNum}">`);
                } else if (itemNum !== currentOrderedNum + 1) {
                    // 列表序号有跳跃，关闭当前列表并开始新列表
                    result.push('</ol>');
                    result.push(`<ol start="${itemNum}">`);
                    currentOrderedNum = itemNum;
                }
                
                result.push(`<li>${olMatch[2]}</li>`);
                currentOrderedNum = itemNum;
                continue;
            }
            
            // 不是列表项，关闭所有列表
            if (inUnorderedList) {
                result.push('</ul>');
                inUnorderedList = false;
            }
            
            if (inOrderedList) {
                result.push('</ol>');
                inOrderedList = false;
                currentOrderedNum = 0;
            }
            
            // 添加普通行
            result.push(line);
        }
        
        // 确保所有列表都被关闭
        if (inUnorderedList) {
            result.push('</ul>');
        }
        
        if (inOrderedList) {
            result.push('</ol>');
        }
        
        return result.join('\n');
    }
}; 