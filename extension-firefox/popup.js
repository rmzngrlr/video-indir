document.addEventListener('DOMContentLoaded', () => {
    const urlInput = document.getElementById('url');
    const downloadBtn = document.getElementById('downloadBtn');
    const resolutionSelect = document.getElementById('resolution');
    const statusMessage = document.getElementById('statusMessage');
    const progressBar = document.getElementById('progressBar');

    const toggleSettingsBtn = document.getElementById('toggleSettingsBtn');
    const settingsPanel = document.getElementById('settingsPanel');
    const serverUrlInput = document.getElementById('serverUrl');
    const saveSettingsBtn = document.getElementById('saveSettingsBtn');

    function showStatus(msg, type) {
        statusMessage.textContent = msg;
        statusMessage.className = 'status ' + type;
    }

    // Load saved server URL from storage (Using browser.* namespace for Firefox, though chrome.* works too)
    browser.storage.local.get('viddown_server_url').then((result) => {
        if (result.viddown_server_url) {
            serverUrlInput.value = result.viddown_server_url;
        }
    });

    // Auto-fetch the active tab URL
    browser.tabs.query({ active: true, currentWindow: true }).then((tabs) => {
        if (tabs.length > 0 && tabs[0].url) {
            urlInput.value = tabs[0].url;
        }
    });

    // Toggle Settings
    toggleSettingsBtn.addEventListener('click', () => {
        settingsPanel.style.display = settingsPanel.style.display === 'block' ? 'none' : 'block';
    });

    // Save Settings
    saveSettingsBtn.addEventListener('click', () => {
        const newUrl = serverUrlInput.value.trim().replace(/\/$/, ''); // Remove trailing slash
        browser.storage.local.set({ 'viddown_server_url': newUrl }).then(() => {
            showStatus('Sunucu URL kaydedildi!', 'success');
            setTimeout(() => { showStatus('', ''); }, 2000);
            settingsPanel.style.display = 'none';
        });
    });

    // Listen for progress from background script
    browser.runtime.onMessage.addListener((message) => {
        if (message.action === 'updateProgress') {
            progressBar.setAttribute('value', message.progress);
            showStatus(`İndiriliyor: %${message.progress}`, 'info');
        } else if (message.action === 'downloadComplete') {
            progressBar.style.display = 'none';
            showStatus('İndirme tamamlandı! Eklentiyi kapatabilirsiniz.', 'success');
            downloadBtn.disabled = false;
        } else if (message.action === 'downloadError') {
            progressBar.style.display = 'none';
            showStatus(message.error, 'error');
            downloadBtn.disabled = false;
        }
    });

    // Download Button
    downloadBtn.addEventListener('click', async () => {
        const url = urlInput.value.trim();
        const resolution = resolutionSelect.value;
        const serverUrl = serverUrlInput.value.trim().replace(/\/$/, '');

        if (!url) {
            showStatus('Geçerli bir video linki bulunamadı.', 'error');
            return;
        }

        downloadBtn.disabled = true;
        showStatus('Hazırlanıyor... Pencereyi kapatsanız da işlem arka planda devam edecek.', 'info');
        progressBar.style.display = 'block';
        progressBar.removeAttribute('value'); // Indeterminate

        const clientId = Date.now().toString();

        // Send background task
        browser.runtime.sendMessage({
            action: 'startDownload',
            payload: { url, resolution, serverUrl, clientId }
        });
    });
});