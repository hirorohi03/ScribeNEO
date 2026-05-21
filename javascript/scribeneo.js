function set_active_prompt_text(text, targetTab) {
    const prefix = targetTab === "txt2img" ? 'txt2img' : 'img2img';
    const textarea = gradioApp().querySelector(`#${prefix}_prompt textarea`);
    if (textarea) {
        textarea.value = text;
        updateInput(textarea);
    }
}

function handle_send_to_tab(sourceId, targetTab) {
    const source = gradioApp().querySelector(`#${sourceId} textarea`);
    if (source && source.value) {
        set_active_prompt_text(source.value, targetTab);
        if (targetTab === "txt2img") {
            if (typeof switch_to_txt2img === 'function') switch_to_txt2img();
            else gradioApp().querySelector('#tabs').querySelectorAll('button')[0].click();
        } else {
            if (typeof switch_to_img2img === 'function') switch_to_img2img();
            else gradioApp().querySelector('#tabs').querySelectorAll('button')[1].click();
        }
    }
}

function scribeneo_copy_to_clipboard(id) {
    const selector = `#${id} textarea`;
    const textarea = gradioApp().querySelector(selector);
    if (textarea && textarea.value) {
        navigator.clipboard.writeText(textarea.value).then(() => {
            // Optional feedback
        });
    }
}

function setStopButtonState(resultId, active) {
    const isVision = resultId === 'scribeneo_vision_result';
    const stopBtnId = isVision ? 'scribeneo_stop_vision' : 'scribeneo_stop_enhance';
    const stopBtn = gradioApp().getElementById(stopBtnId);
    if (stopBtn) {
        stopBtn.disabled = !active;
    }
}

function watchForCompletion(resultId) {
    const container = gradioApp().getElementById(resultId);
    if (!container) return;

    let lastValue = '';
    let unchangedPolls = 0;
    let hasReceivedContent = false;

    const interval = setInterval(() => {
        const textarea = container.querySelector('textarea');
        if (!textarea) return;

        const val = textarea.value || '';

        if (val !== lastValue) {
            lastValue = val;
            unchangedPolls = 0;
            if (val && !val.startsWith('[ScribeNEO')) {
                hasReceivedContent = true;
            }
        } else if (hasReceivedContent) {
            unchangedPolls++;
            if (unchangedPolls >= 3) {
                container.classList.remove('scribeneo-active');
                setStopButtonState(resultId, false);
                clearInterval(interval);
            }
        }
    }, 400);

    // Timeout fallback after 2 minutes
    setTimeout(() => {
        container.classList.remove('scribeneo-active');
        setStopButtonState(resultId, false);
        clearInterval(interval);
    }, 120000);
}

function attach_scribeneo_listeners() {
    // Enhancer actions
    const send_txt = gradioApp().getElementById('scribeneo_send_txt2img');
    const send_img = gradioApp().getElementById('scribeneo_send_img2img');
    const copy_enhance = gradioApp().getElementById('scribeneo_copy_enhance');

    if (send_txt) send_txt.onclick = () => handle_send_to_tab('scribeneo_main_result', 'txt2img');
    if (send_img) send_img.onclick = () => handle_send_to_tab('scribeneo_main_result', 'img2img');
    if (copy_enhance) copy_enhance.onclick = () => scribeneo_copy_to_clipboard('scribeneo_main_result');

    // Vision actions
    const vision_send_txt = gradioApp().getElementById('scribeneo_vision_send_txt2img');
    const vision_send_img = gradioApp().getElementById('scribeneo_vision_img2img');
    const copy_vision = gradioApp().getElementById('scribeneo_copy_vision');

    if (vision_send_txt) vision_send_txt.onclick = () => handle_send_to_tab('scribeneo_vision_result', 'txt2img');
    if (vision_send_img) vision_send_img.onclick = () => handle_send_to_tab('scribeneo_vision_result', 'img2img');
    if (copy_vision) copy_vision.onclick = () => scribeneo_copy_to_clipboard('scribeneo_vision_result');

    // Enhance listener
    const enhance_btn = gradioApp().getElementById('scribeneo_main_enhance_btn');
    const enhance_result = gradioApp().getElementById('scribeneo_main_result');
    if (enhance_btn && enhance_result && !enhance_btn.has_listener) {
        enhance_btn.addEventListener('click', () => {
            enhance_result.classList.add('scribeneo-active');
            setStopButtonState('scribeneo_main_result', true);
            watchForCompletion('scribeneo_main_result');
        });
        enhance_btn.has_listener = true;
    }

    // Vision scanner listener
    const scan_btn = gradioApp().getElementById('scribeneo_decode_btn');
    const scan_result = gradioApp().getElementById('scribeneo_vision_result');
    if (scan_btn && scan_result && !scan_btn.has_listener) {
        scan_btn.addEventListener('click', () => {
            scan_result.classList.add('scribeneo-active');
            setStopButtonState('scribeneo_vision_result', true);
            watchForCompletion('scribeneo_vision_result');
        });
        scan_btn.has_listener = true;
    }

    // Stop buttons immediate visual reset and text update
    const stop_enhance = gradioApp().getElementById('scribeneo_stop_enhance');
    if (stop_enhance && enhance_result && !stop_enhance.has_listener) {
        stop_enhance.disabled = true;
        stop_enhance.addEventListener('click', (e) => {
            if (stop_enhance.disabled) {
                e.preventDefault();
                e.stopPropagation();
                return;
            }
            enhance_result.classList.remove('scribeneo-active');
            setStopButtonState('scribeneo_main_result', false);
            const textarea = enhance_result.querySelector('textarea');
            if (textarea) {
                textarea.value = "[Request cancelled]";
                updateInput(textarea);
            }
        });
        stop_enhance.has_listener = true;
    } else if (stop_enhance) {
        // Ensure disabled state is set even if listener exists
        stop_enhance.disabled = !enhance_result.classList.contains('scribeneo-active');
    }

    const stop_vision = gradioApp().getElementById('scribeneo_stop_vision');
    if (stop_vision && scan_result && !stop_vision.has_listener) {
        stop_vision.disabled = true;
        stop_vision.addEventListener('click', (e) => {
            if (stop_vision.disabled) {
                e.preventDefault();
                e.stopPropagation();
                return;
            }
            scan_result.classList.remove('scribeneo-active');
            setStopButtonState('scribeneo_vision_result', false);
            const textarea = scan_result.querySelector('textarea');
            if (textarea) {
                textarea.value = "[Request cancelled]";
                updateInput(textarea);
            }
        });
        stop_vision.has_listener = true;
    } else if (stop_vision) {
        // Ensure disabled state is set even if listener exists
        stop_vision.disabled = !scan_result.classList.contains('scribeneo-active');
    }
}

// Watch for dynamic WebUI tab changes
onUiTabChange(() => {
    attach_scribeneo_listeners();
});

// Initialization
onUiLoaded(() => {
    attach_scribeneo_listeners();
});
