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
                this.state.lastEventWasToolCall = false;
                // 不再在这里创建助手消息容器，等待思考或消息事件
                this.state.currentAssistantContainer = null;
                break;
                
            case 'message':
                // 如果是第一次收到消息事件，并且还没有显示过思考内容
                if (this.state.isThinkingFirst && !this.state.thinkingMessageContainer && !this.state.responseMessageContainer) {
                    // 先创建最终回答的容器，但放在后面
                    this.state.currentAssistantContainer = this.addMessage('', '', false, 'final-response');
                } else if (this.state.lastEventWasToolCall) {
                    // 在工具调用之后，创建新的消息容器
                    this.state.currentAssistantContainer = this.addMessage('', '', false, 'final-response');
                    this.state.lastEventWasToolCall = false;
                } else if (!this.state.responseMessageContainer && !this.state.currentAssistantContainer) {
                    // 如果还没有创建任何消息容器
                    this.state.currentAssistantContainer = this.addMessage('', '', false, 'final-response');
                }
                
                // 获取消息元素
                if (this.state.currentAssistantContainer && !this.state.responseMessageContainer) {
                    const messageElement = this.state.currentAssistantContainer.querySelector('.message');
                    if (messageElement) {
                        const textContainer = messageElement.querySelector('.message-text');
                        if (textContainer) {
                            this.state.responseMessageContainer = textContainer;
                        }
                    }
                }
                
                // 追加新内容
                const content = eventData.content || eventData.text || '';
                this.state.currentResponseText += content;
                if (this.state.responseMessageContainer) {
                    // 检查内容是否需要保留格式（如数据库内容）
                    if (this.isFormattedDatabaseContent(this.state.currentResponseText)) {
                        // 直接使用文本内容，不使用renderMarkdown
                        this.state.responseMessageContainer.textContent = this.state.currentResponseText;
                    } else {
                        // 使用Markdown处理，支持列表格式
                        this.state.responseMessageContainer.innerHTML = this.processMarkdown(this.state.currentResponseText);
                    }
                }
                this.elements.messagesContainer.scrollTop = this.elements.messagesContainer.scrollHeight;
                break;
                
            case 'thinking':
                // 思考内容放在上方的消息中，使用显眼的黄色背景
                if (!this.state.thinkingMessageContainer) {
                    const container = document.createElement('div');
                    container.className = 'message-container assistant thinking-container'; // 添加thinking-container类
                    const messageDiv = document.createElement('div');
                    messageDiv.className = 'message thinking';
                    
                    // 添加思考标识
                    const thinkingLabel = document.createElement('div');
                    thinkingLabel.className = 'thinking-label';
                    thinkingLabel.textContent = '思考过程';
                    messageDiv.appendChild(thinkingLabel);
                    
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
                    
                    this.elements.messagesContainer.appendChild(container);
                    this.state.thinkingMessageContainer = container;
                    this.state.thinkingTextContainer = textContainer;
                }
                
                // 追加新内容
                const thinkingContent = eventData.content || eventData.text || '';
                this.state.currentThinkingText += thinkingContent;
                
                // 直接设置文本内容，不使用renderMarkdown
                if (this.state.thinkingTextContainer) {
                    this.state.thinkingTextContainer.textContent = this.state.currentThinkingText;
                }
                
                this.elements.messagesContainer.scrollTop = this.elements.messagesContainer.scrollHeight;
                break;
                
            case 'tool_call':
                // 检查当前消息容器是否已经有文本内容
                const hasTextContent = this.state.responseMessageContainer && 
                                       this.state.responseMessageContainer.textContent && 
                                       this.state.responseMessageContainer.textContent.trim() !== '';
                
                // 如果当前消息已经有内容，则在发起工具调用前创建新的消息区域
                // 这样可以让工具调用和相关的消息保持在一起
                if (hasTextContent) {
                    this.state.currentAssistantContainer = this.addMessage('', '', false);
                    this.state.responseMessageContainer = null;
                    this.state.currentResponseText = '';
                }
                
                // 确保有助手容器
                if (!this.state.currentAssistantContainer) {
                    this.state.currentAssistantContainer = this.addMessage('', '', false);
                }
                
                // 添加with-tools类到消息元素
                const messageEl = this.state.currentAssistantContainer.querySelector('.message');
                if (messageEl && !messageEl.classList.contains('with-tools')) {
                    messageEl.classList.add('with-tools');
                }
                
                // 保存工具调用信息，等待结果
                if (eventData && eventData.id) {
                    // 确保pendingToolCalls已初始化
                    if (!this.state.pendingToolCalls) {
                        this.state.pendingToolCalls = {};
                    }
                    
                    // 保存工具调用信息
                    this.state.pendingToolCalls[eventData.id] = {
                        name: eventData.name || eventData.tool || 'unknown_tool',
                        arguments: eventData.input || eventData.params || eventData.arguments || {},
                        id: eventData.id
                    };
                    console.log('Pending tool call saved:', this.state.pendingToolCalls[eventData.id]);
                } else {
                    // 如果没有ID，立即显示工具调用信息
                    this.addToolBubble(
                        this.state.currentAssistantContainer, 
                        'tool-call', 
                        `调用工具: ${eventData.name || eventData.tool}`, 
                        eventData.input || eventData.params ? JSON.stringify(eventData.input || eventData.params, null, 2) : null,
                        null
                    );
                }
                
                // 设置最后事件为工具调用
                this.state.lastEventWasToolCall = true;
                break;
                
            case 'tool_result':
                // 确保有助手容器
                if (!this.state.currentAssistantContainer) {
                    this.state.currentAssistantContainer = this.addMessage('', '', false);
                }
                
                // 检查是否有匹配的工具调用
                if (eventData && eventData.id && this.state.pendingToolCalls && this.state.pendingToolCalls[eventData.id]) {
                    const toolCall = this.state.pendingToolCalls[eventData.id];
                    // 创建合并的工具调用和结果气泡
                    this.createCombinedToolBubble(
                        toolCall.name,
                        toolCall.arguments,
                        eventData.output || eventData.result || "No result",
                        null,
                        eventData.id
                    );
                    
                    // 移除已处理的工具调用
                    delete this.state.pendingToolCalls[eventData.id];
                } else {
                    // 如果没有匹配的工具调用，使用常规方式显示
                    this.addToolBubble(
                        this.state.currentAssistantContainer, 
                        'tool-result', 
                        `工具结果: ${eventData ? (eventData.name || eventData.tool || 'unknown_tool') : 'unknown_tool'}`, 
                        eventData ? (eventData.output || eventData.result || "No result") : "No result",
                        eventData ? eventData.id : null
                    );
                }
                
                // 标记最后事件为工具调用
                this.state.lastEventWasToolCall = true;
                break;
                
            case 'tool_error':
                // 确保有助手容器
                if (!this.state.currentAssistantContainer) {
                    this.state.currentAssistantContainer = this.addMessage('', '', false);
                }
                
                // 检查是否有匹配的工具调用
                if (eventData && eventData.id && this.state.pendingToolCalls && this.state.pendingToolCalls[eventData.id]) {
                    const toolCall = this.state.pendingToolCalls[eventData.id];
                    // 创建合并的工具调用和错误气泡
                    this.createCombinedToolBubble(
                        toolCall.name,
                        toolCall.arguments,
                        null,
                        eventData.error || eventData.message || "未知错误",
                        eventData.id
                    );
                    
                    // 移除已处理的工具调用
                    delete this.state.pendingToolCalls[eventData.id];
                } else {
                    // 如果没有匹配的工具调用，使用常规方式显示
                    this.addToolBubble(
                        this.state.currentAssistantContainer, 
                        'tool-error', 
                        `工具错误`, 
                        eventData ? (eventData.error || eventData.message || "未知错误") : "未知错误",
                        eventData ? eventData.id : null
                    );
                }
                
                // 标记最后事件为工具调用
                this.state.lastEventWasToolCall = true;
                break;
                
            case 'error':
                // 检查错误消息是否来自新格式
                const errorMessage = eventData.error || eventData.message || "未知错误";
                this.addErrorMessage(`错误: ${errorMessage}`);
                this.elements.sendButton.disabled = false;
                break;
                
            case 'done':
            case 'end':
                // 流式输出完成，处理响应文本以移除多余空行
                if (this.state.responseMessageContainer && this.state.currentResponseText) {
                    // 移除开头和结尾的空行以及连续的多个空行变为单个空行
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
                    // 移除开头和结尾的空行以及连续的多个空行变为单个空行
                    const strippedThinkingText = this.stripExtraEmptyLines(this.state.currentThinkingText);
                    
                    // 更新显示内容
                    this.state.thinkingTextContainer.textContent = strippedThinkingText;
                    
                    // 保存处理后的文本
                    this.state.currentThinkingText = strippedThinkingText;
                }
                
                this.elements.sendButton.disabled = false;
                break;
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