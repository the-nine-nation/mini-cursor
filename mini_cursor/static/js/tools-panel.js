/**
 * 工具面板模块 - 处理工具列表显示和操作
 */

const ToolsPanel = {
    // DOM元素
    elements: {
        toolsList: null,
        enableAllBtn: null,
        disableAllBtn: null,
    },
    
    /**
     * 初始化工具面板
     */
    init: function() {
        // 初始化DOM元素引用
        this.elements.toolsList = document.getElementById('tools-list');
        this.elements.enableAllBtn = document.getElementById('enable-all-btn');
        this.elements.disableAllBtn = document.getElementById('disable-all-btn');
        
        // 绑定事件
        this.elements.enableAllBtn.addEventListener('click', this.enableAllTools.bind(this));
        this.elements.disableAllBtn.addEventListener('click', this.disableAllTools.bind(this));
        
        // 初始加载工具列表
        this.loadToolsList();
    },
    
    /**
     * 渲染工具参数
     * @param {Object} parameters - 工具参数对象
     * @returns {string} - 参数HTML
     */
    renderParameters: function(parameters) {
        if (!parameters || !parameters.properties) {
            return '';
        }
        
        let parametersHtml = '<div class="tool-parameters"><h4>参数列表</h4><ul>';
        
        Object.entries(parameters.properties).forEach(([paramName, paramInfo]) => {
            const required = parameters.required && parameters.required.includes(paramName);
            const paramType = paramInfo.type ? `<span class="param-type">${paramInfo.type}</span>` : '';
            const description = paramInfo.description || '';
            
            parametersHtml += `
                <li>
                    <div class="param-header">
                        <span class="param-name">${paramName}</span>
                        ${required ? '<span class="param-required">必需</span>' : ''}
                        ${paramType}
                    </div>
                    <div class="param-description">${description}</div>
                </li>
            `;
        });
        
        parametersHtml += '</ul></div>';
        return parametersHtml;
    },
    
    /**
     * 处理工具描述文本，转换换行符为HTML换行
     * @param {string} description - 原始描述文本
     * @returns {string} - 处理后的HTML格式描述
     */
    formatDescription: function(description) {
        if (!description) return '';
        
        // 将\n换行符转换为<br>标签
        return description.replace(/\n/g, '<br>');
    },
    
    /**
     * 加载工具列表
     */
    loadToolsList: function() {
        this.elements.toolsList.innerHTML = '<div class="loading-tools">加载中...</div>';
        
        API.getTools()
            .then(data => {
                const { servers, enabled_tools } = data;
                
                let toolsHtml = '';
                
                // 遍历每个服务器
                Object.entries(servers).forEach(([serverName, serverInfo]) => {
                    toolsHtml += `<div class="server-name">${serverName}</div>`;
                    
                    // 遍历服务器中的工具
                    serverInfo.tools.forEach(tool => {
                        const isEnabled = enabled_tools.includes(tool.name);
                        
                        // 处理描述文本，确保换行符正确处理
                        const description = this.formatDescription(tool.description || '');
                        
                        toolsHtml += `
                        <div class="tool-item" data-tool="${tool.name}">
                            <div class="tool-header">
                                <input type="checkbox" class="tool-checkbox" data-tool="${tool.name}" 
                                    ${isEnabled ? 'checked' : ''}>
                                <div class="tool-name">${tool.name}</div>
                                <div class="tool-toggle">
                                    <svg class="expand-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="18" height="18">
                                        <path d="M7 10l5 5 5-5z"/>
                                    </svg>
                                </div>
                            </div>
                            <div class="tool-details">
                                <div class="tool-description">${description}</div>
                                ${this.renderParameters(tool.parameters)}
                            </div>
                        </div>`;
                    });
                });
                
                this.elements.toolsList.innerHTML = toolsHtml;
                
                // 添加复选框事件监听
                document.querySelectorAll('.tool-checkbox').forEach(checkbox => {
                    checkbox.addEventListener('change', this.handleToolCheckboxChange.bind(this));
                });
                
                // 添加工具项点击事件监听（展开/收起）
                document.querySelectorAll('.tool-item .tool-header').forEach(header => {
                    header.addEventListener('click', this.toggleToolDetails.bind(this));
                });
                
                // 防止复选框点击事件冒泡
                document.querySelectorAll('.tool-checkbox').forEach(checkbox => {
                    checkbox.addEventListener('click', e => e.stopPropagation());
                });
            })
            .catch(error => {
                console.error('Error loading tools:', error);
                this.elements.toolsList.innerHTML = '<div class="loading-tools">加载工具列表失败</div>';
            });
    },
    
    /**
     * 切换工具详情的显示/隐藏
     * @param {Event} event - 点击事件
     */
    toggleToolDetails: function(event) {
        // 防止与复选框事件冲突
        if (event.target.classList.contains('tool-checkbox')) {
            return;
        }
        
        const toolItem = event.currentTarget.parentElement;
        toolItem.classList.toggle('expanded');
        
        // 更新展开图标方向
        const expandIcon = toolItem.querySelector('.expand-icon');
        if (toolItem.classList.contains('expanded')) {
            expandIcon.style.transform = 'rotate(180deg)';
        } else {
            expandIcon.style.transform = 'rotate(0)';
        }
    },
    
    /**
     * 处理工具复选框变化
     * @param {Event} event - 变化事件
     */
    handleToolCheckboxChange: function(event) {
        const checkbox = event.target;
        const toolName = checkbox.getAttribute('data-tool');
        const isEnabled = checkbox.checked;
        
        // 给复选框添加加载中状态
        checkbox.disabled = true;
        
        // 找到该工具的父元素
        const toolItem = checkbox.closest('.tool-item');
        if (toolItem) {
            toolItem.classList.add('updating');
        }
        
        API.setToolStatus(toolName, isEnabled)
            .then(data => {
                // 移除加载状态
                checkbox.disabled = false;
                if (toolItem) {
                    toolItem.classList.remove('updating');
                }
                
                if (data.status === 'ok') {
                    // 操作成功，重新加载工具列表以确保UI与服务器状态同步
                    this.loadToolsList();
                } else {
                    console.error(data.message || '操作失败');
                    // 如果操作失败，恢复复选框状态
                    checkbox.checked = !checkbox.checked;
                }
            })
            .catch(error => {
                // 移除加载状态
                checkbox.disabled = false;
                if (toolItem) {
                    toolItem.classList.remove('updating');
                }
                
                console.error('Error:', error);
                // 如果发生错误，恢复复选框状态
                checkbox.checked = !checkbox.checked;
            });
    },
    
    /**
     * 启用所有工具
     */
    enableAllTools: function() {
        API.enableAllTools()
            .then(data => {
                if (data.status === 'ok') {
                    this.loadToolsList();
                }
            })
            .catch(error => {
                console.error('Error:', error);
            });
    },
    
    /**
     * 禁用所有工具
     */
    disableAllTools: function() {
        API.disableAllTools()
            .then(data => {
                if (data.status === 'ok') {
                    this.loadToolsList();
                }
            })
            .catch(error => {
                console.error('Error:', error);
            });
    }
}; 