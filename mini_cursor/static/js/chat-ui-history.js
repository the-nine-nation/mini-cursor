/**
 * 聊天UI历史对话管理模块 - 处理历史对话加载与展示
 */

// 确保ChatUI对象存在
if (typeof ChatUI === 'undefined') {
    ChatUI = {};
}

// 扩展ChatUI对象，添加历史对话管理相关功能
Object.assign(ChatUI, {
    /**
     * 历史对话管理的DOM元素
     */
    historyElements: {
        historyBtn: null,
        historyDialog: null,
        historyOverlay: null,
        historyClose: null,
        historyList: null,
        historyLoading: null
    },
    
    /**
     * 初始化历史对话管理功能
     */
    initHistoryManager: function() {
        console.log('Initializing history manager...');
        
        // 确保核心UI元素已初始化
        if (!this.elements || !this.elements.messagesContainer) {
            console.error('核心UI元素未初始化，无法启用历史对话管理功能');
            return;
        }
        
        // 确保引用的DOM元素存在
        if (!document.getElementById('history-manager-btn')) {
            console.error('历史对话管理按钮未找到');
            return;
        }
        
        // 初始化DOM元素引用
        this.historyElements.historyBtn = document.getElementById('history-manager-btn');
        this.historyElements.historyDialog = document.getElementById('history-dialog');
        this.historyElements.historyOverlay = document.getElementById('history-overlay');
        this.historyElements.historyClose = document.getElementById('history-dialog-close');
        this.historyElements.historyList = document.getElementById('history-list');
        this.historyElements.historyLoading = document.getElementById('history-loading');
        
        // 确保所有元素都存在
        for (const key in this.historyElements) {
            if (!this.historyElements[key]) {
                console.error(`历史对话管理元素未找到: ${key}`);
                return;
            }
        }
        
        // 绑定事件
        this.historyElements.historyBtn.addEventListener('click', () => {
            this.openHistoryDialog();
        });
        
        this.historyElements.historyClose.addEventListener('click', () => {
            this.closeHistoryDialog();
        });
        
        this.historyElements.historyOverlay.addEventListener('click', () => {
            this.closeHistoryDialog();
        });
        
        console.log('历史对话管理功能已初始化');
    },
    
    /**
     * 打开历史对话管理弹窗
     */
    openHistoryDialog: function() {
        this.historyElements.historyDialog.style.display = 'flex';
        this.historyElements.historyOverlay.style.display = 'block';
        this.loadConversationHistory();
    },
    
    /**
     * 关闭历史对话管理弹窗
     */
    closeHistoryDialog: function() {
        this.historyElements.historyDialog.style.display = 'none';
        this.historyElements.historyOverlay.style.display = 'none';
    },
    
    /**
     * 加载历史对话列表
     */
    loadConversationHistory: async function() {
        this.historyElements.historyList.innerHTML = '';
        this.historyElements.historyLoading.style.display = 'block';
        
        try {
            const data = await API.getAllConversations();
            this.historyElements.historyLoading.style.display = 'none';
            
            if (data.length === 0) {
                this.historyElements.historyList.innerHTML = '<div style="text-align: center; padding: 20px; color: #666;">暂无历史对话</div>';
                return;
            }
            
            // 显示历史对话列表
            data.forEach(conversation => {
                const li = document.createElement('li');
                li.className = 'history-item';
                li.dataset.id = conversation.id;
                
                // 创建主要内容区域
                const contentWrapper = document.createElement('div');
                contentWrapper.className = 'history-item-content'; // 用于flex布局

                const title = document.createElement('div');
                title.className = 'history-item-title';
                title.textContent = conversation.title;
                
                const info = document.createElement('div');
                info.className = 'history-item-info';
                
                const date = document.createElement('span');
                date.className = 'history-item-date';
                date.textContent = this.formatDate(conversation.updated_at);
                
                const turns = document.createElement('span');
                turns.className = 'history-item-turns';
                turns.textContent = `${conversation.turns} 轮对话`;
                
                info.appendChild(date);
                info.appendChild(turns);

                contentWrapper.appendChild(title);
                contentWrapper.appendChild(info);
                li.appendChild(contentWrapper);
                
                // 创建删除按钮
                const deleteBtn = document.createElement('button');
                deleteBtn.className = 'history-item-delete';
                deleteBtn.innerHTML = '&times;'; // 使用 '×' 符号
                deleteBtn.title = '删除此对话'; // 添加tooltip
                
                // 点击删除按钮的事件处理
                deleteBtn.addEventListener('click', (e) => {
                    e.stopPropagation(); // 阻止事件冒泡到li元素，避免加载对话
                    this.handleDeleteConversation(conversation.id, li);
                });
                
                li.appendChild(deleteBtn); // 将删除按钮添加到li
                
                // 点击列表项加载对话 (只在内容区域响应)
                contentWrapper.addEventListener('click', () => {
                    this.loadConversation(conversation.id, conversation.title);
                });
                
                this.historyElements.historyList.appendChild(li);
            });
            
        } catch (error) {
            console.error('加载历史对话失败:', error);
            this.historyElements.historyLoading.style.display = 'none';
            this.historyElements.historyList.innerHTML = `<div style="text-align: center; padding: 20px; color: #c0392b;">加载失败: ${error.message}</div>`;
        }
    },
    
    /**
     * 处理删除对话的请求
     * @param {string} conversationId - 要删除的对话ID
     * @param {HTMLElement} listItemElement - 对应的列表项元素
     */
    handleDeleteConversation: async function(conversationId, listItemElement) {
        if (!conversationId) return;
        
        // 确认删除
        if (!confirm('确定要删除这条历史对话吗？此操作不可恢复。')) {
            return;
        }
        
        try {
            // 调用API删除对话 (需要先在api.js中添加此函数)
            const response = await API.deleteConversation(conversationId);
            
            if (response.status === 'ok') {
                // 从列表中移除
                listItemElement.remove();
                // 显示成功提示
                if (typeof this.showAlert === 'function') {
                    this.showAlert('对话已成功删除', 'success');
                } else {
                    alert('对话已成功删除');
                }
                // 如果列表为空，显示提示
                if (this.historyElements.historyList.children.length === 0) {
                     this.historyElements.historyList.innerHTML = '<div style="text-align: center; padding: 20px; color: #666;">暂无历史对话</div>';
                }
            } else {
                throw new Error(response.message || '删除对话失败');
            }
        } catch (error) {
            console.error('删除对话失败:', error);
            if (typeof this.showAlert === 'function') {
                 this.showAlert(`删除对话失败: ${error.message}`, 'error');
            } else {
                alert(`删除对话失败: ${error.message}`);
            }
        }
    },
    
    /**
     * 加载特定对话
     * @param {string} conversationId - 对话ID
     * @param {string} title - 对话标题
     */
    loadConversation: async function(conversationId, title) {
        try {
            // 确保核心UI元素已初始化
            if (!this.elements || !this.elements.messagesContainer) {
                console.error('核心UI元素未初始化，无法加载对话');
                this.closeHistoryDialog();
                alert('系统错误：核心UI元素未初始化，无法加载对话');
                return;
            }
            
            // 关闭对话框
            this.closeHistoryDialog();
            
            // 显示加载中消息
            const infoDiv = document.createElement('div');
            infoDiv.className = 'message-info';
            infoDiv.textContent = `正在加载对话: ${title}`;
            this.elements.messagesContainer.appendChild(infoDiv);
            this.elements.messagesContainer.scrollTop = this.elements.messagesContainer.scrollHeight;
            
            // 调用API加载对话
            const response = await fetch('/conversations/load', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    conversation_id: conversationId
                })
            });
            
            if (!response.ok) {
                throw new Error('加载对话失败');
            }
            
            const result = await response.json();
            
            if (result.status === 'ok') {
                // 清空当前消息区域
                this.elements.messagesContainer.innerHTML = '';
                
                // 获取对话详情并显示
                await this.loadConversationDetail(conversationId);
                
                // 添加成功加载消息
                const successInfoDiv = document.createElement('div');
                successInfoDiv.className = 'message-info';
                successInfoDiv.textContent = `已加载对话: ${title} (${result.turns} 轮对话)`;
                this.elements.messagesContainer.appendChild(successInfoDiv);
                this.elements.messagesContainer.scrollTop = this.elements.messagesContainer.scrollHeight;
            } else {
                throw new Error(result.message || '加载对话失败');
            }
            
        } catch (error) {
            console.error('加载对话失败:', error);
            const errorDiv = document.createElement('div');
            errorDiv.className = 'message-error';
            errorDiv.textContent = `加载对话失败: ${error.message}`;
            this.elements.messagesContainer.appendChild(errorDiv);
            this.elements.messagesContainer.scrollTop = this.elements.messagesContainer.scrollHeight;
        }
    },
    
    /**
     * 获取并显示对话详情
     * @param {string} conversationId - 对话ID
     */
    loadConversationDetail: async function(conversationId) {
        // 确保核心UI元素已初始化
        if (!this.elements || !this.elements.messagesContainer) {
            console.error('核心UI元素未初始化，无法加载对话详情');
            alert('系统错误：核心UI元素未初始化，无法加载对话详情');
            return;
        }
        
        try {
            const data = await API.getConversationDetail(conversationId);
            
            if (data.status !== 'ok' || !data.conversation) {
                throw new Error(data.message || '获取对话详情失败');
            }
            
            const conversation = data.conversation;
            
            // 首先添加系统提示信息
            if (conversation.system_prompt) {
                const infoDiv = document.createElement('div');
                infoDiv.className = 'message-info';
                infoDiv.textContent = `系统提示: ${conversation.system_prompt}`;
                this.elements.messagesContainer.appendChild(infoDiv);
            }
            
            // 添加对话消息
            if (conversation.messages && conversation.messages.length > 0) {
                console.log('渲染对话消息:', conversation.messages.length, '条');
                
                conversation.messages.forEach(msg => {
                    // 调试输出每条消息的内容
                    console.log('处理消息类型:', msg.type, '内容:', msg);
                    
                    if (msg.type === 'user') {
                        console.log('渲染用户消息');
                        // 添加用户消息
                        const container = document.createElement('div');
                        container.className = 'message-container user';
                        
                        const senderLabel = document.createElement('div');
                        senderLabel.className = 'sender-label';
                        senderLabel.textContent = '您';
                        
                        const message = document.createElement('div');
                        message.className = 'message';
                        
                        // 创建文本容器
                        const textContainer = document.createElement('pre');
                        textContainer.className = 'message-text';
                        textContainer.textContent = msg.content || ''; // 添加空字符串兜底
                        
                        message.appendChild(textContainer);
                        container.appendChild(senderLabel);
                        container.appendChild(message);
                        this.elements.messagesContainer.appendChild(container);
                    } 
                    else if (msg.type === 'assistant') {
                        console.log('渲染助手消息');
                        // 添加助手消息
                        const container = document.createElement('div');
                        container.className = 'message-container assistant';
                        
                        const senderLabel = document.createElement('div');
                        senderLabel.className = 'sender-label';
                        senderLabel.textContent = 'AI助手';
                        
                        const message = document.createElement('div');
                        message.className = 'message';
                        
                        // 创建文本容器
                        const textContainer = document.createElement('pre');
                        textContainer.className = 'message-text';
                        textContainer.textContent = msg.content || ''; // 添加空字符串兜底
                        
                        message.appendChild(textContainer);
                        container.appendChild(senderLabel);
                        container.appendChild(message);
                        this.elements.messagesContainer.appendChild(container);
                    } 
                    else if (msg.type === 'tool') {
                        console.log('渲染工具消息:', msg.tool_name);
                        // 添加工具消息
                        this.renderToolMessage(
                            msg.tool_name || '未命名工具',
                            msg.tool_args || '{}',
                            msg.tool_result || '无结果'
                        );
                    }
                    else {
                        console.warn('未知消息类型:', msg.type, msg);
                    }
                });
            } else {
                console.warn('对话消息列表为空');
            }
            
            // 滚动到底部
            this.elements.messagesContainer.scrollTop = this.elements.messagesContainer.scrollHeight;
            
        } catch (error) {
            console.error('获取对话详情失败:', error);
            const errorDiv = document.createElement('div');
            errorDiv.className = 'message-error';
            errorDiv.textContent = `获取对话详情失败: ${error.message}`;
            this.elements.messagesContainer.appendChild(errorDiv);
            this.elements.messagesContainer.scrollTop = this.elements.messagesContainer.scrollHeight;
        }
    },
    
    /**
     * 渲染工具调用消息
     * @param {string} toolName - 工具名称
     * @param {string|object} toolArgs - 工具参数（字符串或对象）
     * @param {string|object} toolResult - 工具结果（字符串或对象）
     */
    renderToolMessage: function(toolName, toolArgs, toolResult) {
        console.log('渲染工具消息:', toolName);
        
        // 创建工具消息容器
        const container = document.createElement('div');
        container.className = 'message-container tool';
        
        // 创建工具标题
        const toolHeader = document.createElement('div');
        toolHeader.className = 'tool-header';
        
        // 工具名称
        const toolNameElement = document.createElement('div');
        toolNameElement.className = 'tool-name';
        toolNameElement.textContent = `工具调用: ${toolName}`;
        toolHeader.appendChild(toolNameElement);
        
        // 创建工具内容容器
        const toolContent = document.createElement('div');
        toolContent.className = 'tool-content';
        
        // 添加参数部分
        const argsContainer = document.createElement('div');
        argsContainer.className = 'tool-args';
        
        const argsTitle = document.createElement('div');
        argsTitle.className = 'tool-section-title';
        argsTitle.textContent = '参数:';
        argsContainer.appendChild(argsTitle);
        
        const argsValue = document.createElement('pre');
        argsValue.className = 'tool-args-value';
        
        // 尝试解析和格式化参数
        try {
            let formattedArgs;
            if (typeof toolArgs === 'string') {
                // 尝试将字符串解析为JSON对象
                try {
                    const parsedArgs = JSON.parse(toolArgs);
                    formattedArgs = JSON.stringify(parsedArgs, null, 2);
                } catch (e) {
                    // 如果不是有效的JSON，则原样显示
                    formattedArgs = toolArgs;
                }
            } else if (typeof toolArgs === 'object') {
                // 如果已经是对象，则格式化为JSON字符串
                formattedArgs = JSON.stringify(toolArgs, null, 2);
            } else {
                // 其他情况
                formattedArgs = String(toolArgs || '');
            }
            argsValue.textContent = formattedArgs;
        } catch (error) {
            console.error('格式化工具参数失败:', error);
            argsValue.textContent = '无法显示参数';
        }
        
        argsContainer.appendChild(argsValue);
        toolContent.appendChild(argsContainer);
        
        // 添加结果部分
        const resultContainer = document.createElement('div');
        resultContainer.className = 'tool-result';
        
        const resultTitle = document.createElement('div');
        resultTitle.className = 'tool-section-title';
        resultTitle.textContent = '结果:';
        resultContainer.appendChild(resultTitle);
        
        const resultValue = document.createElement('pre');
        resultValue.className = 'tool-result-value';
        
        // 尝试解析和格式化结果
        try {
            let formattedResult;
            if (typeof toolResult === 'string') {
                // 尝试将字符串解析为JSON对象
                try {
                    const parsedResult = JSON.parse(toolResult);
                    formattedResult = JSON.stringify(parsedResult, null, 2);
                } catch (e) {
                    // 如果不是有效的JSON，则原样显示
                    formattedResult = toolResult;
                }
            } else if (typeof toolResult === 'object') {
                // 如果已经是对象，则格式化为JSON字符串
                formattedResult = JSON.stringify(toolResult, null, 2);
            } else {
                // 其他情况
                formattedResult = String(toolResult || '');
            }
            resultValue.textContent = formattedResult;
        } catch (error) {
            console.error('格式化工具结果失败:', error);
            resultValue.textContent = '无法显示结果';
        }
        
        resultContainer.appendChild(resultValue);
        toolContent.appendChild(resultContainer);
        
        // 组装消息
        container.appendChild(toolHeader);
        container.appendChild(toolContent);
        
        // 添加到消息容器
        this.elements.messagesContainer.appendChild(container);
    },
    
    /**
     * 格式化日期
     * @param {string} dateStr - 日期字符串
     * @returns {string} 格式化后的日期字符串
     */
    formatDate: function(dateStr) {
        const date = new Date(dateStr);
        return date.toLocaleString('zh-CN', { 
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    }
}); 