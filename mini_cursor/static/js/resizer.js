/**
 * 面板大小调整模块 - 处理面板之间的可拖拽大小调整
 */

const PanelResizer = {
    // DOM元素
    elements: {
        resizer: null,
        toolsPanel: null,
        layout: null,
    },
    
    // 状态变量
    state: {
        isDragging: false,
        initialX: 0,
        initialToolsPanelWidth: 0,
        layoutWidth: 0,
    },
    
    /**
     * 初始化拖拽调整大小功能
     */
    init: function() {
        // 获取DOM元素
        this.elements.resizer = document.getElementById('panel-resizer');
        this.elements.toolsPanel = document.querySelector('.tools-panel');
        this.elements.layout = document.querySelector('.layout');
        
        if (!this.elements.resizer || !this.elements.toolsPanel) {
            console.error('必要的DOM元素未找到，拖拽调整功能初始化失败');
            return;
        }
        
        // 绑定事件处理函数
        this.elements.resizer.addEventListener('mousedown', this.startResize.bind(this));
        document.addEventListener('mousemove', this.resize.bind(this));
        document.addEventListener('mouseup', this.stopResize.bind(this));
        
        // 绑定触摸事件支持（移动设备）
        this.elements.resizer.addEventListener('touchstart', this.startResizeTouch.bind(this));
        document.addEventListener('touchmove', this.resizeTouch.bind(this));
        document.addEventListener('touchend', this.stopResize.bind(this));
        
        console.log('面板大小调整功能已初始化');
    },
    
    /**
     * 开始调整大小（鼠标事件）
     * @param {MouseEvent} e - 鼠标事件
     */
    startResize: function(e) {
        e.preventDefault();
        this.state.isDragging = true;
        this.state.initialX = e.clientX;
        this.state.initialToolsPanelWidth = this.elements.toolsPanel.offsetWidth;
        this.state.layoutWidth = this.elements.layout.offsetWidth;
        
        this.elements.resizer.classList.add('dragging');
        document.body.style.cursor = 'col-resize';
        
        // 禁用文本选择，防止拖动时选中文本
        document.body.style.userSelect = 'none';
    },
    
    /**
     * 开始调整大小（触摸事件）
     * @param {TouchEvent} e - 触摸事件
     */
    startResizeTouch: function(e) {
        if (e.touches.length === 1) {
            e.preventDefault();
            this.state.isDragging = true;
            this.state.initialX = e.touches[0].clientX;
            this.state.initialToolsPanelWidth = this.elements.toolsPanel.offsetWidth;
            this.state.layoutWidth = this.elements.layout.offsetWidth;
            
            this.elements.resizer.classList.add('dragging');
        }
    },
    
    /**
     * 调整大小（鼠标事件）
     * @param {MouseEvent} e - 鼠标事件
     */
    resize: function(e) {
        if (!this.state.isDragging) return;
        
        const deltaX = e.clientX - this.state.initialX;
        let newWidth = this.state.initialToolsPanelWidth + deltaX;
        
        // 确保宽度在允许的范围内
        newWidth = Math.max(newWidth, 200); // 最小宽度
        newWidth = Math.min(newWidth, this.state.layoutWidth * 0.4); // 最大宽度
        
        this.elements.toolsPanel.style.width = newWidth + 'px';
    },
    
    /**
     * 调整大小（触摸事件）
     * @param {TouchEvent} e - 触摸事件
     */
    resizeTouch: function(e) {
        if (!this.state.isDragging || e.touches.length !== 1) return;
        
        const deltaX = e.touches[0].clientX - this.state.initialX;
        let newWidth = this.state.initialToolsPanelWidth + deltaX;
        
        // 确保宽度在允许的范围内
        newWidth = Math.max(newWidth, 200); // 最小宽度
        newWidth = Math.min(newWidth, this.state.layoutWidth * 0.4); // 最大宽度
        
        this.elements.toolsPanel.style.width = newWidth + 'px';
    },
    
    /**
     * 停止调整大小
     */
    stopResize: function() {
        if (this.state.isDragging) {
            this.state.isDragging = false;
            this.elements.resizer.classList.remove('dragging');
            document.body.style.cursor = '';
            document.body.style.userSelect = '';
        }
    }
};

// 当文档加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    PanelResizer.init();
}); 