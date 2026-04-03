document.addEventListener('DOMContentLoaded', () => {
    const downloadBtn = document.getElementById('downloadBtn');
    const urlInput = document.getElementById('url');
    const startTimeInput = document.getElementById('start_time');
    const endTimeInput = document.getElementById('end_time');
    const statusMessage = document.getElementById('statusMessage');

    // Basic PWA Service Worker Registration
    if ('serviceWorker' in navigator) {
        window.addEventListener('load', () => {
            navigator.serviceWorker.register('/static/sw.js')
                .then(registration => {
                    console.log('ServiceWorker registration successful with scope: ', registration.scope);
                }, err => {
                    console.log('ServiceWorker registration failed: ', err);
                });
        });
    }

    function showStatus(message, type) {
        statusMessage.textContent = message;
        statusMessage.className = 'status ' + type;
    }

    downloadBtn.addEventListener('click', async () => {
        const url = urlInput.value.trim();
        const startTime = startTimeInput.value.trim();
        const endTime = endTimeInput.value.trim();

        if (!url) {
            showStatus('Lütfen bir video linki girin.', 'error');
            return;
        }

        // Disable button & show loading
        downloadBtn.disabled = true;
        showStatus('İşlem başlatılıyor, lütfen bekleyin... (Bu işlem videonun uzunluğuna göre sürebilir)', 'info');

        try {
            const payload = { url: url };
            if (startTime) payload.start_time = startTime;
            if (endTime) payload.end_time = endTime;

            const response = await fetch('/api/prepare', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || 'İndirme sırasında bir hata oluştu.');
            }

            const data = await response.json();
            
            // Trigger download via GET navigation to avoid OOM crashes entirely
            const downloadUrl = `/api/download_file/${data.token}`;
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = downloadUrl;
            a.download = data.filename;

            // iOS PWA fix: Force opening in a new tab so the user doesn't get stuck on the native video player screen
            a.target = '_blank';
            a.rel = 'noopener noreferrer';

            document.body.appendChild(a);
            a.click();
            a.remove();

            showStatus('İndirme tamamlandı! Yeni bir video indirebilirsiniz.', 'success');

            // Clear inputs for convenience
            urlInput.value = '';
            startTimeInput.value = '';
            endTimeInput.value = '';
        } catch (error) {
            console.error('Download error:', error);
            showStatus(error.message, 'error');
        } finally {
            downloadBtn.disabled = false;
        }
    });
});
