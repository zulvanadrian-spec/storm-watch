
// ========================================
// UBP STORM WATCH
// Dashboard Interaction
// ========================================


// 1. ELEMENT HTML
const sidebar = document.getElementById("sidebar");
const menuToggle = document.getElementById("menuToggle");
const pageTitle = document.getElementById("pageTitle");


// 2. SIDEBAR MOBILE
menuToggle.addEventListener("click", () => {
    sidebar.classList.toggle("show");
});


// 3. NAVIGATION SYSTEM
const navigationLinks = document.querySelectorAll(
    ".sidebar-nav .nav-link"
);

const pages = document.querySelectorAll(".page-section");

navigationLinks.forEach((link) => {

    link.addEventListener("click", (event) => {

        event.preventDefault();

        // Mengambil ID halaman dari href
        const targetId = link.getAttribute("href").substring(1);

        // Mencari halaman berdasarkan ID
        const targetPage = document.getElementById(targetId);

        // Jika halaman belum dibuat, jangan lanjutkan
        if (!targetPage || !targetPage.classList.contains("page-section")) {
            return;
        }

        // Menyembunyikan semua halaman
        pages.forEach((page) => {
            page.classList.add("d-none");
        });

        // Menampilkan halaman yang dipilih
        targetPage.classList.remove("d-none");

        // Menghapus menu aktif sebelumnya
        navigationLinks.forEach((item) => {
            item.classList.remove("active");
        });

        // Mengaktifkan menu yang dipilih
        link.classList.add("active");

        // Mengubah judul topbar
        const selectedMenu = link.querySelector("span").textContent;

        pageTitle.textContent = selectedMenu;

        // Menutup sidebar mobile
        sidebar.classList.remove("show");

        // Kembali ke atas halaman
        window.scrollTo({
            top: 0,
            behavior: "smooth"
        });

    });

});


// 4. CLOCK
function updateClock() {

    const now = new Date();

    const timeElement = document.getElementById("currentTime");
    const dateElement = document.getElementById("currentDate");

    timeElement.textContent = now.toLocaleTimeString("id-ID", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit"
    });

    dateElement.textContent = now.toLocaleDateString("id-ID", {
        weekday: "long",
        day: "numeric",
        month: "long",
        year: "numeric"
    });

}


// 5. UPDATE CLOCK
updateClock();

setInterval(updateClock, 1000);


console.log("UBP Storm Watch Dashboard berhasil dimuat");
