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

    // Load saved server URL from storage
    chrome.storage.local.get(['viddown_server_url'], (result) => {
        if (result.viddown_server_url) {
            serverUrlInput.value = result.viddown_server_url;
        }
    });

    // Auto-fetch the active tab URL
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
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
        chrome.storage.local.set({ 'viddown_server_url': newUrl }, () => {
            showStatus('Sunucu URL kaydedildi!', 'success');
            setTimeout(() => { showStatus('', ''); }, 2000);
            settingsPanel.style.display = 'none';
        });
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
        showStatus('Hazırlanıyor... Lütfen bekleyin.', 'info');
        progressBar.style.display = 'block';
        progressBar.removeAttribute('value'); // Indeterminate

        const clientId = Date.now().toString();
        let progressInterval;

        try {
            // Start polling for progress
            progressInterval = setInterval(async () => {
                try {
                    const progRes = await fetch(`${serverUrl}/api/progress/${clientId}`);
                    if (progRes.ok) {
                        const progData = await progRes.json();
                        if (progData.progress > 0) {
                            progressBar.setAttribute('value', progData.progress);
                            showStatus(`İndiriliyor: %${progData.progress}`, 'info');
                        }
                    }
                } catch (e) {
                    // Ignore connection errors on poll
                }
            }, 500);

            // Prepare the download on the server
            const payload = { url: url, client_id: clientId, resolution: resolution };

            const response = await fetch(`${serverUrl}/api/prepare`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || 'Sunucu hatası: ' + response.statusText);
            }

            const data = await response.json();

            clearInterval(progressInterval);
            progressBar.style.display = 'none';
            showStatus('İndirme tamamlandı! Tarayıcınız indiriyor...', 'success');

            // Trigger actual download from the server
            const downloadUrl = `${serverUrl}/api/download_file/${data.token}`;

            // Use Chrome downloads API
            chrome.downloads.download({
                url: downloadUrl,
                filename: data.filename
            });

        } catch (error) {
            clearInterval(progressInterval);
            progressBar.style.display = 'none';
            console.error(error);
            showStatus(error.message, 'error');
        } finally {
            downloadBtn.disabled = false;
        }
    });
});