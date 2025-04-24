/**
 * API接口模块 - 处理与后端的所有通信
 */

const API = {
    /**
     * 获取API信息
     * @returns {Promise} 返回API信息的Promise
     */
    getApiInfo: function() {
        return fetch('/api-info')
            .then(response => response.json())
            .catch(error => {
                console.error('Error fetching API info:', error);
                throw error;
            });
    },
    
    /**
     * 获取工具列表
     * @returns {Promise} 返回工具列表的Promise
     */
    getTools: function() {
        return fetch('/tools')
            .then(response => response.json())
            .catch(error => {
                console.error('Error loading tools:', error);
                throw error;
            });
    },
    
    /**
     * 设置工具启用状态
     * @param {string} toolName - 工具名称
     * @param {boolean} enable - 是否启用
     * @returns {Promise} 返回操作结果的Promise
     */
    setToolStatus: function(toolName, enable) {
        const action = enable ? 'enable' : 'disable';
        return fetch(`/tools/${action}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tool_name: toolName })
        })
        .then(response => response.json());
    },
    
    /**
     * 设置工具模式
     * @param {string} mode - 模式 ('all' 或 'selective')
     * @returns {Promise} 返回操作结果的Promise
     */
    setToolMode: function(mode) {
        return fetch('/tools/mode', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mode })
        })
        .then(response => response.json());
    },
    
    /**
     * 启用所有工具
     * @returns {Promise} 返回操作结果的Promise
     */
    enableAllTools: function() {
        return fetch('/tools/enable-all', { method: 'POST' })
            .then(response => response.json());
    },
    
    /**
     * 禁用所有工具
     * @returns {Promise} 返回操作结果的Promise
     */
    disableAllTools: function() {
        return fetch('/tools/disable-all', { method: 'POST' })
            .then(response => response.json());
    },
    
    /**
     * 发送聊天请求
     * @param {string} query - 用户查询
     * @returns {Promise} 返回流式响应的Promise
     */
    sendChatRequest: function(query) {
        return fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query })
        });
    },
    
    /**
     * 更新OpenAI配置
     * @param {Object} config - OpenAI配置对象 
     * @param {string} config.base_url - API基础URL
     * @param {string} config.model - 模型名称
     * @param {string} [config.api_key] - API密钥（可选）
     * @returns {Promise} 返回操作结果的Promise
     */
    updateOpenAIConfig: function(config) {
        return fetch('/update-openai-config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        })
        .then(response => response.json());
    },
    
    /**
     * 获取MCP配置
     * @returns {Promise} 返回MCP配置的Promise
     */
    getMCPConfig: function() {
        return fetch('/mcp-config')
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP 错误 ${response.status}`);
                }
                return response.json();
            })
            .catch(error => {
                console.error('Error fetching MCP config:', error);
                throw error;
            });
    },
    
    /**
     * 更新MCP配置
     * @param {Object} config - MCP配置对象
     * @returns {Promise} 返回操作结果的Promise
     */
    updateMCPConfig: function(config) {
        return fetch('/update-mcp-config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ config })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP 错误 ${response.status}`);
            }
            return response.json();
        });
    },
    
    /**
     * 获取所有历史对话
     * @returns {Promise} 返回所有历史对话的Promise
     */
    getAllConversations: function() {
        return fetch('/conversations/all')
            .then(response => response.json())
            .catch(error => {
                console.error('Error fetching conversations:', error);
                throw error;
            });
    },
    
    /**
     * 获取对话详情
     * @param {string} conversationId - 对话ID
     * @returns {Promise} 返回对话详情的Promise
     */
    getConversationDetail: function(conversationId) {
        return fetch(`/conversations/detail/${conversationId}`)
            .then(response => response.json())
            .catch(error => {
                console.error('Error fetching conversation detail:', error);
                throw error;
            });
    },
    
    /**
     * 删除指定的历史对话
     * @param {string} conversationId - 要删除的对话ID
     * @returns {Promise} 返回操作结果的Promise
     */
    deleteConversation: function(conversationId) {
        return fetch(`/conversations/${conversationId}/delete`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        })
        .then(response => response.json())
        .catch(error => {
            console.error('Error deleting conversation:', error);
            // 返回一个表示错误的Promise，以便调用处可以处理
            return Promise.reject(error);
        });
    }
}; 