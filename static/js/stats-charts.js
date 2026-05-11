// --- Color Palette (navy/slate theme) ---
const COLORS = {
  primary: 'rgba(15, 42, 71, 1)',
  primaryLight: 'rgba(15, 42, 71, 0.15)',
  secondary: 'rgba(71, 85, 105, 1)',
  secondaryLight: 'rgba(71, 85, 105, 0.15)',
  accent: 'rgba(245, 158, 11, 1)',
  accentLight: 'rgba(245, 158, 11, 0.15)',
  coral: 'rgba(244, 63, 94, 1)',
  coralLight: 'rgba(244, 63, 94, 0.15)',
  pieColors: [
    '#0F2A47', '#475569', '#94a3b8', '#f59e0b',
    '#10b981', '#f43f5e', '#6366f1', '#14b8a6',
    '#ec4899', '#eab308'
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

// --- Helper: per-clinic colors ---
const CLINIC_COLORS = [
  { border: COLORS.primary, light: COLORS.primaryLight },
  { border: COLORS.accent,  light: COLORS.accentLight },
  { border: COLORS.secondary, light: COLORS.secondaryLight },
  { border: COLORS.coral, light: COLORS.coralLight },
];
function clinicName(id) {
  return (CHART_DATA.clinicNames && CHART_DATA.clinicNames[id]) || ('Clinic ' + id);
}

// ============================================================
// Chart 1: Daily Revenue (Line, per clinic)
// ============================================================
if (CHART_DATA.dailyRevenue) {
  const ctx1 = document.getElementById('chartDailyRevenue').getContext('2d');
  const ds1 = CHART_DATA.dailyRevenue.datasets.map((ds, i) => ({
    label: clinicName(ds.clinic),
    data: ds.values,
    borderColor: CLINIC_COLORS[i % CLINIC_COLORS.length].border,
    backgroundColor: createGradient(ctx1, CLINIC_COLORS[i % CLINIC_COLORS.length].border),
    fill: true,
    tension: 0.35,
    pointRadius: 1,
    pointHoverRadius: 6,
    borderWidth: 2
  }));
  new Chart(ctx1, {
    type: 'line',
    data: { labels: CHART_DATA.dailyRevenue.labels, datasets: ds1 },
    options: {
      responsive: true,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { display: true, position: 'top' },
        tooltip: { callbacks: { label: (ctx) => ctx.dataset.label + ': ' + formatFCFA(ctx.parsed.y) } }
      },
      scales: {
        y: { ticks: { callback: v => v.toLocaleString('fr-FR') }, grid: { color: 'rgba(0,0,0,0.04)' } },
        x: { ticks: { maxTicksLimit: 12, maxRotation: 45 }, grid: { display: false } }
      }
    }
  });
}

// ============================================================
// Chart 2: Monthly Revenue (Line, per clinic)
// ============================================================
if (CHART_DATA.monthlyRevenue) {
  const ctx2 = document.getElementById('chartMonthlyRevenue').getContext('2d');
  const ds2 = CHART_DATA.monthlyRevenue.datasets.map((ds, i) => ({
    label: clinicName(ds.clinic),
    data: ds.values,
    borderColor: CLINIC_COLORS[i % CLINIC_COLORS.length].border,
    backgroundColor: createGradient(ctx2, CLINIC_COLORS[i % CLINIC_COLORS.length].border),
    fill: true,
    tension: 0.35,
    pointRadius: 4,
    pointHoverRadius: 8,
    pointBackgroundColor: '#fff',
    pointBorderColor: CLINIC_COLORS[i % CLINIC_COLORS.length].border,
    pointBorderWidth: 2,
    borderWidth: 2.5
  }));
  new Chart(ctx2, {
    type: 'line',
    data: { labels: CHART_DATA.monthlyRevenue.labels, datasets: ds2 },
    options: {
      responsive: true,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { display: true, position: 'top' },
        tooltip: { callbacks: { label: (ctx) => ctx.dataset.label + ': ' + formatFCFA(ctx.parsed.y) } }
      },
      scales: {
        y: { ticks: { callback: v => v.toLocaleString('fr-FR') }, grid: { color: 'rgba(0,0,0,0.04)' } },
        x: { grid: { display: false } }
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
// Chart 5: New Patients Per Month (Line, per clinic)
// ============================================================
if (CHART_DATA.newPatientsPerMonth) {
  const ctx5 = document.getElementById('chartNewPatients').getContext('2d');
  const ds5 = CHART_DATA.newPatientsPerMonth.datasets.map((ds, i) => ({
    label: clinicName(ds.clinic),
    data: ds.values,
    borderColor: CLINIC_COLORS[i % CLINIC_COLORS.length].border,
    backgroundColor: createGradient(ctx5, CLINIC_COLORS[i % CLINIC_COLORS.length].border),
    fill: true,
    tension: 0.3,
    pointRadius: 5,
    pointHoverRadius: 8,
    pointBackgroundColor: '#fff',
    pointBorderColor: CLINIC_COLORS[i % CLINIC_COLORS.length].border,
    pointBorderWidth: 2,
    borderWidth: 2.5
  }));
  new Chart(ctx5, {
    type: 'line',
    data: { labels: CHART_DATA.newPatientsPerMonth.labels, datasets: ds5 },
    options: {
      responsive: true,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { display: true, position: 'top' },
        tooltip: { callbacks: { label: (ctx) => ctx.dataset.label + ': ' + ctx.parsed.y + ' patients' } }
      },
      scales: {
        y: { beginAtZero: true, ticks: { stepSize: 1 }, grid: { color: 'rgba(0,0,0,0.04)' } },
        x: { ticks: { maxRotation: 45 }, grid: { display: false } }
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
// Chart 7: Monthly Patient Evolution (per clinic, 4 lines)
// ============================================================
if (CHART_DATA.patientEvolution) {
  const ctx7 = document.getElementById('chartEvolution').getContext('2d');
  const evoDatasets = [];
  CHART_DATA.patientEvolution.datasets.forEach((ds, i) => {
    const color = CLINIC_COLORS[i % CLINIC_COLORS.length];
    const name = clinicName(ds.clinic);
    evoDatasets.push({
      label: name + ' — Nouveaux',
      data: ds.newPatients,
      borderColor: color.border,
      backgroundColor: createGradient(ctx7, color.border),
      fill: false,
      tension: 0.3,
      pointRadius: 5,
      pointHoverRadius: 8,
      pointBackgroundColor: '#fff',
      pointBorderColor: color.border,
      pointBorderWidth: 2,
      borderWidth: 2.5
    });
    evoDatasets.push({
      label: name + ' — Récurrents',
      data: ds.recurringPatients,
      borderColor: color.border,
      backgroundColor: 'transparent',
      fill: false,
      tension: 0.3,
      borderDash: [6, 4],
      pointRadius: 4,
      pointHoverRadius: 7,
      pointBackgroundColor: '#fff',
      pointBorderColor: color.border,
      pointBorderWidth: 2,
      borderWidth: 2
    });
  });
  new Chart(ctx7, {
    type: 'line',
    data: { labels: CHART_DATA.patientEvolution.labels, datasets: evoDatasets },
    options: {
      responsive: true,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { position: 'top', labels: { font: { size: 12 } } }
      },
      scales: {
        y: { beginAtZero: true, ticks: { stepSize: 1 }, grid: { color: 'rgba(0,0,0,0.04)' } },
        x: { ticks: { maxRotation: 45 }, grid: { display: false } }
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

// ============================================================
// Chart 10: Top Diagnoses (Stacked Area, per clinic)
// ============================================================
if (CHART_DATA.topDiagnoses) {
  const diagContainer = document.getElementById('diagChartContainer');
  const diagColors = [
    'rgba(15, 42, 71, 0.85)',     // navy
    'rgba(71, 85, 105, 0.85)',    // slate 600
    'rgba(245, 158, 11, 0.85)',   // amber
    'rgba(244, 63, 94, 0.85)',    // rose
    'rgba(16, 185, 129, 0.85)',   // emerald
    'rgba(148, 163, 184, 0.85)',  // slate 400
  ];

  CHART_DATA.topDiagnoses.datasets.forEach((clinicDs, ci) => {
    const div = document.createElement('div');
    div.style.flex = '1';
    div.style.minWidth = '400px';

    const title = document.createElement('h4');
    title.textContent = clinicName(clinicDs.clinic);
    title.style.cssText = 'font-weight:600;font-size:0.95rem;color:#475569;margin-bottom:8px;text-align:center';
    div.appendChild(title);

    const canvas = document.createElement('canvas');
    div.appendChild(canvas);
    diagContainer.appendChild(div);

    const datasets = CHART_DATA.topDiagnoses.diagnoses.map((diag, di) => ({
      label: diag,
      data: clinicDs.series[diag] || [],
      backgroundColor: diagColors[di % diagColors.length],
      borderColor: diagColors[di % diagColors.length].replace('0.85', '1'),
      borderWidth: 1.5,
      fill: true,
      tension: 0.35,
      pointRadius: 0,
      pointHoverRadius: 5,
    }));

    new Chart(canvas, {
      type: 'line',
      data: { labels: CHART_DATA.topDiagnoses.labels, datasets: datasets },
      options: {
        responsive: true,
        interaction: { mode: 'index', intersect: false },
        scales: {
          x: { grid: { display: false }, ticks: { maxRotation: 45 } },
          y: { stacked: true, beginAtZero: true, ticks: { stepSize: 1 }, grid: { color: 'rgba(0,0,0,0.04)' } }
        },
        plugins: {
          legend: { position: 'bottom', labels: { font: { size: 11 }, boxWidth: 12, padding: 10 } },
          tooltip: {
            callbacks: {
              label: (ctx) => ctx.dataset.label + ': ' + ctx.parsed.y + ' cas'
            }
          }
        }
      }
    });
  });
}

// ============================================================
// Chart 9: Activity Heatmap (CSS Grid, per clinic side by side)
// ============================================================
if (CHART_DATA.activityHeatmap && CHART_DATA.activityHeatmap.clinics) {
  const wrapper = document.getElementById('heatmapContainer');
  wrapper.style.display = 'flex';
  wrapper.style.gap = '2rem';
  wrapper.style.flexWrap = 'wrap';

  const dayLabels = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'];
  const hours = [];
  for (let h = 7; h <= 19; h++) hours.push(h);

  // Color palettes per clinic index
  const heatPalettes = [
    { bg: '#f8fafc', from: [248, 250, 252], to: [15, 42, 71] },    // slate-50 → navy
    { bg: '#f1f5f9', from: [241, 245, 249], to: [71, 85, 105] },   // slate-100 → slate-600
  ];

  let clinicIdx = 0;
  for (const [cid, clinicData] of Object.entries(CHART_DATA.activityHeatmap.clinics)) {
    const palette = heatPalettes[clinicIdx % heatPalettes.length];

    // Build lookup & find max
    const lookup = {};
    let maxVal = 0;
    clinicData.data.forEach(d => {
      lookup[d.y + '-' + d.x] = d.v;
      if (d.v > maxVal) maxVal = d.v;
    });

    function heatColor(value) {
      if (value === 0) return palette.bg;
      const t = value / (maxVal || 1);
      const r = Math.round(palette.from[0] + t * (palette.to[0] - palette.from[0]));
      const g = Math.round(palette.from[1] + t * (palette.to[1] - palette.from[1]));
      const b = Math.round(palette.from[2] + t * (palette.to[2] - palette.from[2]));
      return `rgb(${r}, ${g}, ${b})`;
    }

    // Create sub-container
    const section = document.createElement('div');
    section.style.flex = '1';
    section.style.minWidth = '300px';

    const title = document.createElement('h4');
    title.textContent = clinicData.name;
    title.style.cssText = 'font-weight:600;font-size:0.95rem;color:#475569;margin-bottom:8px;text-align:center';
    section.appendChild(title);

    const grid = document.createElement('div');
    grid.style.setProperty('--cols', hours.length);
    grid.classList.add('heatmap-grid');

    // Header
    let html = '<div></div>';
    hours.forEach(h => { html += `<div class="heatmap-col-label">${h}h</div>`; });

    // Rows
    let cellIndex = 0;
    dayLabels.forEach((label, dayIdx) => {
      html += `<div class="heatmap-label">${label}</div>`;
      hours.forEach(h => {
        const val = lookup[dayIdx + '-' + h] || 0;
        const delay = cellIndex * 6;
        html +=
          `<div class="heatmap-cell" style="background:${heatColor(val)};animation-delay:${delay}ms">` +
            `<div class="heatmap-tooltip">${label} ${h}h — ${val} consultation${val !== 1 ? 's' : ''}</div>` +
          `</div>`;
        cellIndex++;
      });
    });

    grid.innerHTML = html;
    section.appendChild(grid);
    wrapper.appendChild(section);
    clinicIdx++;
  }
}
