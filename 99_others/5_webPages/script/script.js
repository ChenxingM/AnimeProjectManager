document.addEventListener('DOMContentLoaded', function() {
    // 部分1: 处理下拉菜单逻辑
    // 通用的设置下拉菜单逻辑
    function setupDropdown(dropdownBtnId, dropdownContentId, updateFunction) {
        const dropdownBtn = document.getElementById(dropdownBtnId);
        const dropdownContent = document.getElementById(dropdownContentId);

        dropdownBtn.addEventListener('click', function(event) {
            event.stopPropagation();
            dropdownContent.style.display = dropdownContent.style.display === 'block' ? 'none' : 'block';
        });

        dropdownContent.querySelectorAll('.dropdown-item').forEach(item => {
            item.addEventListener('click', function() {
                updateFunction(item);
                dropdownContent.style.display = 'none';
            });
        });

        window.addEventListener('click', function() {
            dropdownContent.style.display = 'none';
        });
    }

    // 更新第一步的头像和名称
    function updateStep1User(item) {
        const name = item.textContent.trim();
        const avatarSrc = item.querySelector('.avatar').src;
        document.getElementById('selectedName').textContent = name;
        document.getElementById('selectedAvatar').src = avatarSrc;
    }

    // 设置第一步的下拉菜单
    setupDropdown('dropdownBtn', 'dropdownContent', updateStep1User);

    // 第二步的更新函数（如果需要特殊处理）
    function updateStep2Option(item) {
        // 更新第二步的选项逻辑
        document.getElementById('selectedOptionStep2').textContent = item.textContent.trim();
    }

    // 设置第二步的下拉菜单
    setupDropdown('dropdownBtnStep2', 'dropdownContentStep2', updateStep2Option);


    // 部分2: 处理步骤切换逻辑
    const steps = document.querySelectorAll('.step');
    let currentStep = 0;

    function showStep(stepIndex) {
        if (stepIndex >= 0 && stepIndex < steps.length) {
            steps.forEach(step => step.style.display = 'none');
            steps[stepIndex].style.display = 'block';
            currentStep = stepIndex;
        }
    }

    showStep(currentStep);

    document.querySelectorAll('.next-btn').forEach((button, index) => {
        button.addEventListener('click', function() {
            showStep(currentStep + 1);
        });
    });

    document.querySelectorAll('.prev-btn').forEach((button, index) => {
        button.addEventListener('click', function() {
            showStep(currentStep - 1);
        });
    });
});
