(() => {
  const page = document.body.dataset.page;

  const chartDefaults = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        labels: {
          color: "#cbd5e1",
          font: {
            family: "Inter",
          },
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

    if (revenueChart) {
      new Chart(revenueChart, {
        type: "line",
        data: {
          labels: ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul"],
          datasets: [
            {
              label: "Ingresos",
              data: [82, 95, 88, 118, 132, 141, 148],
              borderColor: "#8b5cf6",
              backgroundColor: "rgba(139, 92, 246, 0.18)",
              fill: true,
              tension: 0.38,
              pointRadius: 3,
              pointBackgroundColor: "#22d3ee",
              borderWidth: 3,
            },
          ],
        },
        options: {
          ...chartDefaults,
          plugins: {
            ...chartDefaults.plugins,
            legend: {
              display: false,
            },
          },
        },
      });
    }

    if (distributionChart) {
      new Chart(distributionChart, {
        type: "doughnut",
        data: {
          labels: ["SUV", "Electrico", "Comercial", "Urbano"],
          datasets: [
            {
              data: [34, 22, 26, 18],
              backgroundColor: ["#8b5cf6", "#3b82f6", "#22d3ee", "#a78bfa"],
              borderWidth: 0,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              position: "bottom",
              labels: {
                color: "#cbd5e1",
                padding: 18,
                font: {
                  family: "Inter",
                },
              },
            },
          },
        },
      });
    }

    if (activityChart) {
      new Chart(activityChart, {
        type: "bar",
        data: {
          labels: ["Lun", "Mar", "Mie", "Jue", "Vie", "Sab", "Dom"],
          datasets: [
            {
              label: "Reservas",
              data: [14, 18, 13, 22, 25, 19, 16],
              backgroundColor: ["#3b82f6", "#3b82f6", "#8b5cf6", "#8b5cf6", "#22d3ee", "#3b82f6", "#8b5cf6"],
              borderRadius: 12,
            },
          ],
        },
        options: chartDefaults,
      });
    }
  }

  if (page === "catalogo") {
    const categoryFilter = document.getElementById("categoryFilter");
    const availabilityFilter = document.getElementById("availabilityFilter");
    const priceFilter = document.getElementById("priceFilter");
    const priceOutput = document.getElementById("priceOutput");
    const resetButton = document.getElementById("resetFilters");
    const vehicles = [...document.querySelectorAll(".vehicle-item")];

    const applyFilters = () => {
      const category = categoryFilter.value;
      const availability = availabilityFilter.value;
      const maxPrice = Number(priceFilter.value);

      if (priceOutput) {
        priceOutput.textContent = `$${maxPrice}/dia`;
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
        priceFilter.value = "250";
        applyFilters();
      });
    }

    applyFilters();
  }
})();
