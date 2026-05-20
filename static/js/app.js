(() => {
  const page = document.body.dataset.page;
  const attachImageFallbacks = () => {
    document.querySelectorAll("img[data-fallback-src]").forEach((img) => {
      img.addEventListener("error", () => {
        const fallback = img.dataset.fallbackSrc;
        if (fallback && img.src !== fallback) {
          img.src = fallback;
          img.removeAttribute("referrerpolicy");
        }
      }, { once: true });
    });
  };

  attachImageFallbacks();

  const chartDefaults = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        labels: {
          color: "#cbd5e1",
          font: { family: "Inter" },
        },
      },
    },
    scales: {
      x: {
        ticks: { color: "#94a3b8" },
        grid: { color: "rgba(255,255,255,0.06)" },
      },
      y: {
        ticks: { color: "#94a3b8" },
        grid: { color: "rgba(255,255,255,0.06)" },
        beginAtZero: true,
      },
    },
  };

  if (page === "dashboard" && window.Chart) {
    const revenueChart = document.getElementById("revenueChart");
    const distributionChart = document.getElementById("distributionChart");
    const activityChart = document.getElementById("activityChart");

    const apiBase = "/api/graficos";

    const emptyData = (label = "Sin datos") => ({
      labels: [],
      datasets: [{ label, data: [], backgroundColor: [], borderColor: [], borderWidth: 0 }],
    });

    const fetchChart = (url, label) => (
      fetch(url)
        .then(r => r.ok ? r.json() : emptyData(label))
        .catch(() => emptyData(label))
    );

    Promise.all([
      fetchChart(`${apiBase}/ingresos-mensuales/`, "Ingresos"),
      fetchChart(`${apiBase}/estado-reservas/`, "Reservas"),
      fetchChart(`${apiBase}/top-vehiculos/`, "Vehiculos"),
    ]).then(([ingresos, estados, topVehiculos]) => {
      if (revenueChart) {
        new Chart(revenueChart, {
          type: "line",
          data: ingresos,
          options: {
            ...chartDefaults,
            plugins: { ...chartDefaults.plugins, legend: { display: false } },
          },
        });
      }

      if (distributionChart) {
        new Chart(distributionChart, {
          type: "doughnut",
          data: estados,
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: {
                position: "bottom",
                labels: {
                  color: "#cbd5e1",
                  padding: 18,
                  font: { family: "Inter" },
                },
              },
            },
          },
        });
      }

      if (activityChart) {
        new Chart(activityChart, {
          type: "bar",
          data: topVehiculos,
          options: {
            ...chartDefaults,
            plugins: {
              ...chartDefaults.plugins,
              legend: { display: true, labels: { color: "#cbd5e1", font: { family: "Inter" } } },
            },
            scales: {
              ...chartDefaults.scales,
              x: { ...chartDefaults.scales.x, ticks: { ...chartDefaults.scales.x.ticks, maxRotation: 45 } },
            },
          },
        });
      }
    }).catch(() => {});
  }

  if (page === "catalogo") {
    const categoryFilter = document.getElementById("categoryFilter");
    const availabilityFilter = document.getElementById("availabilityFilter");
    const priceFilter = document.getElementById("priceFilter");
    const priceOutput = document.getElementById("priceOutput");
    const resetButton = document.getElementById("resetFilters");
    const vehicles = [...document.querySelectorAll(".vehicle-item")];

    if (!categoryFilter || !availabilityFilter || !priceFilter) {
      return;
    }

    const applyFilters = () => {
      const category = categoryFilter.value;
      const availability = availabilityFilter.value;
      const maxPrice = Number(priceFilter.value);

      if (priceOutput) {
        priceOutput.textContent = `$${maxPrice.toLocaleString("es-CO")}/dia`;
      }

      vehicles.forEach((vehicle) => {
        const matchesCategory = category === "all" || vehicle.dataset.category === category;
        const matchesAvailability = availability === "all" || vehicle.dataset.status === availability;
        const matchesPrice = Number(vehicle.dataset.price) <= maxPrice;
        vehicle.classList.toggle("d-none", !(matchesCategory && matchesAvailability && matchesPrice));
      });
    };

    [categoryFilter, availabilityFilter, priceFilter].forEach((element) => {
      if (element) {
        element.addEventListener("input", applyFilters);
        element.addEventListener("change", applyFilters);
      }
    });

    if (resetButton) {
      resetButton.addEventListener("click", () => {
        categoryFilter.value = "all";
        availabilityFilter.value = "all";
        priceFilter.value = priceFilter.max || "0";
        applyFilters();
      });
    }

    applyFilters();
  }
})();
