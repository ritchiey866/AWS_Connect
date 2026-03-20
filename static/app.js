function $(id) {
  return document.getElementById(id);
}

function setLoading(el, show) {
  if (!el) return;
  el.style.display = show ? "block" : "none";
}

function showError(msg) {
  const box = $("errorBox");
  if (!box) return;
  box.textContent = msg;
  box.style.display = msg ? "block" : "none";
}

function escapeHtml(str) {
  return String(str)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function getQueueField(q, field) {
  // AWS responses are typically PascalCase (QueueId, Name, Description).
  return q?.[field] ?? q?.[field.toLowerCase()] ?? "";
}

async function loadQueues() {
  showError("");

  const instanceId = $("instanceId").value.trim();
  const region = $("region").value.trim();

  if (!instanceId) {
    showError("Missing Connect Instance ID. Enter it and try again.");
    return;
  }

  const btn = $("loadQueuesBtn");
  btn.disabled = true;

  const tbody = $("queuesTable").querySelector("tbody");
  tbody.innerHTML = "";

  setLoading($("queueLoading"), true);
  $("queuesEmpty").style.display = "none";

  try {
    const qs = new URLSearchParams();
    qs.set("instance_id", instanceId);
    if (region) qs.set("region", region);

    const res = await fetch(`/api/queues?${qs.toString()}`);
    const data = await res.json();

    if (!res.ok) {
      showError(`${data.error || "Request failed" }\n${data.detail || ""}`.trim());
      return;
    }

    const queues = Array.isArray(data.queues) ? data.queues : [];
    if (queues.length === 0) {
      $("queuesEmpty").style.display = "block";
      return;
    }

    for (const q of queues) {
      const queueId = getQueueField(q, "QueueId");
      const name = getQueueField(q, "Name");
      const description = getQueueField(q, "Description");

      const tr = document.createElement("tr");
      tr.dataset.queueId = queueId;

      tr.innerHTML = `
        <td>${escapeHtml(queueId || q.queueId || "")}</td>
        <td>${escapeHtml(name || "")}</td>
        <td>${escapeHtml(description || q.Description || "")}</td>
      `;

      tr.addEventListener("click", () => loadQueueDetails(instanceId, queueId, region));
      tbody.appendChild(tr);
    }
  } catch (e) {
    showError(`Failed to load queues.\n${e?.message || e}`);
  } finally {
    setLoading($("queueLoading"), false);
    btn.disabled = false;
  }
}

async function loadQueueDetails(instanceId, queueId, region) {
  const detailsBox = $("queueDetails");
  detailsBox.textContent = "";

  if (!queueId) {
    detailsBox.textContent = "No QueueId found in list response for this row.";
    return;
  }

  setLoading($("detailLoading"), true);
  try {
    const qs = new URLSearchParams();
    qs.set("instance_id", instanceId);
    if (region) qs.set("region", region);

    const res = await fetch(`/api/queues/${encodeURIComponent(queueId)}?${qs.toString()}`);
    const data = await res.json();

    if (!res.ok) {
      showError(`${data.error || "Request failed"}\n${data.detail || ""}`.trim());
      detailsBox.textContent = "";
      return;
    }

    // Show the raw response so it's clear what AWS returns.
    const details = data.details ?? {};
    detailsBox.textContent = JSON.stringify(details, null, 2);
  } catch (e) {
    showError(`Failed to load queue details.\n${e?.message || e}`);
  } finally {
    setLoading($("detailLoading"), false);
  }
}

window.addEventListener("DOMContentLoaded", () => {
  $("loadQueuesBtn").addEventListener("click", loadQueues);
});

