browser.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'startDownload') {
        const { url, resolution, serverUrl, clientId } = request.payload;

        // Start polling for progress
        let progressInterval = setInterval(async () => {
            try {
                const progRes = await fetch(`${serverUrl}/api/progress/${clientId}`);
                if (progRes.ok) {
                    const progData = await progRes.json();
                    if (progData.progress > 0) {
                        // Send progress updates back to popup if it's still open
                        browser.runtime.sendMessage({
                            action: 'updateProgress',
                            clientId: clientId,
                            progress: progData.progress
                        }).catch(() => {}); // Catch error if popup is closed
                    }
                }
            } catch (e) {
                // Ignore connection errors
            }
        }, 1000);

        // Prepare the download on the server
        fetch(`${serverUrl}/api/prepare`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: url, client_id: clientId, resolution: resolution })
        })
        .then(async (response) => {
            clearInterval(progressInterval);

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || 'Sunucu hatası: ' + response.statusText);
            }

            return response.json();
        })
        .then((data) => {
            // If the backend returns multiple files (e.g. twitter playlist)
            const files = data.files || [{ token: data.token, filename: data.filename }];

            files.forEach((file, index) => {
                setTimeout(() => {
                    const downloadUrl = `${serverUrl}/api/download_file/${file.token}`;
                    browser.downloads.download({
                        url: downloadUrl,
                        filename: file.filename
                    });
                }, index * 1000); // 1-second delay between multiple downloads
            });

            browser.runtime.sendMessage({ action: 'downloadComplete', clientId: clientId }).catch(() => {});

            // Show notification
            browser.notifications.create({
                type: 'basic',
                iconUrl: 'icon.png',
                title: 'İndirme Hazır',
                message: `${files.length} adet video başarıyla hazırlandı ve indiriliyor!`
            });
        })
        .catch((error) => {
            clearInterval(progressInterval);
            browser.runtime.sendMessage({ action: 'downloadError', clientId: clientId, error: error.message }).catch(() => {});
            browser.notifications.create({
                type: 'basic',
                iconUrl: 'icon.png',
                title: 'İndirme Hatası',
                message: error.message
            });
        });

        // Tell caller we are handling this asynchronously
        sendResponse({ status: "started" });
    }
    return true;
});