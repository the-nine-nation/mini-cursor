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
    
    // 添加工作目录刷新功能
    setTimeout(refreshWorkspacePath, 1000);
    
    console.log('API Demo界面已初始化完成');
});

/**
 * 刷新工作目录显示
 */
function refreshWorkspacePath() {
    const workspacePathElement = document.getElementById('workspace-path');
    if (!workspacePathElement) return;
    
    // 尝试直接从当前URL推断工作目录
    const url = window.location.href;
    
    // 从URL中提取项目根目录（最可能的路径）
    let rootPath = '';
    
    if (url.includes('/mini-cursor/') || url.includes('/mini_cursor/')) {
        // 使用正则表达式提取到mini-cursor或mini_cursor的路径
        const match = url.match(/(.*?\/(?:mini-cursor|mini_cursor))/);
        if (match && match[1]) {
            rootPath = match[1];
        }
    }
    
    // 判断当前显示的工作目录是否需要更新
    const currentPath = workspacePathElement.textContent;
    if (currentPath === '加载中...' || 
        currentPath.includes('/static/') || 
        currentPath.includes('/libs/')) {
        
        if (rootPath) {
            workspacePathElement.textContent = rootPath;
            console.log('已更新工作目录显示:', rootPath);
        } else {
            // 如果无法从URL推断，尝试从API重新获取
            console.log('尝试从API刷新工作目录...');
            if (typeof API !== 'undefined' && API.getApiInfo) {
                API.getApiInfo()
                    .then(data => {
                        if (data && data.workspace) {
                            let workspace = data.workspace;
                            // 清理路径，确保只显示项目根目录
                            if (workspace.includes('/static/') || workspace.includes('/mini_cursor/')) {
                                workspace = workspace.split('/mini_cursor')[0];
                                if (workspace.endsWith('/')) {
                                    workspace += 'mini_cursor';
                                } else {
                                    workspace += '/mini_cursor';
                                }
                            }
                            workspacePathElement.textContent = workspace;
                            console.log('已从API更新工作目录:', workspace);
                        }
                    })
                    .catch(err => {
                        console.error('刷新工作目录失败:', err);
                    });
            }
        }
    }
}

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