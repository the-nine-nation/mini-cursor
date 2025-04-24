/**
 * 聊天UI消息模块 - 处理消息渲染和显示
 */

// 确保ChatUI对象存在
if (typeof ChatUI === 'undefined') {
    ChatUI = {};
}

// 确保hljs对象存在并且正确初始化

// 扩展ChatUI对象
Object.assign(ChatUI, {
    /**
     * 使用Marked库渲染Markdown，带容错处理
     * @param {string} text - 需要渲染的Markdown文本
     * @returns {string} - 渲染后的HTML或原始文本
     */
    renderMarkdown: function(text) {
        if (!text) return '';
        
        try {
            // 尝试使用marked库渲染
            if (typeof marked !== 'undefined') {
                return marked.parse(text);
            } else {
                // 回退到简单的文本渲染
                console.warn('Marked库未加载，使用简单文本渲染');
                // 转义HTML
                const escapedText = this.escapeHTML(text);
                // 简单处理换行和代码块
                return escapedText
                    .replace(/\n/g, '<br>')
                    .replace(/```([^`]+)```/g, '<pre><code>$1</code></pre>');
            }
        } catch (error) {
            console.error('渲染Markdown时出错:', error);
            return this.escapeHTML(text);
        }
    },
    
    /**
     * 添加消息到聊天区域
     * @param {string} content - 消息内容
     * @param {string} type - 消息类型
     * @param {boolean} isUser - 是否是用户消息
     * @param {string} customClass - 自定义消息类名
     * @returns {HTMLElement} 消息容器元素
     */
    addMessage: function(content, type = '', isUser = false, customClass = '') {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;
        
        // 添加自定义类名
        if (customClass) {
            messageDiv.classList.add(customClass);
        }
        
        // 总是使用 pre 元素来保留格式
        const textContainer = document.createElement('pre');
        textContainer.className = 'message-text';
        textContainer.style.backgroundColor = 'transparent';
        textContainer.style.border = 'none';
        textContainer.style.padding = '0';
        textContainer.style.margin = '0';
        textContainer.style.fontFamily = 'inherit';
        textContainer.style.fontSize = 'inherit';
        textContainer.style.whiteSpace = 'pre-wrap';
        textContainer.style.wordBreak = 'break-word';
        textContainer.style.color = 'inherit';

        textContainer.textContent = content; // 直接设置文本内容
        messageDiv.appendChild(textContainer);
        
        const container = document.createElement('div');
        container.className = `message-container ${isUser ? 'user' : 'assistant'}`;
        
        if (!isUser) {
            const senderLabel = document.createElement('div');
            senderLabel.className = 'sender-label';
            senderLabel.textContent = 'AI助手';
            container.appendChild(senderLabel);
        } else {
            const senderLabel = document.createElement('div');
            senderLabel.className = 'sender-label';
            senderLabel.textContent = '您';
            container.appendChild(senderLabel);
        }
        
        container.appendChild(messageDiv);
        this.elements.messagesContainer.appendChild(container);
        this.elements.messagesContainer.scrollTop = this.elements.messagesContainer.scrollHeight;
        
        return container;
    },
    
    /**
     * 获取工具调用详情
     * @param {string} callId - 工具调用ID
     * @returns {Promise<Object>} 工具调用详情
     */
    getToolCallDetail: async function(callId) {
        try {
            const response = await fetch(`/tools/history/${callId}`);
            if (!response.ok) {
                throw new Error(`HTTP error ${response.status}`);
            }
            const data = await response.json();
            return data.tool_call;
        } catch (error) {
            console.error('Error fetching tool call detail:', error);
            return null;
        }
    },
    
    /**
     * 显示工具调用详情对话框
     * @param {string} callId - 工具调用ID
     */
    showToolCallDetail: async function(callId) {
        const toolCall = await this.getToolCallDetail(callId);
        if (!toolCall) {
            alert('无法获取工具调用详情');
            return;
        }
        
        // 创建模态对话框
        const modal = document.createElement('div');
        modal.className = 'tool-detail-modal';
        modal.innerHTML = `
            <div class="tool-detail-content">
                <div class="tool-detail-header">
                    <h3>工具调用详情</h3>
                    <button class="close-btn">&times;</button>
                </div>
                <div class="tool-detail-body">
                    <div class="tool-info">
                        <div class="tool-info-item">
                            <span class="label">工具名称:</span>
                            <span class="value">${toolCall.tool_name}</span>
                        </div>
                        <div class="tool-info-item">
                            <span class="label">调用时间:</span>
                            <span class="value">${new Date(toolCall.timestamp * 1000).toLocaleString()}</span>
                        </div>
                        ${toolCall.execution_time ? `
                        <div class="tool-info-item">
                            <span class="label">执行耗时:</span>
                            <span class="value">${toolCall.execution_time.toFixed(2)}s</span>
                        </div>
                        ` : ''}
                    </div>
                    <div class="tool-section">
                        <h4>参数</h4>
                        <pre>${JSON.stringify(toolCall.arguments, null, 2)}</pre>
                    </div>
                    <div class="tool-section">
                        <h4>结果</h4>
                        ${toolCall.error ? 
                            `<pre class="error">${this.escapeHTML(toolCall.error)}</pre>` : 
                            `<pre>${this.escapeHTML(typeof toolCall.result === 'string' ? 
                                toolCall.result : 
                                JSON.stringify(toolCall.result, null, 2))}</pre>`
                        }
                    </div>
                </div>
            </div>
        `;
        
        // 添加样式
        const style = document.createElement('style');
        style.textContent = `
            .tool-detail-modal {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0, 0, 0, 0.5);
                display: flex;
                justify-content: center;
                align-items: center;
                z-index: 1000;
            }
            .tool-detail-content {
                background-color: white;
                border-radius: 5px;
                width: 80%;
                max-width: 800px;
                max-height: 90%;
                overflow-y: auto;
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
            }
            .tool-detail-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 15px;
                border-bottom: 1px solid #eee;
            }
            .tool-detail-header h3 {
                margin: 0;
            }
            .close-btn {
                background: none;
                border: none;
                font-size: 20px;
                cursor: pointer;
            }
            .tool-detail-body {
                padding: 15px;
            }
            .tool-info {
                margin-bottom: 20px;
            }
            .tool-info-item {
                margin-bottom: 8px;
            }
            .tool-info-item .label {
                font-weight: bold;
                margin-right: 10px;
            }
            .tool-section {
                margin-bottom: 20px;
            }
            .tool-section h4 {
                margin-top: 0;
                margin-bottom: 10px;
            }
            .tool-section pre {
                background-color: #f5f5f5;
                padding: 10px;
                border-radius: 4px;
                overflow-x: auto;
                white-space: pre-wrap;
                word-wrap: break-word;
            }
            .error {
                color: #d32f2f;
            }
        `;
        document.head.appendChild(style);
        
        // 添加到文档
        document.body.appendChild(modal);
        
        // 关闭按钮事件
        modal.querySelector('.close-btn').addEventListener('click', () => {
            document.body.removeChild(modal);
        });
        
        // 点击遮罩层关闭
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                document.body.removeChild(modal);
            }
        });
    },
    
    /**
     * 检查内容是否看起来像格式化的数据库查询结果或类似内容
     * 简单的检查，可以根据需要扩展
     * @param {string} content - 要检查的内容
     * @returns {boolean} - 是否是需要保留格式的内容
     */
    isFormattedDatabaseContent: function(content) {
        if (!content) return false;
        
        // 检查是否是数据库相关内容或包含多行
        const dbErrorPatterns = [
            'Database error:',
            'Error executing query:',
            'Error getting schema:',
            'Total rows:',
            'ClickHouse',
            'MySQL',
            'Table:',
            'Available tables',
            '---'
        ];
        
        // 检查是否包含任何数据库相关内容或包含换行符
        return dbErrorPatterns.some(pattern => content.includes(pattern)) || content.includes('\n');
    },
    
    /**
     * 转义HTML特殊字符
     * @param {string} unsafe - 可能包含HTML的字符串
     * @returns {string} - 转义后的安全字符串
     */
    escapeHTML: function(unsafe) {
        return unsafe
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    },
    
    /**
     * 高亮代码块
     * @param {HTMLElement} container - 包含代码块的元素
     */
    highlightCode: function(container) {
        // Implementation of highlightCode function
    },
    
    /**
     * 添加用户消息
     * @param {string} message - 用户输入的消息
     */
    addUserMessage: function(message) {
        // Implementation of addUserMessage function
    },
    
    /**
     * 添加助手消息（非流式）
     * @param {string} message - 助手回复的消息
     */
    addAssistantMessage: function(message) {
        // Implementation of addAssistantMessage function
    },
    
    /**
     * 添加工具调用消息气泡
     * @param {string} toolName - 工具名称
     */
    addToolCallMessage: function(toolName) {
        // Implementation of addToolCallMessage function
    },
    
    /**
     * 添加工具结果消息气泡
     * @param {string} toolName - 工具名称
     */
    addToolResultMessage: function(toolName) {
        // Implementation of addToolResultMessage function
    },
    
    /**
     * 更新或添加助手流式消息
     * @param {string} content - 消息内容
     */
    updateAssistantMessage: function(content) {
        // Implementation of updateAssistantMessage function
    }
}); 