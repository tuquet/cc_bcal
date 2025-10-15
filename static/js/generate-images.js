// Client-side helper to trigger image generation for a single script and poll status
(function () {
  function qs(sel, root) { return (root || document).querySelector(sel); }
  function qsa(sel, root) { return Array.from((root || document).querySelectorAll(sel)); }

  async function postJson(url, body) {
    const res = await fetch(url, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body) });
    return res.json();
  }

  async function getJson(url) {
    const res = await fetch(url);
    return res.json();
  }

  function setStatusElem(el, text, extraClass) {
    el.textContent = text;
    el.className = 'inline ml-2 text-sm script-gen-status ' + (extraClass || '');
  }

  async function handleGenerateClick(btn) {
    const path = btn.getAttribute('data-script-json-path');
    const statusEl = btn.parentElement.querySelector('.script-gen-status');
    if (!path) {
      setStatusElem(statusEl, 'Không có file kịch bản', 'text-red-600');
      return;
    }

    setStatusElem(statusEl, 'Đang gửi job...', 'text-slate-600');
    try {
      const payload = { script_json_path: path, headless: false };
      const res = await postJson('/api/generate_images', payload);
      if (res && res.job_id) {
        setStatusElem(statusEl, `job ${res.job_id} queued`, 'text-slate-600');
        pollStatus(res.job_id, statusEl);
      } else if (res && res.error) {
        setStatusElem(statusEl, `Lỗi: ${res.error}`, 'text-red-600');
      } else {
        setStatusElem(statusEl, 'Không rõ phản hồi', 'text-red-600');
      }
    } catch (e) {
      setStatusElem(statusEl, 'Lỗi mạng', 'text-red-600');
    }
  }

  async function handleTranscribeClick(btn) {
    const path = btn.getAttribute('data-script-json-path');
    const statusEl = btn.parentElement.querySelector('.script-gen-status');
    if (!path) { setStatusElem(statusEl, 'Không có file kịch bản', 'text-red-600'); return; }
    setStatusElem(statusEl, 'Đang gửi job transcript...', 'text-slate-600');
    try {
      const res = await postJson('/api/transcribe', { script_json_path: path });
      if (res && res.job_id) { setStatusElem(statusEl, `job ${res.job_id} queued`, 'text-slate-600'); pollStatus(res.job_id, statusEl); }
      else if (res && res.error) setStatusElem(statusEl, `Lỗi: ${res.error}`, 'text-red-600');
      else setStatusElem(statusEl, 'Không rõ phản hồi', 'text-red-600');
    } catch (e) { setStatusElem(statusEl, 'Lỗi mạng', 'text-red-600'); }
  }

  async function handleCapcutClick(btn) {
    const path = btn.getAttribute('data-script-json-path');
    const statusEl = btn.parentElement.querySelector('.script-gen-status');
    if (!path) { setStatusElem(statusEl, 'Không có file kịch bản', 'text-red-600'); return; }
    setStatusElem(statusEl, 'Đang gửi job tạo CapCut...', 'text-slate-600');
    try {
      const res = await postJson('/api/generate_capcut', { script_json_path: path });
      if (res && res.job_id) { setStatusElem(statusEl, `job ${res.job_id} queued`, 'text-slate-600'); pollStatus(res.job_id, statusEl); }
      else if (res && res.error) setStatusElem(statusEl, `Lỗi: ${res.error}`, 'text-red-600');
      else setStatusElem(statusEl, 'Không rõ phản hồi', 'text-red-600');
    } catch (e) { setStatusElem(statusEl, 'Lỗi mạng', 'text-red-600'); }
  }

  async function pollStatus(jobId, statusEl) {
    const url = `/api/generate_images/status/${jobId}`;
    let lastStatus = null;
    const start = Date.now();
    while (true) {
      try {
        const info = await getJson(url);
        if (!info) {
          setStatusElem(statusEl, 'Không tìm thấy job', 'text-red-600');
          return;
        }
        if (info.status !== lastStatus) {
          lastStatus = info.status;
          if (info.status === 'queued') setStatusElem(statusEl, `queued`, 'text-slate-600');
          else if (info.status === 'started') setStatusElem(statusEl, `running`, 'text-slate-600');
          else if (info.status === 'done') {
            if (info.result && info.result.ok) {
              setStatusElem(statusEl, `done - ${info.result.images} ảnh`, 'text-green-600');
            } else {
              setStatusElem(statusEl, `done - lỗi: ${info.result && info.result.error}`, 'text-red-600');
            }
            return;
          } else if (info.status === 'error') {
            setStatusElem(statusEl, `error: ${info.error}`, 'text-red-600');
            return;
          }
        }
      } catch (e) {
        setStatusElem(statusEl, 'Lỗi khi lấy trạng thái', 'text-red-600');
        return;
      }
      // Poll interval
      await new Promise(r => setTimeout(r, 2000));
      // optional overall timeout (5 mins)
      if (Date.now() - start > 5 * 60 * 1000) {
        setStatusElem(statusEl, 'Hết thời gian chờ', 'text-red-600');
        return;
      }
    }
  }

  function init() {
    qsa('.generate-images-btn').forEach(btn => {
      btn.addEventListener('click', function () { handleGenerateClick(btn); });
    });
    qsa('.transcribe-btn').forEach(btn => btn.addEventListener('click', function () { handleTranscribeClick(btn); }));
    qsa('.capcut-btn').forEach(btn => btn.addEventListener('click', function () { handleCapcutClick(btn); }));
    // Hide broken thumbnails and show placeholder text
    qsa('.thumb-img').forEach(img => {
      img.addEventListener('error', function () {
        const wrapper = document.createElement('div');
        wrapper.className = 'text-xs text-slate-500';
        wrapper.textContent = 'Chưa có ảnh';
        img.parentElement.replaceChild(wrapper, img);
      });
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
