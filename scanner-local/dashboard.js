const form = document.querySelector("#scan-form");
const button = document.querySelector("#scan-button");
const status = document.querySelector("#form-status");
const list = document.querySelector("#scan-list");
const detail = document.querySelector("#scan-detail");
const detailTitle = document.querySelector("#detail-title");
const health = document.querySelector("#health");

const escapeHtml = (value) => String(value).replace(/[&<>'"]/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;"
}[character]));

async function request(path, options) {
    const response = await fetch(path, options);
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || `Erreur HTTP ${response.status}`);
    return payload;
}

function formatDate(value) {
    return new Date(value).toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" });
}

function renderDetail(report) {
    detailTitle.textContent = `Scan #${report.id}`;
    document.querySelector("#open-count").textContent = report.results.filter((result) => result.state === "open").length;
    detail.innerHTML = `
        <div class="detail-summary">
            <div><span>Cible</span><strong>${escapeHtml(report.target)}</strong></div>
            <div><span>Ports inspectés</span><strong>${report.scanned_ports}</strong></div>
        </div>
        ${report.results.map((result) => `
            <div class="port-row">
                <span><strong>${result.port}</strong> · ${escapeHtml(result.service)}</span>
                <span class="state-${escapeHtml(result.state)}">${escapeHtml(result.state)}</span>
            </div>
        `).join("")}
    `;
}

async function showDetail(id) {
    try { renderDetail(await request(`/scans/${id}`)); }
    catch (error) { detail.textContent = error.message; }
}

async function refreshScans() {
    const payload = await request("/scans");
    const scans = payload.scans;
    document.querySelector("#scan-count").textContent = scans.length;
    document.querySelector("#last-target").textContent = scans[0]?.target || "-";
    if (!scans.length) {
        list.innerHTML = '<tr><td colspan="5" class="empty">Aucun scan enregistré.</td></tr>';
        return;
    }
    list.innerHTML = scans.map((scan) => `
        <tr>
            <td>#${scan.id}</td>
            <td>${escapeHtml(scan.target)}</td>
            <td>${scan.scanned_ports}</td>
            <td>${formatDate(scan.started_at_utc)}</td>
            <td><button type="button" data-scan-id="${scan.id}">Voir</button></td>
        </tr>
    `).join("");
    list.querySelectorAll("[data-scan-id]").forEach((item) => item.addEventListener("click", () => showDetail(item.dataset.scanId)));
}

async function checkHealth() {
    try {
        await request("/health");
        health.classList.add("ok");
        health.lastElementChild.textContent = "API opérationnelle";
    } catch {
        health.lastElementChild.textContent = "API indisponible";
    }
}

form.addEventListener("submit", async (event) => {
    event.preventDefault();
    button.disabled = true;
    status.className = "form-status";
    status.textContent = "Analyse en cours...";
    try {
        const payload = await request("/scans", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                target: document.querySelector("#target").value.trim(),
                ports: document.querySelector("#ports").value.trim(),
                timeout: Number(document.querySelector("#timeout").value)
            })
        });
        status.textContent = `Scan #${payload.id} enregistré.`;
        await refreshScans();
        await showDetail(payload.id);
    } catch (error) {
        status.className = "form-status error";
        status.textContent = error.message;
    } finally {
        button.disabled = false;
    }
});

document.querySelector("#refresh-button").addEventListener("click", () => refreshScans().catch((error) => { status.textContent = error.message; }));
checkHealth();
refreshScans().catch((error) => { list.innerHTML = `<tr><td colspan="5" class="empty">${escapeHtml(error.message)}</td></tr>`; });
