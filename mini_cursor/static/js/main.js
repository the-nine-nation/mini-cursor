/**
 * 主JavaScript文件 - 负责初始化和协调各个模块
 */

document.addEventListener('DOMContentLoaded', function() {
    // 初始化各个模块
    API; // 确保API模块已经加载
    
    // 注意：ChatUI.init() 在chat-ui.js中自动完成加载和初始化
    
    // 初始化工具面板
    if (typeof ToolsPanel !== 'undefined' && ToolsPanel.init) {
        ToolsPanel.init();
    } else {
        console.error('工具面板模块未正确加载');
    }
    
    // 初始化配置面板
    if (typeof ConfigPanel !== 'undefined' && ConfigPanel.init) {
        ConfigPanel.init();
    } else {
        console.error('配置面板模块未正确加载');
    }
    
    // 检查外部库是否加载成功，如果失败则提示用户刷新页面
    setTimeout(checkExternalLibraries, 2000);
    
    console.log('API Demo界面已初始化完成');
});

/**
 * 检查外部库是否成功加载
 */
function checkExternalLibraries() {
    let missingLibraries = [];
    
    if (missingLibraries.length > 0) {
        console.warn('以下库加载失败:', missingLibraries.join(', '));
        
        // 创建友好提示
        const warningDiv = document.createElement('div');
        warningDiv.style.position = 'fixed';
        warningDiv.style.top = '10px';
        warningDiv.style.left = '10px';
        warningDiv.style.right = '10px';
        warningDiv.style.padding = '10px';
        warningDiv.style.backgroundColor = '#fff3cd';
        warningDiv.style.color = '#856404';
        warningDiv.style.border = '1px solid #ffeeba';
        warningDiv.style.borderRadius = '4px';
        warningDiv.style.zIndex = '10000';
        warningDiv.style.boxShadow = '0 2px 5px rgba(0,0,0,0.1)';
        warningDiv.style.textAlign = 'center';
        
        warningDiv.innerHTML = `
            <p>部分功能库加载失败，可能影响界面显示: ${missingLibraries.join(', ')}</p>
            <p>已自动使用本地文件替代，如仍有问题请刷新页面</p>
            <button id="close-warning" style="background-color: #856404; color: white; border: none; padding: 5px 10px; border-radius: 3px; cursor: pointer;">关闭提示</button>
        `;
        
        document.body.appendChild(warningDiv);
        
        document.getElementById('close-warning').addEventListener('click', function() {
            document.body.removeChild(warningDiv);
        });
    }
} 