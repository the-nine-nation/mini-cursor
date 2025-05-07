/**
 * 聊天UI流式响应模块 - 处理聊天API的流式响应
 */

// 确保ChatUI对象存在
if (typeof ChatUI === 'undefined') {
    ChatUI = {};
}

// 扩展ChatUI对象
Object.assign(ChatUI, {
    /**
     * 处理流式响应
     * @param {Response} response - 流式响应对象
     */
    processStreamResponse: function(response) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        
        // 重置状态
        this.state = {
            currentResponseText: '',
            currentThinkingText: '',
            responseMessageContainer: null,
            thinkingMessageContainer: null,
            lastEventWasToolCall: false,
            currentAssistantContainer: null,
            pendingToolCalls: {}, // 确保初始化为空对象
            isThinkingFirst: true, // 标记思考过程应该先于回答显示
            lastEventType: null, // 追踪上一个事件类型
            messageContainers: [], // 用于跟踪按顺序创建的所有消息容器
        };
        
        // 添加调试信息
        console.log('Processing stream response');
        
        function processChunk(result) {
            if (result.done) {
                console.log('Stream complete');
                this.elements.sendButton.disabled = false;
                return;
            }
            
            // 解码接收到的数据块并添加到缓冲区
            buffer += decoder.decode(result.value, { stream: true });
            console.log('Received chunk:', buffer);
            
            // 处理完整的SSE事件
            const events = buffer.split('\n\n');
            buffer = events.pop() || ''; // 保留最后一个可能不完整的事件
            
            for (const event of events) {
                if (!event.trim()) continue;
                
                console.log('Processing event:', event);
                
                const lines = event.split('\n');
                const eventTypeMatch = lines[0].match(/^event:\s*(.+)$/);
                const eventDataMatch = lines[1]?.match(/^data:\s*(.+)$/);
                
                if (!eventTypeMatch) continue;
                
                const eventType = eventTypeMatch[1];
                console.log('Event type:', eventType);
                
                let eventData = {};
                
                // 处理data行
                if (eventDataMatch) {
                    try {
                        eventData = JSON.parse(eventDataMatch[1]);
                        console.log('Event data:', eventData);
                    } catch (e) {
                        console.error('Error parsing event data:', e);
                        continue;
                    }
                }
                
                // 处理tool_result的output行或tool_error的error行
                if (eventType === 'tool_result') {
                    const outputMatch = lines.find(line => line.startsWith('output:'));
                    if (outputMatch) {
                        // 提取output内容，保留原始格式包括换行符
                        const outputContent = outputMatch.substring('output:'.length + 1);
                        eventData.output = outputContent;
                        console.log('Tool result output:', outputContent);
                    }
                    
                    // 确保事件数据中有工具调用ID
                    if (eventData && !eventData.id && eventDataMatch) {
                        try {
                            const jsonData = JSON.parse(eventDataMatch[1]);
                            if (jsonData && jsonData.id) {
                                eventData.id = jsonData.id;
                            }
                        } catch (e) {
                            console.error('Error parsing id from event data:', e);
                        }
                    }
                    
                    // 检查如果output是数组格式，直接提取文本内容
                    if (Array.isArray(eventData.output)) {
                        console.log('Output is an array, extracting content');
                        if (eventData.output.length > 0) {
                            const firstItem = eventData.output[0];
                            if (typeof firstItem === 'object' && firstItem.text) {
                                console.log('Found text property in array item:', firstItem.text);
                                eventData.output = firstItem.text;
                            } else {
                                console.log('No text property found in array item, using as is');
                                eventData.output = JSON.stringify(eventData.output, null, 2);
                            }
                        }
                    }
                    
                    // 确保我们有一个输出，即使是空的
                    if (!eventData.output && !eventData.result) {
                        eventData.output = "No result";
                        console.log('Setting default output');
                    }
                } else if (eventType === 'tool_error') {
                    const errorMatch = lines.find(line => line.startsWith('error:'));
                    if (errorMatch) {
                        // 提取error内容，保留原始格式包括换行符
                        const errorContent = errorMatch.substring('error:'.length + 1);
                        eventData.error = errorContent;
                        console.log('Tool error content:', errorContent);
                    }
                    
                    // 确保事件数据中有工具调用ID
                    if (eventData && !eventData.id && eventDataMatch) {
                        try {
                            const jsonData = JSON.parse(eventDataMatch[1]);
                            if (jsonData && jsonData.id) {
                                eventData.id = jsonData.id;
                            }
                        } catch (e) {
                            console.error('Error parsing id from event data:', e);
                        }
                    }
                } else if (eventType === 'tool_call' && eventDataMatch) {
                    // 确保事件数据中有工具调用ID
                    try {
                        const jsonData = JSON.parse(eventDataMatch[1]);
                        if (jsonData && jsonData.id) {
                            eventData.id = jsonData.id;
                        }
                    } catch (e) {
                        console.error('Error parsing id from event data:', e);
                    }
                }
                
                this.handleEvent(eventType, eventData);
            }
            
            // 继续读取下一个数据块
            return reader.read().then(processChunk.bind(this));
        }
        
        return reader.read().then(processChunk.bind(this));
    },
    
    /**
     * 创建消息容器（通用方法）
     * @param {string} type - 消息类型
     * @param {string} className - 额外的CSS类名
     * @param {string} label - 标签文本（如果适用）
     * @return {Object} 包含容器元素和文本容器的对象
     */
    createMessageContainer: function(type, className, label) {
        const container = document.createElement('div');
        container.className = `message-container assistant ${className || ''}`;
        container.dataset.messageType = type;
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;
        
        // 如果有标签，添加标签元素
        if (label) {
            const labelElement = document.createElement('div');
            labelElement.className = `${type}-label`;
            labelElement.textContent = label;
            messageDiv.appendChild(labelElement);
        }
        
        // 创建文本容器
        const textContainer = document.createElement('pre');
        textContainer.className = 'message-text';
        textContainer.style.margin = '0';
        textContainer.style.fontFamily = 'inherit';
        textContainer.style.fontSize = 'inherit';
        textContainer.style.whiteSpace = 'pre-wrap';
        textContainer.style.wordBreak = 'break-word';
        
        messageDiv.appendChild(textContainer);
        container.appendChild(messageDiv);
        
        return {
            container: container,
            textContainer: textContainer,
            messageDiv: messageDiv
        };
    },
    
    /**
     * 查找或创建工具消息容器
     * @param {string} toolId - 工具调用ID
     * @return {HTMLElement} 工具消息容器
     */
    getToolContainer: function(toolId) {
        // 查找已有的工具容器
        if (toolId && this.state.pendingToolCalls && this.state.pendingToolCalls[toolId]) {
            const toolCall = this.state.pendingToolCalls[toolId];
            if (toolCall.container) {
                return toolCall.container;
            }
        }
        
        // 创建新的工具消息容器
        const elements = this.createMessageContainer('tool', 'tool-container');
        
        // 如果有工具ID，存储容器引用
        if (toolId && this.state.pendingToolCalls && this.state.pendingToolCalls[toolId]) {
            this.state.pendingToolCalls[toolId].container = elements.container;
        }
        
        // 将容器添加到消息列表
        this.elements.messagesContainer.appendChild(elements.container);
        
        // 添加到消息容器数组，保持时间顺序
        this.state.messageContainers.push({
            type: 'tool',
            id: toolId,
            container: elements.container
        });
        
        return elements;
    },
    
    /**
     * 处理事件
     * @param {string} eventType - 事件类型
     * @param {Object} eventData - 事件数据
     */
    handleEvent: function(eventType, eventData) {
        console.log(`Event: ${eventType}`, eventData);
        
        switch (eventType) {
            case 'start':
                // 初始化新响应
                this.state.currentResponseText = '';
                this.state.currentThinkingText = '';
                this.state.responseMessageContainer = null;
                this.state.thinkingMessageContainer = null;
                this.state.thinkingTextContainer = null;
                this.state.lastEventWasToolCall = false;
                this.state.currentAssistantContainer = null;
                this.state.messageContainers = [];
                this.state.lastEventType = 'start';
                break;
                
            case 'message':
                // 获取内容，用于检查是否有实际内容
                const content = eventData.content || eventData.text || '';
                
                // 只在有内容时处理容器创建
                if (content) {
                    // 如果最后一个事件不是消息事件，或者还没有创建消息容器
                    if (this.state.lastEventType !== 'message' || !this.state.responseMessageContainer) {
                        // 创建新的消息容器
                        const elements = this.createMessageContainer('response', 'final-response');
                        
                        // 将容器添加到消息列表
                        this.elements.messagesContainer.appendChild(elements.container);
                        
                        // 设置当前响应容器引用
                        this.state.responseMessageContainer = elements.textContainer;
                        this.state.currentAssistantContainer = elements.container;
                        
                        // 重置响应文本
                        this.state.currentResponseText = '';
                        
                        // 添加到消息容器数组，保持时间顺序
                        this.state.messageContainers.push({
                            type: 'message',
                            container: elements.container
                        });
                    }
                    
                    // 追加新内容
                    this.state.currentResponseText += content;
                    
                    // 更新显示内容
                    if (this.isFormattedDatabaseContent(this.state.currentResponseText)) {
                        // 直接使用文本内容，不使用renderMarkdown
                        this.state.responseMessageContainer.textContent = this.state.currentResponseText;
                    } else {
                        // 使用Markdown处理，支持列表格式
                        this.state.responseMessageContainer.innerHTML = this.processMarkdown(this.state.currentResponseText);
                    }
                    
                    // 滚动到底部
                    this.elements.messagesContainer.scrollTop = this.elements.messagesContainer.scrollHeight;
                }
                
                // 更新最后事件类型
                this.state.lastEventType = 'message';
                this.state.lastEventWasToolCall = false;
                break;
                
            case 'thinking':
                // 获取思考内容
                const thinkingContent = eventData.content || eventData.text || '';
                
                // 只在有内容时处理
                if (thinkingContent) {
                    // 如果最后一个事件不是thinking事件，或者还没有创建思考容器
                    if (this.state.lastEventType !== 'thinking' || !this.state.thinkingMessageContainer) {
                        // 创建新的思考容器
                        const elements = this.createMessageContainer('thinking', 'thinking-container', '思考过程');
                        
                        // 将容器添加到消息列表
                        this.elements.messagesContainer.appendChild(elements.container);
                        
                        // 设置当前思考容器引用
                        this.state.thinkingMessageContainer = elements.container;
                        this.state.thinkingTextContainer = elements.textContainer;
                        
                        // 重置思考文本
                        this.state.currentThinkingText = '';
                        
                        // 添加到消息容器数组，保持时间顺序
                        this.state.messageContainers.push({
                            type: 'thinking',
                            container: elements.container
                        });
                    }
                    
                    // 追加新内容
                    this.state.currentThinkingText += thinkingContent;
                    
                    // 更新显示内容
                    this.state.thinkingTextContainer.textContent = this.state.currentThinkingText;
                    
                    // 滚动到底部
                    this.elements.messagesContainer.scrollTop = this.elements.messagesContainer.scrollHeight;
                }
                
                // 更新最后事件类型
                this.state.lastEventType = 'thinking';
                break;
                
            case 'tool_call':
                // 获取工具调用信息
                const toolName = eventData.name || eventData.tool || 'unknown_tool';
                const toolArgs = eventData.input || eventData.params || eventData.arguments || {};
                const toolId = eventData.id;
                
                // 创建工具调用容器
                let toolContainer;
                
                // 如果有ID，保存工具调用信息
                if (toolId) {
                    // 确保pendingToolCalls已初始化
                    if (!this.state.pendingToolCalls) {
                        this.state.pendingToolCalls = {};
                    }
                    
                    // 保存工具调用信息
                    this.state.pendingToolCalls[toolId] = {
                        name: toolName,
                        arguments: toolArgs,
                        id: toolId
                    };
                    
                    console.log('Pending tool call saved:', this.state.pendingToolCalls[toolId]);
                    
                    // 创建新的工具消息容器
                    const elements = this.getToolContainer(toolId);
                    toolContainer = elements.container;
                    
                    // 添加工具调用信息到容器
                    this.addToolBubble(
                        elements.container,
                        'tool-call',
                        `调用工具: ${toolName}`,
                        toolArgs ? JSON.stringify(toolArgs, null, 2) : null,
                        toolId
                    );
                } else {
                    // 如果没有ID，创建简单的工具调用消息
                    const elements = this.createMessageContainer('tool', 'tool-container');
                    this.elements.messagesContainer.appendChild(elements.container);
                    
                    // 添加工具调用信息到容器
                    this.addToolBubble(
                        elements.container,
                        'tool-call',
                        `调用工具: ${toolName}`,
                        toolArgs ? JSON.stringify(toolArgs, null, 2) : null,
                        null
                    );
                    
                    toolContainer = elements.container;
                    
                    // 添加到消息容器数组，保持时间顺序
                    this.state.messageContainers.push({
                        type: 'tool',
                        container: elements.container
                    });
                }
                
                // 更新最后事件类型和标记
                this.state.lastEventType = 'tool_call';
                this.state.lastEventWasToolCall = true;
                
                // 滚动到底部
                this.elements.messagesContainer.scrollTop = this.elements.messagesContainer.scrollHeight;
                break;
                
            case 'tool_result':
                // 检查是否有匹配的工具调用
                if (eventData && eventData.id && this.state.pendingToolCalls && this.state.pendingToolCalls[eventData.id]) {
                    const toolCall = this.state.pendingToolCalls[eventData.id];
                    const toolOutput = eventData.output || eventData.result || "No result";
                    
                    // 获取工具调用的容器
                    let elements = this.getToolContainer(eventData.id);
                    
                    // 添加工具结果信息到容器
                    this.addToolBubble(
                        elements.container,
                        'tool-result',
                        `工具结果: ${toolCall.name || 'unknown_tool'}`,
                        toolOutput,
                        eventData.id
                    );
                    
                    // 移除已处理的工具调用
                    delete this.state.pendingToolCalls[eventData.id];
                } else {
                    // 如果没有匹配的工具调用，创建新的工具结果消息
                    const elements = this.createMessageContainer('tool', 'tool-container');
                    this.elements.messagesContainer.appendChild(elements.container);
                    
                    // 添加工具结果信息到容器
                    this.addToolBubble(
                        elements.container,
                        'tool-result',
                        `工具结果: ${eventData ? (eventData.name || eventData.tool || 'unknown_tool') : 'unknown_tool'}`,
                        eventData ? (eventData.output || eventData.result || "No result") : "No result",
                        eventData ? eventData.id : null
                    );
                    
                    // 添加到消息容器数组，保持时间顺序
                    this.state.messageContainers.push({
                        type: 'tool',
                        container: elements.container
                    });
                }
                
                // 更新最后事件类型和标记
                this.state.lastEventType = 'tool_result';
                this.state.lastEventWasToolCall = true;
                
                // 滚动到底部
                this.elements.messagesContainer.scrollTop = this.elements.messagesContainer.scrollHeight;
                break;
                
            case 'tool_error':
                // 检查是否有匹配的工具调用
                if (eventData && eventData.id && this.state.pendingToolCalls && this.state.pendingToolCalls[eventData.id]) {
                    const toolCall = this.state.pendingToolCalls[eventData.id];
                    const toolError = eventData.error || eventData.message || "未知错误";
                    
                    // 获取工具调用的容器
                    let elements = this.getToolContainer(eventData.id);
                    
                    // 添加工具错误信息到容器
                    this.addToolBubble(
                        elements.container,
                        'tool-error',
                        `工具错误: ${toolCall.name || 'unknown_tool'}`,
                        toolError,
                        eventData.id
                    );
                    
                    // 移除已处理的工具调用
                    delete this.state.pendingToolCalls[eventData.id];
                } else {
                    // 如果没有匹配的工具调用，创建新的工具错误消息
                    const elements = this.createMessageContainer('tool', 'tool-container');
                    this.elements.messagesContainer.appendChild(elements.container);
                    
                    // 添加工具错误信息到容器
                    this.addToolBubble(
                        elements.container,
                        'tool-error',
                        `工具错误`,
                        eventData ? (eventData.error || eventData.message || "未知错误") : "未知错误",
                        eventData ? eventData.id : null
                    );
                    
                    // 添加到消息容器数组，保持时间顺序
                    this.state.messageContainers.push({
                        type: 'tool',
                        container: elements.container
                    });
                }
                
                // 更新最后事件类型和标记
                this.state.lastEventType = 'tool_error';
                this.state.lastEventWasToolCall = true;
                
                // 滚动到底部
                this.elements.messagesContainer.scrollTop = this.elements.messagesContainer.scrollHeight;
                break;
                
            case 'error':
                // 添加错误消息
                const errorMessage = eventData.error || eventData.message || "未知错误";
                this.addErrorMessage(`错误: ${errorMessage}`);
                this.elements.sendButton.disabled = false;
                this.state.lastEventType = 'error';
                break;
                
            case 'done':
            case 'end':
                // 流式输出完成，处理响应文本以移除多余空行
                if (this.state.responseMessageContainer && this.state.currentResponseText) {
                    // 移除多余空行
                    const strippedText = this.stripExtraEmptyLines(this.state.currentResponseText);
                    
                    // 更新显示内容
                    if (this.isFormattedDatabaseContent(strippedText)) {
                        // 直接使用文本内容，不使用renderMarkdown
                        this.state.responseMessageContainer.textContent = strippedText;
                    } else {
                        // 使用Markdown处理，支持列表格式
                        this.state.responseMessageContainer.innerHTML = this.processMarkdown(strippedText);
                    }
                    
                    // 保存处理后的文本
                    this.state.currentResponseText = strippedText;
                }
                
                // 处理思考内容以移除多余空行
                if (this.state.thinkingTextContainer && this.state.currentThinkingText) {
                    // 移除多余空行
                    const strippedThinkingText = this.stripExtraEmptyLines(this.state.currentThinkingText);
                    
                    // 更新显示内容
                    this.state.thinkingTextContainer.textContent = strippedThinkingText;
                    
                    // 保存处理后的文本
                    this.state.currentThinkingText = strippedThinkingText;
                }
                
                // 清理空白消息容器
                this.cleanupEmptyContainers();
                
                // 启用发送按钮
                this.elements.sendButton.disabled = false;
                this.state.lastEventType = eventType;
                break;
        }
    },
    
    /**
     * 清理空白消息容器
     */
    cleanupEmptyContainers: function() {
        // 遍历所有消息容器，移除空的容器
        for (let i = 0; i < this.state.messageContainers.length; i++) {
            const containerInfo = this.state.messageContainers[i];
            const container = containerInfo.container;
            
            // 检查容器是否为空
            if (container && (!container.textContent || container.textContent.trim() === '')) {
                // 检查容器是否包含工具调用
                const hasTools = container.querySelector('.tool-bubble');
                
                // 如果容器为空且不包含工具调用，移除它
                if (!hasTools) {
                    if (container.parentNode) {
                        container.parentNode.removeChild(container);
                    }
                    
                    // 从数组中移除引用
                    this.state.messageContainers.splice(i, 1);
                    i--; // 调整索引
                    
                    // 重置相关引用
                    if (container === this.state.thinkingMessageContainer) {
                        this.state.thinkingMessageContainer = null;
                        this.state.thinkingTextContainer = null;
                    } else if (container === this.state.currentAssistantContainer) {
                        this.state.currentAssistantContainer = null;
                        this.state.responseMessageContainer = null;
                    }
                }
            }
        }
    },
    
    /**
     * 移除文本中多余的空行
     * @param {string} text - 要处理的文本
     * @return {string} 处理后的文本
     */
    stripExtraEmptyLines: function(text) {
        if (!text) return text;
        
        // 分割成行
        let lines = text.split('\n');
        
        // 移除开头的空行
        while (lines.length > 0 && lines[0].trim() === '') {
            lines.shift();
        }
        
        // 移除结尾的空行
        while (lines.length > 0 && lines[lines.length - 1].trim() === '') {
            lines.pop();
        }
        
        // 处理中间的连续空行（将多个连续空行替换为单个空行）
        let result = [];
        let previousLineEmpty = false;
        
        for (const line of lines) {
            const isEmpty = line.trim() === '';
            
            if (isEmpty && previousLineEmpty) {
                // 跳过连续的空行
                continue;
            }
            
            result.push(line);
            previousLineEmpty = isEmpty;
        }
        
        return result.join('\n');
    }
}); 