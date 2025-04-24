/**
 * 系统提示管理模块 - 处理系统提示的修改与保存
 */

// 初始化系统提示管理功能
function initSystemPromptManager() {
    console.log('初始化系统提示管理功能...');

    // 获取DOM元素
    const systemPromptBtn = document.getElementById('system-prompt-btn');
    const systemPromptDialog = document.getElementById('system-prompt-dialog');
    const systemPromptOverlay = document.getElementById('system-prompt-overlay');
    const systemPromptClose = document.getElementById('system-prompt-dialog-close');
    const systemPromptTextarea = document.getElementById('system-prompt-textarea');
    const systemPromptSaveBtn = document.getElementById('system-prompt-save');
    const systemPromptResetBtn = document.getElementById('system-prompt-reset');
    const systemPromptLoading = document.getElementById('system-prompt-loading');

    // 检查必要的DOM元素是否存在
    if (!systemPromptBtn || !systemPromptDialog || !systemPromptOverlay) {
        console.error('系统提示管理所需DOM元素不完整，无法初始化');
        return;
    }

    // 打开系统提示编辑弹窗
    function openSystemPromptDialog() {
        console.log('打开系统提示编辑弹窗');
        systemPromptDialog.style.display = 'flex';
        systemPromptOverlay.style.display = 'block';
        loadSystemPrompt();
    }

    // 关闭系统提示编辑弹窗
    function closeSystemPromptDialog() {
        console.log('关闭系统提示编辑弹窗');
        systemPromptDialog.style.display = 'none';
        systemPromptOverlay.style.display = 'none';
    }

    // 加载系统提示内容
    async function loadSystemPrompt() {
        try {
            systemPromptLoading.style.display = 'block';
            systemPromptTextarea.style.display = 'none';

            const response = await fetch('/system-prompt');
            if (!response.ok) {
                throw new Error('获取系统提示失败');
            }

            const data = await response.json();
            console.log('获取到系统提示内容');

            if (data.status === 'success') {
                systemPromptTextarea.value = data.content;
                systemPromptTextarea.style.display = 'block';
            } else {
                throw new Error(data.message || '获取系统提示失败');
            }
        } catch (error) {
            console.error('加载系统提示失败:', error);
            systemPromptTextarea.value = '加载系统提示失败，请重试: ' + error.message;
        } finally {
            systemPromptLoading.style.display = 'none';
        }
    }

    // 保存系统提示内容
    async function saveSystemPrompt() {
        try {
            systemPromptLoading.style.display = 'block';
            const content = systemPromptTextarea.value;

            const response = await fetch('/update-system-prompt', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ content }),
            });

            if (!response.ok) {
                throw new Error('保存系统提示失败');
            }

            const data = await response.json();
            if (data.status === 'success') {
                alert('系统提示已保存成功！');
                closeSystemPromptDialog();
            } else {
                throw new Error(data.message || '保存系统提示失败');
            }
        } catch (error) {
            console.error('保存系统提示失败:', error);
            alert('保存系统提示失败: ' + error.message);
        } finally {
            systemPromptLoading.style.display = 'none';
        }
    }

    // 重置系统提示内容为默认值
    async function resetSystemPrompt() {
        if (!confirm('确定要将系统提示重置为默认值吗？此操作不可恢复。')) {
            return;
        }

        try {
            systemPromptLoading.style.display = 'block';
            systemPromptTextarea.style.display = 'none';

            const response = await fetch('/reset-system-prompt', {
                method: 'POST',
            });

            if (!response.ok) {
                throw new Error('重置系统提示失败');
            }

            const data = await response.json();
            if (data.status === 'success') {
                systemPromptTextarea.value = data.content;
                alert('系统提示已重置为默认值！');
            } else {
                throw new Error(data.message || '重置系统提示失败');
            }
        } catch (error) {
            console.error('重置系统提示失败:', error);
            alert('重置系统提示失败: ' + error.message);
        } finally {
            systemPromptLoading.style.display = 'none';
            systemPromptTextarea.style.display = 'block';
        }
    }

    // 绑定事件
    systemPromptBtn.addEventListener('click', openSystemPromptDialog);
    systemPromptClose.addEventListener('click', closeSystemPromptDialog);
    systemPromptOverlay.addEventListener('click', closeSystemPromptDialog);
    systemPromptSaveBtn.addEventListener('click', saveSystemPrompt);
    systemPromptResetBtn.addEventListener('click', resetSystemPrompt);

    console.log('系统提示管理功能初始化完成');
}

// 当文档加载完成后初始化
document.addEventListener('DOMContentLoaded', initSystemPromptManager); 