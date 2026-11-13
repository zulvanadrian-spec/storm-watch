import { renderDeviceStatistics, renderDeviceTable } from './devices.js';

const BACKEND_URL = "http://127.0.0.1:8000";

async function fetchDashboardData() {
    try {
        const response = await fetch(`${BACKEND_URL}/ringkasan`);
        const data = await response.json();

        // Fungsi pencari kartu di dashboard
        const updateCard = (title, value, unit = "") => {
            const cards = document.querySelectorAll('.stat-card');
            cards.forEach(card => {
                const titleEl = card.querySelector('.stat-top span');
                if (titleEl && titleEl.textContent.trim() === title) {
                    const h2 = card.querySelector('h2');
                    if (h2) h2.innerHTML = `${value} ${unit ? `<small>${unit}</small>` : ''}`;
                }
            });
        };

        // Ambil data cuaca dari server (kalau kosong, set 0)
        const cuaca = data.cuaca_terbaru || {};

        // UPDATE KARTU ANGKA SESUAI NAMA DI DASHBOARD
        updateCard("Total Lightning", data.total_event ?? 0);
        updateCard("Total Deteksi Petir", data.total_event ?? 0);
        updateCard("Humidity", cuaca.lembap ?? 0, "%");
        updateCard("Rainfall", cuaca.hujan ?? 0, "mm");
        
        // UBAH INDIKATOR JADI HIJAU (ONLINE)
        document.querySelectorAll('.status-dot').forEach(dot => dot.style.background = '#22c55e');
        
        const topbarStatus = document.querySelector('.live-indicator');
        if (topbarStatus) {
            topbarStatus.innerHTML = `<span class="status-dot" style="background:#22c55e"></span> LIVE DATA`;
            topbarStatus.style.color = '#22c55e';
        }
        
        const sidebarStatus = document.querySelector('.system-info small');
        if (sidebarStatus) sidebarStatus.textContent = "Terhubung ke Backend";

    } catch (error) {
        console.error("Gagal ambil data:", error);
        // Kalau server mati, indikator jadi merah
        document.querySelectorAll('.status-dot').forEach(dot => dot.style.background = '#ef4444');
        const sidebarStatus = document.querySelector('.system-info small');
        if (sidebarStatus) sidebarStatus.textContent = "Gagal koneksi backend";
    }
}

// Tarik data setiap 1 detik
fetchDashboardData();
setInterval(fetchDashboardData, 1000);