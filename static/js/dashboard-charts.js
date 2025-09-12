// dashboard-charts.js

// Utility: Create gradient
function createGradient(ctx, color1, color2) {
  const gradient = ctx.createLinearGradient(0, 0, 0, 400);
  gradient.addColorStop(0, color1);
  gradient.addColorStop(1, color2);
  return gradient;
}

// ---------------- Donut Chart: Fees Status ----------------
function renderDonutChart() {
  fetch("/api/charts/fees-status/")
    .then((response) => response.json())
    .then((data) => {
      const ctx = document.getElementById("feesStatusChart").getContext("2d");
      new Chart(ctx, {
        type: "doughnut",
        data: {
          labels: data.labels,
          datasets: [
            {
              data: data.data,
              backgroundColor: ["#C7D2FE","#10B981", "#F59E0B", "#EF4444",],
              borderWidth: 4,
              borderColor: "#fff",
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          cutout: "70%",
          radius: "65%",

          plugins: {
            legend: {
              position: "bottom",
              labels: { padding: 20, font: { size: 14 } },
            },
          },
        },
      });
    })
    .catch((error) => console.error("Error loading fees status chart:", error));
}

function renderBarChart() {
  fetch("/api/charts/students-by-division/")
    .then((response) => response.json())
    .then((data) => {
      const ctx = document
        .getElementById("studentsByDivisionChart")
        .getContext("2d");
      const gradient = createGradient(ctx, "#3B82F6", "#93C5FD");

      new Chart(ctx, {
        type: "bar",
        data: {
          labels: data.labels,
          datasets: [
            {
              label: "Students",
              data: data.data,
              backgroundColor: gradient,
              borderRadius: 8, // rounded bars
              barThickness: 40,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: { backgroundColor: "#111827" },
          },
          scales: {
            x: {
              ticks: { font: { size: 12 } },
              grid: { display: false },
            },
            y: {
              beginAtZero: true,
              ticks: { font: { size: 12 } },
            },
          },
        },
      });
    })
    .catch((error) =>
      console.error("Error loading students by class chart:", error)
    );
}

// ---------------- Line Chart: Monthly Collections ----------------
function renderLineChart() {
  fetch("/api/charts/monthly-collections/")
    .then((response) => response.json())
    .then((data) => {
      const ctx = document
        .getElementById("monthlyCollectionsChart")
        .getContext("2d");
      const gradient = ctx.createLinearGradient(0, 0, 0, 400);
      gradient.addColorStop(0, "rgba(16,185,129,0.4)");
      gradient.addColorStop(1, "rgba(16,185,129,0)");

      new Chart(ctx, {
        type: "line",
        data: {
          labels: data.labels,
          datasets: [
            {
              label: "Collections (Br.)",
              data: data.data,
              borderColor: "#10B981",
              backgroundColor: gradient,
              borderWidth: 3,
              fill: true,
              tension: 0.4, // smooth curves
              pointBackgroundColor: "#10B981",
              pointRadius: 4,
              pointHoverRadius: 6,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: { backgroundColor: "#111827" },
          },
          scales: {
            x: {
              ticks: { font: { size: 12 } },
              grid: { display: false },
            },
            y: {
              beginAtZero: true,
              ticks: { font: { size: 12 } },
            },
          },
        },
      });
    })
    .catch((error) =>
      console.error("Error loading monthly collections chart:", error)
    );
}

function renderRevenueTrendChart() {
  fetch("/api/revenue-trend/")
    .then((response) => response.json())
    .then((data) => {
      const ctx = document.getElementById("revenueTrendChart").getContext("2d");
      const gradient = ctx.createLinearGradient(0, 0, 0, 400);
      gradient.addColorStop(0, "rgba(99,102,241,0.4)");
      gradient.addColorStop(1, "rgba(99,102,241,0)");

      new Chart(ctx, {
        type: "line",
        data: {
          labels: data.labels,
          datasets: [
            {
              label: "Revenue (Br.)",
              data: data.data,
                borderColor: "#A5B4FC",
              backgroundColor: gradient,
              borderWidth: 3,
              borderDash: [5, 5],
              fill: true,
              fill: false,
              tension: 0.4,
              pointBackgroundColor: "#6366F1",
              pointRadius: 4,
              pointHoverRadius: 6,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: { backgroundColor: "#111827" },
          },
          scales: {
            x: { ticks: { font: { size: 12 } }, grid: { display: false } },
            y: { beginAtZero: true, ticks: { font: { size: 12 } } },
          },
        },
      });
    })
    .catch((error) =>
      console.error("Error loading revenue trend chart:", error)
    );
}

function loadSummaryCards() {
  fetch("/api/summary/")
    .then((response) => response.json())
    .then((data) => {
      const revenueEl = document.getElementById("totalRevenue");
      const pendingEl = document.getElementById("pendingInvoices");
      const paidEl = document.getElementById("paidInvoices");
      const balanceEl = document.getElementById("totalUnpaid");
      if (revenueEl) {
        const formattedRevenue = Number(data.total_revenue).toLocaleString(
          "en-US"
        );
        revenueEl.textContent = `ETB ${formattedRevenue}`;
      }

      if (pendingEl) {
        const formattedPending = Number(data.pending_invoices).toLocaleString(
          "en-US"
        );
        pendingEl.textContent = formattedPending;
      }

      if (paidEl) {
        const formattedPaid = Number(data.paid_invoices).toLocaleString(
          "en-US"
        );
        paidEl.textContent = formattedPaid;
      }

      if (balanceEl) {
        const formattedBalance = Number(
          data.total_unpaid
        ).toLocaleString("en-US");
        balanceEl.textContent = `ETB ${formattedBalance}`;
      }
    })
    .catch((error) => console.error("Error loading summary cards:", error));
}

function renderInvoiceStatusChart() {
  const ctx = document.getElementById("invoiceStatusChart").getContext("2d");

  let chart;

  function fetchAndUpdateChart() {
    fetch("/api/invoice-status/")
      .then((response) => response.json())
      .then((data) => {
        if (!chart) {
          chart = new Chart(ctx, {
            type: "doughnut",
            data: {
              labels: data.labels,
              datasets: [
                {
                  data: data.data,
                  backgroundColor: ["#14B8A6", "#F43F5E", "#F59E0B"], // Paid, Unpaid, Opening Balance
                  borderWidth: 4,
                  borderColor: "#fff",
                },
              ],
            },
            options: {
              responsive: true,
              maintainAspectRatio: false,
              animation: {
                animateScale: true,
                duration: 800,
                easing: "easeOutQuart",
              },
              plugins: {
                legend: {
                  position: "bottom",
                  labels: {
                    padding: 20,
                    font: { size: 14 },
                  },
                },
                tooltip: {
                  callbacks: {
                    label: function (context) {
                      const label = context.label || "";
                      const value = context.parsed || 0;
                      return `${label}: ${value} invoices`;
                    },
                  },
                },
              },
            },
          });
        } else {
          chart.data.datasets[0].data = data.data;
          chart.update();
          showToast("📊 Invoice chart updated");
        }
      })
      .catch((error) => {
        console.error("Error loading invoice status chart:", error);
        showToast("⚠️ Failed to update chart", true);
      });
  }

  function showToast(message, isError = false) {
    const toast = document.createElement("div");
    toast.textContent = message;
    toast.className = `fixed bottom-6 right-6 px-4 py-2 rounded-lg shadow-lg text-white text-sm z-50 ${
      isError ? "bg-red-500" : "bg-primary-600"
    }`;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
  }

  // Initial render
  fetchAndUpdateChart();

  // Auto-refresh every 30 seconds
  setInterval(fetchAndUpdateChart, 30000);
}

// ---------------- Initialize Charts ----------------
document.addEventListener("DOMContentLoaded", function () {
  loadSummaryCards();
  if (document.getElementById("feesStatusChart")) renderDonutChart();
  if (document.getElementById("studentsByDivisionChart")) renderBarChart();
  if (document.getElementById("monthlyCollectionsChart")) renderLineChart();
  if (document.getElementById("revenueTrendChart")) renderRevenueTrendChart();
  if (document.getElementById("invoiceStatusChart")) renderInvoiceStatusChart();
});

document.addEventListener("DOMContentLoaded", function () {
  console.log("it is loading");
  const billingCycleSelect = document.getElementById("id_billing_cycle");
  const customMonthsField = document.getElementById("custom-months-field");
  if (billingCycleSelect) {
    function toggleCustomField() {
      if (billingCycleSelect.value === "CUSTOM") {
        customMonthsField.classList.remove("hidden");
      } else {
        customMonthsField.classList.add("hidden");
        console.log("it is remail hidden it did not change");
      }
    }

    toggleCustomField(); // Run on page load
    billingCycleSelect.addEventListener("change", toggleCustomField);
  }
});

document.addEventListener("DOMContentLoaded", () => {
  // Collapsible toggle
  document.querySelectorAll(".collapsible").forEach((btn) => {
    btn.addEventListener("click", () => {
      const content = btn.nextElementSibling;
      content.classList.toggle("hidden");
      const chevron = btn.querySelector(".chevron");
      chevron.textContent = content.classList.contains("hidden") ? "▼" : "▲";
    });
  });

  // Fee total calculation
  const feeCheckboxes = document.querySelectorAll(".fee-checkbox");
  const totalFeeDisplay = document.getElementById("total-fee");
  function updateTotal() {
    let total = 0;
    feeCheckboxes.forEach((cb) => {
      if (cb.checked) total += parseFloat(cb.dataset.amount);
    });
    totalFeeDisplay.textContent = total.toFixed(2);
  }
  feeCheckboxes.forEach((cb) => cb.addEventListener("change", updateTotal));
  updateTotal();

  // Show custom months field
  const billingCycle = document.getElementById("id_billing_cycle");
  const customField = document.getElementById("custom-months-field");
  function toggleCustom() {
    customField.classList.toggle("hidden", billingCycle.value !== "CUSTOM");
  }
  billingCycle.addEventListener("change", toggleCustom);
  toggleCustom();

  // Auto next payment date
  const startMonth = document.getElementById("start-month");
  const nextDate = document.getElementById("next-payment-date");
  billingCycle.addEventListener("change", calcNextDate);
  startMonth.addEventListener("input", calcNextDate);

  function calcNextDate() {
    if (!startMonth.value) {
      nextDate.value = "";
      return;
    }
    const date = new Date(startMonth.value + "-01");
    if (billingCycle.value === "MONTHLY") date.setMonth(date.getMonth() + 1);
    if (billingCycle.value === "TERMLY") date.setMonth(date.getMonth() + 4);
    nextDate.value = date.toLocaleDateString();
  }
});

// universal.js
document.addEventListener("DOMContentLoaded", () => {
  // ========= COLLAPSIBLE SECTIONS =========
  // ========= TOTAL FEES CALCULATION =========
  const feeCheckboxes = document.querySelectorAll(".fee-checkbox");
  const totalFeesEl = document.getElementById("total-fees");
  if (feeCheckboxes.length && totalFeesEl) {
    const updateTotal = () => {
      let total = 0;
      feeCheckboxes.forEach((cb) => {
        if (cb.checked) {
          const text = cb.parentElement.innerText;
          const match = text.match(/(\d+(\.\d+)?)/);
          if (match) total += parseFloat(match[1]);
        }
      });
      totalFeesEl.textContent = `${total.toFixed(2)} birr`;
    };

    feeCheckboxes.forEach((cb) => cb.addEventListener("change", updateTotal));
    updateTotal();
  }

  // ========= CUSTOM MONTHS FIELD TOGGLE =========
  const billingCycleSelect = document.querySelector("#id_billing_cycle");
  const customMonthsWrapper = document.getElementById("custom-months-wrapper");
  if (billingCycleSelect && customMonthsWrapper) {
    const toggleCustomMonths = () => {
      if (billingCycleSelect.value === "CUSTOM") {
        customMonthsWrapper.classList.remove("hidden");
      } else {
        customMonthsWrapper.classList.add("hidden");
      }
    };
    billingCycleSelect.addEventListener("change", toggleCustomMonths);
    toggleCustomMonths();
  }

  // ========= AUTO NEXT PAYMENT DATE (Future Extension) =========
  const startMonthInput = document.querySelector("#id_start_billing_month");
  const cycleInput = document.querySelector("#id_billing_cycle");
  const nextPaymentPreview = document.getElementById("next-payment-preview");

  if (startMonthInput && cycleInput && nextPaymentPreview) {
    const calculateNextPayment = () => {
      const startDate = new Date(startMonthInput.value);
      if (!isNaN(startDate.getTime())) {
        let monthsToAdd = 1;
        if (cycleInput.value === "QUARTERLY") monthsToAdd = 3;
        if (cycleInput.value === "SEMI_ANNUAL") monthsToAdd = 6;
        if (cycleInput.value === "ANNUAL") monthsToAdd = 12;

        const nextDate = new Date(startDate);
        nextDate.setMonth(nextDate.getMonth() + monthsToAdd);

        nextPaymentPreview.textContent = nextDate.toISOString().split("T")[0];
      } else {
        nextPaymentPreview.textContent = "N/A";
      }
    };

    startMonthInput.addEventListener("change", calculateNextPayment);
    cycleInput.addEventListener("change", calculateNextPayment);
  }
});



  document.addEventListener("DOMContentLoaded", function() {
    clickableRow = document.querySelectorAll('.clickable-row')
    if (clickableRow){
        clickableRow.forEach(row => {
            row.addEventListener("click", () => {
                window.location = row.dataset.href;
            });
        });
    }
  });

const checkboxes = document.querySelectorAll('.invoice-checkbox');
  const totalSpan = document.getElementById('selected-total');
  const selectAll = document.getElementById('select-all');
 if (checkboxes){
  function updateTotal() {
    let total = 0;
    checkboxes.forEach(cb => {
      if (cb.checked) total += parseFloat(cb.dataset.amount);
    });
    totalSpan.textContent = total.toFixed(2);
  }

  checkboxes.forEach(cb => cb.addEventListener('change', updateTotal));
  selectAll.addEventListener('change', function() {
    checkboxes.forEach(cb => cb.checked = this.checked);
    updateTotal();
  });
 }
