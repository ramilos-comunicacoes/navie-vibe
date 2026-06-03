/**
 * Naviê Vibe - Unified Analytics Tracker
 * Monitora o tempo ativo que o usuário passa na página de forma não-bloqueante.
 * Desconsidera tempo em abas inativas ou quando a janela está minimizada/fora de foco.
 */
(function() {
    // Configurações padrão caso não sejam definidas
    const config = window.NavieConfig || {
        trackUrl: '/analytics/track/',
        category: null,
        itemId: null,
        parentId: null,
        metadata: {}
    };

    let startTime = performance.now();
    let accumulatedTime = 0;
    let isActive = true;

    function pause() {
        if (isActive) {
            const now = performance.now();
            accumulatedTime += (now - startTime) / 1000;
            isActive = false;
        }
    }

    function resume() {
        if (!isActive) {
            startTime = performance.now();
            isActive = true;
        }
    }

    function sendPing() {
        // Se pausado no momento do ping, já capturou o tempo pendente.
        // Se ainda ativo, pausa temporariamente para somar o tempo restante.
        const wasActive = isActive;
        if (wasActive) {
            pause();
        }

        const timeSpent = Math.round(accumulatedTime);
        
        // Apenas envia se houver tempo acumulado relevante (>= 1 segundo)
        if (timeSpent >= 1) {
            // Se for um detalhe de quarto/item, a interação é 'item_detail', senão 'page_view'
            const isDetail = !!(config.itemId || config.quartoId);
            const interactionType = isDetail ? 'item_detail' : 'page_view';

            const payload = {
                url: window.location.href,
                path: window.location.pathname,
                time_spent: timeSpent,
                interaction_type: interactionType,
                category: config.category,
                item_id: config.itemId || config.quartoId || null,
                parent_id: config.parentId || config.hotelId || null,
                metadata: config.metadata || {}
            };

            const url = config.trackUrl;
            const blob = new Blob([JSON.stringify(payload)], { type: 'application/json' });

            // Enviar os dados de forma assíncrona em background
            if (navigator.sendBeacon) {
                navigator.sendBeacon(url, blob);
            } else {
                fetch(url, {
                    method: 'POST',
                    body: blob,
                    headers: { 'Content-Type': 'application/json' },
                    keepalive: true
                }).catch(() => {});
            }

            // Limpa o tempo acumulado transmitido
            accumulatedTime = 0;
        }

        // Se a página continuar aberta, retoma o timer
        if (wasActive) {
            resume();
        }
    }

    // Ouvintes para detectar perda de foco/abas inativas
    window.addEventListener('focus', resume);
    window.addEventListener('blur', pause);

    // Visibility API (abas trocadas, minimizar app, puxar barra de notificações)
    document.addEventListener('visibilitychange', function() {
        if (document.visibilityState === 'visible') {
            resume();
        } else {
            pause();
            sendPing(); // Envia o tempo imediatamente quando sai da aba
        }
    });

    // Eventos de descarregamento da página (unload/fechar aba)
    window.addEventListener('pagehide', function() {
        pause();
        sendPing();
    });
})();
