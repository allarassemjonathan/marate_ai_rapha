// --- Color Palette (cyan/blue theme) ---
const COLORS = {
  primary: 'rgba(6, 182, 212, 1)',
  primaryLight: 'rgba(6, 182, 212, 0.15)',
  secondary: 'rgba(59, 130, 246, 1)',
  secondaryLight: 'rgba(59, 130, 246, 0.15)',
  accent: 'rgba(249, 115, 22, 1)',
  accentLight: 'rgba(249, 115, 22, 0.15)',
  coral: 'rgba(251, 113, 133, 1)',
  coralLight: 'rgba(251, 113, 133, 0.15)',
  pieColors: [
    '#06b6d4', '#3b82f6', '#8b5cf6', '#ec4899',
    '#f97316', '#eab308', '#22c55e', '#14b8a6',
    '#6366f1', '#f43f5e'
  ]
};

// --- Global Chart.js Defaults ---
Chart.defaults.font.family = "'Inter', 'Segoe UI', sans-serif";
Chart.defaults.animation.duration = 800;
Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(15, 23, 42, 0.85)';
Chart.defaults.plugins.tooltip.padding = 12;
Chart.defaults.plugins.tooltip.cornerRadius = 8;
Chart.defaults.plugins.tooltip.titleFont = { weight: 'bold', size: 13 };
Chart.defaults.plugins.tooltip.bodyFont = { size: 12 };
Chart.defaults.plugins.legend.labels.usePointStyle = true;
Chart.defaults.plugins.legend.labels.padding = 16;
Chart.defaults.scale.grid = { color: 'rgba(0, 0, 0, 0.04)' };

// --- Helper: create gradient fill ---
function createGradient(ctx, color) {
  const gradient = ctx.createLinearGradient(0, 0, 0, ctx.canvas.height);
  gradient.addColorStop(0, color.replace(/[\d.]+\)$/, '0.3)'));
  gradient.addColorStop(1, color.replace(/[\d.]+\)$/, '0.02)'));
  return gradient;
}

// --- Helper: format FCFA ---
function formatFCFA(value) {
  return value.toLocaleString('fr-FR') + ' FCFA';
}

// ============================================================
// Chart 1: Daily Revenue (Line)
// ============================================================
if (CHART_DATA.dailyRevenue) {
  const ctx1 = document.getElementById('chartDailyRevenue').getContext('2d');
  new Chart(ctx1, {
    type: 'line',
    data: {
      labels: CHART_DATA.dailyRevenue.labels,
      datasets: [{
        label: 'Revenu (FCFA)',
        data: CHART_DATA.dailyRevenue.values,
        borderColor: COLORS.primary,
        backgroundColor: createGradient(ctx1, COLORS.primary),
        fill: true,
        tension: 0.35,
        pointRadius: 1,
        pointHoverRadius: 6,
        pointBackgroundColor: COLORS.primary,
        borderWidth: 2
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => formatFCFA(ctx.parsed.y)
          }
        }
      },
      scales: {
        y: {
          ticks: { callback: v => v.toLocaleString('fr-FR') },
          grid: { color: 'rgba(0,0,0,0.04)' }
        },
        x: {
          ticks: { maxTicksLimit: 12, maxRotation: 45 },
          grid: { display: false }
        }
      }
    }
  });
}

// ============================================================
// Chart 2: Monthly Revenue (Line)
// ============================================================
if (CHART_DATA.monthlyRevenue) {
  const ctx2 = document.getElementById('chartMonthlyRevenue').getContext('2d');
  new Chart(ctx2, {
    type: 'line',
    data: {
      labels: CHART_DATA.monthlyRevenue.labels,
      datasets: [{
        label: 'Revenu (FCFA)',
        data: CHART_DATA.monthlyRevenue.values,
        borderColor: COLORS.secondary,
        backgroundColor: createGradient(ctx2, COLORS.secondary),
        fill: true,
        tension: 0.35,
        pointRadius: 4,
        pointHoverRadius: 8,
        pointBackgroundColor: '#fff',
        pointBorderColor: COLORS.secondary,
        pointBorderWidth: 2,
        borderWidth: 2.5
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => formatFCFA(ctx.parsed.y)
          }
        }
      },
      scales: {
        y: {
          ticks: { callback: v => v.toLocaleString('fr-FR') },
          grid: { color: 'rgba(0,0,0,0.04)' }
        },
        x: {
          grid: { display: false }
        }
      }
    }
  });
}

// ============================================================
// Chart 3: Recurring Patients (Line)
// ============================================================
if (CHART_DATA.recurringPatients) {
  const ctx3 = document.getElementById('chartRecurringPatients').getContext('2d');
  new Chart(ctx3, {
    type: 'line',
    data: {
      labels: CHART_DATA.recurringPatients.labels,
      datasets: [{
        label: 'Visites',
        data: CHART_DATA.recurringPatients.values,
        borderColor: COLORS.primary,
        backgroundColor: createGradient(ctx3, COLORS.primary),
        fill: true,
        tension: 0.3,
        pointRadius: 5,
        pointHoverRadius: 8,
        pointBackgroundColor: '#fff',
        pointBorderColor: COLORS.primary,
        pointBorderWidth: 2,
        borderWidth: 2.5
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { display: false }
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: { stepSize: 1 },
          grid: { color: 'rgba(0,0,0,0.04)' }
        },
        x: {
          ticks: { maxRotation: 45 },
          grid: { display: false }
        }
      }
    }
  });
}

// ============================================================
// Chart 4: Neighborhood Distribution (Doughnut)
// ============================================================
if (CHART_DATA.neighborhoodDistribution) {
  new Chart(document.getElementById('chartNeighborhood'), {
    type: 'doughnut',
    data: {
      labels: CHART_DATA.neighborhoodDistribution.labels,
      datasets: [{
        data: CHART_DATA.neighborhoodDistribution.values,
        backgroundColor: COLORS.pieColors,
        borderWidth: 2,
        borderColor: '#ffffff',
        hoverOffset: 8
      }]
    },
    options: {
      responsive: true,
      cutout: '45%',
      plugins: {
        legend: {
          position: 'right',
          labels: { padding: 14, font: { size: 12 } }
        },
        tooltip: {
          callbacks: {
            label: (ctx) => {
              const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
              const pct = ((ctx.raw / total) * 100).toFixed(1);
              return `${ctx.label}: ${ctx.raw} (${pct}%)`;
            }
          }
        }
      }
    }
  });
}

// ============================================================
// Chart 5: New Patients Per Month (Line)
// ============================================================
if (CHART_DATA.newPatientsPerMonth) {
  const ctx5 = document.getElementById('chartNewPatients').getContext('2d');
  new Chart(ctx5, {
    type: 'line',
    data: {
      labels: CHART_DATA.newPatientsPerMonth.labels,
      datasets: [{
        label: 'Nouveaux patients',
        data: CHART_DATA.newPatientsPerMonth.values,
        borderColor: COLORS.secondary,
        backgroundColor: createGradient(ctx5, COLORS.secondary),
        fill: true,
        tension: 0.3,
        pointRadius: 5,
        pointHoverRadius: 8,
        pointBackgroundColor: '#fff',
        pointBorderColor: COLORS.secondary,
        pointBorderWidth: 2,
        borderWidth: 2.5
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => `${ctx.parsed.y} patients`
          }
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: { stepSize: 1 },
          grid: { color: 'rgba(0,0,0,0.04)' }
        },
        x: {
          ticks: { maxRotation: 45 },
          grid: { display: false }
        }
      }
    }
  });
}

// ============================================================
// Chart 6: Patients Per Doctor (Line, switchable by month)
// ============================================================
let doctorChart = null;

function updateDoctorChart(month) {
  if (!CHART_DATA.patientsPerDoctor) return;
  const monthData = CHART_DATA.patientsPerDoctor.byMonth[month];
  if (!monthData) return;

  const canvas = document.getElementById('chartDoctors');
  if (doctorChart) doctorChart.destroy();

  const ctx6 = canvas.getContext('2d');
  doctorChart = new Chart(ctx6, {
    type: 'line',
    data: {
      labels: monthData.labels,
      datasets: [{
        label: 'Patients',
        data: monthData.values,
        borderColor: COLORS.accent,
        backgroundColor: createGradient(ctx6, COLORS.accent),
        fill: true,
        tension: 0.3,
        pointRadius: 5,
        pointHoverRadius: 8,
        pointBackgroundColor: '#fff',
        pointBorderColor: COLORS.accent,
        pointBorderWidth: 2,
        borderWidth: 2.5
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { display: false },
        title: {
          display: true,
          text: 'Mois: ' + month,
          font: { size: 14, weight: '500' },
          color: '#6b7280',
          padding: { bottom: 16 }
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: { stepSize: 1 },
          grid: { color: 'rgba(0,0,0,0.04)' }
        },
        x: {
          grid: { display: false }
        }
      }
    }
  });
}

if (CHART_DATA.patientsPerDoctor) {
  updateDoctorChart(CHART_DATA.patientsPerDoctor.defaultMonth);
}

// ============================================================
// Chart 7: Monthly Patient Evolution (Dual Line)
// ============================================================
if (CHART_DATA.patientEvolution) {
  const ctx7 = document.getElementById('chartEvolution').getContext('2d');
  new Chart(ctx7, {
    type: 'line',
    data: {
      labels: CHART_DATA.patientEvolution.labels,
      datasets: [
        {
          label: 'Nouveaux patients',
          data: CHART_DATA.patientEvolution.newPatients,
          borderColor: COLORS.primary,
          backgroundColor: createGradient(ctx7, COLORS.primary),
          fill: true,
          tension: 0.3,
          pointRadius: 5,
          pointHoverRadius: 8,
          pointBackgroundColor: '#fff',
          pointBorderColor: COLORS.primary,
          pointBorderWidth: 2,
          borderWidth: 2.5
        },
        {
          label: 'Patients récurrents',
          data: CHART_DATA.patientEvolution.recurringPatients,
          borderColor: COLORS.accent,
          backgroundColor: createGradient(ctx7, COLORS.accent),
          fill: true,
          tension: 0.3,
          pointRadius: 5,
          pointHoverRadius: 8,
          pointBackgroundColor: '#fff',
          pointBorderColor: COLORS.accent,
          pointBorderWidth: 2,
          borderWidth: 2.5
        }
      ]
    },
    options: {
      responsive: true,
      interaction: {
        mode: 'index',
        intersect: false
      },
      plugins: {
        legend: {
          position: 'top',
          labels: { font: { size: 13 } }
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: { stepSize: 1 },
          grid: { color: 'rgba(0,0,0,0.04)' }
        },
        x: {
          ticks: { maxRotation: 45 },
          grid: { display: false }
        }
      }
    }
  });
}

// ============================================================
// Chart 8: Data Distribution (Conditional)
// ============================================================
if (CHART_DATA.distribution) {
  const dist = CHART_DATA.distribution;
  const ctx8 = document.getElementById('chartDistribution').getContext('2d');

  if (dist.type === 'histogram') {
    new Chart(ctx8, {
      type: 'line',
      data: {
        labels: dist.labels,
        datasets: [{
          label: dist.columnName,
          data: dist.values,
          borderColor: COLORS.primary,
          backgroundColor: createGradient(ctx8, COLORS.primary),
          fill: true,
          tension: 0.3,
          pointRadius: 2,
          pointHoverRadius: 6,
          pointBackgroundColor: COLORS.primary,
          borderWidth: 2
        }]
      },
      options: {
        responsive: true,
        plugins: {
          legend: { display: false }
        },
        scales: {
          y: {
            beginAtZero: true,
            title: { display: true, text: 'Fréquence' },
            grid: { color: 'rgba(0,0,0,0.04)' }
          },
          x: {
            title: { display: true, text: dist.columnName },
            ticks: { maxRotation: 45, maxTicksLimit: 15 },
            grid: { display: false }
          }
        }
      }
    });
  } else {
    // Line chart for categorical data
    new Chart(ctx8, {
      type: 'line',
      data: {
        labels: dist.labels,
        datasets: [{
          label: "Nombre d'occurrences",
          data: dist.values,
          borderColor: COLORS.secondary,
          backgroundColor: createGradient(ctx8, COLORS.secondary),
          fill: true,
          tension: 0.3,
          pointRadius: 5,
          pointHoverRadius: 8,
          pointBackgroundColor: '#fff',
          pointBorderColor: COLORS.secondary,
          pointBorderWidth: 2,
          borderWidth: 2.5
        }]
      },
      options: {
        responsive: true,
        plugins: {
          legend: { display: false },
          title: {
            display: true,
            text: dist.columnName + ' (Top 20)',
            font: { size: 14, weight: '500' },
            color: '#6b7280'
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            title: { display: true, text: "Nombre d'occurrences" },
            grid: { color: 'rgba(0,0,0,0.04)' }
          },
          x: {
            ticks: { maxRotation: 45 },
            grid: { display: false }
          }
        }
      }
    });
  }
} else if (document.getElementById('chartDistribution')) {
  // No column selected — placeholder
  const ctx = document.getElementById('chartDistribution').getContext('2d');
  ctx.canvas.style.minHeight = '200px';
  ctx.font = "italic 15px 'Inter', sans-serif";
  ctx.fillStyle = '#9ca3af';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText(
    'Sélectionnez une colonne pour afficher la distribution',
    ctx.canvas.width / 2,
    ctx.canvas.height / 2
  );
}
