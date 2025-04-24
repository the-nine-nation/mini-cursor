// 等所有DOM元素加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    console.log('初始化历史对话管理功能...');
    
    // 确保所有需要的DOM元素都存在
    const historyBtn = document.getElementById('history-manager-btn');
    const historyDialog = document.getElementById('history-dialog');
    const historyOverlay = document.getElementById('history-overlay');
    const historyClose = document.getElementById('history-dialog-close');
    const historyList = document.getElementById('history-list');
    const historyLoading = document.getElementById('history-loading');
    const messagesContainer = document.getElementById('messages');
    
    if (!historyBtn || !historyDialog || !historyOverlay || !historyClose || !historyList || !historyLoading || !messagesContainer) {
        console.error('历史对话管理所需DOM元素不完整，无法初始化');
        return;
    }
    
    // 绑定事件
    historyBtn.addEventListener('click', function() {
        console.log('打开历史对话管理弹窗');
        historyDialog.style.display = 'flex';
        historyOverlay.style.display = 'block';
        loadConversationHistory();
    });
    
    historyClose.addEventListener('click', function() {
        console.log('关闭历史对话管理弹窗');
        historyDialog.style.display = 'none';
        historyOverlay.style.display = 'none';
    });
    
    historyOverlay.addEventListener('click', function() {
        console.log('点击遮罩层关闭弹窗');
        historyDialog.style.display = 'none';
        historyOverlay.style.display = 'none';
    });
    
    // 加载历史对话列表
    async function loadConversationHistory() {
        console.log('加载历史对话列表...');
        historyList.innerHTML = '';
        historyLoading.style.display = 'block';
        
        try {
            const data = await API.getAllConversations();
            console.log('获取到历史对话数据:', data.length, '条记录');
            historyLoading.style.display = 'none';
            
            if (data.length === 0) {
                historyList.innerHTML = '<div style="text-align: center; padding: 20px; color: #666;">暂无历史对话</div>';
                return;
            }
            
            // 显示历史对话列表
            data.forEach(conversation => {
                const li = document.createElement('li');
                li.className = 'history-item';
                li.dataset.id = conversation.id;
                
                const contentDiv = document.createElement('div');
                contentDiv.className = 'history-item-content';

                const title = document.createElement('div');
                title.className = 'history-item-title';
                title.textContent = conversation.title || `对话 ${conversation.id}`; // 添加后备标题
                
                const info = document.createElement('div');
                info.className = 'history-item-info';
                
                const date = document.createElement('span');
                date.className = 'history-item-date';
                date.textContent = formatDate(conversation.updated_at);
                
                const turns = document.createElement('span');
                turns.className = 'history-item-turns';
                turns.textContent = `${conversation.turns} 轮对话`;
                
                info.appendChild(date);
                info.appendChild(turns);
                
                contentDiv.appendChild(title);
                contentDiv.appendChild(info);

                // 删除按钮
                const deleteBtn = document.createElement('button');
                deleteBtn.className = 'history-item-delete';
                deleteBtn.innerHTML = '&times;';
                deleteBtn.title = '删除此对话';
                deleteBtn.addEventListener('click', (event) => {
                    event.stopPropagation(); // 防止触发加载对话的事件
                    deleteConversation(conversation.id, conversation.title || `对话 ${conversation.id}`, li);
                });

                li.appendChild(contentDiv);
                li.appendChild(deleteBtn);
                
                // 点击加载对话 (绑定到 contentDiv)
                contentDiv.addEventListener('click', function() {
                    console.log('加载对话:', conversation.id, conversation.title);
                    loadConversation(conversation.id, conversation.title || `对话 ${conversation.id}`);
                });
                
                historyList.appendChild(li);
            });
            
        } catch (error) {
            console.error('加载历史对话失败:', error);
            historyLoading.style.display = 'none';
            historyList.innerHTML = `<div style="text-align: center; padding: 20px; color: #c0392b;">加载失败: ${error.message}</div>`;
        }
    }
    
    // 加载特定对话
    async function loadConversation(conversationId, title) {
        console.log('开始加载对话:', conversationId, title);
        try {
            // 关闭对话框
            historyDialog.style.display = 'none';
            historyOverlay.style.display = 'none';
            
            // 清空当前消息区域并显示加载中
            // 保留工作路径信息
            const workspaceInfo = messagesContainer.querySelector('.message-info');
            messagesContainer.innerHTML = '';
            if (workspaceInfo) {
                messagesContainer.appendChild(workspaceInfo);
            }
            
            addInfoMessage(`正在加载对话: ${title}`);
            
            // 调用API加载对话到后端状态
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
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.message || '加载对话失败，服务器错误');
            }
            
            const result = await response.json();
            console.log('对话加载结果:', result);
            
            if (result.status === 'ok') {
                // 重新从后端获取并显示对话详情
                await loadConversationDetail(conversationId);
                addInfoMessage(`已加载对话: ${title} (${result.turns} 轮对话)`);
            } else {
                throw new Error(result.message || '加载对话失败');
            }
            
        } catch (error) {
            console.error('加载对话失败:', error);
            addErrorMessage(`加载对话失败: ${error.message}`);
        }
    }

    // 删除特定对话
    async function deleteConversation(conversationId, title, listItemElement) {
        console.log('尝试删除对话:', conversationId, title);
        if (!confirm(`确定要删除对话 "${title}" 吗？此操作无法撤销。`)) {
            return;
        }

        try {
            // 尝试先使用新API路径删除对话
            let response;
            try {
                response = await fetch(`/conversations/${conversationId}/delete`, {
                    method: 'POST',
                });
            } catch (e) {
                // 如果新API路径失败，尝试旧API路径
                console.log('新API路径删除失败，尝试旧API路径');
                response = await fetch('/conversations/delete', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ conversation_id: conversationId })
                });
            }

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.message || '删除对话失败，服务器错误');
            }

            const result = await response.json();
            console.log('对话删除结果:', result);

            if (result.status === 'ok') {
                console.log('对话删除成功，从列表中移除:', conversationId);
                // 从列表中移除该项
                listItemElement.remove();
                // 检查列表是否为空
                if (historyList.children.length === 0) {
                   historyList.innerHTML = '<div style="text-align: center; padding: 20px; color: #666;">暂无历史对话</div>';
                }
                // 可选：如果删除的是当前加载的对话，可以清空聊天界面或加载默认对话
                // if (isCurrentConversation(conversationId)) { ... }
            } else {
                throw new Error(result.message || '删除对话失败');
            }

        } catch (error) {
            console.error('删除对话失败:', error);
            alert(`删除对话 "${title}" 失败: ${error.message}`); // 使用alert提示用户
        }
    }
            
    // 获取并显示对话详情
    async function loadConversationDetail(conversationId) {
        console.log('获取对话详情:', conversationId);
        try {
            const data = await API.getConversationDetail(conversationId);
            console.log('获取到对话详情:', data);
            
            if (data.status !== 'ok' || !data.conversation) {
                throw new Error(data.message || '获取对话详情失败');
            }
            
            const conversation = data.conversation;

            // 清空现有内容 (确保在加载新内容前是空的，保留工作目录信息)
            const workspaceInfo = messagesContainer.querySelector('.message-info');
            messagesContainer.innerHTML = '';
            if (workspaceInfo) {
                messagesContainer.appendChild(workspaceInfo);
            } else {
                // 添加工作目录信息
                const workspacePath = document.getElementById('workspace-path');
                if (workspacePath) {
                     const workspaceInfoDiv = document.createElement('div');
                     workspaceInfoDiv.className = 'message-info';
                     workspaceInfoDiv.textContent = `当前工作目录: ${workspacePath.textContent || '未知'}`; 
                     messagesContainer.appendChild(workspaceInfoDiv);
                }
            }
            
            // Render messages
            if (typeof ChatUI !== 'undefined' && Array.isArray(conversation.messages)) {
                conversation.messages.forEach(msg => {
                    const role = msg.role || msg.type;
                    const content = msg.content || '';

                    try { // Add try-catch for individual message rendering
                        if (role === 'user') {
                            if (typeof ChatUI.addUserMessage === 'function') {
                                ChatUI.addUserMessage(content);
                            } else { console.warn('ChatUI.addUserMessage not found'); }
                        } else if (role === 'assistant') {
                             if (typeof ChatUI.addAssistantMessage === 'function') {
                                // Handle assistant messages, potentially with tool calls
                                // This might require checking msg.tool_calls and rendering appropriately
                                // If ChatUI.addAssistantMessage handles tool calls internally, this is fine.
                                // If not, we might need more complex logic like adding tool calls separately.
                                ChatUI.addAssistantMessage(content, msg.tool_calls || []);
                                // Note: Check if ChatUI.addAssistantMessage correctly renders tool calls visually.
                                // If it just shows placeholders, we might need to call addToolCallMessage/addToolResultMessage here.
                            } else { console.warn('ChatUI.addAssistantMessage not found'); }
                        } else if (role === 'tool_code') {
                             if (typeof ChatUI.addToolCallMessage === 'function') {
                                ChatUI.addToolCallMessage(msg.tool_name || 'tool_code', msg.tool_args || '{}');
                             } else { console.warn('ChatUI.addToolCallMessage not found'); }
                        } else if (role === 'tool_result') {
                             if (typeof ChatUI.addToolResultMessage === 'function') {
                                ChatUI.addToolResultMessage(msg.tool_name || 'tool_result', msg.tool_result || '', msg.is_error || false);
                             } else { console.warn('ChatUI.addToolResultMessage not found'); }
                        } else if (role === 'text') { // Explicitly handle 'text' type if it's just assistant text
                             if (typeof ChatUI.addAssistantMessage === 'function') {
                                ChatUI.addAssistantMessage(content); // Assume no tool calls for pure 'text' type
                            } else { console.warn('ChatUI.addAssistantMessage not found'); }
                        }
                         else {
                            console.warn(`Unhandled message role/type '${role}' during history load.`);
                            if (typeof ChatUI.addInfoMessage === 'function') {
                               ChatUI.addInfoMessage(`[${role}] ${content.substring(0, 100)}...`);
                            }
                        }
                    } catch (renderError) {
                        console.error(`Error rendering message (role: ${role}):`, msg, renderError);
                         if (typeof ChatUI.addErrorMessage === 'function') {
                             ChatUI.addErrorMessage(`渲染消息时出错: ${renderError.message}`);
                         }
                    }
                });
            } else {
                 if (!Array.isArray(conversation.messages)) {
                     console.error('Conversation messages format is not an array:', conversation.messages);
                      if (typeof ChatUI !== 'undefined' && typeof ChatUI.addErrorMessage === 'function') {
                         ChatUI.addErrorMessage('历史对话数据格式错误。');
                     }
                 }
                 if (typeof ChatUI === 'undefined') {
                    console.error('ChatUI is not defined. Cannot render historical messages.');
                    addErrorMessage('无法渲染历史消息：UI组件未定义'); // Use the local helper
                 }
            }

            // 设置滚动条到底部
            scrollToBottom();
            
        } catch (error) {
            console.error('获取对话详情失败:', error);
            addErrorMessage(`获取对话详情失败: ${error.message}`);
        }
    }
    
    // 辅助函数：添加信息消息
    function addInfoMessage(message) {
        if (typeof ChatUI !== 'undefined' && ChatUI.addInfoMessage) {
            ChatUI.addInfoMessage(message);
        } else {
            const infoDiv = document.createElement('div');
            infoDiv.className = 'message-info';
            infoDiv.textContent = message;
            messagesContainer.appendChild(infoDiv);
            scrollToBottom();
        }
    }
    
    // 辅助函数：添加错误消息
    function addErrorMessage(message) {
        if (typeof ChatUI !== 'undefined' && ChatUI.addErrorMessage) {
            ChatUI.addErrorMessage(message);
        } else {
            const errorDiv = document.createElement('div');
            errorDiv.className = 'message-error'; // 确保这个 class 有定义样式
            errorDiv.textContent = message;
            messagesContainer.appendChild(errorDiv);
            scrollToBottom();
        }
    }
    
    // 辅助函数：滚动到底部
    function scrollToBottom() {
        if (typeof ChatUI !== 'undefined' && ChatUI.scrollToBottom) {
            ChatUI.scrollToBottom();
        } else {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
    }
    
    // 辅助函数：格式化日期
    function formatDate(dateStr) {
        try {
            const date = new Date(dateStr);
            // 检查日期是否有效
            if (isNaN(date.getTime())) {
                return '无效日期';
            }
            return date.toLocaleString('zh-CN', { 
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit'
            });
        } catch (e) {
            console.error("日期格式化错误:", e);
            return dateStr; // 返回原始字符串以防万一
        }
    }
    
    console.log('历史对话管理功能初始化完成');
}); 