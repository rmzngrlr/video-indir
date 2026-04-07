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
    const progressContainer = document.getElementById('progressContainer');
    const downloadProgress = document.getElementById('downloadProgress');
    const progressText = document.getElementById('progressText');
    const playlistContainer = document.getElementById('playlistContainer');
    const playlistItems = document.getElementById('playlistItems');
    const timeInputsContainer = document.getElementById('timeInputsContainer');

    let originalStartTime = null;
    let originalEndTime = null;
    let isPlaylist = false;

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

        // Show indeterminate progress bar
        progressContainer.style.display = 'block';
        downloadProgress.removeAttribute('value'); // makes it indeterminate
        progressText.textContent = 'Aranıyor...';

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

            if (data.videos && data.videos.length > 1) {
                // Multi-video post
                isPlaylist = true;
                if (videoThumbnail) videoThumbnail.style.display = 'none'; // Hide single thumbnail
                if (timeInputsContainer) timeInputsContainer.style.display = 'none'; // Disable trimming for multi-video

                // Render checklist
                playlistItems.innerHTML = '';
                data.videos.forEach(v => {
                    const div = document.createElement('div');
                    div.style.display = 'flex';
                    div.style.alignItems = 'center';
                    div.style.marginBottom = '10px';
                    div.style.gap = '10px';

                    const checkbox = document.createElement('input');
                    checkbox.type = 'checkbox';
                    checkbox.value = v.index;
                    checkbox.checked = true; // Default to all selected
                    checkbox.className = 'playlist-checkbox';
                    checkbox.style.width = '20px';
                    checkbox.style.height = '20px';

                    const thumb = document.createElement('img');
                    thumb.src = v.thumbnail;
                    thumb.style.width = '60px';
                    thumb.style.height = '60px';
                    thumb.style.objectFit = 'cover';
                    thumb.style.borderRadius = '4px';

                    const label = document.createElement('label');
                    label.textContent = v.title;
                    label.style.fontSize = '12px';
                    label.style.flex = '1';

                    div.appendChild(checkbox);
                    if(v.thumbnail) div.appendChild(thumb);
                    div.appendChild(label);
                    playlistItems.appendChild(div);
                });

                if (playlistContainer) playlistContainer.style.display = 'block';

            } else {
                // Single video
                isPlaylist = false;
                if (playlistContainer) playlistContainer.style.display = 'none';
                if (timeInputsContainer) timeInputsContainer.style.display = 'flex';

                if (data.thumbnail && videoThumbnail) {
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
            }

            videoInfoContainer.style.display = 'block';
            showStatus('Video bulundu! İndirmek için Şimdi İndir butonuna tıklayın.', 'success');
            progressContainer.style.display = 'none';

        } catch (error) {
            console.error('Info fetch error:', error);
            showStatus(error.message, 'error');
            progressContainer.style.display = 'none';
        } finally {
            downloadBtn.disabled = false;
        }
    });

    confirmDownloadBtn.addEventListener('click', async () => {
        const url = urlInput.value.trim();
        const startTime = startTimeInput.value.trim();
        const endTime = endTimeInput.value.trim();
        const resolution = document.getElementById('resolution_select').value;

        if (!url) {
            showStatus('Lütfen bir video linki girin.', 'error');
            return;
        }

        confirmDownloadBtn.disabled = true;
        showStatus('İndirme hazırlanıyor, lütfen bekleyin... (Bu işlem videonun uzunluğuna göre sürebilir)', 'info');

        progressContainer.style.display = 'block';
        // Set it back to a determinate state just in case it was indeterminate
        downloadProgress.setAttribute('value', '0');
        progressText.textContent = '%0';

        let progressInterval;
        const clientId = Date.now().toString();

        try {
            const payload = { url: url, client_id: clientId, resolution: resolution };

            if (isPlaylist) {
                // Gather selected indices
                const checkboxes = document.querySelectorAll('.playlist-checkbox');
                const selected = [];
                checkboxes.forEach(cb => {
                    if (cb.checked) selected.push(parseInt(cb.value));
                });

                if (selected.length === 0) {
                    showStatus('Lütfen indirmek için en az bir video seçin.', 'error');
                    confirmDownloadBtn.disabled = false;
                    progressContainer.style.display = 'none';
                    return;
                }
                payload.selected_indices = selected;
            } else {
                // Only send slice times if the user actually modified them
                if ((startTime && startTime !== originalStartTime) || (endTime && endTime !== originalEndTime)) {
                    payload.start_time = startTime;
                    payload.end_time = endTime;
                }
            }

            progressInterval = setInterval(async () => {
                try {
                    const progRes = await fetch(`/api/progress/${clientId}`);
                    if (progRes.ok) {
                        const progData = await progRes.json();
                        if (progData.progress > 0) {
                            downloadProgress.value = progData.progress;
                            progressText.textContent = '%' + progData.progress.toFixed(1);
                        }
                    }
                } catch (e) {
                    console.log('Progress fetch error', e);
                }
            }, 500);

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
            
            clearInterval(progressInterval);
            progressContainer.style.display = 'none';

            const files = data.files || [{token: data.token, filename: data.filename}];

            // Trigger download via GET navigation to avoid OOM crashes entirely
            files.forEach((file, index) => {
                setTimeout(() => {
                    const downloadUrl = `/api/download_file/${file.token}`;
                    const a = document.createElement('a');
                    a.style.display = 'none';
                    a.href = downloadUrl;
                    a.download = file.filename;

                    // iOS PWA fix: Force opening in a new tab so the user doesn't get stuck on the native video player screen
                    a.target = '_blank';
                    a.rel = 'noopener noreferrer';

                    document.body.appendChild(a);
                    a.click();
                    a.remove();
                }, index * 1000); // 1 second delay between downloads to prevent popup blockers
            });

            if (files.length > 1) {
                showStatus(`${files.length} video bulundu ve indiriliyor!`, 'success');
            } else {
                showStatus('İndirme tamamlandı! Yeni bir video arayabilirsiniz.', 'success');
            }
            videoInfoContainer.style.display = 'none';

            // Clear inputs for convenience
            urlInput.value = '';
            startTimeInput.value = '';
            endTimeInput.value = '';
        } catch (error) {
            clearInterval(progressInterval);
            progressContainer.style.display = 'none';
            console.error('Download error:', error);
            showStatus(error.message, 'error');
        } finally {
            confirmDownloadBtn.disabled = false;
        }
    });
});
