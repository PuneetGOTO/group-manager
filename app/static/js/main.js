/**
 * 主JavaScript文件
 * 用于处理网站主要交互功能
 */

// 当文档加载完成时执行
document.addEventListener('DOMContentLoaded', function() {
    console.log('main.js 加载成功');
    
    // 初始化Bootstrap工具提示
    initTooltips();
    
    // 初始化表单验证
    initFormValidation();
    
    // 设置全局AJAX错误处理
    setupAjaxErrorHandling();
});

/**
 * 初始化Bootstrap工具提示
 */
function initTooltips() {
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    if (tooltipTriggerList.length > 0) {
        var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
        console.log('工具提示初始化成功');
    }
}

/**
 * 初始化表单验证
 */
function initFormValidation() {
    // 查找所有需要验证的表单
    const forms = document.querySelectorAll('.needs-validation');
    
    if (forms.length > 0) {
        // 为每个表单添加提交事件处理
        Array.from(forms).forEach(form => {
            form.addEventListener('submit', event => {
                if (!form.checkValidity()) {
                    event.preventDefault();
                    event.stopPropagation();
                }
                
                form.classList.add('was-validated');
            }, false);
        });
        console.log('表单验证初始化成功');
    }
}

/**
 * 设置全局AJAX错误处理
 */
function setupAjaxErrorHandling() {
    // 如果使用jQuery AJAX
    if (typeof jQuery !== 'undefined') {
        $(document).ajaxError(function(event, jqxhr, settings, thrownError) {
            console.error('AJAX 请求失败:', thrownError);
            // 可以在这里添加用户通知
        });
        console.log('AJAX错误处理初始化成功');
    }
}

/**
 * 安全获取DOM元素，避免NULL错误
 */
function safeGetElement(id) {
    const element = document.getElementById(id);
    if (!element) {
        console.warn(`找不到元素: ${id}`);
    }
    return element;
}

/**
 * 安全添加事件监听器
 */
function safeAddEventListener(element, event, handler) {
    if (element) {
        element.addEventListener(event, handler);
        return true;
    } else {
        console.warn('无法为空元素添加事件监听器');
        return false;
    }
}

/**
 * 切换密码可见性
 */
function togglePasswordVisibility(inputId, buttonId) {
    const input = document.getElementById(inputId);
    const button = document.getElementById(buttonId);
    
    if (!input || !button) {
        console.error('密码输入字段或按钮未找到');
        return;
    }
    
    if (input.type === 'password') {
        input.type = 'text';
        button.innerHTML = '<i class="fas fa-eye-slash"></i>';
    } else {
        input.type = 'password';
        button.innerHTML = '<i class="fas fa-eye"></i>';
    }
}
