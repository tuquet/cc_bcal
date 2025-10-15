// Simple handler for Transcript button
document.addEventListener('DOMContentLoaded', function () {
  function findStatusElement(scriptId) {
    return document.querySelector('.script-gen-status[data-script-id="' + scriptId + '"]');
  }

  async function postJSON(url, body) {
    const resp = await fetch(url, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(body)
    });
    return resp.json();
  }

  async function pollStatus(jobId, statusElem, stopWhenDone=true) {
    let interval = 1500;
    while (true) {
      try {
        const res = await fetch('/api/transcribe/status/' + encodeURIComponent(jobId));
        const data = await res.json();
        statusElem.textContent = data.status || JSON.stringify(data);
        if (data.status === 'completed' || data.status === 'failed' || data.transcript_exists) {
          if (stopWhenDone) return data;
        }
      } catch (e) {
        statusElem.textContent = 'error';
      }
      await new Promise(r => setTimeout(r, interval));
      interval = Math.min(5000, interval + 500);
    }
  }

  // Dropdown toggle
  function closeAllActionMenus() {
    document.querySelectorAll('.action-menu').forEach(function(m) {
      // if menu was moved to body, move it back to its original parent container
      const placeholder = m._placeholder;
      if (placeholder && placeholder.parentNode) {
        placeholder.parentNode.replaceChild(m, placeholder);
        delete m._placeholder;
      }
      m.classList.add('hidden');
      const btn = m.parentElement ? m.parentElement.querySelector('.action-toggle') : null;
      if (btn) btn.setAttribute('aria-expanded', 'false');
    });
  }

  document.querySelectorAll('.action-toggle').forEach(function(toggle) {
    toggle.addEventListener('click', function (ev) {
      ev.stopPropagation();
      const menu = toggle.parentElement.querySelector('.action-menu');
      if (!menu) return;
      const isHidden = menu.classList.contains('hidden');
      // close others
      closeAllActionMenus();
      if (isHidden) {
        // detach menu to body to avoid clipping by overflow
        const btnRect = toggle.getBoundingClientRect();
        // create a placeholder to restore later
        const ph = document.createElement('div');
        ph.style.display = 'none';
        menu.parentNode.replaceChild(ph, menu);
        document.body.appendChild(menu);

        // prepare menu for measurement
        menu.style.position = 'absolute';
        menu.style.visibility = 'hidden';
        menu.classList.remove('hidden');

        // measure
        const mWidth = menu.offsetWidth;
        const mHeight = menu.offsetHeight;

        // compute left so right edges align with button's right
        let left = btnRect.right + window.scrollX - mWidth;
        let top = btnRect.bottom + window.scrollY + 6; // small gap

        // clamp to viewport
        const pad = 8;
        const vw = window.innerWidth;
        const vh = window.innerHeight;
        if (left < pad) left = btnRect.left + window.scrollX;
        if (left + mWidth > vw - pad) left = Math.max(pad, vw - mWidth - pad) + window.scrollX;
        if (top + mHeight > window.scrollY + vh - pad) {
          // open upwards if there's no space below
          top = btnRect.top + window.scrollY - mHeight - 6;
        }

        menu.style.left = left + 'px';
        menu.style.top = top + 'px';
        menu.style.zIndex = 99999;
        menu.style.visibility = 'visible';
        menu._placeholder = ph;
        toggle.setAttribute('aria-expanded', 'true');
      } else {
        // will be closed by closeAllActionMenus
        menu.classList.add('hidden');
        toggle.setAttribute('aria-expanded', 'false');
      }
    });
  });

  // Close menus when clicking outside
  document.addEventListener('click', function () {
    closeAllActionMenus();
  });

  // Delegate action-item clicks
  document.querySelectorAll('.action-item').forEach(function(item) {
    item.addEventListener('click', async function (ev) {
      const action = item.getAttribute('data-action');
      const path = item.getAttribute('data-script-json-path');
      // find the closest status element in the row
      const row = item.closest('tr');
      const statusElem = row ? row.querySelector('.script-gen-status') : null;
      if (!statusElem) return;
      item.disabled = true;
      statusElem.textContent = 'starting...';
      try {
        let resp;
        if (action === 'transcribe') {
          resp = await postJSON('/api/transcribe', { script_json_path: path });
          if (resp.job_id) {
            statusElem.textContent = 'running (' + resp.job_id + ')';
            await pollStatus(resp.job_id, statusElem);
            statusElem.textContent = 'done';
          } else if (resp.error) {
            statusElem.textContent = 'error: ' + resp.error;
          } else {
            statusElem.textContent = JSON.stringify(resp);
          }
        } else if (action === 'generate_images') {
          resp = await postJSON('/api/generate_images', { script_json_path: path });
          if (resp.job_id) {
            statusElem.textContent = 'generating images (' + resp.job_id + ')';
            // optional: poll status if you have /api/generate_images/status/<job_id>
          } else if (resp.error) {
            statusElem.textContent = 'error: ' + resp.error;
          }
        } else if (action === 'generate_capcut') {
          resp = await postJSON('/api/generate_capcut', { script_json_path: path });
          if (resp.job_id) {
            statusElem.textContent = 'generating capcut (' + resp.job_id + ')';
          } else if (resp.error) {
            statusElem.textContent = 'error: ' + resp.error;
          }
        }
        else if (action === 'open_folder') {
          const sid = item.getAttribute('data-script-id');
          // First try the dedicated script-folder API which resolves based on DB/script_data
          try {
            const scriptResp = await postJSON('/api/open_script_folder', { script_id: sid });
            if (scriptResp && scriptResp.ok && scriptResp.folder) {
              // request server to open the folder (server-side open avoids browser file:// restrictions)
              const openResp = await postJSON('/api/open_folder', { folder: scriptResp.folder });
              if (openResp && openResp.ok) {
                statusElem.textContent = 'opened: ' + openResp.folder;
                return;
              } else if (openResp && openResp.error) {
                statusElem.textContent = 'error: ' + openResp.error;
                return;
              }
            }
          } catch (e) {
            // ignore and fallback to previous resolution
          }

          // fallback: call the open_folder endpoint which attempts various resolutions server-side
          resp = await postJSON('/api/open_folder', { script_json_path: path, script_id: sid });
          if (resp.ok) {
            statusElem.textContent = 'opened: ' + resp.folder;
          } else if (resp.error) {
            statusElem.textContent = 'error: ' + resp.error;
            if (resp.tried) {
              statusElem.textContent += ' (tried: ' + resp.tried.join(', ') + ')';
            }
          } else {
            statusElem.textContent = JSON.stringify(resp);
          }
        }
      } catch (e) {
        statusElem.textContent = 'error';
      } finally {
        item.disabled = false;
        // hide menu after action
        const menu = item.closest('.action-menu');
        if (menu) menu.classList.add('hidden');
      }
    });
  });

  // Realtime updates via Server-Sent Events (fallback to polling handled elsewhere)
  if (typeof EventSource !== 'undefined') {
    try {
      const es = new EventSource('/api/jobs/stream');
      es.onmessage = function (ev) {
        try {
          const msg = JSON.parse(ev.data);
          if (!msg || !msg.job_id || !msg.data) return;
          const data = msg.data;
          // find script row by matching BACKGROUND_JOBS[jid]['script'] path
          // Each .script-gen-status has data-script-id attribute set to script.id; we must map job->script id by scanning BACKGROUND_JOBS info
          // Simplify: if job contains 'script' path, find the row with matching data attribute 'data-script-json-path' on action buttons
          if (data.script) {
            const btn = document.querySelector('[data-script-json-path="' + data.script + '"]');
            if (btn) {
              const row = btn.closest('tr');
              const statusElem = row ? row.querySelector('.script-gen-status') : null;
              if (statusElem) {
                // display concise status
                let txt = data.status || JSON.stringify(data);
                if (data.transcript_segments) txt += ' • ' + data.transcript_segments + ' segs';
                statusElem.textContent = txt;
              }
            }
          }
        } catch (e) {
          // ignore parse errors
        }
      };
      es.onerror = function () {
        // close and allow fallback
        try { es.close(); } catch(e){}
      };
    } catch (e) {
      // ignore if EventSource cannot be established
    }
  }
});
