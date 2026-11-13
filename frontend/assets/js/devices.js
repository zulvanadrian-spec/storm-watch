
/* =====================================
   UBP STORM WATCH
   DEVICE MONITORING
===================================== */


/*
    Fungsi: renderDeviceStatistics()

    Tujuan:
    Menampilkan ringkasan jumlah perangkat.

    Parameter:
    devices = array perangkat dari backend.
*/

export function renderDeviceStatistics(devices) {

    const total = devices.length;

    const online = devices.filter(
        device => device.connection_status === "online"
    ).length;

    const offline = devices.filter(
        device => device.connection_status === "offline"
    ).length;

    document.getElementById("totalDevices").textContent = total;

    document.getElementById("onlineDevices").textContent = online;

    document.getElementById("offlineDevices").textContent = offline;

}


/*
    Fungsi: renderDeviceTable()

    Tujuan:
    Menampilkan daftar perangkat pada tabel.

    Parameter:
    devices = array perangkat dari backend.
*/

export function renderDeviceTable(devices) {

    const tableBody = document.getElementById("deviceTableBody");

    if (!tableBody) return;

    if (!devices.length) {

        tableBody.innerHTML = `
            <tr>
                <td colspan="5" class="text-center">
                    Belum ada perangkat terdaftar
                </td>
            </tr>
        `;

        return;

    }

    tableBody.innerHTML = devices.map(device => {

        const status = ["online", "offline"].includes(
            device.connection_status
        ) ? device.connection_status : "unknown";

        const sensorStatus = device.sensor_status || "Tidak diketahui";

        return `
            <tr>
                <td>${escapeHTML(device.device_id)}</td>

                <td>${escapeHTML(device.device_name)}</td>

                <td>
                    <span class="device-status ${status}">
                        ${status === "unknown" ? "Unknown" : status}
                    </span>
                </td>

                <td>${escapeHTML(device.last_seen || "—")}</td>

                <td>${escapeHTML(sensorStatus)}</td>
            </tr>
        `;

    }).join("");

}


/*
    Fungsi: escapeHTML()

    Tujuan:
    Mengamankan teks yang ditampilkan pada tabel
    agar karakter HTML tidak dieksekusi sebagai markup.
*/

function escapeHTML(value) {

    const element = document.createElement("div");

    element.textContent = value ?? "";

    return element.innerHTML;

}


/*
    Inisialisasi halaman Device Monitoring.

    Belum mengambil data karena endpoint API
    dari tim backend belum disepakati.
*/

document.addEventListener("DOMContentLoaded", () => {

    console.log("Device Monitoring module berhasil dimuat");

});
