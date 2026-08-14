// Mobile nav toggle
document.addEventListener("DOMContentLoaded", () => {
  const toggle = document.querySelector(".menu-toggle");
  const catalog = document.querySelector(".catalog");
  if (toggle && catalog) {
    toggle.addEventListener("click", () => catalog.classList.toggle("open"));
    document.addEventListener("click", (e) => {
      if (!catalog.contains(e.target) && !toggle.contains(e.target)) {
        catalog.classList.remove("open");
      }
    });
  }

  // Animate KPI numbers that are plain integers/currency (skips % values, keeps them instant)
  document.querySelectorAll(".kpi-value[data-count]").forEach((el) => {
    const raw = el.dataset.count;
    const prefix = el.dataset.prefix || "";
    const suffix = el.dataset.suffix || "";
    const target = parseFloat(raw.replace(/,/g, ""));
    if (isNaN(target)) return;
    const duration = 900;
    const start = performance.now();
    function tick(now) {
      const progress = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      const value = target * eased;
      el.textContent = prefix + Math.round(value).toLocaleString() + suffix;
      if (progress < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  });
});
