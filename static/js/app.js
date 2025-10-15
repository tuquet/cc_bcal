// static/js/app.js

document.addEventListener('DOMContentLoaded', function () {
    // --- Helper Functions ---
    const qs = (selector, root = document) => root.querySelector(selector);
    const qsa = (selector, root = document) => Array.from(root.querySelectorAll(selector));

    // --- Bulk Actions Logic (from base.html) ---
    const selectAllCheckbox = qs('#select-all');
    const rowCheckboxes = qsa('.row-checkbox');
    const bulkForm = qs('#bulk-form');

    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', function () {
            rowCheckboxes.forEach(cb => {
                cb.checked = this.checked;
            });
        });
    }

    rowCheckboxes.forEach(cb => {
        cb.addEventListener('change', function () {
            const allChecked = rowCheckboxes.every(c => c.checked);
            const anyChecked = rowCheckboxes.some(c => c.checked);
            if (selectAllCheckbox) {
                selectAllCheckbox.checked = allChecked && anyChecked;
            }
        });
    });

    if (bulkForm) {
        bulkForm.addEventListener('submit', function (ev) {
            if (!rowCheckboxes.some(cb => cb.checked)) {
                ev.preventDefault();
                alert('Vui lòng chọn ít nhất một kịch bản trước khi áp dụng thay đổi.');
            }
        });
    }

    // --- Action Dropdown Menu Logic (from index.html) ---
    document.body.addEventListener('click', function(e) {
        // Close all open menus if clicking outside
        if (!e.target.closest('.action-toggle')) {
            qsa('.action-menu').forEach(menu => menu.classList.add('hidden'));
        }

        // Handle toggle click
        if (e.target.classList.contains('action-toggle')) {
            const menu = e.target.nextElementSibling;
            if (menu && menu.classList.contains('action-menu')) {
                // Close other menus before opening a new one
                qsa('.action-menu').forEach(m => {
                    if (m !== menu) m.classList.add('hidden');
                });
                menu.classList.toggle('hidden');
            }
        }
    });

    // --- Open Project Folder in Header (from base.html) ---
    const openProjectFolderBtn = qs('#open-project-folder-btn');
    if (openProjectFolderBtn) {
        openProjectFolderBtn.addEventListener('click', (e) => {
            e.preventDefault();
            const form = qs('#openProjectForm');
            if (form) {
                form.submit();
            }
        });
    }

    // --- Action Item Clicks (Generate Images, Transcribe, etc.) ---
    document.body.addEventListener('click', function(e) {
        if (e.target.classList.contains('action-item')) {
            const action = e.target.getAttribute('data-action');
            const scriptJsonPath = e.target.getAttribute('data-script-json-path');

            if (!action || !scriptJsonPath) return;

            let apiUrl = '';
            if (action === 'generate_images') {
                apiUrl = '/api/generate_images'; // As defined in main.py
            }
            // Add other actions here in the future
            // else if (action === 'transcribe') { ... }

            if (apiUrl) {
                fetch(apiUrl, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ script_json_path: scriptJsonPath })
                })
                .then(res => res.json())
                .then(data => {
                    console.log(`Job started for ${action}:`, data);
                    alert(`Đã bắt đầu tác vụ '${action}' với Job ID: ${data.job_id}`);
                })
                .catch(err => console.error(`Error starting ${action}:`, err));
            }
        }
    });

    // --- Open Individual Script Folder (from script_manager/index.html) ---
    // This logic is now part of the main app.js and will work on any page
    qsa('.open-folder-btn').forEach(button => {
        button.addEventListener('click', function () {
            const scriptId = this.getAttribute('data-script-id');
            const url = this.getAttribute('data-url'); // Get URL from data attribute

            fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ script_id: scriptId }),
            })
            .then(response => response.json())
            .then(data => {
                if (data.ok) {
                    console.log('Opened folder:', data.folder);
                } else {
                    alert('Lỗi: ' + data.error);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Đã xảy ra lỗi khi cố gắng mở thư mục.');
            });
        });
    });
});