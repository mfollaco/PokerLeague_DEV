// Chart.js helper utilities (minimalist defaults, Vegas lives in the shell)

export function destroyChartIfExists(canvasEl) {
  if (!canvasEl) return;
  const existing = canvasEl.__chartInstance;
  if (existing) {
    existing.destroy();
    canvasEl.__chartInstance = null;
  }
}

export function createBarChart(canvasOrId, opts) {
  const {
    labels,
    values,
    colors,          // ✅ NEW
    yLabel,
    valueSuffix = ""
  } = opts;

  const canvas =
    typeof canvasOrId === "string"
      ? document.getElementById(canvasOrId)
      : canvasOrId;

  if (!(canvas instanceof HTMLCanvasElement)) {
    throw new Error(`createBarChart: expected HTMLCanvasElement, got ${Object.prototype.toString.call(canvas)}`);
  }

  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("createBarChart: could not get 2D context");

  // If colors not provided, fall back to a neutral slate for all bars
  const barColors =
    Array.isArray(colors) && colors.length === values.length
      ? colors
      : Array(values.length).fill("#8ea7b6");

  const chart = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [{
        label: yLabel,
        data: values,
        backgroundColor: barColors,   // ✅ THIS is what makes per-bar colors work
        borderWidth: 0,
        borderRadius: 6,
        barThickness: 18,
        maxBarThickness: 22
      }]
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => `${ctx.parsed.x}${valueSuffix}`
          }
        }
      },
      scales: {
        x: {
          suggestedMin: 0,
          suggestedMax: 100,
          ticks: {
            callback: (v) => `${v}${valueSuffix}`
          }
        }
      }
    }
  });

  canvas._chartInstance = chart;
  return chart;
}

export function setActiveBar(chart, index) {
  chart.$activeIndex = index;
  chart.update();
}