/**
 * API演示页面错误处理器 - 处理API错误并提供友好的用户界面
 */

const ErrorHandler = {
    // 存储检测到的配置错误
    configErrors: {},

    // 初始化错误处理器
    init: function() {
        console.log('初始化错误处理器');
        this.setupGlobalErrorHandling();
        this.checkServerStatus();
    },
    
    // 设置全局错误处理
    setupGlobalErrorHandling: function() {
        // 拦截 fetch 以处理 API 错误
        const originalFetch = window.fetch;
        window.fetch = async function() {
            try {
                const response = await originalFetch.apply(this, arguments);
                if (!response.ok) {
                    ErrorHandler.handleApiError(response);
                }
                return response;
            } catch (error) {
                ErrorHandler.handleNetworkError(error);
                throw error;
            }
        };
    },
    
    // 检查服务器状态并处理配置错误
    checkServerStatus: function() {
        fetch('/api-info')
            .then(response => response.json())
            .then(data => {
                if (data.status === 'warning' && data.configuration_errors) {
                    this.configErrors = data.configuration_errors;
                    this.showConfigErrorNotification(data.message, data.configuration_errors);
                }
            })
            .catch(error => {
                console.error('检查服务器状态失败:', error);
                // 即使API出错也允许UI加载
            });
    },
    
    // 显示配置错误通知
    showConfigErrorNotification: function(message, errors) {
        // 创建错误通知容器
        const container = document.createElement('div');
        container.className = 'error-notification';
        container.style.cssText = 'position: fixed; top: 10px; left: 50%; transform: translateX(-50%); background-color: #ffebee; color: #d32f2f; padding: 10px 15px; border-radius: 4px; box-shadow: 0 2px 4px rgba(0,0,0,0.2); z-index: 1000; max-width: 90%; font-family: system-ui, -apple-system, sans-serif; display: flex; flex-direction: column; gap: 10px;';
    
        // 创建消息元素
        const messageElem = document.createElement('div');
        messageElem.innerHTML = `<strong>⚠️ ${message}</strong>`;
        container.appendChild(messageElem);
    
        // 添加配置按钮
        const configButton = document.createElement('button');
        configButton.textContent = '打开配置面板';
        configButton.style.cssText = 'background-color: #d32f2f; color: white; border: none; padding: 8px 12px; border-radius: 4px; cursor: pointer; align-self: center;';
        configButton.onclick = function() {
            if (typeof ConfigPanel !== 'undefined' && ConfigPanel.show) {
                ConfigPanel.show();
                // 打开设置选项卡
                const tabLinks = document.querySelectorAll('.config-tab-link');
                if (tabLinks && tabLinks.length) {
                    tabLinks[0].click(); // 点击第一个选项卡（通常是设置）
                }
            } else {
                alert('无法加载配置面板，配置脚本可能缺失。请检查终端日志获取更多信息。');
            }
        };
        container.appendChild(configButton);

        // 添加关闭按钮
        const closeButton = document.createElement('button');
        closeButton.textContent = 'X';
        closeButton.style.cssText = 'position: absolute; top: 5px; right: 5px; background: none; border: none; color: #d32f2f; cursor: pointer;';
        closeButton.onclick = function() {
            container.remove();
        };
        container.appendChild(closeButton);
    
        // 添加到文档
        document.body.appendChild(container);
    },
    
    // 处理API错误
    handleApiError: function(response) {
        console.error('API错误:', response.status, response.statusText);
        // 在这里我们不阻止UI加载，只记录错误
    },
    
    // 处理网络错误
    handleNetworkError: function(error) {
        console.error('网络错误:', error);
        // 在这里我们不阻止UI加载，只记录错误
    }
};

// 页面加载时初始化错误处理器
document.addEventListener('DOMContentLoaded', function() {
    ErrorHandler.init();
}); 