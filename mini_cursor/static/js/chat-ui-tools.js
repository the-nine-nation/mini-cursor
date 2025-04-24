/**
 * 聊天UI工具模块 - 处理工具调用和结果显示
 */

// 确保ChatUI对象存在
if (typeof ChatUI === 'undefined') {
    ChatUI = {};
}

// 扩展ChatUI对象
Object.assign(ChatUI, {
    /**
     * 添加工具相关的气泡内容
     * @param {HTMLElement} container - 消息容器
     * @param {string} type - 工具类型
     * @param {string} name - 工具名称
     * @param {string} content - 工具内容
     * @param {string} callId - 工具调用ID，如果有的话
     */
    addToolBubble: function(container, type, name, content, callId) {
        if (!container) return;
        
        // 添加调试信息
        console.log(`Adding tool bubble: type=${type}, name=${name}`);
        console.log('Content:', content);
        console.log('Content type:', typeof content);
        console.log('Call ID:', callId);
        
        const messageDiv = container.querySelector('.message');
        if (!messageDiv) return;
        
        const nestedBubble = document.createElement('div');
        nestedBubble.className = `nested-bubble ${type}`;
        
        const header = document.createElement('div');
        header.className = 'nested-bubble-header';
        
        let icon = '';
        if (type === 'tool-call') {
            icon = '🔧';
        } else if (type === 'tool-result') {
            icon = '✅';
        } else if (type === 'tool-error') {
            icon = '❌';
        }
        
        // 添加折叠/展开按钮
        const toggleIcon = document.createElement('span');
        toggleIcon.className = 'toggle-icon';
        toggleIcon.textContent = '▶'; // 默认折叠
        toggleIcon.style.marginRight = '6px';
        toggleIcon.style.cursor = 'pointer';
        
        // 添加标题文本
        const titleText = document.createElement('span');
        titleText.innerHTML = `<span class="icon">${icon}</span> ${name}`;
        
        header.appendChild(toggleIcon);
        header.appendChild(titleText);
        
        // 如果有工具调用ID，添加查看详情按钮
        if (callId) {
            const detailsButton = document.createElement('button');
            detailsButton.className = 'tool-details-btn';
            detailsButton.textContent = '查看详情';
            detailsButton.style.marginLeft = 'auto';
            detailsButton.style.padding = '2px 8px';
            detailsButton.style.fontSize = '12px';
            detailsButton.style.border = '1px solid #ccc';
            detailsButton.style.borderRadius = '3px';
            detailsButton.style.backgroundColor = '#f8f8f8';
            detailsButton.style.cursor = 'pointer';
            
            // 添加点击事件处理程序
            detailsButton.addEventListener('click', (e) => {
                e.stopPropagation(); // 阻止事件冒泡，避免触发折叠/展开
                this.showToolCallDetail(callId);
            });
            
            header.appendChild(detailsButton);
        }
        
        nestedBubble.appendChild(header);
        
        // 创建内容容器
        let contentDiv = null;
        if (content) {
            contentDiv = document.createElement('div');
            contentDiv.className = 'nested-bubble-content';
            contentDiv.style.display = 'none'; // 默认折叠内容
            
            // 打印原始内容，帮助调试
            console.log('Raw content to render:', content);
            
            // 处理换行符，将它们转换为HTML换行
            if (typeof content === 'string') {
                // 检查是否包含需要保留格式的数据库内容或多行内容
                if (this.isFormattedDatabaseContent(content) || content.includes('\n')) {
                    // 使用pre标签保留原始格式
                    console.log('Rendering as formatted content with <pre>');
                    
                    // 检查内容是否太长，如果超过1000个字符就截断
                    let displayContent = content;
                    if (content.length > 1000) {
                        displayContent = content.substring(0, 1000) + '... (内容已截断，点击展开可查看完整内容)';
                    }
                    
                    // 使用pre标签并确保内容安全
                    contentDiv.innerHTML = `<pre>${this.escapeHTML(displayContent)}</pre>`;
                } else {
                    // 普通文本，直接设置textContent以防止XSS
                    console.log('Rendering as plain text');
                    contentDiv.textContent = content;
                }
            } else {
                console.log('Content is not a string, using as is');
                // 非字符串内容，转换为JSON字符串后使用textContent显示
                contentDiv.textContent = typeof content === 'object' ? 
                    JSON.stringify(content, null, 2) : 
                    String(content);
            }
            
            nestedBubble.appendChild(contentDiv);
        } else {
            console.log('No content provided for tool bubble');
        }
        
        // 添加点击事件处理程序，切换内容显示/隐藏
        header.addEventListener('click', function() {
            if (!contentDiv) return;
            
            // 切换内容显示状态
            if (contentDiv.style.display === 'none') {
                contentDiv.style.display = '';
                toggleIcon.textContent = '▼'; // 展开
                console.log('Expanding content');
                
                // 如果内容被截断了，恢复完整内容
                if (content && typeof content === 'string' && content.length > 1000 && 
                    contentDiv.querySelector('pre')?.textContent.includes('内容已截断')) {
                    console.log('Restoring full content');
                    contentDiv.querySelector('pre').innerHTML = this.escapeHTML(content);
                }
            } else {
                contentDiv.style.display = 'none';
                toggleIcon.textContent = '▶'; // 折叠
                console.log('Collapsing content');
            }
        }.bind(this));
        
        messageDiv.appendChild(nestedBubble);
        this.elements.messagesContainer.scrollTop = this.elements.messagesContainer.scrollHeight;
    },
    
    /**
     * 创建合并的工具调用和结果气泡
     * @param {string} toolName - 工具名称
     * @param {Object} args - 工具参数
     * @param {string|Object} result - 工具结果
     * @param {string} error - 错误信息，如果有
     * @param {string} callId - 工具调用ID
     */
    createCombinedToolBubble: function(toolName, args, result, error, callId) {
        // 确保有助手容器
        if (!this.state.currentAssistantContainer) {
            this.state.currentAssistantContainer = this.addMessage('', '', false);
        }
        
        // 添加with-tools类到消息元素
        const messageEl = this.state.currentAssistantContainer.querySelector('.message');
        if (messageEl && !messageEl.classList.contains('with-tools')) {
            messageEl.classList.add('with-tools');
        }
        
        // 创建气泡容器
        const nestedBubble = document.createElement('div');
        nestedBubble.className = 'nested-bubble tool-combined';
        
        // 创建头部
        const header = document.createElement('div');
        header.className = 'nested-bubble-header';
        
        // 图标和标题
        const icon = error ? '❌' : '🔧';
        const titleText = document.createElement('span');
        titleText.innerHTML = `<span class="icon">${icon}</span> 工具调用: ${toolName}`;
        
        // 添加折叠/展开按钮
        const toggleIcon = document.createElement('span');
        toggleIcon.className = 'toggle-icon';
        toggleIcon.textContent = '▶'; // 默认折叠
        toggleIcon.style.marginRight = '6px';
        toggleIcon.style.cursor = 'pointer';
        
        header.appendChild(toggleIcon);
        header.appendChild(titleText);
        
        // 添加查看详情按钮
        if (callId) {
            const detailsButton = document.createElement('button');
            detailsButton.className = 'tool-details-btn';
            detailsButton.textContent = '查看详情';
            detailsButton.style.marginLeft = 'auto';
            detailsButton.style.padding = '2px 8px';
            detailsButton.style.fontSize = '12px';
            detailsButton.style.border = '1px solid #ccc';
            detailsButton.style.borderRadius = '3px';
            detailsButton.style.backgroundColor = '#f8f8f8';
            detailsButton.style.cursor = 'pointer';
            
            // 添加点击事件
            detailsButton.addEventListener('click', (e) => {
                e.stopPropagation(); // 阻止事件冒泡
                this.showToolCallDetail(callId);
            });
            
            header.appendChild(detailsButton);
        }
        
        nestedBubble.appendChild(header);
        
        // 创建内容区域
        const contentDiv = document.createElement('div');
        contentDiv.className = 'nested-bubble-content';
        contentDiv.style.display = 'none'; // 默认折叠内容
        
        // 创建参数部分
        const argsSection = document.createElement('div');
        argsSection.className = 'tool-section';
        
        // 添加参数标题
        const argsHeader = document.createElement('div');
        argsHeader.className = 'tool-section-header';
        argsHeader.textContent = '参数:';
        argsSection.appendChild(argsHeader);
        
        // 添加参数内容
        const argsPre = document.createElement('pre');
        argsPre.textContent = typeof args === 'string' ? args : JSON.stringify(args, null, 2);
        argsSection.appendChild(argsPre);
        
        contentDiv.appendChild(argsSection);
        
        // 创建结果部分
        const resultSection = document.createElement('div');
        resultSection.className = 'tool-section';
        
        if (error) {
            // 错误结果
            const errorHeader = document.createElement('div');
            errorHeader.className = 'tool-section-header';
            errorHeader.textContent = '错误:';
            resultSection.appendChild(errorHeader);
            
            const errorPre = document.createElement('pre');
            errorPre.className = 'error';
            errorPre.textContent = error;
            resultSection.appendChild(errorPre);
        } else {
            // 正常结果
            let displayResult = result;
            
            // 处理数组或对象类型的结果
            if (typeof result !== 'string') {
                displayResult = JSON.stringify(result, null, 2);
            }
            
            // 处理长文本截断
            if (typeof displayResult === 'string' && displayResult.length > 1000) {
                displayResult = displayResult.substring(0, 1000) + '... (内容已截断，点击展开可查看完整内容)';
            }
            
            const resultHeader = document.createElement('div');
            resultHeader.className = 'tool-section-header';
            resultHeader.textContent = '结果:';
            resultSection.appendChild(resultHeader);
            
            const resultPre = document.createElement('pre');
            resultPre.textContent = displayResult;
            resultSection.appendChild(resultPre);
        }
        
        contentDiv.appendChild(resultSection);
        nestedBubble.appendChild(contentDiv);
        
        // 添加点击事件，处理折叠/展开
        header.addEventListener('click', function() {
            // 切换内容显示状态
            if (contentDiv.style.display === 'none') {
                contentDiv.style.display = '';
                toggleIcon.textContent = '▼'; // 展开
                
                // 如果有截断的内容，恢复完整内容
                const resultPre = resultSection.querySelector('pre');
                if (resultPre && typeof result === 'string' && result.length > 1000 && 
                    resultPre.textContent.includes('内容已截断')) {
                    resultPre.textContent = result;
                }
            } else {
                contentDiv.style.display = 'none';
                toggleIcon.textContent = '▶'; // 折叠
            }
        }.bind(this));
        
        // 添加到消息元素
        messageEl.appendChild(nestedBubble);
        this.elements.messagesContainer.scrollTop = this.elements.messagesContainer.scrollHeight;
        
        return nestedBubble;
    }
}); 