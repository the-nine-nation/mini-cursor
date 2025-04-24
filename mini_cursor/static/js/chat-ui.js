/**
 * 聊天UI主文件 - 加载模块化的组件
 */

// 异步加载所有模块
document.addEventListener('DOMContentLoaded', async function() {
    // 定义核心模块和扩展模块
    const coreModules = [
        'chat-ui-core.js',
        'chat-ui-messages.js', 
        'chat-ui-tools.js',
        'chat-ui-stream.js'
    ];
    
    const extensionModules = [
        'chat-ui-history.js'
    ];
    
    try {
        // 先加载核心模块
        console.log('加载核心模块...');
        for (const module of coreModules) {
            console.log(`加载模块: ${module}`);
            await loadModule(`/static/js/${module}`);
        }
        
        // 初始化核心UI
        console.log('初始化核心UI...');
        ChatUI.init();
        
        // 再加载扩展模块
        console.log('加载扩展模块...');
        for (const module of extensionModules) {
            try {
                console.log(`加载模块: ${module}`);
                await loadModule(`/static/js/${module}`);
                
                // 获取模块名称
                const moduleName = module.replace('.js', '').split('-').pop();
                const initFunction = `init${moduleName.charAt(0).toUpperCase() + moduleName.slice(1)}`;
                
                // 如果有对应的初始化函数，则调用
                if (typeof ChatUI[initFunction] === 'function') {
                    console.log(`初始化模块: ${moduleName}`);
                    setTimeout(() => {
                        try {
                            ChatUI[initFunction]();
                        } catch (err) {
                            console.error(`初始化模块 ${moduleName} 时出错:`, err);
                        }
                    }, 200);
                }
            } catch (err) {
                console.error(`加载扩展模块 ${module} 时出错:`, err);
                // 继续加载其他模块
            }
        }
        
        console.log('聊天UI初始化完成');
    } catch (error) {
        console.error('初始化聊天UI时出错:', error);
    }
});

/**
 * 异步加载JavaScript模块
 * @param {string} url - 模块URL
 * @returns {Promise} - 加载完成的Promise
 */
function loadModule(url) {
    return new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = url;
        script.onload = () => {
            console.log(`模块加载成功: ${url}`);
            resolve();
        };
        script.onerror = (err) => {
            console.error(`模块加载失败: ${url}`, err);
            reject(new Error(`模块加载失败: ${url}`));
        };
        document.head.appendChild(script);
    });
} 