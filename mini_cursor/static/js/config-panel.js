/**
 * 配置面板模块 - 处理配置信息显示和操作
 */

const ConfigPanel = {
    // DOM元素
    elements: {
        apiBase: null,
        apiKey: null, 
        modelName: null,
        clearHistoryBtn: null,
        workspacePath: null,
        editOpenaiConfigBtn: null,
        editMcpConfigBtn: null,
        enableAllBtn: null,
        disableAllBtn: null
    },
    
    // 配置缓存
    configCache: {
        apiBase: '',
        model: '',
        mcpConfig: null
    },
    
    /**
     * 初始化配置面板
     */
    init: function() {
        // 初始化DOM元素引用
        this.elements.apiBase = document.getElementById('api-base');
        this.elements.apiKey = document.getElementById('api-key');
        this.elements.modelName = document.getElementById('model-name');
        this.elements.workspacePath = document.getElementById('workspace-path');
        this.elements.clearHistoryBtn = document.getElementById('clear-history-btn');
        this.elements.editOpenaiConfigBtn = document.getElementById('edit-openai-config');
        this.elements.editMcpConfigBtn = document.getElementById('edit-mcp-config');
        this.elements.enableAllBtn = document.getElementById('enable-all-btn');
        this.elements.disableAllBtn = document.getElementById('disable-all-btn');
        
        // 设置临时工作目录显示，避免空白
        if (this.elements.workspacePath) {
            this.elements.workspacePath.textContent = '加载中...';
            
            // 尝试从URL获取基本信息
            const currentPath = window.location.pathname;
            if (currentPath.includes('/mini-cursor') || currentPath.includes('/mini_cursor')) {
                const parts = window.location.href.split('/');
                const index = parts.findIndex(part => part.includes('mini-cursor') || part.includes('mini_cursor'));
                if (index > 0) {
                    const basePath = parts.slice(0, index + 1).join('/');
                    this.elements.workspacePath.textContent = basePath;
                }
            }
        }
        
        // 绑定事件
        this.elements.clearHistoryBtn.addEventListener('click', this.handleClearHistory.bind(this));
        this.elements.editOpenaiConfigBtn.addEventListener('click', this.handleEditOpenaiConfig.bind(this));
        this.elements.editMcpConfigBtn.addEventListener('click', this.handleEditMcpConfig.bind(this));
        this.elements.enableAllBtn.addEventListener('click', this.handleEnableAllTools.bind(this));
        this.elements.disableAllBtn.addEventListener('click', this.handleDisableAllTools.bind(this));
        
        // 加载API信息
        this.loadApiInfo();
        // 加载MCP配置
        this.loadMCPConfig();
    },
    
    /**
     * 加载API信息
     */
    loadApiInfo: function() {
        API.getApiInfo()
            .then(data => {
                this.elements.apiBase.textContent = data.base_url;
                this.elements.modelName.textContent = data.model;
                
                // 修正工作目录路径显示
                let workspace = data.workspace || window.location.hostname;
                
                // 如果路径包含 mini_cursor/static 或其他子目录，截取到项目根目录
                if (workspace.includes('/mini_cursor/static')) {
                    workspace = workspace.split('/mini_cursor/static')[0];
                } else if (workspace.includes('/static/libs')) {
                    workspace = workspace.split('/static/libs')[0];
                } else if (workspace.includes('/static')) {
                    workspace = workspace.split('/static')[0];
                } else if (workspace.includes('/mini_cursor')) {
                    workspace = workspace.split('/mini_cursor')[0];
                }
                
                this.elements.workspacePath.textContent = workspace;
                
                // 缓存配置
                this.configCache.apiBase = data.base_url;
                this.configCache.model = data.model;
            })
            .catch(error => {
                console.error('Error fetching API info:', error);
                this.elements.apiBase.textContent = 'Error loading';
                this.elements.modelName.textContent = 'Error loading';
                this.elements.workspacePath.textContent = '未知工作目录';
            });
    },
    
    /**
     * 加载MCP配置
     */
    loadMCPConfig: function() {
        API.getMCPConfig()
            .then(data => {
                if (data.status === 'success') {
                    this.configCache.mcpConfig = data.data;
                }
            })
            .catch(error => {
                console.error('Error loading MCP config:', error);
            });
    },
    
    /**
     * 处理清空聊天历史
     * @param {boolean} skipConfirm - 是否跳过确认对话框
     */
    handleClearHistory: function(skipConfirm = false) {
        console.log('清除对话历史，创建新会话...');
        
        // 确认是否清除历史
        if (!skipConfirm && !confirm('确定要清除当前对话历史并开始新的会话吗？')) {
            return;
        }
        
        // 发送请求，清除当前会话历史
        fetch('/conversations/clear', {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'ok') {
                console.log('新会话已创建，ID:', data.conversation_id);
                
                const messagesContainer = document.getElementById('messages');
                messagesContainer.innerHTML = '';
                
                // 添加成功消息
                const infoDiv1 = document.createElement('div');
                infoDiv1.className = 'message-info';
                infoDiv1.textContent = '聊天历史已清空';
                messagesContainer.appendChild(infoDiv1);
                
                // 添加新会话ID信息
                const infoDiv2 = document.createElement('div');
                infoDiv2.className = 'message-info';
                infoDiv2.textContent = `新会话已创建，ID: ${data.conversation_id}`;
                messagesContainer.appendChild(infoDiv2);
                
                // 添加工作目录信息
                const infoDiv3 = document.createElement('div');
                infoDiv3.className = 'message-info';
                infoDiv3.textContent = `当前工作目录: ${this.elements.workspacePath.textContent}`;
                messagesContainer.appendChild(infoDiv3);
                
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
                
                // 显示成功提示
                this.showAlert('已开始新的会话', 'success');
                
                // 触发自定义事件，通知其他模块会话已更新
                const event = new CustomEvent('conversationCleared', {
                    detail: { newConversationId: data.conversation_id }
                });
                document.dispatchEvent(event);
            } else {
                console.error('清除历史失败:', data.message);
                this.showAlert('清除历史失败: ' + data.message, 'error');
            }
        })
        .catch(error => {
            console.error('Error clearing history:', error);
            this.showAlert('清除历史出错: ' + error.message, 'error');
        });
    },
    
    /**
     * 处理启用所有工具按钮点击
     */
    handleEnableAllTools: function() {
        this.elements.enableAllBtn.disabled = true;
        this.elements.enableAllBtn.textContent = '正在启用...';
        
        API.enableAllTools()
            .then(data => {
                if (data.status === 'ok') {
                    this.showAlert('所有工具已启用', 'success');
                    // 工具列表会由ToolsPanel自动刷新
                } else {
                    this.showAlert('启用所有工具失败: ' + data.message, 'error');
                }
            })
            .catch(error => {
                console.error('Error enabling all tools:', error);
                this.showAlert('启用所有工具时发生错误', 'error');
            })
            .finally(() => {
                this.elements.enableAllBtn.disabled = false;
                this.elements.enableAllBtn.textContent = '启用所有工具';
            });
    },
    
    /**
     * 处理禁用所有工具按钮点击
     */
    handleDisableAllTools: function() {
        this.elements.disableAllBtn.disabled = true;
        this.elements.disableAllBtn.textContent = '正在禁用...';
        
        API.disableAllTools()
            .then(data => {
                if (data.status === 'ok') {
                    this.showAlert('所有工具已禁用', 'success');
                    // 工具列表会由ToolsPanel自动刷新
                } else {
                    this.showAlert('禁用所有工具失败: ' + data.message, 'error');
                }
            })
            .catch(error => {
                console.error('Error disabling all tools:', error);
                this.showAlert('禁用所有工具时发生错误', 'error');
            })
            .finally(() => {
                this.elements.disableAllBtn.disabled = false;
                this.elements.disableAllBtn.textContent = '禁用所有工具';
            });
    },
    
    /**
     * 处理编辑OpenAI配置
     */
    handleEditOpenaiConfig: function() {
        // 创建遮罩层
        const overlay = document.createElement('div');
        overlay.className = 'modal-overlay';
        document.body.appendChild(overlay);
        
        // 创建模态框
        const modal = document.createElement('div');
        modal.className = 'modal';
        
        // 模态框内容
        modal.innerHTML = `
            <div class="modal-header">
                <h3>编辑 OpenAI 配置</h3>
                <button class="modal-close-btn">&times;</button>
            </div>
            <div class="modal-body">
                <form id="openai-config-form">
                    <div class="form-group">
                        <label for="api-base-url">API Base URL:</label>
                        <input type="text" id="api-base-url" value="${this.configCache.apiBase}" required>
                    </div>
                    <div class="form-group">
                        <label for="api-model">模型:</label>
                        <input type="text" id="api-model" value="${this.configCache.model}" required>
                    </div>
                    <div class="form-group">
                        <label for="api-key-input">API Key (可选):</label>
                        <input type="password" id="api-key-input" placeholder="填写新的API Key或留空保持不变">
                        <small class="form-text text-muted">仅在需要更改时填写，留空将保持当前API Key不变</small>
                    </div>
                </form>
            </div>
            <div class="modal-footer">
                <button class="btn cancel-btn">取消</button>
                <button class="btn primary-btn" id="save-openai-config-btn">保存</button>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // 添加模态框样式（如果不存在）
        this.addModalStyles();
        
        // 绑定事件
        const closeBtn = modal.querySelector('.modal-close-btn');
        const cancelBtn = modal.querySelector('.cancel-btn');
        const saveBtn = modal.querySelector('#save-openai-config-btn');
        
        const closeModal = () => {
            document.body.removeChild(overlay);
            document.body.removeChild(modal);
        };
        
        closeBtn.addEventListener('click', closeModal);
        cancelBtn.addEventListener('click', closeModal);
        overlay.addEventListener('click', closeModal);
        
        // 保存配置
        saveBtn.addEventListener('click', () => {
            const baseUrl = document.getElementById('api-base-url').value.trim();
            const model = document.getElementById('api-model').value.trim();
            const apiKey = document.getElementById('api-key-input').value.trim();
            
            if (!baseUrl || !model) {
                this.showAlert('请填写所有必填字段', 'error');
                return;
            }
            
            const config = {
                base_url: baseUrl,
                model: model
            };
            
            // 仅在提供了API Key时添加它
            if (apiKey) {
                config.api_key = apiKey;
            }
            
            // 禁用保存按钮，防止重复提交
            saveBtn.disabled = true;
            saveBtn.textContent = '保存中...';
            
            // 发送配置更新请求
            API.updateOpenAIConfig(config)
                .then(response => {
                    if (response.status === 'ok') {
                        // 更新显示
                        this.elements.apiBase.textContent = baseUrl;
                        this.elements.modelName.textContent = model;
                        
                        // 更新缓存
                        this.configCache.apiBase = baseUrl;
                        this.configCache.model = model;
                        
                        // 显示成功消息
                        this.showAlert('OpenAI 配置已成功更新', 'success');
                        
                        // 清除当前会话，确保新配置立即生效
                        this.handleClearHistory(true);
                        
                        // 关闭模态框
                        closeModal();
                    } else {
                        // 显示错误消息
                        this.showAlert('更新配置失败: ' + response.message, 'error');
                    }
                })
                .catch(error => {
                    console.error('Error updating OpenAI config:', error);
                    this.showAlert('更新配置时发生错误', 'error');
                })
                .finally(() => {
                    // 重新启用保存按钮
                    saveBtn.disabled = false;
                    saveBtn.textContent = '保存';
                });
        });
    },
    
    /**
     * 添加模态框样式到页面
     */
    addModalStyles: function() {
        if (!document.getElementById('modal-styles')) {
            const modalStyles = document.createElement('style');
            modalStyles.id = 'modal-styles';
            modalStyles.textContent = `
                .modal-overlay {
                    position: fixed;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background-color: rgba(0, 0, 0, 0.5);
                    z-index: 1000;
                }
                
                .modal {
                    position: fixed;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    background-color: white;
                    border-radius: 8px;
                    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
                    z-index: 1001;
                    width: 450px;
                    max-width: 90%;
                    max-height: 90vh;
                    display: flex;
                    flex-direction: column;
                }
                
                .modal-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 15px 20px;
                    border-bottom: 1px solid #eee;
                }
                
                .modal-header h3 {
                    margin: 0;
                    font-size: 18px;
                    color: #333;
                }
                
                .modal-close-btn {
                    background: none;
                    border: none;
                    font-size: 24px;
                    cursor: pointer;
                    color: #777;
                }
                
                .modal-body {
                    padding: 20px;
                    overflow-y: auto;
                    flex: 1;
                }
                
                .modal-footer {
                    padding: 15px 20px;
                    border-top: 1px solid #eee;
                    display: flex;
                    justify-content: flex-end;
                    gap: 10px;
                }
                
                .form-group {
                    margin-bottom: 15px;
                }
                
                .form-group label {
                    display: block;
                    margin-bottom: 5px;
                    font-weight: 500;
                }
                
                .form-group input, .form-group textarea {
                    width: 100%;
                    padding: 8px 10px;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    font-size: 14px;
                }
                
                .form-group textarea {
                    min-height: 150px;
                    font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
                    font-size: 12px;
                    line-height: 1.5;
                }
                
                .form-text {
                    display: block;
                    margin-top: 5px;
                    font-size: 12px;
                    color: #666;
                }
                
                .btn {
                    padding: 8px 16px;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    background-color: #f5f5f5;
                    cursor: pointer;
                    font-size: 14px;
                }
                
                .primary-btn {
                    background-color: #4a90e2;
                    color: white;
                    border-color: #3a80d2;
                }
                
                .cancel-btn {
                    background-color: #f5f5f5;
                    color: #333;
                }
                
                .alert-container {
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    z-index: 1002;
                    max-width: 350px;
                }
                
                .alert {
                    padding: 12px 16px;
                    margin-bottom: 10px;
                    border-radius: 4px;
                    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
                    animation: fade-in 0.3s ease;
                    position: relative;
                    overflow: hidden;
                }
                
                .alert-success {
                    background-color: #d4edda;
                    color: #155724;
                    border-left: 4px solid #28a745;
                }
                
                .alert-error {
                    background-color: #f8d7da;
                    color: #721c24;
                    border-left: 4px solid #dc3545;
                }
                
                @keyframes fade-in {
                    from { opacity: 0; transform: translateY(-10px); }
                    to { opacity: 1; transform: translateY(0); }
                }
            `;
            document.head.appendChild(modalStyles);
        }
    },
    
    /**
     * 显示通知消息
     * @param {string} message - 消息内容
     * @param {string} type - 消息类型 ('success' 或 'error')
     */
    showAlert: function(message, type) {
        // 检查是否已存在通知容器
        let alertContainer = document.querySelector('.alert-container');
        if (!alertContainer) {
            alertContainer = document.createElement('div');
            alertContainer.className = 'alert-container';
            document.body.appendChild(alertContainer);
        }
        
        // 创建通知元素
        const alert = document.createElement('div');
        alert.className = `alert alert-${type}`;
        alert.textContent = message;
        
        // 添加到容器
        alertContainer.appendChild(alert);
        
        // 自动移除
        setTimeout(() => {
            alert.style.opacity = '0';
            alert.style.transform = 'translateY(-10px)';
            alert.style.transition = 'all 0.3s ease';
            
            setTimeout(() => {
                alertContainer.removeChild(alert);
                
                // 如果没有更多通知，移除容器
                if (alertContainer.children.length === 0) {
                    document.body.removeChild(alertContainer);
                }
            }, 300);
        }, 3000);
    },
    
    /**
     * 处理编辑MCP配置
     */
    handleEditMcpConfig: function() {
        // 如果配置尚未加载，先加载配置
        if (!this.configCache.mcpConfig) {
            this.showAlert('正在加载MCP配置...', 'info');
            
            API.getMCPConfig()
                .then(data => {
                    if (data.status === 'success') {
                        this.configCache.mcpConfig = data.data;
                        this.openMCPConfigModal();
                    } else {
                        this.showAlert('加载MCP配置失败: ' + data.message, 'error');
                    }
                })
                .catch(error => {
                    console.error('Error loading MCP config:', error);
                    this.showAlert('加载MCP配置时发生错误', 'error');
                });
        } else {
            this.openMCPConfigModal();
        }
    },
    
    /**
     * 打开MCP配置编辑模态框
     */
    openMCPConfigModal: function() {
        // 创建遮罩层
        const overlay = document.createElement('div');
        overlay.className = 'modal-overlay';
        document.body.appendChild(overlay);
        
        // 创建模态框
        const modal = document.createElement('div');
        modal.className = 'modal';
        
        // 格式化JSON配置为美观的文本
        const formattedConfig = JSON.stringify(this.configCache.mcpConfig, null, 4);
        
        // 模态框内容
        modal.innerHTML = `
            <div class="modal-header">
                <h3>编辑 MCP 配置</h3>
                <button class="modal-close-btn">&times;</button>
            </div>
            <div class="modal-body">
                <form id="mcp-config-form">
                    <div class="form-group">
                        <label for="mcp-config-textarea">配置内容 (JSON):</label>
                        <textarea id="mcp-config-textarea" spellcheck="false">${formattedConfig}</textarea>
                        <small class="form-text text-muted">编辑此JSON配置以修改MCP服务设置。保存后将自动重启MCP服务器。</small>
                    </div>
                </form>
            </div>
            <div class="modal-footer">
                <button class="btn cancel-btn">取消</button>
                <button class="btn primary-btn" id="save-mcp-config-btn">保存</button>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // 添加模态框样式（如果不存在）
        this.addModalStyles();
        
        // 绑定事件
        const closeBtn = modal.querySelector('.modal-close-btn');
        const cancelBtn = modal.querySelector('.cancel-btn');
        const saveBtn = modal.querySelector('#save-mcp-config-btn');
        
        const closeModal = () => {
            document.body.removeChild(overlay);
            document.body.removeChild(modal);
        };
        
        closeBtn.addEventListener('click', closeModal);
        cancelBtn.addEventListener('click', closeModal);
        overlay.addEventListener('click', closeModal);
        
        // 保存配置
        saveBtn.addEventListener('click', () => {
            const configTextarea = document.getElementById('mcp-config-textarea');
            const configText = configTextarea.value.trim();
            
            try {
                // 尝试解析JSON
                const configObj = JSON.parse(configText);
                
                // 禁用保存按钮，防止重复提交
                saveBtn.disabled = true;
                saveBtn.textContent = '保存中...';
                
                // 发送配置更新请求
                API.updateMCPConfig(configObj)
                    .then(response => {
                        if (response.status === 'ok') {
                            // 更新缓存
                            this.configCache.mcpConfig = configObj;
                            
                            // 显示成功消息
                            this.showAlert('MCP配置已成功更新，服务器已重新启动', 'success');
                            
                            // 关闭模态框
                            closeModal();
                        } else {
                            // 显示错误消息
                            this.showAlert('更新配置失败: ' + response.message, 'error');
                        }
                    })
                    .catch(error => {
                        console.error('Error updating MCP config:', error);
                        this.showAlert('更新配置时发生错误', 'error');
                    })
                    .finally(() => {
                        // 重新启用保存按钮
                        saveBtn.disabled = false;
                        saveBtn.textContent = '保存';
                    });
            } catch (e) {
                // JSON解析失败
                this.showAlert('配置格式无效，请提供有效的JSON', 'error');
            }
        });
    }
}; 