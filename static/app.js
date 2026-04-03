document.addEventListener('DOMContentLoaded', () => {
    const downloadBtn = document.getElementById('downloadBtn');
    const confirmDownloadBtn = document.getElementById('confirmDownloadBtn');
    const urlInput = document.getElementById('url');
    const startTimeInput = document.getElementById('start_time');
    const endTimeInput = document.getElementById('end_time');
    const statusMessage = document.getElementById('statusMessage');
    const videoInfoContainer = document.getElementById('videoInfoContainer');
    const videoThumbnail = document.getElementById('videoThumbnail');
    const videoTitle = document.getElementById('videoTitle');
    const showShortcutBtn = document.getElementById('showShortcutBtn');
    const shortcutModal = document.getElementById('shortcutModal');
    const closeModalBtn = document.getElementById('closeModalBtn');
    const apiEndpointUrl = document.getElementById('apiEndpointUrl');

    let originalStartTime = null;
    let originalEndTime = null;

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

    // Reset the UI if the URL changes
    urlInput.addEventListener('input', () => {
        videoInfoContainer.style.display = 'none';
        showStatus('', '');
    });

    // Shortcut Modal Logic
    if (showShortcutBtn && shortcutModal && closeModalBtn && apiEndpointUrl) {
        showShortcutBtn.addEventListener('click', () => {
            // Set the absolute URL dynamically based on where the app is hosted
            apiEndpointUrl.value = window.location.origin + '/api/download';
            shortcutModal.style.display = 'flex';
        });

        closeModalBtn.addEventListener('click', () => {
            shortcutModal.style.display = 'none';
        });

        // Close modal if clicked outside of the content
        window.addEventListener('click', (event) => {
            if (event.target === shortcutModal) {
                shortcutModal.style.display = 'none';
            }
        });
    }

    downloadBtn.addEventListener('click', async () => {
        const url = urlInput.value.trim();

        if (!url) {
            showStatus('Lütfen bir video linki girin.', 'error');
            return;
        }

        // Disable button & show loading
        downloadBtn.disabled = true;
        videoInfoContainer.style.display = 'none';
        showStatus('Video aranıyor, lütfen bekleyin...', 'info');

        try {
            const response = await fetch('/api/info', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ url: url })
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || 'Video bulunamadı veya bir hata oluştu.');
            }

            const data = await response.json();

            videoTitle.textContent = data.title;
            if (data.thumbnail) {
                videoThumbnail.src = data.thumbnail;
                videoThumbnail.style.display = 'block';
            } else {
                videoThumbnail.style.display = 'none';
            }

            // Saniyeyi SS:DD:SS formatına çevirme
            if (data.duration) {
                const totalSeconds = parseInt(data.duration, 10);
                const hours = Math.floor(totalSeconds / 3600);
                const minutes = Math.floor((totalSeconds % 3600) / 60);
                const seconds = totalSeconds % 60;

                const formatTime = (time) => String(time).padStart(2, '0');

                originalStartTime = "00:00:00";
                originalEndTime = `${formatTime(hours)}:${formatTime(minutes)}:${formatTime(seconds)}`;

                startTimeInput.value = originalStartTime;
                endTimeInput.value = originalEndTime;
            } else {
                // Uzunluk okunamadıysa varsayılan boş kalsın
                originalStartTime = "";
                originalEndTime = "";
                startTimeInput.value = "";
                endTimeInput.value = "";
            }

            videoInfoContainer.style.display = 'block';
            showStatus('Video bulundu! İndirmek için Şimdi İndir butonuna tıklayın.', 'success');

        } catch (error) {
            console.error('Info fetch error:', error);
            showStatus(error.message, 'error');
        } finally {
            downloadBtn.disabled = false;
        }
    });

    confirmDownloadBtn.addEventListener('click', async () => {
        const url = urlInput.value.trim();
        const startTime = startTimeInput.value.trim();
        const endTime = endTimeInput.value.trim();

        if (!url) {
            showStatus('Lütfen bir video linki girin.', 'error');
            return;
        }

        confirmDownloadBtn.disabled = true;
        showStatus('İndirme hazırlanıyor, lütfen bekleyin... (Bu işlem videonun uzunluğuna göre sürebilir)', 'info');

        try {
            const payload = { url: url };

            // Only send slice times if the user actually modified them
            // This prevents full-video re-encoding when downloading the entire clip
            if ((startTime && startTime !== originalStartTime) || (endTime && endTime !== originalEndTime)) {
                payload.start_time = startTime;
                payload.end_time = endTime;
            }

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

            showStatus('İndirme tamamlandı! Yeni bir video arayabilirsiniz.', 'success');
            videoInfoContainer.style.display = 'none';

            // Clear inputs for convenience
            urlInput.value = '';
            startTimeInput.value = '';
            endTimeInput.value = '';
        } catch (error) {
            console.error('Download error:', error);
            showStatus(error.message, 'error');
        } finally {
            confirmDownloadBtn.disabled = false;
        }
    });
});
