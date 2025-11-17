let selectedTests = new Set();
let availableTests = [];

async function loadAvailableTests() {
    const result = await apiGet('/api/tests/available');
    if (result.tests) {
        availableTests = result.tests;
        renderTestList();
    }
}

function renderTestList() {
    const listContainer = document.getElementById('test-list');
    if (!listContainer) return;
    if (availableTests.length === 0) {
        listContainer.innerHTML = '<p>No tests available.</p>';
        return;
    }
    listContainer.innerHTML = '';
    availableTests.forEach((test, index) => {
        const testItem = document.createElement('div');
        testItem.className = 'test-item';
        testItem.innerHTML = `
            <input type="checkbox" id="test-${index}" value="${test.id}" onchange="toggleTest('${test.id}')">
            <div class="test-info">
                <div class="test-name">${test.name}</div>
                <div class="test-description">${test.description || ''}</div>
            </div>
        `;
        listContainer.appendChild(testItem);
    });
}

function toggleTest(testId) {
    if (selectedTests.has(testId)) {
        selectedTests.delete(testId);
    } else {
        selectedTests.add(testId);
    }
    updateRunButton();
}

function selectAllTests() {
    document.querySelectorAll('input[id^="test-"]').forEach(cb => {
        cb.checked = true;
        selectedTests.add(cb.value);
    });
    updateRunButton();
}

function deselectAllTests() {
    document.querySelectorAll('input[id^="test-"]').forEach(cb => {
        cb.checked = false;
        selectedTests.delete(cb.value);
    });
    updateRunButton();
}

function updateRunButton() {
    const btn = document.getElementById('run-tests-btn');
    if (btn) {
        btn.disabled = selectedTests.size === 0;
        btn.textContent = selectedTests.size > 0 
            ? `Run ${selectedTests.size} Test${selectedTests.size > 1 ? 's' : ''}`
            : 'Select Tests';
    }
}

async function runSelectedTests() {
    if (selectedTests.size === 0) return;
    const btn = document.getElementById('run-tests-btn');
    const orig = btn.textContent;
    showLoading(btn, 'Starting...');
    const result = await apiPost('/api/tests/run', {
        test_ids: Array.from(selectedTests)
    });
    hideLoading(btn, orig);
    if (result.success) {
        showMessage('test-run-result', 'Tests started!', 'success');
        deselectAllTests();
    } else {
        showMessage('test-run-result', 'Failed', 'error');
    }
}

async function refreshTestList() {
    await loadAvailableTests();
}

document.addEventListener('DOMContentLoaded', () => {
    loadAvailableTests();
    updateRunButton();
});
